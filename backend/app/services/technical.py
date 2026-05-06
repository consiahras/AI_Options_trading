import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Horizontal Support / Resistance
# ---------------------------------------------------------------------------

def find_horizontal_sr(df: pd.DataFrame, lookback: int = 10, max_levels: int = 5) -> list[dict]:
    """
    Find horizontal S/R levels by detecting local pivot highs (resistance)
    and pivot lows (support) using a lookback window.
    Returns the top levels closest to current price.
    """
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values
    current_price = closes[-1]

    pivot_highs = []
    pivot_lows = []

    for i in range(lookback, len(df) - lookback):
        window_high = highs[i - lookback:i + lookback + 1]
        if highs[i] == max(window_high):
            pivot_highs.append(highs[i])

        window_low = lows[i - lookback:i + lookback + 1]
        if lows[i] == min(window_low):
            pivot_lows.append(lows[i])

    # Cluster nearby levels (within 1%)
    def cluster(levels: list[float], threshold: float = 0.01) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for level in levels[1:]:
            if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [float(np.mean(c)) for c in clusters]

    resistance_levels = cluster(pivot_highs)
    support_levels = cluster(pivot_lows)

    # Sort by distance to current price
    resistance_levels = sorted(resistance_levels, key=lambda x: abs(x - current_price))[:max_levels]
    support_levels = sorted(support_levels, key=lambda x: abs(x - current_price))[:max_levels]

    results = []
    for lvl in resistance_levels:
        results.append({
            "price": round(lvl, 4),
            "level_type": "resistance",
            "color": "#ef4444",  # red
            "label": f"R {lvl:.2f}",
        })
    for lvl in support_levels:
        results.append({
            "price": round(lvl, 4),
            "level_type": "support",
            "color": "#22c55e",  # green
            "label": f"S {lvl:.2f}",
        })

    return results


# ---------------------------------------------------------------------------
# Fibonacci Levels
# ---------------------------------------------------------------------------

FIBO_LEVELS = [
    (0.0,   "0% — Low",  "#94a3b8"),   # slate  — anchor bottom
    (0.236, "23.6%",     "#f97316"),   # orange
    (0.382, "38.2%",     "#f97316"),
    (0.500, "50.0%",     "#fbbf24"),   # amber  — midpoint
    (0.618, "61.8%",     "#f97316"),
    (0.786, "78.6%",     "#f97316"),
    (1.0,   "100% — High","#94a3b8"),  # slate  — anchor top
]


def find_fibonacci_levels(df: pd.DataFrame) -> list[dict]:
    """
    Levels are measured upward from the 6-month swing low (0%) to the
    swing high (100%): price = swing_low + ratio * range.
    This is direction-neutral — the 0% and 100% anchors mark the extremes,
    and the intermediate levels are the classic retracement zones.
    """
    six_months = df.iloc[-126:]
    swing_high = float(six_months["High"].max())
    swing_low  = float(six_months["Low"].min())
    swing_range = swing_high - swing_low

    if swing_range <= 0:
        return []

    return [
        {
            "price": round(swing_low + ratio * swing_range, 4),
            "label": label,
            "color": color,
        }
        for ratio, label, color in FIBO_LEVELS
    ]


# ---------------------------------------------------------------------------
# Pivot price markers (dots on chart at significant highs/lows)
# ---------------------------------------------------------------------------

def find_pivot_markers(df: pd.DataFrame, lookback: int = 15, max_per_type: int = 10) -> list[dict]:
    """
    Return the date + price of the most significant local pivot highs and lows.
    These are rendered as small dots on the price chart so the user can see
    which price levels have historically acted as support/resistance.
    """
    highs  = df["High"].values
    lows   = df["Low"].values
    dates  = df.index

    pivot_highs = []
    pivot_lows  = []

    for i in range(lookback, len(df) - lookback):
        if highs[i] == max(highs[i - lookback:i + lookback + 1]):
            pivot_highs.append({
                "date":  dates[i].strftime("%Y-%m-%d"),
                "price": round(float(highs[i]), 2),
                "type":  "high",
            })
        if lows[i] == min(lows[i - lookback:i + lookback + 1]):
            pivot_lows.append({
                "date":  dates[i].strftime("%Y-%m-%d"),
                "price": round(float(lows[i]), 2),
                "type":  "low",
            })

    # Keep only the most recent max_per_type of each
    return pivot_highs[-max_per_type:] + pivot_lows[-max_per_type:]


# ---------------------------------------------------------------------------
# Moving Averages
# ---------------------------------------------------------------------------

def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate 50, 100, and 200 day SMAs.
    Returns a DataFrame with columns: date, ma50, ma100, ma200.
    """
    result = pd.DataFrame(index=df.index)
    result["date"] = df.index.strftime("%Y-%m-%d")
    result["ma50"] = df["Close"].rolling(window=50).mean()
    result["ma100"] = df["Close"].rolling(window=100).mean()
    result["ma200"] = df["Close"].rolling(window=200).mean()
    return result


# ---------------------------------------------------------------------------
# Pivot Points (Classic Daily)
# ---------------------------------------------------------------------------

def calculate_pivot_points(df: pd.DataFrame) -> Optional[dict]:
    """
    Classic pivot points calculated from the most recent complete trading day.
    P = (H+L+C)/3, R1=2P-L, R2=P+(H-L), S1=2P-H, S2=P-(H-L)
    """
    if len(df) < 2:
        return None

    last = df.iloc[-1]
    H = float(last["High"])
    L = float(last["Low"])
    C = float(last["Close"])

    P = (H + L + C) / 3
    R1 = 2 * P - L
    R2 = P + (H - L)
    S1 = 2 * P - H
    S2 = P - (H - L)

    return {
        "P": round(P, 4),
        "R1": round(R1, 4),
        "R2": round(R2, 4),
        "S1": round(S1, 4),
        "S2": round(S2, 4),
    }


# ---------------------------------------------------------------------------
# Trendlines
# ---------------------------------------------------------------------------

def _find_pivot_indices(values: np.ndarray, lookback: int = 10) -> list[int]:
    indices = []
    for i in range(lookback, len(values) - lookback):
        window = values[i - lookback:i + lookback + 1]
        if values[i] == max(window) or values[i] == min(window):
            indices.append(i)
    return indices


def calculate_trendlines(df: pd.DataFrame, lookback: int = 10) -> list[dict]:
    """
    Fit least-squares trendlines through pivot highs (resistance/magenta)
    and pivot lows (support/magenta).
    Returns slope, intercept, start_date, end_date for each line.
    """
    dates = df.index
    highs = df["High"].values
    lows = df["Low"].values

    results = []

    def fit_line(indices: list[int], values: np.ndarray, line_type: str) -> Optional[dict]:
        if len(indices) < 2:
            return None
        x = np.array(indices, dtype=float)
        y = values[indices]
        coeffs = np.polyfit(x, y, 1)
        slope = float(coeffs[0])
        intercept = float(coeffs[1])
        start_idx = indices[0]
        end_idx = indices[-1]
        return {
            "slope": round(slope, 6),
            "intercept": round(intercept, 4),
            "start_date": dates[start_idx].strftime("%Y-%m-%d"),
            "end_date": dates[end_idx].strftime("%Y-%m-%d"),
            "line_type": line_type,
            "color": "#e879f9",  # magenta
        }

    pivot_high_idx = []
    for i in range(lookback, len(highs) - lookback):
        window = highs[i - lookback:i + lookback + 1]
        if highs[i] == max(window):
            pivot_high_idx.append(i)

    pivot_low_idx = []
    for i in range(lookback, len(lows) - lookback):
        window = lows[i - lookback:i + lookback + 1]
        if lows[i] == min(window):
            pivot_low_idx.append(i)

    tl_high = fit_line(pivot_high_idx, highs, "resistance")
    if tl_high:
        results.append(tl_high)

    tl_low = fit_line(pivot_low_idx, lows, "support")
    if tl_low:
        results.append(tl_low)

    return results


# ---------------------------------------------------------------------------
# Stochastic Oscillator
# ---------------------------------------------------------------------------

def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> list[dict]:
    """
    Stochastic Oscillator: %K = (Close - LowestLow) / (HighestHigh - LowestLow) * 100
    %D = 3-period SMA of %K.
    """
    low_min = df["Low"].rolling(window=k_period).min()
    high_max = df["High"].rolling(window=k_period).max()
    denom = high_max - low_min
    k = ((df["Close"] - low_min) / denom.replace(0, np.nan)) * 100
    d = k.rolling(window=d_period).mean()

    results = []
    for date, k_val, d_val in zip(df.index, k, d):
        results.append({
            "date": date.strftime("%Y-%m-%d"),
            "k": None if pd.isna(k_val) else round(float(k_val), 2),
            "d": None if pd.isna(d_val) else round(float(d_val), 2),
        })
    return results


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def calculate_all_technical(df: pd.DataFrame) -> dict:
    """Run all technical analysis and return structured results."""
    sr_levels = find_horizontal_sr(df)
    fib_levels = find_fibonacci_levels(df)
    ma_df = calculate_moving_averages(df)
    pivot_pts = calculate_pivot_points(df)
    trendlines = calculate_trendlines(df)
    stochastic    = calculate_stochastic(df)
    pivot_markers = find_pivot_markers(df)

    ma_data = []
    for idx, row in ma_df.iterrows():
        ma_data.append({
            "date": row["date"],
            "ma50": None if pd.isna(row["ma50"]) else round(float(row["ma50"]), 4),
            "ma100": None if pd.isna(row["ma100"]) else round(float(row["ma100"]), 4),
            "ma200": None if pd.isna(row["ma200"]) else round(float(row["ma200"]), 4),
        })

    return {
        "sr_levels": sr_levels,
        "fibonacci_levels": fib_levels,
        "ma_data": ma_data,
        "pivot_points": pivot_pts,
        "trendlines": trendlines,
        "stochastic": stochastic,
        "pivot_markers": pivot_markers,
    }
