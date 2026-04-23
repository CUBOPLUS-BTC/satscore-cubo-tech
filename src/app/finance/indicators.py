"""
Technical analysis indicators for Bitcoin price data.

All functions operate on plain Python lists and return plain Python
lists or dicts. No third-party dependencies are used.

Convention
----------
- Input lists are chronologically ordered (oldest index 0, newest index -1).
- Where an indicator cannot be computed for early indices (warm-up period),
  those positions are filled with None.
- All price values are assumed to be float-compatible numbers.
"""

import math
import statistics
from typing import List, Optional, Dict, Any

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _require_same_length(*lists):
    lengths = [len(lst) for lst in lists]
    if len(set(lengths)) != 1:
        raise ValueError(
            f"All input lists must have the same length. Got: {lengths}"
        )


def _rolling_mean(values: list, period: int) -> list:
    """Simple rolling mean; positions before warm-up period are None."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        result[i] = sum(window) / period
    return result


def _rolling_stdev(values: list, period: int, population: bool = False) -> list:
    """Rolling standard deviation; population=False uses sample stdev."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        if population:
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
        else:
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / (period - 1)
        result[i] = math.sqrt(variance)
    return result


# ---------------------------------------------------------------------------
# Trend-following indicators
# ---------------------------------------------------------------------------

def sma(prices: list, period: int) -> list:
    """
    Simple Moving Average.

    Parameters
    ----------
    prices : list of float
        Closing (or any) prices, oldest first.
    period : int
        Look-back window.

    Returns
    -------
    list of float or None
        SMA values aligned with input; None for the warm-up period.
    """
    if period <= 0:
        raise ValueError("period must be a positive integer")
    return _rolling_mean(prices, period)


def ema(prices: list, period: int) -> list:
    """
    Exponential Moving Average using the standard smoothing factor
    k = 2 / (period + 1).

    Parameters
    ----------
    prices : list of float
    period : int

    Returns
    -------
    list of float or None
        EMA values; None until the first full SMA seed is available.
    """
    if period <= 0:
        raise ValueError("period must be a positive integer")
    k = 2.0 / (period + 1)
    result = [None] * len(prices)
    if len(prices) < period:
        return result

    # Seed with the first SMA
    seed = sum(prices[:period]) / period
    result[period - 1] = seed

    for i in range(period, len(prices)):
        result[i] = prices[i] * k + result[i - 1] * (1 - k)

    return result


def rsi(prices: list, period: int = 14) -> list:
    """
    Relative Strength Index (Wilder smoothing).

    Values range from 0 to 100.
    > 70  commonly considered overbought.
    < 30  commonly considered oversold.

    Parameters
    ----------
    prices : list of float
    period : int, default 14

    Returns
    -------
    list of float or None
    """
    if period <= 0:
        raise ValueError("period must be a positive integer")
    n = len(prices)
    result = [None] * n
    if n < period + 1:
        return result

    gains = []
    losses = []
    for i in range(1, n):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    # Initial averages (simple mean for first period)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_val(ag, al):
        if al == 0:
            return 100.0
        rs = ag / al
        return 100.0 - (100.0 / (1.0 + rs))

    result[period] = _rsi_val(avg_gain, avg_loss)

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        result[i] = _rsi_val(avg_gain, avg_loss)

    return result


def macd(
    prices: list,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict:
    """
    Moving Average Convergence / Divergence.

    Parameters
    ----------
    prices : list of float
    fast : int, default 12
    slow : int, default 26
    signal : int, default 9

    Returns
    -------
    dict with keys:
        'macd'      - MACD line (fast EMA - slow EMA)
        'signal'    - Signal line (EMA of MACD)
        'histogram' - MACD - Signal
    All values are lists of float or None.
    """
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)

    n = len(prices)
    macd_line = [None] * n
    for i in range(n):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            macd_line[i] = fast_ema[i] - slow_ema[i]

    # EMA of MACD (signal line)
    # Compute only over valid (non-None) stretch starting at first non-None index
    first_valid = next((i for i, v in enumerate(macd_line) if v is not None), None)
    signal_line = [None] * n
    histogram = [None] * n

    if first_valid is None:
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    valid_macd = macd_line[first_valid:]
    k = 2.0 / (signal + 1)

    if len(valid_macd) < signal:
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

    seed = sum(valid_macd[:signal]) / signal
    offset = first_valid + signal - 1
    signal_line[offset] = seed

    for i in range(1, len(valid_macd) - signal + 1):
        idx = offset + i
        signal_line[idx] = valid_macd[signal - 1 + i] * k + signal_line[idx - 1] * (1 - k)

    for i in range(n):
        if macd_line[i] is not None and signal_line[i] is not None:
            histogram[i] = macd_line[i] - signal_line[i]

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger_bands(
    prices: list,
    period: int = 20,
    std_dev: float = 2.0,
) -> dict:
    """
    Bollinger Bands.

    Parameters
    ----------
    prices : list of float
    period : int, default 20
    std_dev : float, default 2.0   multiplier for band width

    Returns
    -------
    dict with keys:
        'upper'  - Upper band
        'middle' - Middle band (SMA)
        'lower'  - Lower band
        'width'  - Band width ((upper - lower) / middle)
        'pct_b'  - %B: (price - lower) / (upper - lower)
    """
    middle = _rolling_mean(prices, period)
    rolling_std = _rolling_stdev(prices, period, population=True)

    n = len(prices)
    upper = [None] * n
    lower = [None] * n
    width = [None] * n
    pct_b = [None] * n

    for i in range(n):
        if middle[i] is not None and rolling_std[i] is not None:
            upper[i] = middle[i] + std_dev * rolling_std[i]
            lower[i] = middle[i] - std_dev * rolling_std[i]
            if middle[i] != 0:
                width[i] = (upper[i] - lower[i]) / middle[i]
            if upper[i] != lower[i]:
                pct_b[i] = (prices[i] - lower[i]) / (upper[i] - lower[i])

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "width": width,
        "pct_b": pct_b,
    }


# ---------------------------------------------------------------------------
# Volatility indicators
# ---------------------------------------------------------------------------

def atr(
    highs: list,
    lows: list,
    closes: list,
    period: int = 14,
) -> list:
    """
    Average True Range (Wilder smoothing).

    True Range = max(H-L, |H-C_prev|, |L-C_prev|)

    Parameters
    ----------
    highs, lows, closes : list of float
    period : int, default 14

    Returns
    -------
    list of float or None
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)
    tr = [None] * n

    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    result = [None] * n
    if n < period:
        return result

    # Seed with simple mean
    seed = sum(tr[1 : period + 1]) / period
    result[period] = seed

    for i in range(period + 1, n):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period

    return result


# ---------------------------------------------------------------------------
# Momentum oscillators
# ---------------------------------------------------------------------------

def stochastic_oscillator(
    highs: list,
    lows: list,
    closes: list,
    k_period: int = 14,
    d_period: int = 3,
) -> dict:
    """
    Stochastic Oscillator (%K and %D).

    %K = (close - lowest_low) / (highest_high - lowest_low) * 100
    %D = SMA(%K, d_period)

    Returns
    -------
    dict with keys 'k' and 'd'
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)
    k = [None] * n

    for i in range(k_period - 1, n):
        hh = max(highs[i - k_period + 1 : i + 1])
        ll = min(lows[i - k_period + 1 : i + 1])
        denom = hh - ll
        if denom == 0:
            k[i] = 50.0
        else:
            k[i] = (closes[i] - ll) / denom * 100.0

    valid_k = [v if v is not None else 0 for v in k]
    d_raw = _rolling_mean(valid_k, d_period)
    # Mask d where k was None
    d = [None] * n
    for i in range(n):
        if k[i] is not None and d_raw[i] is not None:
            d[i] = d_raw[i]

    return {"k": k, "d": d}


def williams_r(
    highs: list,
    lows: list,
    closes: list,
    period: int = 14,
) -> list:
    """
    Williams %R.

    Range: -100 (oversold) to 0 (overbought).
    %R = (highest_high - close) / (highest_high - lowest_low) * -100

    Returns
    -------
    list of float or None
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)
    result = [None] * n

    for i in range(period - 1, n):
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        denom = hh - ll
        if denom == 0:
            result[i] = -50.0
        else:
            result[i] = (hh - closes[i]) / denom * -100.0

    return result


def rate_of_change(prices: list, period: int = 12) -> list:
    """
    Rate of Change (momentum).

    ROC = (price - price_n_periods_ago) / price_n_periods_ago * 100

    Returns
    -------
    list of float or None
    """
    n = len(prices)
    result = [None] * n
    for i in range(period, n):
        if prices[i - period] != 0:
            result[i] = (prices[i] - prices[i - period]) / prices[i - period] * 100.0
    return result


def commodity_channel_index(
    highs: list,
    lows: list,
    closes: list,
    period: int = 20,
) -> list:
    """
    Commodity Channel Index.

    CCI = (typical_price - SMA_tp) / (0.015 * mean_deviation)

    Returns
    -------
    list of float or None
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)
    tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(n)]
    sma_tp = _rolling_mean(tp, period)
    result = [None] * n

    for i in range(period - 1, n):
        window_tp = tp[i - period + 1 : i + 1]
        if sma_tp[i] is None:
            continue
        mean_dev = sum(abs(x - sma_tp[i]) for x in window_tp) / period
        if mean_dev == 0:
            result[i] = 0.0
        else:
            result[i] = (tp[i] - sma_tp[i]) / (0.015 * mean_dev)

    return result


def money_flow_index(
    highs: list,
    lows: list,
    closes: list,
    volumes: list,
    period: int = 14,
) -> list:
    """
    Money Flow Index — a volume-weighted RSI.

    Range 0-100; >80 overbought, <20 oversold.

    Returns
    -------
    list of float or None
    """
    _require_same_length(highs, lows, closes, volumes)
    n = len(closes)
    tp = [(highs[i] + lows[i] + closes[i]) / 3.0 for i in range(n)]
    mf = [tp[i] * volumes[i] for i in range(n)]

    result = [None] * n
    for i in range(period, n):
        pos_flow = sum(
            mf[j] for j in range(i - period + 1, i + 1)
            if tp[j] > tp[j - 1]
        )
        neg_flow = sum(
            mf[j] for j in range(i - period + 1, i + 1)
            if tp[j] < tp[j - 1]
        )
        if neg_flow == 0:
            result[i] = 100.0
        else:
            mfr = pos_flow / neg_flow
            result[i] = 100.0 - (100.0 / (1.0 + mfr))

    return result


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------

def obv(closes: list, volumes: list) -> list:
    """
    On-Balance Volume.

    OBV adds volume on up days and subtracts on down days.

    Returns
    -------
    list of float  (no warm-up; first value equals first volume)
    """
    _require_same_length(closes, volumes)
    n = len(closes)
    result = [0.0] * n
    result[0] = float(volumes[0])
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            result[i] = result[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            result[i] = result[i - 1] - volumes[i]
        else:
            result[i] = result[i - 1]
    return result


def accumulation_distribution(
    highs: list,
    lows: list,
    closes: list,
    volumes: list,
) -> list:
    """
    Accumulation / Distribution Line.

    CLV = ((close - low) - (high - close)) / (high - low)
    A/D = cumulative sum of CLV * volume

    Returns
    -------
    list of float
    """
    _require_same_length(highs, lows, closes, volumes)
    n = len(closes)
    result = [0.0] * n
    running = 0.0
    for i in range(n):
        hl = highs[i] - lows[i]
        if hl == 0:
            clv = 0.0
        else:
            clv = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
        running += clv * volumes[i]
        result[i] = running
    return result


def vwap(
    highs: list,
    lows: list,
    closes: list,
    volumes: list,
) -> list:
    """
    Volume Weighted Average Price (cumulative intraday).

    VWAP = cumulative(typical_price * volume) / cumulative(volume)

    Returns
    -------
    list of float
    """
    _require_same_length(highs, lows, closes, volumes)
    n = len(closes)
    result = [None] * n
    cum_tp_vol = 0.0
    cum_vol = 0.0
    for i in range(n):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        cum_tp_vol += tp * volumes[i]
        cum_vol += volumes[i]
        if cum_vol != 0:
            result[i] = cum_tp_vol / cum_vol
    return result


# ---------------------------------------------------------------------------
# Fibonacci & pivot levels
# ---------------------------------------------------------------------------

def fibonacci_retracement(high: float, low: float) -> dict:
    """
    Classic Fibonacci retracement levels between high and low.

    Returns
    -------
    dict with keys: '0', '23.6', '38.2', '50', '61.8', '78.6', '100'
    and extension levels '127.2', '161.8', '261.8'
    """
    diff = high - low
    levels = {
        "0.0": high,
        "23.6": high - 0.236 * diff,
        "38.2": high - 0.382 * diff,
        "50.0": high - 0.500 * diff,
        "61.8": high - 0.618 * diff,
        "78.6": high - 0.786 * diff,
        "100.0": low,
        "127.2": low - 0.272 * diff,
        "161.8": low - 0.618 * diff,
        "261.8": low - 1.618 * diff,
    }
    return levels


def pivot_points(high: float, low: float, close: float) -> dict:
    """
    Classic, Woodie, Camarilla, and DeMark pivot point calculations.

    Returns
    -------
    dict with sub-dicts for each method:
        'classic', 'woodie', 'camarilla', 'demark'
    Each sub-dict has keys: 'pp', 'r1', 'r2', 'r3', 's1', 's2', 's3'
    (and 'r4'/'s4' for camarilla).
    """
    # Classic
    pp_c = (high + low + close) / 3.0
    classic = {
        "pp": pp_c,
        "r1": 2 * pp_c - low,
        "r2": pp_c + (high - low),
        "r3": high + 2 * (pp_c - low),
        "s1": 2 * pp_c - high,
        "s2": pp_c - (high - low),
        "s3": low - 2 * (high - pp_c),
    }

    # Woodie (pivot based on open of new session — we use close as open proxy)
    pp_w = (high + low + 2 * close) / 4.0
    woodie = {
        "pp": pp_w,
        "r1": 2 * pp_w - low,
        "r2": pp_w + (high - low),
        "r3": high + 2 * (pp_w - low),
        "s1": 2 * pp_w - high,
        "s2": pp_w - (high - low),
        "s3": low - 2 * (high - pp_w),
    }

    # Camarilla
    diff = high - low
    camarilla = {
        "pp": (high + low + close) / 3.0,
        "r1": close + diff * 1.1 / 12.0,
        "r2": close + diff * 1.1 / 6.0,
        "r3": close + diff * 1.1 / 4.0,
        "r4": close + diff * 1.1 / 2.0,
        "s1": close - diff * 1.1 / 12.0,
        "s2": close - diff * 1.1 / 6.0,
        "s3": close - diff * 1.1 / 4.0,
        "s4": close - diff * 1.1 / 2.0,
    }

    # DeMark
    if close < high:
        x = high + 2 * low + close
    elif close > high:
        x = 2 * high + low + close
    else:
        x = high + low + 2 * close
    pp_d = x / 4.0
    demark = {
        "pp": pp_d,
        "r1": x / 2.0 - low,
        "s1": x / 2.0 - high,
    }

    return {
        "classic": classic,
        "woodie": woodie,
        "camarilla": camarilla,
        "demark": demark,
    }


# ---------------------------------------------------------------------------
# Ichimoku Cloud
# ---------------------------------------------------------------------------

def ichimoku_cloud(
    highs: list,
    lows: list,
    closes: list,
    tenkan: int = 9,
    kijun: int = 26,
    senkou: int = 52,
) -> dict:
    """
    Ichimoku Kinko Hyo cloud components.

    Returns
    -------
    dict with keys:
        'tenkan_sen'    - Conversion line
        'kijun_sen'     - Base line
        'senkou_span_a' - Leading Span A (shifted forward by kijun periods)
        'senkou_span_b' - Leading Span B (shifted forward by kijun periods)
        'chikou_span'   - Lagging Span (shifted back by kijun periods)
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)

    def donchian_mid(period, i):
        if i < period - 1:
            return None
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        return (hh + ll) / 2.0

    tenkan_sen = [donchian_mid(tenkan, i) for i in range(n)]
    kijun_sen = [donchian_mid(kijun, i) for i in range(n)]

    # Senkou Span A = (tenkan + kijun) / 2, projected kijun periods forward
    raw_span_a = [None] * n
    for i in range(n):
        if tenkan_sen[i] is not None and kijun_sen[i] is not None:
            raw_span_a[i] = (tenkan_sen[i] + kijun_sen[i]) / 2.0

    senkou_span_a = [None] * (n + kijun)
    for i in range(n):
        if raw_span_a[i] is not None:
            senkou_span_a[i + kijun] = raw_span_a[i]

    # Senkou Span B = donchian(senkou period), projected kijun periods forward
    raw_span_b = [donchian_mid(senkou, i) for i in range(n)]
    senkou_span_b = [None] * (n + kijun)
    for i in range(n):
        if raw_span_b[i] is not None:
            senkou_span_b[i + kijun] = raw_span_b[i]

    # Chikou Span = close shifted back kijun periods
    chikou_span = [None] * n
    for i in range(n):
        shifted = i - kijun
        if shifted >= 0:
            chikou_span[shifted] = closes[i]

    return {
        "tenkan_sen": tenkan_sen,
        "kijun_sen": kijun_sen,
        "senkou_span_a": senkou_span_a[:n],
        "senkou_span_b": senkou_span_b[:n],
        "chikou_span": chikou_span,
    }


# ---------------------------------------------------------------------------
# ADX / Directional Movement
# ---------------------------------------------------------------------------

def average_directional_index(
    highs: list,
    lows: list,
    closes: list,
    period: int = 14,
) -> dict:
    """
    Average Directional Index with +DI and -DI.

    ADX > 25 indicates a trending market.
    +DI > -DI suggests bullish trend; -DI > +DI suggests bearish.

    Returns
    -------
    dict with keys 'adx', 'plus_di', 'minus_di'
    All values are lists of float or None.
    """
    _require_same_length(highs, lows, closes)
    n = len(closes)

    tr_list = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n

    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

        tr_list[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    def wilder_smooth(data, p):
        result = [None] * n
        if n <= p:
            return result
        seed = sum(data[1 : p + 1])
        result[p] = seed
        for i in range(p + 1, n):
            result[i] = result[i - 1] - result[i - 1] / p + data[i]
        return result

    smoothed_tr = wilder_smooth(tr_list, period)
    smoothed_pdm = wilder_smooth(plus_dm, period)
    smoothed_mdm = wilder_smooth(minus_dm, period)

    plus_di = [None] * n
    minus_di = [None] * n
    dx = [None] * n

    for i in range(period, n):
        if smoothed_tr[i] and smoothed_tr[i] != 0:
            plus_di[i] = 100.0 * smoothed_pdm[i] / smoothed_tr[i]
            minus_di[i] = 100.0 * smoothed_mdm[i] / smoothed_tr[i]
            di_sum = plus_di[i] + minus_di[i]
            if di_sum != 0:
                dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / di_sum

    # ADX = smoothed DX
    adx = [None] * n
    first_dx = next((i for i, v in enumerate(dx) if v is not None), None)
    if first_dx is not None and first_dx + period <= n:
        dx_values = [v for v in dx[first_dx:first_dx + period] if v is not None]
        if len(dx_values) == period:
            adx[first_dx + period - 1] = sum(dx_values) / period
            for i in range(first_dx + period, n):
                if dx[i] is not None and adx[i - 1] is not None:
                    adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}


# ---------------------------------------------------------------------------
# Parabolic SAR
# ---------------------------------------------------------------------------

def parabolic_sar(
    highs: list,
    lows: list,
    af_start: float = 0.02,
    af_max: float = 0.2,
) -> list:
    """
    Parabolic Stop and Reverse (SAR).

    Returns
    -------
    list of float  — SAR value for each bar (first bar is None).
    Above price = bearish (short); below price = bullish (long).
    """
    _require_same_length(highs, lows)
    n = len(highs)
    if n < 2:
        return [None] * n

    result = [None] * n
    # Initial direction: long if first bar closes higher (we compare H)
    bull = highs[1] >= highs[0]
    af = af_start
    ep = highs[1] if bull else lows[1]
    sar = lows[0] if bull else highs[0]
    result[1] = sar

    for i in range(2, n):
        if bull:
            sar = sar + af * (ep - sar)
            # SAR cannot be above the two prior lows
            sar = min(sar, lows[i - 1], lows[i - 2] if i >= 2 else lows[i - 1])
            if lows[i] < sar:
                # Flip to bear
                bull = False
                sar = ep
                ep = lows[i]
                af = af_start
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_start, af_max)
        else:
            sar = sar + af * (ep - sar)
            sar = max(sar, highs[i - 1], highs[i - 2] if i >= 2 else highs[i - 1])
            if highs[i] > sar:
                # Flip to bull
                bull = True
                sar = ep
                ep = highs[i]
                af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_start, af_max)

        result[i] = sar

    return result


# ---------------------------------------------------------------------------
# Comprehensive trend analysis
# ---------------------------------------------------------------------------

def analyze_trend(prices: list) -> dict:
    """
    Comprehensive trend analysis combining multiple indicators.

    Parameters
    ----------
    prices : list of float  (at least 60 data points recommended)

    Returns
    -------
    dict with keys:
        'direction'          - 'bullish', 'bearish', or 'sideways'
        'strength'           - 0.0 to 1.0 (0 = no trend, 1 = very strong)
        'signal'             - 'buy', 'sell', or 'neutral'
        'confidence'         - 0-100 (%) composite confidence
        'indicators'         - sub-dict with latest values of each indicator
        'support_levels'     - list of detected support prices
        'resistance_levels'  - list of detected resistance prices
        'summary'            - human-readable string
    """
    n = len(prices)
    if n < 20:
        return {
            "direction": "unknown",
            "strength": 0.0,
            "signal": "neutral",
            "confidence": 0,
            "indicators": {},
            "support_levels": [],
            "resistance_levels": [],
            "summary": "Insufficient data (need >= 20 price points)",
        }

    # Compute indicators
    sma20 = sma(prices, 20)
    sma50 = sma(prices, min(50, n))
    ema12 = ema(prices, 12)
    ema26 = ema(prices, min(26, n))
    rsi14 = rsi(prices, min(14, n - 1))
    bb = bollinger_bands(prices, min(20, n))
    macd_data = macd(prices)
    roc12 = rate_of_change(prices, min(12, n - 1))

    latest = prices[-1]
    indicators = {}

    # --- SMA alignment ---
    sma20_val = next((v for v in reversed(sma20) if v is not None), None)
    sma50_val = next((v for v in reversed(sma50) if v is not None), None)
    ema12_val = next((v for v in reversed(ema12) if v is not None), None)
    ema26_val = next((v for v in reversed(ema26) if v is not None), None)
    rsi_val = next((v for v in reversed(rsi14) if v is not None), None)
    macd_val = next((v for v in reversed(macd_data["macd"]) if v is not None), None)
    signal_val = next((v for v in reversed(macd_data["signal"]) if v is not None), None)
    hist_val = next((v for v in reversed(macd_data["histogram"]) if v is not None), None)
    roc_val = next((v for v in reversed(roc12) if v is not None), None)
    upper_bb = next((v for v in reversed(bb["upper"]) if v is not None), None)
    lower_bb = next((v for v in reversed(bb["lower"]) if v is not None), None)
    mid_bb = next((v for v in reversed(bb["middle"]) if v is not None), None)

    indicators["sma_20"] = sma20_val
    indicators["sma_50"] = sma50_val
    indicators["ema_12"] = ema12_val
    indicators["ema_26"] = ema26_val
    indicators["rsi_14"] = rsi_val
    indicators["macd"] = macd_val
    indicators["macd_signal"] = signal_val
    indicators["macd_histogram"] = hist_val
    indicators["roc_12"] = roc_val
    indicators["bollinger_upper"] = upper_bb
    indicators["bollinger_lower"] = lower_bb
    indicators["bollinger_middle"] = mid_bb

    # --- Scoring ---
    bullish_points = 0
    bearish_points = 0
    total_checks = 0

    def score(cond_bull, cond_bear, weight=1):
        nonlocal bullish_points, bearish_points, total_checks
        if cond_bull:
            bullish_points += weight
        if cond_bear:
            bearish_points += weight
        total_checks += weight

    # Price vs MAs
    if sma20_val:
        score(latest > sma20_val, latest < sma20_val, 2)
    if sma50_val:
        score(latest > sma50_val, latest < sma50_val, 2)
    if ema12_val and ema26_val:
        score(ema12_val > ema26_val, ema12_val < ema26_val, 2)

    # RSI
    if rsi_val is not None:
        score(40 < rsi_val < 70, rsi_val < 40 or rsi_val > 70, 1)
        score(rsi_val > 50, rsi_val < 50, 1)

    # MACD
    if hist_val is not None:
        score(hist_val > 0, hist_val < 0, 2)
    if macd_val is not None and signal_val is not None:
        score(macd_val > signal_val, macd_val < signal_val, 1)

    # ROC
    if roc_val is not None:
        score(roc_val > 0, roc_val < 0, 1)

    # Bollinger
    if upper_bb and lower_bb and mid_bb:
        score(latest > mid_bb, latest < mid_bb, 1)

    # Direction & strength
    if total_checks == 0:
        direction = "sideways"
        strength = 0.0
        confidence = 0
    else:
        net = (bullish_points - bearish_points) / total_checks
        if net > 0.2:
            direction = "bullish"
        elif net < -0.2:
            direction = "bearish"
        else:
            direction = "sideways"
        strength = min(abs(net), 1.0)
        confidence = int(strength * 100)

    # Signal
    if direction == "bullish" and strength > 0.5:
        signal = "buy"
    elif direction == "bearish" and strength > 0.5:
        signal = "sell"
    else:
        signal = "neutral"

    # Support / resistance (simple swing highs/lows)
    support_levels = []
    resistance_levels = []
    window = 5
    for i in range(window, n - window):
        local_low = min(prices[i - window : i + window + 1])
        local_high = max(prices[i - window : i + window + 1])
        if prices[i] == local_low:
            support_levels.append(round(prices[i], 2))
        if prices[i] == local_high:
            resistance_levels.append(round(prices[i], 2))

    # Deduplicate (cluster within 1%)
    def cluster(levels):
        if not levels:
            return []
        levels = sorted(set(levels))
        clustered = [levels[0]]
        for lv in levels[1:]:
            if abs(lv - clustered[-1]) / clustered[-1] > 0.01:
                clustered.append(lv)
        return clustered

    support_levels = cluster(support_levels)[-5:]
    resistance_levels = cluster(resistance_levels)[-5:]

    summary = (
        f"Trend is {direction} with {confidence}% confidence. "
        f"Signal: {signal}. "
        f"RSI={rsi_val:.1f}" if rsi_val else f"Trend is {direction}."
    )

    return {
        "direction": direction,
        "strength": round(strength, 4),
        "signal": signal,
        "confidence": confidence,
        "indicators": indicators,
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
        "summary": summary,
    }
