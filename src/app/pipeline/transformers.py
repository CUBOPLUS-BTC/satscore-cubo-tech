"""
Data transformation functions for the Magma pipeline framework.

All methods are static and operate on plain Python lists/dicts so that
transformations can be composed freely inside PipelineStep instances.
No third-party libraries – pure stdlib only.
"""

import math
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Transformers:
    """
    Collection of static data-transformation methods.

    Each method accepts and returns plain Python objects (lists of dicts,
    lists of numbers, etc.) and can be passed directly as PipelineStep
    transform functions.
    """

    # ------------------------------------------------------------------
    # Price / return transformations
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_prices(data: List[Dict], field: str = "price_usd") -> List[Dict]:
        """
        Min-max normalize a numeric field to the [0, 1] range.

        Args:
            data:  List of row dicts.
            field: Key of the numeric field to normalise.

        Returns:
            New list with an additional ``{field}_norm`` key on each row.
        """
        values = [float(row[field]) for row in data if field in row]
        if not values:
            return data
        mn, mx = min(values), max(values)
        span = mx - mn or 1.0
        result = []
        for row in data:
            r = dict(row)
            if field in r:
                r[f"{field}_norm"] = round((float(r[field]) - mn) / span, 8)
            result.append(r)
        return result

    @staticmethod
    def calculate_returns(prices: List[float]) -> List[float]:
        """
        Calculate simple percentage returns from a price series.

        Returns:
            List of length ``len(prices) - 1`` where each element is
            ``(p[i] - p[i-1]) / p[i-1]``.
        """
        if len(prices) < 2:
            return []
        returns = []
        for i in range(1, len(prices)):
            prev = prices[i - 1]
            if prev == 0:
                returns.append(0.0)
            else:
                returns.append((prices[i] - prev) / prev)
        return returns

    @staticmethod
    def calculate_log_returns(prices: List[float]) -> List[float]:
        """
        Calculate log returns: ``ln(p[i] / p[i-1])``.

        Returns:
            List of length ``len(prices) - 1``.
        """
        if len(prices) < 2:
            return []
        log_returns = []
        for i in range(1, len(prices)):
            prev = prices[i - 1]
            curr = prices[i]
            if prev <= 0 or curr <= 0:
                log_returns.append(0.0)
            else:
                log_returns.append(math.log(curr / prev))
        return log_returns

    # ------------------------------------------------------------------
    # Time-series reshaping
    # ------------------------------------------------------------------

    @staticmethod
    def resample_timeseries(
        data: List[Dict],
        interval: str = "1d",
        timestamp_field: str = "timestamp",
        open_field: str = "open",
        high_field: str = "high",
        low_field: str = "low",
        close_field: str = "close",
        volume_field: str = "volume",
    ) -> List[Dict]:
        """
        Resample OHLCV data to a coarser time interval.

        Supported intervals: ``1h``, ``4h``, ``1d``, ``1w``, ``1M``.

        Args:
            data:            List of OHLCV dicts with a Unix timestamp.
            interval:        Target interval string.
            *_field args:    Keys for each OHLCV component.

        Returns:
            List of resampled OHLCV dicts.
        """
        seconds_map = {
            "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
            "4h": 14400, "1d": 86400, "1w": 604800, "1M": 2592000,
        }
        bucket_size = seconds_map.get(interval, 86400)
        buckets: Dict[int, List[Dict]] = defaultdict(list)

        for row in data:
            ts = int(row.get(timestamp_field, 0))
            bucket_key = (ts // bucket_size) * bucket_size
            buckets[bucket_key].append(row)

        result = []
        for bucket_ts in sorted(buckets):
            rows = buckets[bucket_ts]
            prices_close = [float(r.get(close_field, 0)) for r in rows]
            prices_high = [float(r.get(high_field, 0)) for r in rows]
            prices_low = [float(r.get(low_field, float("inf"))) for r in rows]
            volumes = [float(r.get(volume_field, 0)) for r in rows]
            result.append({
                timestamp_field: bucket_ts,
                open_field: float(rows[0].get(open_field, 0)),
                high_field: max(prices_high) if prices_high else 0,
                low_field: min(prices_low) if prices_low else 0,
                close_field: prices_close[-1] if prices_close else 0,
                volume_field: sum(volumes),
                "bar_count": len(rows),
            })
        return result

    @staticmethod
    def fill_missing_values(
        data: List[Dict],
        field: str,
        method: str = "forward",
    ) -> List[Dict]:
        """
        Fill missing (None / NaN) values in a list of dicts.

        Args:
            data:   List of row dicts.
            field:  Key to fill.
            method: ``"forward"``, ``"backward"``, or ``"linear"``.

        Returns:
            New list with missing values filled.
        """
        result = [dict(row) for row in data]
        n = len(result)
        if n == 0:
            return result

        def _is_missing(v):
            return v is None or (isinstance(v, float) and math.isnan(v))

        if method == "forward":
            last_valid = None
            for row in result:
                if not _is_missing(row.get(field)):
                    last_valid = row[field]
                elif last_valid is not None:
                    row[field] = last_valid

        elif method == "backward":
            next_valid = None
            for row in reversed(result):
                if not _is_missing(row.get(field)):
                    next_valid = row[field]
                elif next_valid is not None:
                    row[field] = next_valid

        elif method == "linear":
            # Find gaps and interpolate
            i = 0
            while i < n:
                if _is_missing(result[i].get(field)):
                    # Find start of gap
                    gap_start = i - 1
                    j = i
                    while j < n and _is_missing(result[j].get(field)):
                        j += 1
                    gap_end = j
                    # Interpolate if we have anchors on both sides
                    if gap_start >= 0 and gap_end < n:
                        v0 = result[gap_start][field]
                        v1 = result[gap_end][field]
                        steps = gap_end - gap_start
                        for k in range(i, j):
                            frac = (k - gap_start) / steps
                            result[k][field] = v0 + frac * (v1 - v0)
                    elif gap_start < 0 and gap_end < n:
                        for k in range(i, j):
                            result[k][field] = result[gap_end][field]
                    elif gap_start >= 0:
                        for k in range(i, j):
                            result[k][field] = result[gap_start][field]
                    i = j
                else:
                    i += 1
        return result

    @staticmethod
    def remove_outliers(
        data: List[Dict],
        field: str,
        method: str = "zscore",
        threshold: float = 3.0,
    ) -> List[Dict]:
        """
        Remove rows whose ``field`` value is an outlier.

        Args:
            data:      Input rows.
            field:     Numeric field to test.
            method:    ``"zscore"`` or ``"iqr"``.
            threshold: Z-score cutoff (default 3) or IQR multiplier (default 1.5).

        Returns:
            Filtered list.
        """
        values = [float(row[field]) for row in data if field in row]
        if len(values) < 4:
            return data

        if method == "zscore":
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(variance) or 1.0
            return [
                row for row in data
                if field not in row or abs((float(row[field]) - mean) / std) <= threshold
            ]

        elif method == "iqr":
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            q1 = sorted_vals[n // 4]
            q3 = sorted_vals[(3 * n) // 4]
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            return [
                row for row in data
                if field not in row or lower <= float(row[field]) <= upper
            ]

        return data

    @staticmethod
    def aggregate_by_period(
        data: List[Dict],
        period: str = "month",
        timestamp_field: str = "timestamp",
        value_field: str = "value",
        agg_func: str = "sum",
    ) -> List[Dict]:
        """
        Aggregate numeric values by time period.

        Args:
            data:            Input rows.
            period:          ``"day"``, ``"week"``, ``"month"``, ``"year"``.
            timestamp_field: Key for Unix timestamps.
            value_field:     Key for the value to aggregate.
            agg_func:        ``"sum"``, ``"avg"``, ``"min"``, ``"max"``, ``"count"``.

        Returns:
            Aggregated rows with ``period``, ``value``, ``count`` keys.
        """
        import datetime
        buckets: Dict[str, List[float]] = defaultdict(list)
        for row in data:
            ts = int(row.get(timestamp_field, 0))
            dt = datetime.datetime.utcfromtimestamp(ts)
            if period == "day":
                key = dt.strftime("%Y-%m-%d")
            elif period == "week":
                key = dt.strftime("%Y-W%W")
            elif period == "month":
                key = dt.strftime("%Y-%m")
            elif period == "year":
                key = dt.strftime("%Y")
            else:
                key = dt.strftime("%Y-%m-%d")
            val = row.get(value_field)
            if val is not None:
                buckets[key].append(float(val))

        result = []
        for key in sorted(buckets):
            vals = buckets[key]
            if agg_func == "sum":
                agg_val = sum(vals)
            elif agg_func == "avg":
                agg_val = sum(vals) / len(vals) if vals else 0.0
            elif agg_func == "min":
                agg_val = min(vals) if vals else 0.0
            elif agg_func == "max":
                agg_val = max(vals) if vals else 0.0
            else:  # count
                agg_val = len(vals)
            result.append({
                "period": key,
                "value": round(agg_val, 8),
                "count": len(vals),
            })
        return result

    @staticmethod
    def pivot_data(data: List[Dict], key: str, value: str) -> Dict:
        """
        Create a dict from a list of dicts using ``key`` as the map key
        and ``value`` as the map value.

        Args:
            data:  Input rows.
            key:   Field to use as dict key.
            value: Field to use as dict value.

        Returns:
            ``{row[key]: row[value], ...}``
        """
        return {row[key]: row[value] for row in data if key in row and value in row}

    @staticmethod
    def flatten_nested(data: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """
        Recursively flatten a nested dict.

        Example::

            {"a": {"b": 1}} → {"a.b": 1}

        Args:
            data:       Nested dict.
            parent_key: Prefix for keys (used in recursion).
            sep:        Separator between nested key levels.

        Returns:
            Flat dict.
        """
        items: List[Tuple] = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(Transformers.flatten_nested(v, new_key, sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def merge_datasets(
        left: List[Dict],
        right: List[Dict],
        on: str,
        how: str = "inner",
    ) -> List[Dict]:
        """
        Merge two lists of dicts on a common key, similar to a SQL JOIN.

        Args:
            left:  Left dataset.
            right: Right dataset.
            on:    Key to join on.
            how:   ``"inner"`` or ``"left"``.

        Returns:
            Merged rows.
        """
        right_index: Dict[Any, Dict] = {}
        for row in right:
            k = row.get(on)
            if k is not None:
                right_index[k] = row

        result = []
        for lrow in left:
            k = lrow.get(on)
            rrow = right_index.get(k)
            if rrow is not None:
                merged = {**lrow, **rrow}
                result.append(merged)
            elif how == "left":
                result.append(dict(lrow))
        return result

    @staticmethod
    def window_function(
        data: List[Any],
        window: int,
        func: Callable[[List[Any]], Any],
    ) -> List[Any]:
        """
        Apply a rolling window function to a list.

        The first ``window - 1`` elements will be ``None``.

        Args:
            data:   Input list.
            window: Window size.
            func:   Function that takes a list and returns a scalar.

        Returns:
            List of same length as ``data`` with ``None`` padding.
        """
        result: List[Any] = [None] * (window - 1)
        for i in range(window - 1, len(data)):
            chunk = data[i - window + 1: i + 1]
            result.append(func(chunk))
        return result

    @staticmethod
    def cumulative_sum(data: List[float]) -> List[float]:
        """Return the running cumulative sum of a list of numbers."""
        result = []
        total = 0.0
        for v in data:
            total += v
            result.append(total)
        return result

    @staticmethod
    def rolling_statistics(
        data: List[Dict],
        window: int,
        field: str = "value",
    ) -> List[Dict]:
        """
        Compute rolling mean, std, min, and max for a numeric field.

        Args:
            data:   List of row dicts.
            window: Rolling window size.
            field:  Field to compute statistics on.

        Returns:
            Same-length list with added ``_rolling_*`` keys; ``None`` for early rows.
        """
        values = [float(row.get(field, 0)) for row in data]
        result = []
        for i, row in enumerate(data):
            r = dict(row)
            if i < window - 1:
                r[f"{field}_rolling_mean"] = None
                r[f"{field}_rolling_std"] = None
                r[f"{field}_rolling_min"] = None
                r[f"{field}_rolling_max"] = None
            else:
                chunk = values[i - window + 1: i + 1]
                mean = sum(chunk) / len(chunk)
                variance = sum((v - mean) ** 2 for v in chunk) / len(chunk)
                r[f"{field}_rolling_mean"] = round(mean, 6)
                r[f"{field}_rolling_std"] = round(math.sqrt(variance), 6)
                r[f"{field}_rolling_min"] = min(chunk)
                r[f"{field}_rolling_max"] = max(chunk)
            result.append(r)
        return result

    @staticmethod
    def lag(data: List[Any], periods: int = 1) -> List[Any]:
        """
        Shift a list forward by ``periods`` positions (introducing ``None``).

        Args:
            data:    Input list.
            periods: Number of periods to lag.

        Returns:
            List of same length with ``None`` prepended.
        """
        if periods <= 0:
            return list(data)
        return [None] * periods + list(data[:-periods] if periods < len(data) else [])

    @staticmethod
    def difference(data: List[float], periods: int = 1) -> List[Optional[float]]:
        """
        Compute the n-period difference: ``data[i] - data[i - periods]``.

        The first ``periods`` elements will be ``None``.

        Args:
            data:    Numeric list.
            periods: Differencing lag.

        Returns:
            List of same length with ``None`` prefix.
        """
        result: List[Optional[float]] = [None] * periods
        for i in range(periods, len(data)):
            result.append(data[i] - data[i - periods])
        return result

    @staticmethod
    def z_score(data: List[float]) -> List[float]:
        """
        Standardise a list of numbers to z-scores: ``(x - mean) / std``.

        Returns:
            List of z-scores (same length). Returns zeros if std is 0.
        """
        n = len(data)
        if n == 0:
            return []
        mean = sum(data) / n
        variance = sum((v - mean) ** 2 for v in data) / n
        std = math.sqrt(variance)
        if std == 0:
            return [0.0] * n
        return [(v - mean) / std for v in data]

    @staticmethod
    def min_max_scale(
        data: List[float],
        feature_range: Tuple[float, float] = (0.0, 1.0),
    ) -> List[float]:
        """
        Scale a list to a custom [min, max] range.

        Args:
            data:          Numeric list.
            feature_range: Target range as (min, max) tuple.

        Returns:
            Scaled list.
        """
        if not data:
            return []
        lo, hi = feature_range
        mn, mx = min(data), max(data)
        span = mx - mn or 1.0
        return [lo + (v - mn) / span * (hi - lo) for v in data]
