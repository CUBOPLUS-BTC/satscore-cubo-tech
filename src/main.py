import json
import re
import socketserver
from http.server import BaseHTTPRequestHandler

from app.database import init_db
from app.config import settings
from app.scoring.engine import ScoringEngine
from app.services.price_aggregator import PriceAggregator
from app.auth.routes import handle_challenge, handle_verify, handle_me
from app.simulator.routes import handle_volatility, handle_conversion
from app.remittance.routes import handle_compare, handle_fees

_engine = ScoringEngine()
_price_aggregator = PriceAggregator(settings.COINGECKO_API_KEY)

ROUTES = [
    ("GET", re.compile(r"^/$"), "_root"),
    ("GET", re.compile(r"^/health$"), "_health"),
    ("GET", re.compile(r"^/price$"), "_price"),
    ("GET", re.compile(r"^/score/(?P<address>[^/]+)$"), "_score"),
    ("POST", re.compile(r"^/auth/challenge$"), "_auth_challenge"),
    ("POST", re.compile(r"^/auth/verify$"), "_auth_verify"),
    ("GET", re.compile(r"^/auth/me$"), "_auth_me"),
    ("POST", re.compile(r"^/simulate/volatility$"), "_sim_volatility"),
    ("POST", re.compile(r"^/simulate/conversion$"), "_sim_conversion"),
    ("POST", re.compile(r"^/remittance/compare$"), "_remittance_compare"),
    ("GET", re.compile(r"^/remittance/fees$"), "_remittance_fees"),
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
        path = self.path.split("?")[0]
        for method, pattern, handler_name in ROUTES:
            if self.command != method:
                continue
            m = pattern.match(path)
            if m:
                handler_fn = getattr(self, handler_name)
                body = self._read_body()
                data, status = handler_fn(m.groupdict(), body)
                self._send_json(data, status)
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

    def _root(self, params: dict, body: dict) -> tuple[dict, int]:
        return {"message": "Vulk API - Don't trust, verify"}, 200

    def _health(self, params: dict, body: dict) -> tuple[dict, int]:
        return {"status": "ok", "service": "vulk-backend"}, 200

    def _price(self, params: dict, body: dict) -> tuple[dict, int]:
        try:
            return _price_aggregator.get_verified_price(), 200
        except Exception as e:
            return {
                "error": str(e),
                "price_usd": 0,
                "sources_count": 0,
                "has_warning": True,
            }, 200

    def _score(self, params: dict, body: dict) -> tuple[dict, int]:
        address = params.get("address", "")
        try:
            result = _engine.calculate_score(address)
            return {
                "total_score": result.total_score,
                "rank": result.rank,
                "address": result.address,
                "breakdown": result.breakdown,
                "recommendations": result.recommendations,
            }, 200
        except Exception as e:
            return {"detail": str(e)}, 500

    def _auth_challenge(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_challenge(body)

    def _auth_verify(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_verify(body)

    def _auth_me(self, params: dict, body: dict) -> tuple[dict, int]:
        auth = self.headers.get("Authorization", "")
        return handle_me(auth)

    def _sim_volatility(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_volatility(body)

    def _sim_conversion(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_conversion(body)

    def _remittance_compare(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_compare(body)

    def _remittance_fees(self, params: dict, body: dict) -> tuple[dict, int]:
        return handle_fees(body)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    init_db()
    port = 8000
    print(f"[Vulk] Starting server on http://0.0.0.0:{port}")
    with ThreadedTCPServer(("", port), Handler) as server:
        server.serve_forever()
