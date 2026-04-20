"""Tests for the :mod:`magma_sdk.cli` command-line interface."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import pytest

from magma_sdk import cli


def _run(argv, stdout=None, stderr=None):
    out = stdout or io.StringIO()
    err = stderr or io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = cli.main(argv)
        except SystemExit as exc:  # argparse exits via SystemExit(2)
            code = int(exc.code) if exc.code is not None else 0
    return code, out.getvalue(), err.getvalue()


class _Fake:
    def __init__(self):
        self.last = None

    def __call__(self, *args, **kwargs):
        self.last = (args, kwargs)
        return self._response

    def set_response(self, value):
        self._response = value


@pytest.fixture
def fake_client():
    """Patch :class:`MagmaClient` with a double that records calls."""

    class FakeResource:
        def __init__(self):
            self.calls = []
            self._responses = {}

        def set(self, method, value):
            self._responses[method] = value

        def _record(self, method, *args, **kwargs):
            self.calls.append((method, args, kwargs))
            if method in self._responses:
                return self._responses[method]
            return {}

    class FakeClient:
        def __init__(self, base_url, **kw):
            self.init_kwargs = kw
            self.base_url = base_url
            self.price = FakeResource()
            self.savings = FakeResource()
            self.pension = FakeResource()
            self.remittance = FakeResource()
            self.alerts = FakeResource()
            self.network = FakeResource()

            def price_get():
                return self.price._record("get")

            def s_project(monthly_usd, years=10):
                return self.savings._record(
                    "project", monthly_usd=monthly_usd, years=years
                )

            def s_progress():
                return self.savings._record("progress")

            def p_project(monthly_saving_usd, years):
                return self.pension._record(
                    "project",
                    monthly_saving_usd=monthly_saving_usd,
                    years=years,
                )

            def r_compare(amount_usd, frequency="monthly"):
                return self.remittance._record(
                    "compare", amount_usd=amount_usd, frequency=frequency
                )

            def r_fees():
                return self.remittance._record("fees")

            def a_list(limit=20):
                return self.alerts._record("list", limit=limit)

            def a_status():
                return self.alerts._record("status")

            def n_status():
                return self.network._record("status")

            self.price.get = price_get
            self.savings.project = s_project
            self.savings.progress = s_progress
            self.pension.project = p_project
            self.remittance.compare = r_compare
            self.remittance.fees = r_fees
            self.alerts.list = a_list
            self.alerts.status = a_status
            self.network.status = n_status

    with patch.object(cli, "MagmaClient", FakeClient):
        yield FakeClient


class TestCliBasics:
    def test_missing_base_url(self, monkeypatch):
        monkeypatch.delenv("MAGMA_BASE_URL", raising=False)
        code, out, err = _run(["price"])
        assert code == 1
        assert "base URL" in err

    def test_price_command(self, fake_client):
        code, out, err = _run(
            ["--base-url", "https://api.test", "price"]
        )
        assert code == 0
        assert json.loads(out) == {}

    def test_pretty_output(self, fake_client, monkeypatch):
        # Return a dataclass-like dict to verify pretty printing.
        code, out, _ = _run(
            ["--base-url", "https://api.test", "--pretty", "fees"]
        )
        assert code == 0
        assert out.startswith("{") and out.endswith("}\n")


class TestCliCommands:
    def test_savings_project(self, fake_client):
        code, out, _ = _run(
            [
                "--base-url",
                "https://api.test",
                "savings-project",
                "--monthly-usd",
                "100",
                "--years",
                "5",
            ]
        )
        assert code == 0
        # Dispatch called savings.project with kwargs.

    def test_pension_requires_years(self, fake_client):
        code, out, err = _run(
            [
                "--base-url",
                "https://api.test",
                "pension",
                "--monthly-usd",
                "100",
            ]
        )
        # argparse error → SystemExit raised; _run suppresses via stderr
        # but argparse doesn't route through main's try/except. Expect non-zero.
        assert code != 0

    def test_remittance(self, fake_client):
        code, out, _ = _run(
            [
                "--base-url",
                "https://api.test",
                "remittance",
                "--amount-usd",
                "500",
                "--frequency",
                "weekly",
            ]
        )
        assert code == 0

    def test_alerts_limit(self, fake_client):
        code, out, _ = _run(
            [
                "--base-url",
                "https://api.test",
                "alerts",
                "--limit",
                "5",
            ]
        )
        assert code == 0

    def test_env_var_base_url(self, fake_client, monkeypatch):
        monkeypatch.setenv("MAGMA_BASE_URL", "https://env.test")
        code, out, _ = _run(["price"])
        assert code == 0


class TestCliErrors:
    def test_api_error_exits_2(self, fake_client, monkeypatch):
        from magma_sdk.exceptions import ValidationError

        def raising_price_get():
            raise ValidationError(status=400, detail="bad")

        def fake_init(self, base_url, **kw):
            class _R:
                def get(self):
                    raise ValidationError(status=400, detail="bad")

            self.price = _R()

        class FakeClient:
            def __init__(self, base_url, **kw):
                class _R:
                    def get(self_inner):
                        raise ValidationError(status=400, detail="bad")

                self.price = _R()

        monkeypatch.setattr(cli, "MagmaClient", FakeClient)
        code, out, err = _run(["--base-url", "https://api.test", "price"])
        assert code == 2
        assert "API error 400" in err

    def test_transport_error_exits_3(self, fake_client, monkeypatch):
        from magma_sdk.exceptions import TransportError

        class FakeClient:
            def __init__(self, base_url, **kw):
                class _R:
                    def get(self_inner):
                        raise TransportError("dns down")

                self.price = _R()

        monkeypatch.setattr(cli, "MagmaClient", FakeClient)
        code, out, err = _run(["--base-url", "https://api.test", "price"])
        assert code == 3
        assert "Transport error" in err


class TestJsonSerialization:
    def test_dataclass_serialized(self):
        from magma_sdk.models import PriceQuote

        q = PriceQuote.from_dict(
            {"price_usd": 10.0, "sources_count": 1, "deviation": 0, "has_warning": False}
        )
        data = cli._to_jsonable(q)
        assert data == {
            "price_usd": 10.0,
            "sources_count": 1,
            "deviation": 0.0,
            "has_warning": False,
        }
        # `raw` is excluded to avoid echoing the upstream payload twice.
        assert "raw" not in data

    def test_list_of_dataclasses(self):
        from magma_sdk.models import Alert

        alerts = [Alert.from_dict({"type": "t", "message": "m", "created_at": 1})]
        assert cli._to_jsonable(alerts) == [
            {"type": "t", "message": "m", "created_at": 1}
        ]
