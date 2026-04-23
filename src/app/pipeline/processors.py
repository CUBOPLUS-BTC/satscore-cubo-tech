"""
Data processing classes for the Magma pipeline framework.

Provides:
  - BatchProcessor       — chunked batch processing with optional parallelism
  - StreamProcessor      — streaming item-by-item processing
  - AggregationProcessor — aggregation helpers (sum, avg, group_by, histograms…)
  - TimeSeriesProcessor  — anomaly detection, decomposition, forecasting

Pure Python stdlib only.
"""

import math
import logging
import statistics
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BatchProcessor
# ---------------------------------------------------------------------------

class BatchProcessor:
    """
    Process a list of items in fixed-size batches.

    Batches can be processed sequentially or in parallel.  Thread-safe
    progress tracking is included.

    Example::

        def handle_deposit(dep):
            return {"pubkey": dep["pubkey"], "processed": True}

        bp = BatchProcessor(batch_size=50)
        result = bp.process(deposits, handle_deposit)
        print(result["processed"], result["failed"])
    """

    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self._lock = threading.Lock()
        self._processed = 0
        self._failed = 0
        self._total = 0
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None

    def _reset_progress(self, total: int):
        with self._lock:
            self._processed = 0
            self._failed = 0
            self._total = total
            self._started_at = time.time()
            self._finished_at = None

    def _record_batch(self, succeeded: int, failed: int):
        with self._lock:
            self._processed += succeeded
            self._failed += failed

    def get_progress(self) -> Dict:
        """Return current processing progress."""
        with self._lock:
            total = self._total or 1
            elapsed = (
                (self._finished_at or time.time()) - (self._started_at or time.time())
            )
            done = self._processed + self._failed
            pct = done / total * 100
            rps = done / elapsed if elapsed > 0 else 0.0
            return {
                "total": self._total,
                "processed": self._processed,
                "failed": self._failed,
                "percent_complete": round(pct, 2),
                "elapsed_seconds": round(elapsed, 3),
                "items_per_second": round(rps, 2),
                "finished": self._finished_at is not None,
            }

    def process(
        self,
        items: List[Any],
        processor_fn: Callable[[Any], Any],
    ) -> Dict:
        """
        Process all items sequentially in batches.

        Args:
            items:        Items to process.
            processor_fn: Callable applied to each item individually.

        Returns:
            Dict with ``results``, ``errors``, ``processed``, ``failed`` keys.
        """
        self._reset_progress(len(items))
        results = []
        errors = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i: i + self.batch_size]
            batch_ok = 0
            batch_fail = 0
            for item in batch:
                try:
                    results.append(processor_fn(item))
                    batch_ok += 1
                except Exception as exc:
                    errors.append({"item": str(item)[:200], "error": str(exc)})
                    batch_fail += 1
            self._record_batch(batch_ok, batch_fail)
            logger.debug(
                "BatchProcessor: batch %d/%d done",
                (i // self.batch_size) + 1,
                math.ceil(len(items) / self.batch_size),
            )

        with self._lock:
            self._finished_at = time.time()

        return {
            "results": results,
            "errors": errors,
            "processed": self._processed,
            "failed": self._failed,
            "total": self._total,
        }

    def process_parallel(
        self,
        items: List[Any],
        processor_fn: Callable[[Any], Any],
        workers: int = 4,
    ) -> Dict:
        """
        Process all items in parallel using a thread pool.

        Each batch is submitted as a task to the executor.

        Args:
            items:        Items to process.
            processor_fn: Callable applied to each item individually.
            workers:      Number of worker threads.

        Returns:
            Dict with ``results``, ``errors``, ``processed``, ``failed`` keys.
        """
        self._reset_progress(len(items))
        batches = [
            items[i: i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        results: List[Any] = []
        errors: List[Dict] = []
        lock = threading.Lock()

        def _process_batch(batch):
            batch_results = []
            batch_errors = []
            for item in batch:
                try:
                    batch_results.append(processor_fn(item))
                except Exception as exc:
                    batch_errors.append({"item": str(item)[:200], "error": str(exc)})
            return batch_results, batch_errors

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_process_batch, b): b for b in batches}
            for future in as_completed(futures):
                try:
                    b_results, b_errors = future.result()
                    with lock:
                        results.extend(b_results)
                        errors.extend(b_errors)
                    self._record_batch(len(b_results), len(b_errors))
                except Exception as exc:
                    logger.error("BatchProcessor parallel batch error: %s", exc)

        with self._lock:
            self._finished_at = time.time()

        return {
            "results": results,
            "errors": errors,
            "processed": self._processed,
            "failed": self._failed,
            "total": self._total,
        }


# ---------------------------------------------------------------------------
# StreamProcessor
# ---------------------------------------------------------------------------

class StreamProcessor:
    """
    Process items one at a time in a streaming fashion.

    Items are fed with :meth:`feed` and accumulated in a buffer.
    Call :meth:`flush` to retrieve and clear the processed buffer.

    Example::

        sp = StreamProcessor(handler=lambda x: {**x, "processed": True})
        for event in websocket_events:
            sp.feed(event)
        processed = sp.flush()
    """

    def __init__(self, handler: Callable[[Any], Any]):
        self._handler = handler
        self._buffer: List[Any] = []
        self._lock = threading.Lock()
        self._total_fed = 0
        self._total_errors = 0
        self._total_processed = 0
        self._started_at = time.time()

    def feed(self, item: Any) -> Optional[Any]:
        """
        Process a single item and append the result to the internal buffer.

        Args:
            item: Item to process.

        Returns:
            Processed result, or None on error.
        """
        try:
            result = self._handler(item)
            with self._lock:
                self._buffer.append(result)
                self._total_fed += 1
                self._total_processed += 1
            return result
        except Exception as exc:
            logger.warning("StreamProcessor.feed error: %s", exc)
            with self._lock:
                self._total_fed += 1
                self._total_errors += 1
            return None

    def flush(self) -> List[Any]:
        """
        Retrieve and clear all buffered processed items.

        Returns:
            List of processed results.
        """
        with self._lock:
            items = list(self._buffer)
            self._buffer.clear()
        return items

    def get_stats(self) -> Dict:
        """Return cumulative processing statistics."""
        with self._lock:
            elapsed = time.time() - self._started_at
            return {
                "total_fed": self._total_fed,
                "total_processed": self._total_processed,
                "total_errors": self._total_errors,
                "buffer_size": len(self._buffer),
                "elapsed_seconds": round(elapsed, 3),
                "items_per_second": round(
                    self._total_fed / elapsed if elapsed > 0 else 0.0, 2
                ),
                "error_rate": round(
                    self._total_errors / self._total_fed
                    if self._total_fed > 0 else 0.0, 4
                ),
            }


# ---------------------------------------------------------------------------
# AggregationProcessor
# ---------------------------------------------------------------------------

class AggregationProcessor:
    """
    Statistical aggregation helpers over lists of dicts.

    All methods are stateless and accept a ``data`` list plus a ``field``
    key. They are intentionally simple so they compose well inside pipeline
    steps.
    """

    @staticmethod
    def sum(data: List[Dict], field: str) -> float:
        """Sum the numeric values of ``field`` across all rows."""
        return sum(float(row[field]) for row in data if field in row and row[field] is not None)

    @staticmethod
    def avg(data: List[Dict], field: str) -> float:
        """Average the numeric values of ``field``. Returns 0 for empty input."""
        values = [float(row[field]) for row in data if field in row and row[field] is not None]
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def min_val(data: List[Dict], field: str) -> Any:
        """Return the minimum value of ``field``."""
        values = [row[field] for row in data if field in row and row[field] is not None]
        return min(values) if values else None

    @staticmethod
    def max_val(data: List[Dict], field: str) -> Any:
        """Return the maximum value of ``field``."""
        values = [row[field] for row in data if field in row and row[field] is not None]
        return max(values) if values else None

    @staticmethod
    def count(data: List[Dict], field: Optional[str] = None) -> int:
        """
        Count rows. If ``field`` is given, count non-null values of that field.

        Args:
            data:  List of row dicts.
            field: Optional field to count non-null values.

        Returns:
            Integer count.
        """
        if field is None:
            return len(data)
        return sum(1 for row in data if field in row and row[field] is not None)

    @staticmethod
    def group_by(data: List[Dict], field: str) -> Dict[Any, List[Dict]]:
        """
        Group rows by the value of ``field``.

        Args:
            data:  List of row dicts.
            field: Key to group on.

        Returns:
            ``{field_value: [rows], ...}``
        """
        groups: Dict[Any, List[Dict]] = defaultdict(list)
        for row in data:
            groups[row.get(field)].append(row)
        return dict(groups)

    @staticmethod
    def top_n(data: List[Dict], field: str, n: int = 10) -> List[Dict]:
        """
        Return the top ``n`` rows sorted by descending ``field`` value.

        Args:
            data:  List of row dicts.
            field: Numeric field to sort on.
            n:     Number of top rows to return.

        Returns:
            List of up to ``n`` rows.
        """
        sortable = [row for row in data if field in row and row[field] is not None]
        sortable.sort(key=lambda r: r[field], reverse=True)
        return sortable[:n]

    @staticmethod
    def percentile(data: List[Dict], field: str, p: float) -> float:
        """
        Compute the p-th percentile (0–100) for ``field``.

        Uses linear interpolation.

        Args:
            data:  List of row dicts.
            field: Numeric field.
            p:     Percentile in [0, 100].

        Returns:
            Interpolated percentile value.
        """
        values = sorted(
            float(row[field])
            for row in data
            if field in row and row[field] is not None
        )
        if not values:
            return 0.0
        if p <= 0:
            return values[0]
        if p >= 100:
            return values[-1]
        idx = (p / 100) * (len(values) - 1)
        lo = int(idx)
        hi = lo + 1
        frac = idx - lo
        if hi >= len(values):
            return values[-1]
        return values[lo] + frac * (values[hi] - values[lo])

    @staticmethod
    def histogram(
        data: List[Dict],
        field: str,
        bins: int = 10,
    ) -> Dict:
        """
        Build a histogram of numeric values.

        Args:
            data:  List of row dicts.
            field: Numeric field.
            bins:  Number of histogram bins.

        Returns:
            Dict with ``bins``, ``counts``, ``edges``, ``min``, ``max`` keys.
        """
        values = sorted(
            float(row[field])
            for row in data
            if field in row and row[field] is not None
        )
        if not values:
            return {"bins": [], "counts": [], "edges": [], "min": None, "max": None}

        mn, mx = values[0], values[-1]
        span = mx - mn or 1.0
        bin_width = span / bins
        edges = [mn + i * bin_width for i in range(bins + 1)]
        counts = [0] * bins

        for v in values:
            idx = min(int((v - mn) / bin_width), bins - 1)
            counts[idx] += 1

        return {
            "bins": bins,
            "counts": counts,
            "edges": [round(e, 6) for e in edges],
            "min": mn,
            "max": mx,
            "total": len(values),
        }

    @staticmethod
    def frequency_distribution(data: List[Dict], field: str) -> Dict:
        """
        Count the frequency of each distinct value in ``field``.

        Returns:
            ``{value: count, ...}`` sorted by descending count.
        """
        freq: Dict[Any, int] = defaultdict(int)
        for row in data:
            val = row.get(field)
            if val is not None:
                freq[val] += 1
        return dict(sorted(freq.items(), key=lambda kv: kv[1], reverse=True))


# ---------------------------------------------------------------------------
# TimeSeriesProcessor
# ---------------------------------------------------------------------------

class TimeSeriesProcessor:
    """
    Algorithms for time-series analysis: anomaly detection, decomposition,
    forecasting, autocorrelation, and stationarity testing.

    All methods accept a list of numeric values (floats/ints) representing
    observations at equal time intervals.
    """

    @staticmethod
    def detect_anomalies(
        data: List[float],
        method: str = "zscore",
        threshold: float = 3.0,
    ) -> List[Dict]:
        """
        Detect anomalous values in a time series.

        Args:
            data:      Ordered list of numeric values.
            method:    ``"zscore"`` or ``"iqr"``.
            threshold: Z-score cutoff or IQR multiplier.

        Returns:
            List of dicts with ``index``, ``value``, ``score``, ``is_anomaly`` keys.
        """
        n = len(data)
        if n < 4:
            return [{"index": i, "value": v, "score": 0.0, "is_anomaly": False}
                    for i, v in enumerate(data)]

        results = []

        if method == "zscore":
            mean = sum(data) / n
            variance = sum((v - mean) ** 2 for v in data) / n
            std = math.sqrt(variance) or 1.0
            for i, v in enumerate(data):
                score = abs((v - mean) / std)
                results.append({
                    "index": i,
                    "value": v,
                    "score": round(score, 4),
                    "is_anomaly": score > threshold,
                })

        elif method == "iqr":
            sorted_vals = sorted(data)
            q1 = sorted_vals[n // 4]
            q3 = sorted_vals[(3 * n) // 4]
            iqr = q3 - q1 or 1.0
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            for i, v in enumerate(data):
                score = max(
                    (lower - v) / iqr if v < lower else 0.0,
                    (v - upper) / iqr if v > upper else 0.0,
                )
                results.append({
                    "index": i,
                    "value": v,
                    "score": round(score, 4),
                    "is_anomaly": v < lower or v > upper,
                })

        return results

    @staticmethod
    def decompose(
        data: List[float],
        period: int = 7,
    ) -> Dict:
        """
        Decompose a time series into trend, seasonal, and residual components.

        Uses a simple centred moving average for the trend, then isolates
        the seasonal component by averaging residuals across periods.

        Args:
            data:   Ordered list of numeric values.
            period: Seasonal period (e.g. 7 for weekly).

        Returns:
            Dict with ``trend``, ``seasonal``, ``residual`` lists (same length).
        """
        n = len(data)
        half = period // 2

        # Centred moving average for trend
        trend = [None] * n
        for i in range(half, n - half):
            window = data[i - half: i + half + 1]
            trend[i] = sum(window) / len(window)

        # De-trended series
        detrended = [
            data[i] - trend[i] if trend[i] is not None else None
            for i in range(n)
        ]

        # Average seasonal component per period position
        seasonal_avgs: Dict[int, List[float]] = defaultdict(list)
        for i, v in enumerate(detrended):
            if v is not None:
                seasonal_avgs[i % period].append(v)
        avg_seasonal = {
            k: sum(vals) / len(vals) for k, vals in seasonal_avgs.items()
        }

        seasonal = [avg_seasonal.get(i % period, 0.0) for i in range(n)]

        # Residual
        residual = [
            data[i] - (trend[i] or data[i]) - seasonal[i]
            for i in range(n)
        ]

        return {
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual,
        }

    @staticmethod
    def forecast(
        data: List[float],
        periods: int = 10,
        method: str = "ema",
    ) -> List[float]:
        """
        Produce a simple forward forecast.

        Args:
            data:    Historical values.
            periods: Number of future periods to forecast.
            method:  ``"ema"`` (exponential MA), ``"sma"`` (simple MA),
                     ``"naive"`` (last value).

        Returns:
            List of ``periods`` forecasted values.
        """
        if not data:
            return [0.0] * periods

        if method == "naive":
            return [data[-1]] * periods

        if method == "sma":
            window = min(10, len(data))
            base = sum(data[-window:]) / window
            return [base] * periods

        if method == "ema":
            alpha = 0.2
            ema = data[0]
            for v in data[1:]:
                ema = alpha * v + (1 - alpha) * ema

            # Compute slope from last two EMA values
            if len(data) >= 2:
                prev_ema = data[-2] * alpha + ema * (1 - alpha)
                slope = ema - prev_ema
            else:
                slope = 0.0

            result = []
            current = ema
            for _ in range(periods):
                current = current + slope
                result.append(round(current, 8))
            return result

        return [data[-1]] * periods

    @staticmethod
    def autocorrelation(
        data: List[float],
        max_lag: int = 20,
    ) -> List[Dict]:
        """
        Compute the autocorrelation function (ACF) up to ``max_lag`` lags.

        Args:
            data:    Numeric series.
            max_lag: Maximum lag to compute.

        Returns:
            List of dicts with ``lag`` and ``acf`` keys.
        """
        n = len(data)
        if n < 2:
            return []
        mean = sum(data) / n
        variance = sum((v - mean) ** 2 for v in data) / n
        if variance == 0:
            return [{"lag": lag, "acf": 0.0} for lag in range(max_lag + 1)]

        results = []
        for lag in range(max_lag + 1):
            if lag == 0:
                results.append({"lag": 0, "acf": 1.0})
                continue
            covariance = sum(
                (data[i] - mean) * (data[i - lag] - mean)
                for i in range(lag, n)
            ) / n
            acf = covariance / variance
            results.append({"lag": lag, "acf": round(acf, 6)})
        return results

    @staticmethod
    def stationarity_test(data: List[float]) -> Dict:
        """
        Perform a lightweight stationarity test (Augmented Dickey-Fuller
        approximation using variance ratio and mean shift).

        Note: This is a heuristic approximation, not a proper ADF test.
        For a production system use a statistical library.

        Args:
            data: Numeric series.

        Returns:
            Dict with ``is_stationary`` bool, ``mean``, ``variance``,
            ``mean_shift``, ``variance_ratio``, and ``interpretation`` keys.
        """
        n = len(data)
        if n < 10:
            return {
                "is_stationary": None,
                "message": "Not enough data (need at least 10 points)",
            }

        half = n // 2
        first_half = data[:half]
        second_half = data[half:]

        def _mean(lst):
            return sum(lst) / len(lst)

        def _variance(lst):
            m = _mean(lst)
            return sum((v - m) ** 2 for v in lst) / len(lst)

        m1, m2 = _mean(first_half), _mean(second_half)
        v1, v2 = _variance(first_half), _variance(second_half)
        overall_mean = _mean(data)
        overall_std = math.sqrt(_variance(data)) or 1.0

        mean_shift = abs(m2 - m1) / overall_std
        variance_ratio = (v2 / v1) if v1 > 0 else float("inf")

        # Heuristic thresholds
        is_stationary = mean_shift < 0.5 and 0.5 < variance_ratio < 2.0

        return {
            "is_stationary": is_stationary,
            "mean": round(overall_mean, 6),
            "variance": round(_variance(data), 6),
            "first_half_mean": round(m1, 6),
            "second_half_mean": round(m2, 6),
            "mean_shift_z": round(mean_shift, 4),
            "variance_ratio": round(variance_ratio, 4),
            "interpretation": (
                "Likely stationary" if is_stationary
                else "Likely non-stationary (trend or heteroscedasticity detected)"
            ),
        }
