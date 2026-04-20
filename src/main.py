import json
import re
import socketserver
import urllib.parse
from http.server import BaseHTTPRequestHandler

from app.database import init_db
from app.config import settings
from app.services.price_aggregator import PriceAggregator
from app.auth.routes import (
    handle_challenge,
    handle_verify,
    handle_me,
    handle_lnurl_create,
    handle_lnurl_callback,
    handle_lnurl_status,
)
from app.remittance.routes import handle_compare, handle_fees
from app.pension.routes import handle_projection as handle_pension_projection
from app.network.routes import handle_network_status
from app.savings.routes import (
    handle_projection,
    handle_create_goal,
    handle_record_deposit,
    handle_progress as handle_savings_progress,
)
from app.alerts.monitor import AlertMonitor
from app.alerts.routes import handle_alerts, handle_alert_status
from app.gamification.routes import handle_achievements
from app.gamification.achievements import AchievementEngine
from app.liquid.routes import (
    handle_network_status as handle_liquid_status,
    handle_asset_info as handle_liquid_asset,
    handle_lbtc,
    handle_usdt,
)

_achievement_engine = AchievementEngine()
_price_aggregator = PriceAggregator(settings.COINGECKO_API_KEY)
_monitor = AlertMonitor(_price_aggregator)

ROUTES = [
    ("GET", re.compile(r"^/$"), "_root"),
    ("GET", re.compile(r"^/health$"), "_health"),
    ("GET", re.compile(r"^/price$"), "_price"),
    ("POST", re.compile(r"^/auth/challenge$"), "_auth_challenge"),
    ("POST", re.compile(r"^/auth/verify$"), "_auth_verify"),
    ("GET", re.compile(r"^/auth/me$"), "_auth_me"),
    ("POST", re.compile(r"^/auth/lnurl$"), "_auth_lnurl_create"),
    ("GET", re.compile(r"^/auth/lnurl-callback$"), "_auth_lnurl_callback"),
    ("GET", re.compile(r"^/auth/lnurl-status$"), "_auth_lnurl_status"),
    ("POST", re.compile(r"^/remittance/compare$"), "_remittance_compare"),
    ("GET", re.compile(r"^/remittance/fees$"), "_remittance_fees"),
    ("POST", re.compile(r"^/savings/project$"), "_savings_project"),
    ("POST", re.compile(r"^/savings/goal$"), "_savings_goal"),
    ("POST", re.compile(r"^/savings/deposit$"), "_savings_deposit"),
    ("GET", re.compile(r"^/savings/progress$"), "_savings_progress"),
    ("GET", re.compile(r"^/achievements$"), "_achievements"),
    ("GET", re.compile(r"^/alerts$"), "_alerts"),
    ("GET", re.compile(r"^/alerts/status$"), "_alert_status"),
    ("POST", re.compile(r"^/pension/projection$"), "_pension_projection"),
    ("GET", re.compile(r"^/network/status$"), "_network_status"),
    ("GET", re.compile(r"^/liquid/status$"), "_liquid_status"),
    ("GET", re.compile(r"^/liquid/lbtc$"), "_liquid_lbtc"),
    ("GET", re.compile(r"^/liquid/usdt$"), "_liquid_usdt"),
    ("GET", re.compile(r"^/liquid/asset/(?P<asset_id>[0-9a-f]{64})$"), "_liquid_asset"),
]


class Handler(BaseHTTPRequestHandler):
    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode())
        except Exception:
            return {}

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _add_cors_headers(self) -> None:
        origins = settings.CORS_ORIGINS
        origin_header = self.headers.get("Origin", "")
        if origin_header in origins or "*" in origins:
            self.send_header("Access-Control-Allow-Origin", origin_header or "*")
        else:
            self.send_header(
                "Access-Control-Allow-Origin", origins[0] if origins else "*"
            )
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _dispatch(self) -> None:
        import time

        raw_path = self.path
        path = raw_path.split("?")[0]
        query_string = raw_path.split("?", 1)[1] if "?" in raw_path else ""
        query = dict(urllib.parse.parse_qsl(query_string))

        for method, pattern, handler_name in ROUTES:
            if self.command != method:
                continue
            m = pattern.match(path)
            if m:
                handler_fn = getattr(self, handler_name)
                body = self._read_body()
                start = time.time()
                data, status = handler_fn(m.groupdict(), body, query)
                elapsed = (time.time() - start) * 1000
                self._send_json(data, status)
                print(
                    f"[{self.address_string()}] {self.command} {path} {status} {elapsed:.1f}ms"
                )
                return
        self._send_json({"detail": "Not found"}, 404)

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._add_cors_headers()
        self.end_headers()

    def log_message(self, format, *args) -> None:
        print(f"[{self.address_string()}] {format % args}")

    def _root(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return {"message": "Magma API - Don't trust, verify"}, 200

    def _health(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return {"status": "ok", "service": "magma-backend"}, 200

    def _price(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        try:
            return _price_aggregator.get_verified_price(), 200
        except Exception as e:
            return {
                "error": str(e),
                "price_usd": 0,
                "sources_count": 0,
                "has_warning": True,
            }, 200

    def _auth_challenge(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_challenge(body)

    def _auth_verify(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_verify(body)

    def _auth_me(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        return handle_me(auth, url=url, method=self.command)

    def _remittance_compare(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        result = handle_compare(body)
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, me_status = handle_me(auth_header, url=url, method=self.command)
        if me_status == 200:
            _achievement_engine.check_and_award(me_data["pubkey"], "remittance", {})
        return result

    def _remittance_fees(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_fees(body)

    def _auth_lnurl_create(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lnurl_create(body)

    def _auth_lnurl_callback(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lnurl_callback(query)

    def _auth_lnurl_status(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lnurl_status(query)

    def _savings_project(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_projection(body)

    def _savings_goal(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_create_goal(body, me_data["pubkey"])

    def _savings_deposit(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        result = handle_record_deposit(body, me_data["pubkey"])
        if result[1] == 200:
            progress = handle_savings_progress(me_data["pubkey"])
            if progress[1] == 200:
                _achievement_engine.check_and_award(
                    me_data["pubkey"], "deposit", progress[0]
                )
        return result

    def _savings_progress(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_savings_progress(me_data["pubkey"])

    def _achievements(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_achievements(me_data["pubkey"])

    def _alerts(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_alerts(_monitor, query)

    def _alert_status(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_alert_status(_monitor)

    def _pension_projection(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_pension_projection(body)

    def _network_status(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_network_status(body)

    def _liquid_status(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_liquid_status(body)

    def _liquid_lbtc(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lbtc(body)

    def _liquid_usdt(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_usdt(body)

    def _liquid_asset(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_liquid_asset(body, params.get("asset_id", ""))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    init_db()
    _monitor.start()
    port = 8000
    print(f"[Magma] Starting server on http://0.0.0.0:{port}")
    with ThreadedTCPServer(("", port), Handler) as server:
        server.serve_forever()
