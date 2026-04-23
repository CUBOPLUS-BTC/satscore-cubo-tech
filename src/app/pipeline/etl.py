"""
ETL Framework for the Magma Bitcoin application.

Provides Pipeline, PipelineStep, PipelineResult, DataExtractor, DataLoader
classes and predefined pipeline factory functions. All pure stdlib - no
third-party dependencies.
"""

import csv
import io
import json
import logging
import time
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------

class PipelineResult:
    """Holds the result of a pipeline execution."""

    def __init__(self):
        self.data: Any = None
        self.errors: List[Dict] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {
            "started_at": None,
            "finished_at": None,
            "duration_ms": 0,
            "rows_processed": 0,
            "rows_failed": 0,
            "throughput_rps": 0.0,
        }
        self.steps_completed: List[str] = []
        self.success: bool = False

    def add_error(self, step: str, message: str, exception: Optional[Exception] = None):
        entry = {"step": step, "message": message}
        if exception:
            entry["traceback"] = traceback.format_exc()
        self.errors.append(entry)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "steps_completed": self.steps_completed,
            "data_type": type(self.data).__name__,
            "data_length": len(self.data) if isinstance(self.data, (list, dict)) else None,
        }

    def __repr__(self):
        return (
            f"<PipelineResult success={self.success} "
            f"steps={len(self.steps_completed)} "
            f"errors={len(self.errors)}>"
        )


# ---------------------------------------------------------------------------
# PipelineStep
# ---------------------------------------------------------------------------

class PipelineStep:
    """A single step in a data pipeline."""

    def __init__(
        self,
        name: str,
        transform_fn: Callable,
        validate_fn: Optional[Callable] = None,
        error_handler: Optional[Callable] = None,
        skip_on_empty: bool = True,
        description: str = "",
    ):
        self.name = name
        self.transform_fn = transform_fn
        self.validate_fn = validate_fn
        self.error_handler = error_handler
        self.skip_on_empty = skip_on_empty
        self.description = description
        self._executions = 0
        self._total_ms = 0.0
        self._errors = 0

    def execute(self, data: Any) -> Any:
        """Execute the step's transformation. Returns transformed data."""
        if self.skip_on_empty and data is None:
            logger.debug("Step '%s' skipped (data is None)", self.name)
            return data

        if self.validate_fn is not None:
            try:
                ok = self.validate_fn(data)
                if not ok:
                    raise ValueError(f"Pre-validation failed for step '{self.name}'")
            except Exception as exc:
                logger.warning("Validation error in step '%s': %s", self.name, exc)
                if self.error_handler:
                    return self.error_handler(data, exc)
                raise

        start = time.perf_counter()
        try:
            result = self.transform_fn(data)
            elapsed = (time.perf_counter() - start) * 1000
            self._executions += 1
            self._total_ms += elapsed
            logger.debug("Step '%s' completed in %.2f ms", self.name, elapsed)
            return result
        except Exception as exc:
            self._errors += 1
            if self.error_handler:
                logger.warning("Step '%s' error, using handler: %s", self.name, exc)
                return self.error_handler(data, exc)
            raise

    def get_stats(self) -> Dict:
        avg = self._total_ms / self._executions if self._executions else 0.0
        return {
            "name": self.name,
            "executions": self._executions,
            "errors": self._errors,
            "avg_ms": round(avg, 3),
            "total_ms": round(self._total_ms, 3),
        }

    def __repr__(self):
        return f"<PipelineStep name='{self.name}'>"


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """
    Composable data pipeline.

    Usage::

        pipeline = (
            Pipeline("price_update")
            .add_step(PipelineStep("extract", extract_fn))
            .add_step(PipelineStep("transform", transform_fn))
            .add_step(PipelineStep("load", load_fn))
        )
        result = pipeline.run(initial_data)
    """

    def __init__(self, name: str):
        self.name = name
        self.steps: List[PipelineStep] = []
        self._run_count = 0
        self._total_duration_ms = 0.0
        self._last_result: Optional[PipelineResult] = None
        self._created_at = time.time()
        self._status = "idle"

    def add_step(self, step: PipelineStep) -> "Pipeline":
        """Add a step. Returns self for chaining."""
        if not isinstance(step, PipelineStep):
            raise TypeError("Expected a PipelineStep instance")
        self.steps.append(step)
        logger.debug("Pipeline '%s': added step '%s'", self.name, step.name)
        return self

    def validate(self) -> bool:
        """Validate pipeline configuration before running."""
        if not self.steps:
            logger.warning("Pipeline '%s' has no steps", self.name)
            return False
        names = [s.name for s in self.steps]
        if len(names) != len(set(names)):
            logger.warning("Pipeline '%s' has duplicate step names", self.name)
            return False
        for step in self.steps:
            if not callable(step.transform_fn):
                logger.warning(
                    "Pipeline '%s': step '%s' transform_fn is not callable",
                    self.name, step.name,
                )
                return False
        return True

    def run(self, data: Any) -> PipelineResult:
        """Execute all steps sequentially."""
        result = PipelineResult()
        result.metrics["started_at"] = time.time()
        self._status = "running"
        current = data

        try:
            for step in self.steps:
                try:
                    current = step.execute(current)
                    result.steps_completed.append(step.name)
                except Exception as exc:
                    result.add_error(step.name, str(exc), exc)
                    self._status = "failed"
                    logger.error(
                        "Pipeline '%s' failed at step '%s': %s",
                        self.name, step.name, exc,
                    )
                    result.metrics["finished_at"] = time.time()
                    result.metrics["duration_ms"] = (
                        result.metrics["finished_at"] - result.metrics["started_at"]
                    ) * 1000
                    return result

            result.data = current
            result.success = True
            self._status = "idle"

        finally:
            finished = time.time()
            result.metrics["finished_at"] = finished
            duration_ms = (finished - result.metrics["started_at"]) * 1000
            result.metrics["duration_ms"] = round(duration_ms, 3)

            rows = len(current) if isinstance(current, list) else 1
            result.metrics["rows_processed"] = rows
            if duration_ms > 0:
                result.metrics["throughput_rps"] = round(rows / (duration_ms / 1000), 2)

            self._run_count += 1
            self._total_duration_ms += duration_ms
            self._last_result = result

        return result

    def run_parallel(self, data_chunks: List[Any]) -> List[PipelineResult]:
        """
        Execute the pipeline on multiple data chunks in parallel using threads.
        Returns one PipelineResult per chunk.
        """
        workers = min(len(data_chunks), 8)
        results = [None] * len(data_chunks)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_index = {
                executor.submit(self.run, chunk): i
                for i, chunk in enumerate(data_chunks)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    r = PipelineResult()
                    r.add_error("parallel_runner", str(exc), exc)
                    results[idx] = r

        return results

    def get_status(self) -> Dict:
        """Return current execution status."""
        return {
            "name": self.name,
            "status": self._status,
            "run_count": self._run_count,
            "step_count": len(self.steps),
            "steps": [s.name for s in self.steps],
            "created_at": self._created_at,
        }

    def get_metrics(self) -> Dict:
        """Return aggregate execution metrics."""
        avg_ms = (
            self._total_duration_ms / self._run_count if self._run_count else 0.0
        )
        return {
            "name": self.name,
            "run_count": self._run_count,
            "total_duration_ms": round(self._total_duration_ms, 3),
            "avg_duration_ms": round(avg_ms, 3),
            "step_stats": [s.get_stats() for s in self.steps],
        }

    def __repr__(self):
        return f"<Pipeline name='{self.name}' steps={len(self.steps)}>"


# ---------------------------------------------------------------------------
# DataExtractor
# ---------------------------------------------------------------------------

class DataExtractor:
    """
    Extracts raw data from various sources (database queries, HTTP APIs,
    CSV strings, JSON strings).
    """

    def __init__(self, db_conn_factory: Optional[Callable] = None):
        """
        Args:
            db_conn_factory: Zero-argument callable that returns a DB connection.
        """
        self._db_conn_factory = db_conn_factory

    def from_database(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute a SELECT query and return results as a list of dicts.

        Args:
            query:  SQL query string (use ? placeholders for sqlite3).
            params: Query parameters dict or list (passed to cursor.execute).

        Returns:
            List of row dicts.
        """
        if self._db_conn_factory is None:
            raise RuntimeError("No database connection factory provided")

        conn = self._db_conn_factory()
        conn.row_factory = _dict_row_factory(conn)
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        except Exception as exc:
            logger.error("DataExtractor.from_database error: %s", exc)
            raise
        finally:
            cursor.close()

    def from_api(
        self,
        url: str,
        headers: Optional[Dict] = None,
        timeout: int = 10,
    ) -> Any:
        """
        Fetch JSON data from an HTTP API endpoint.

        Args:
            url:     Full URL to GET.
            headers: Optional HTTP headers dict.
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON (dict / list).
        """
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            logger.error("DataExtractor.from_api HTTP %s: %s", exc.code, url)
            raise
        except urllib.error.URLError as exc:
            logger.error("DataExtractor.from_api URL error: %s", exc.reason)
            raise

    def from_csv(self, data: str, delimiter: str = ",") -> List[Dict]:
        """
        Parse a CSV string into a list of dicts (first row = headers).

        Args:
            data:      CSV text.
            delimiter: Column separator.

        Returns:
            List of row dicts.
        """
        reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
        rows = []
        for row in reader:
            rows.append(dict(row))
        return rows

    def from_json(self, data: str) -> Any:
        """
        Parse a JSON string.

        Args:
            data: JSON text.

        Returns:
            Parsed Python object.
        """
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            logger.error("DataExtractor.from_json parse error: %s", exc)
            raise


# ---------------------------------------------------------------------------
# DataLoader
# ---------------------------------------------------------------------------

class DataLoader:
    """
    Loads transformed data into a target (database table, JSON string, CSV string).
    """

    def __init__(self, db_conn_factory: Optional[Callable] = None):
        self._db_conn_factory = db_conn_factory

    def to_database(
        self,
        table: str,
        rows: List[Dict],
        mode: str = "insert",
    ) -> int:
        """
        Write rows to a database table.

        Args:
            table: Target table name.
            rows:  List of row dicts (keys must match column names).
            mode:  "insert" | "upsert" (INSERT OR REPLACE).

        Returns:
            Number of rows written.
        """
        if not rows:
            return 0
        if self._db_conn_factory is None:
            raise RuntimeError("No database connection factory provided")

        conn = self._db_conn_factory()
        cursor = conn.cursor()

        columns = list(rows[0].keys())
        placeholders = ", ".join("?" for _ in columns)
        col_names = ", ".join(columns)

        verb = "INSERT OR REPLACE" if mode == "upsert" else "INSERT"
        sql = f"{verb} INTO {table} ({col_names}) VALUES ({placeholders})"

        count = 0
        try:
            for row in rows:
                values = [row.get(c) for c in columns]
                cursor.execute(sql, values)
                count += 1
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("DataLoader.to_database error: %s", exc)
            raise
        finally:
            cursor.close()

        return count

    def to_json(self, data: Any, indent: int = 2) -> str:
        """Serialize data to a JSON string."""
        return json.dumps(data, indent=indent, default=str)

    def to_csv(self, data: List[Dict], headers: Optional[List[str]] = None) -> str:
        """
        Serialize a list of dicts to CSV text.

        Args:
            data:    List of row dicts.
            headers: Column order; if None, uses sorted keys of first row.

        Returns:
            CSV string with header row.
        """
        if not data:
            return ""
        if headers is None:
            headers = sorted(data[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _dict_row_factory(conn):
    """Return a row factory that yields dicts instead of tuples."""
    import sqlite3
    def factory(cursor, row):
        return {
            description[0]: row[idx]
            for idx, description in enumerate(cursor.description)
        }
    conn.row_factory = factory
    return factory


# ---------------------------------------------------------------------------
# Transform helper functions used by predefined pipelines
# ---------------------------------------------------------------------------

def _extract_prices_from_api(data: Any) -> List[Dict]:
    """Extract and normalise price records from CoinGecko-style response."""
    if isinstance(data, dict) and "prices" in data:
        return [
            {"timestamp": int(p[0] / 1000), "price_usd": float(p[1])}
            for p in data["prices"]
        ]
    if isinstance(data, list):
        return data
    return []


def _validate_price_list(data: Any) -> bool:
    if not isinstance(data, list):
        return False
    if not data:
        return True
    first = data[0]
    return "price_usd" in first


def _deduplicate_prices(data: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for row in data:
        ts = row.get("timestamp")
        if ts not in seen:
            seen.add(ts)
            out.append(row)
    return sorted(out, key=lambda r: r.get("timestamp", 0))


def _enrich_price_rows(data: List[Dict]) -> List[Dict]:
    """Add date string and round price."""
    import datetime
    for row in data:
        ts = row.get("timestamp", 0)
        row["date"] = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        row["price_usd"] = round(row.get("price_usd", 0.0), 2)
    return data


def _validate_user_events(data: Any) -> bool:
    return isinstance(data, list)


def _aggregate_user_events(data: List[Dict]) -> Dict:
    """Group events by pubkey and summarise."""
    groups: Dict[str, List] = {}
    for event in data:
        pk = event.get("pubkey", "unknown")
        groups.setdefault(pk, []).append(event)
    summary = {}
    for pk, events in groups.items():
        summary[pk] = {
            "pubkey": pk,
            "event_count": len(events),
            "event_types": list({e.get("event_type") for e in events}),
            "first_seen": min(e.get("timestamp", 0) for e in events),
            "last_seen": max(e.get("timestamp", 0) for e in events),
        }
    return summary


def _flatten_analytics_summary(data: Dict) -> List[Dict]:
    return list(data.values())


def _validate_deposits(data: Any) -> bool:
    return isinstance(data, list)


def _aggregate_deposits(data: List[Dict]) -> List[Dict]:
    """Sum deposits per pubkey per month."""
    from collections import defaultdict
    import datetime
    buckets: Dict[str, Dict] = defaultdict(lambda: {"total_sats": 0, "count": 0})
    for dep in data:
        pk = dep.get("pubkey", "")
        ts = dep.get("created_at", 0)
        month = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m")
        key = f"{pk}:{month}"
        buckets[key]["pubkey"] = pk
        buckets[key]["month"] = month
        buckets[key]["total_sats"] += dep.get("amount_sats", 0)
        buckets[key]["count"] += 1
    return list(buckets.values())


def _validate_compliance_data(data: Any) -> bool:
    return isinstance(data, list)


def _flag_large_transactions(data: List[Dict]) -> List[Dict]:
    """Flag transactions above threshold for compliance review."""
    THRESHOLD_SATS = 10_000_000  # ~$5k at ~$50k BTC
    for row in data:
        row["compliance_flag"] = row.get("amount_sats", 0) >= THRESHOLD_SATS
        row["requires_review"] = row.get("compliance_flag", False)
    return data


def _score_compliance_risk(data: List[Dict]) -> List[Dict]:
    """Assign a simple risk score 0-100."""
    for row in data:
        score = 0
        if row.get("compliance_flag"):
            score += 50
        if row.get("amount_sats", 0) > 50_000_000:
            score += 30
        if not row.get("pubkey"):
            score += 20
        row["risk_score"] = min(score, 100)
    return data


# ---------------------------------------------------------------------------
# Predefined pipeline factories
# ---------------------------------------------------------------------------

def build_price_update_pipeline() -> Pipeline:
    """
    Pipeline: raw CoinGecko API response → cleaned, deduplicated price rows.

    Steps:
      1. extract  – parse prices from API response structure
      2. dedup    – remove duplicate timestamps
      3. enrich   – add human-readable date, round price
    """
    return (
        Pipeline("price_update")
        .add_step(PipelineStep(
            name="extract",
            transform_fn=_extract_prices_from_api,
            validate_fn=lambda d: d is not None,
            description="Parse CoinGecko response into price rows",
        ))
        .add_step(PipelineStep(
            name="validate",
            transform_fn=lambda d: d,
            validate_fn=_validate_price_list,
            description="Validate price list structure",
        ))
        .add_step(PipelineStep(
            name="dedup",
            transform_fn=_deduplicate_prices,
            description="Remove duplicate timestamp rows",
        ))
        .add_step(PipelineStep(
            name="enrich",
            transform_fn=_enrich_price_rows,
            description="Add date string, round price",
        ))
    )


def build_user_analytics_pipeline() -> Pipeline:
    """
    Pipeline: raw analytics event list → per-user summary list.

    Steps:
      1. validate – check input is a list
      2. aggregate – group by pubkey
      3. flatten   – convert dict to list
    """
    return (
        Pipeline("user_analytics")
        .add_step(PipelineStep(
            name="validate",
            transform_fn=lambda d: d,
            validate_fn=_validate_user_events,
            description="Validate analytics event list",
        ))
        .add_step(PipelineStep(
            name="aggregate",
            transform_fn=_aggregate_user_events,
            description="Group and summarise events per user",
        ))
        .add_step(PipelineStep(
            name="flatten",
            transform_fn=_flatten_analytics_summary,
            description="Convert summary dict to list",
        ))
    )


def build_deposit_aggregation_pipeline() -> Pipeline:
    """
    Pipeline: raw deposit rows → monthly aggregation per user.

    Steps:
      1. validate  – check input is a list
      2. aggregate – sum sats per pubkey per month
    """
    return (
        Pipeline("deposit_aggregation")
        .add_step(PipelineStep(
            name="validate",
            transform_fn=lambda d: d,
            validate_fn=_validate_deposits,
            description="Validate deposit list",
        ))
        .add_step(PipelineStep(
            name="aggregate",
            transform_fn=_aggregate_deposits,
            description="Sum deposits per pubkey per month",
        ))
    )


def build_compliance_check_pipeline() -> Pipeline:
    """
    Pipeline: raw transaction rows → compliance-flagged, risk-scored rows.

    Steps:
      1. validate    – check input is a list
      2. flag_large  – mark transactions above threshold
      3. risk_score  – compute 0-100 risk score
    """
    return (
        Pipeline("compliance_check")
        .add_step(PipelineStep(
            name="validate",
            transform_fn=lambda d: d,
            validate_fn=_validate_compliance_data,
            description="Validate transaction list",
        ))
        .add_step(PipelineStep(
            name="flag_large",
            transform_fn=_flag_large_transactions,
            description="Flag transactions above compliance threshold",
        ))
        .add_step(PipelineStep(
            name="risk_score",
            transform_fn=_score_compliance_risk,
            description="Assign compliance risk score",
        ))
    )
