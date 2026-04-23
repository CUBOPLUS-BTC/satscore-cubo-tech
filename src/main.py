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
from app.scoring.routes import handle_score, handle_score_summary
from app.preferences.routes import (
    handle_get_preferences,
    handle_update_preferences,
    handle_add_price_alert,
    handle_remove_price_alert,
)
from app.lightning.routes import (
    handle_lightning_overview,
    handle_lightning_compare,
    handle_lightning_recommend,
)
from app.analytics.routes import (
    handle_user_analytics,
    handle_platform_stats,
    handle_dca_performance,
    handle_leaderboard,
)
from app.export.routes import (
    handle_export_data,
    handle_export_deposits,
    handle_export_report,
)
from app.webhooks.routes import (
    handle_webhook_subscribe,
    handle_webhook_unsubscribe,
    handle_webhook_list,
    handle_webhook_test,
)
from app.docs import handle_openapi_json, handle_swagger_ui
from app.ratelimit import RateLimiter, MemoryStorage
from app.webhooks.manager import WebhookManager
from app.webhooks.dispatcher import WebhookDispatcher
from app.analytics.engine import AnalyticsEngine
from app.scheduler.tasks import build_default_scheduler
from app.logging_config import setup_logging, StructuredLogger
from app.market.routes import (
    handle_market_overview,
    handle_price_history,
    handle_market_signals,
    handle_market_sentiment,
    handle_halving_info,
    handle_fair_value,
)
from app.portfolio.routes import (
    handle_portfolio_holdings,
    handle_portfolio_summary,
    handle_portfolio_transaction,
    handle_portfolio_performance,
    handle_portfolio_optimize,
    handle_portfolio_risk,
)
from app.simulation.routes import (
    handle_simulate_portfolio,
    handle_simulate_dca,
    handle_backtest,
    handle_scenario_analysis,
    handle_monte_carlo,
    handle_retirement_sim,
)
from app.admin.routes import (
    handle_admin_overview,
    handle_admin_users,
    handle_admin_user_detail,
    handle_admin_system,
    handle_admin_diagnostics,
    handle_admin_user_ban,
    handle_admin_config,
    handle_admin_maintenance,
)
from app.healthcheck.routes import (
    handle_health_detailed,
    handle_health_liveness,
    handle_health_readiness,
)
from app.education.routes import (
    handle_glossary,
    handle_lesson_list,
    handle_lesson_detail,
    handle_quiz,
)
from app.notifications.routes import (
    handle_notification_templates,
    handle_notification_preview,
    handle_notification_render,
)
from app.stats.routes import (
    handle_stats_analyze,
    handle_stats_correlation,
    handle_stats_regression,
)

_achievement_engine = AchievementEngine()
_price_aggregator = PriceAggregator(settings.COINGECKO_API_KEY)
_monitor = AlertMonitor(_price_aggregator)
_rate_limit_storage = MemoryStorage()
_rate_limiter = RateLimiter(_rate_limit_storage)
_webhook_manager = WebhookManager()
_webhook_dispatcher = WebhookDispatcher(_webhook_manager)
_analytics_engine = AnalyticsEngine()
_logger = StructuredLogger("magma.server")

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
    # Scoring
    ("POST", re.compile(r"^/score$"),          "_score"),
    ("GET",  re.compile(r"^/score/summary$"),  "_score_summary"),
    # Preferences
    ("GET",    re.compile(r"^/preferences$"),         "_preferences_get"),
    ("PATCH",  re.compile(r"^/preferences$"),         "_preferences_update"),
    ("POST",   re.compile(r"^/preferences/alerts$"),  "_preferences_add_alert"),
    ("DELETE", re.compile(r"^/preferences/alerts$"),  "_preferences_remove_alert"),
    # Lightning
    ("GET",  re.compile(r"^/lightning/overview$"),   "_lightning_overview"),
    ("GET",  re.compile(r"^/lightning/compare$"),    "_lightning_compare"),
    ("POST", re.compile(r"^/lightning/recommend$"),  "_lightning_recommend"),
    # Analytics
    ("GET",  re.compile(r"^/analytics/user$"),       "_analytics_user"),
    ("GET",  re.compile(r"^/analytics/platform$"),   "_analytics_platform"),
    ("GET",  re.compile(r"^/analytics/dca$"),        "_analytics_dca"),
    ("GET",  re.compile(r"^/analytics/leaderboard$"), "_analytics_leaderboard"),
    # Export
    ("POST", re.compile(r"^/export/data$"),          "_export_data"),
    ("GET",  re.compile(r"^/export/deposits$"),      "_export_deposits"),
    ("POST", re.compile(r"^/export/report$"),        "_export_report"),
    # Webhooks
    ("POST",   re.compile(r"^/webhooks/subscribe$"),   "_webhook_subscribe"),
    ("DELETE", re.compile(r"^/webhooks/unsubscribe$"), "_webhook_unsubscribe"),
    ("GET",    re.compile(r"^/webhooks$"),              "_webhook_list"),
    ("POST",   re.compile(r"^/webhooks/test$"),        "_webhook_test"),
    # Docs
    ("GET", re.compile(r"^/docs/openapi\.json$"), "_docs_openapi"),
    ("GET", re.compile(r"^/docs$"),               "_docs_swagger"),
    # Market
    ("GET",  re.compile(r"^/market/overview$"),    "_market_overview"),
    ("GET",  re.compile(r"^/market/history$"),     "_market_history"),
    ("POST", re.compile(r"^/market/signals$"),     "_market_signals"),
    ("GET",  re.compile(r"^/market/sentiment$"),   "_market_sentiment"),
    ("GET",  re.compile(r"^/market/halving$"),     "_market_halving"),
    ("GET",  re.compile(r"^/market/fair-value$"),  "_market_fair_value"),
    # Portfolio
    ("GET",  re.compile(r"^/portfolio/holdings$"),     "_portfolio_holdings"),
    ("GET",  re.compile(r"^/portfolio/summary$"),      "_portfolio_summary"),
    ("POST", re.compile(r"^/portfolio/transaction$"),  "_portfolio_transaction"),
    ("GET",  re.compile(r"^/portfolio/performance$"),  "_portfolio_performance"),
    ("POST", re.compile(r"^/portfolio/optimize$"),     "_portfolio_optimize"),
    ("GET",  re.compile(r"^/portfolio/risk$"),         "_portfolio_risk"),
    # Simulation
    ("POST", re.compile(r"^/simulation/portfolio$"),   "_sim_portfolio"),
    ("POST", re.compile(r"^/simulation/dca$"),         "_sim_dca"),
    ("POST", re.compile(r"^/simulation/backtest$"),    "_sim_backtest"),
    ("POST", re.compile(r"^/simulation/scenario$"),    "_sim_scenario"),
    ("POST", re.compile(r"^/simulation/montecarlo$"),  "_sim_montecarlo"),
    ("POST", re.compile(r"^/simulation/retirement$"),  "_sim_retirement"),
    # Admin
    ("GET",  re.compile(r"^/admin/overview$"),      "_admin_overview"),
    ("GET",  re.compile(r"^/admin/users$"),         "_admin_users"),
    ("GET",  re.compile(r"^/admin/user$"),          "_admin_user_detail"),
    ("GET",  re.compile(r"^/admin/system$"),        "_admin_system"),
    ("GET",  re.compile(r"^/admin/diagnostics$"),   "_admin_diagnostics"),
    ("POST", re.compile(r"^/admin/ban$"),           "_admin_ban"),
    ("POST", re.compile(r"^/admin/config$"),        "_admin_config"),
    ("POST", re.compile(r"^/admin/maintenance$"),   "_admin_maintenance"),
    # Health (detailed)
    ("GET", re.compile(r"^/health/detailed$"),   "_health_detailed"),
    ("GET", re.compile(r"^/health/live$"),        "_health_liveness"),
    ("GET", re.compile(r"^/health/ready$"),       "_health_readiness"),
    # Education
    ("GET",  re.compile(r"^/education/glossary$"),  "_education_glossary"),
    ("GET",  re.compile(r"^/education/lessons$"),   "_education_lessons"),
    ("GET",  re.compile(r"^/education/lesson$"),    "_education_lesson_detail"),
    ("POST", re.compile(r"^/education/quiz$"),      "_education_quiz"),
    # Notifications
    ("GET",  re.compile(r"^/notifications/templates$"), "_notification_templates"),
    ("POST", re.compile(r"^/notifications/preview$"),   "_notification_preview"),
    ("POST", re.compile(r"^/notifications/render$"),    "_notification_render"),
    # Stats
    ("POST", re.compile(r"^/stats/analyze$"),       "_stats_analyze"),
    ("POST", re.compile(r"^/stats/correlation$"),   "_stats_correlation"),
    ("POST", re.compile(r"^/stats/regression$"),    "_stats_regression"),
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
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

    def do_PATCH(self) -> None:
        self._dispatch()

    def do_DELETE(self) -> None:
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

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        result = handle_score(body)
        if result[1] == 200:
            auth_header = self.headers.get("Authorization", "")
            url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
            me_data, me_status = handle_me(auth_header, url=url, method=self.command)
            if me_status == 200:
                _achievement_engine.check_and_award(
                    me_data["pubkey"], "score", {"total_score": result[0].get("total_score", 0)}
                )
        return result

    def _score_summary(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_score_summary(query)

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def _preferences_get(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_get_preferences(me_data["pubkey"])

    def _preferences_update(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_update_preferences(body, me_data["pubkey"])

    def _preferences_add_alert(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_add_price_alert(body, me_data["pubkey"])

    def _preferences_remove_alert(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_remove_price_alert(body, me_data["pubkey"])

    # ------------------------------------------------------------------
    # Lightning
    # ------------------------------------------------------------------

    def _lightning_overview(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lightning_overview(body)

    def _lightning_compare(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lightning_compare(body)

    def _lightning_recommend(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_lightning_recommend(body, query)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def _analytics_user(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_user_analytics(me_data["pubkey"])

    def _analytics_platform(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_platform_stats(body)

    def _analytics_dca(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_dca_performance(me_data["pubkey"])

    def _analytics_leaderboard(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_leaderboard(query)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_data(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_export_data(body, me_data["pubkey"])

    def _export_deposits(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_export_deposits(query, me_data["pubkey"])

    def _export_report(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_export_report(body, me_data["pubkey"])

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def _webhook_subscribe(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_webhook_subscribe(body, me_data["pubkey"])

    def _webhook_unsubscribe(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_webhook_unsubscribe(body, me_data["pubkey"])

    def _webhook_list(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_webhook_list(me_data["pubkey"])

    def _webhook_test(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_webhook_test(body, me_data["pubkey"])

    # ------------------------------------------------------------------
    # Docs
    # ------------------------------------------------------------------

    def _docs_openapi(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_openapi_json()

    def _docs_swagger(
        self, params: dict, body: dict, query: dict
    ) -> tuple[dict, int]:
        return handle_swagger_ui()

    # ------------------------------------------------------------------
    # Market
    # ------------------------------------------------------------------

    def _market_overview(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_market_overview(body)

    def _market_history(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_price_history(query)

    def _market_signals(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_market_signals(body)

    def _market_sentiment(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_market_sentiment(body)

    def _market_halving(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_halving_info(body)

    def _market_fair_value(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_fair_value(body)

    # ------------------------------------------------------------------
    # Portfolio
    # ------------------------------------------------------------------

    def _portfolio_holdings(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_holdings(me_data["pubkey"])

    def _portfolio_summary(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_summary(me_data["pubkey"])

    def _portfolio_transaction(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_transaction(body, me_data["pubkey"])

    def _portfolio_performance(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_performance(query, me_data["pubkey"])

    def _portfolio_optimize(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_optimize(body, me_data["pubkey"])

    def _portfolio_risk(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        auth_header = self.headers.get("Authorization", "")
        url = f"{settings.PUBLIC_URL}{self.path.split('?')[0]}"
        me_data, status = handle_me(auth_header, url=url, method=self.command)
        if status != 200:
            return {"detail": "Authentication required"}, 401
        return handle_portfolio_risk(me_data["pubkey"])

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _sim_portfolio(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_simulate_portfolio(body)

    def _sim_dca(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_simulate_dca(body)

    def _sim_backtest(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_backtest(body)

    def _sim_scenario(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_scenario_analysis(body)

    def _sim_montecarlo(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_monte_carlo(body)

    def _sim_retirement(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_retirement_sim(body)

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def _admin_overview(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_overview(body)

    def _admin_users(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_users(query)

    def _admin_user_detail(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_user_detail(query)

    def _admin_system(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_system(body)

    def _admin_diagnostics(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_diagnostics(body)

    def _admin_ban(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_user_ban(body)

    def _admin_config(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_config(body)

    def _admin_maintenance(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_admin_maintenance(body)

    # ------------------------------------------------------------------
    # Health (detailed)
    # ------------------------------------------------------------------

    def _health_detailed(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_health_detailed(body)

    def _health_liveness(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_health_liveness(body)

    def _health_readiness(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_health_readiness(body)

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------

    def _education_glossary(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_glossary(query)

    def _education_lessons(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_lesson_list(query)

    def _education_lesson_detail(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_lesson_detail(query)

    def _education_quiz(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_quiz(body)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notification_templates(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_notification_templates(query)

    def _notification_preview(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_notification_preview(body)

    def _notification_render(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_notification_render(body)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def _stats_analyze(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_stats_analyze(body)

    def _stats_correlation(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_stats_correlation(body)

    def _stats_regression(self, params: dict, body: dict, query: dict) -> tuple[dict, int]:
        return handle_stats_regression(body)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    setup_logging()
    init_db()
    _monitor.start()
    _scheduler = build_default_scheduler(
        price_aggregator=_price_aggregator,
        webhook_dispatcher=_webhook_dispatcher,
        analytics_engine=_analytics_engine,
        rate_limit_storage=_rate_limit_storage,
    )
    _scheduler.start()
    port = 8000
    _logger.info("server_start", port=port)
    print(f"[Magma] Starting server on http://0.0.0.0:{port}")
    with ThreadedTCPServer(("", port), Handler) as server:
        server.serve_forever()
