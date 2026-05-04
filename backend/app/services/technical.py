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

FIBO_RETRACEMENTS = [0.236, 0.382, 0.500, 0.618, 0.786]
FIBO_EXTENSIONS = [1.272, 1.618]


def find_fibonacci_levels(df: pd.DataFrame) -> list[dict]:
    """
    Find the last major swing (6-month high/low) and calculate
    Fibonacci retracements (orange) and extensions (yellow).
    """
    six_months = df.iloc[-126:]  # ~6 months of trading days
    swing_high = float(six_months["High"].max())
    swing_low = float(six_months["Low"].min())
    swing_range = swing_high - swing_low

    if swing_range <= 0:
        return []

    results = []

    # Retracements (from swing high down to low)
    for ratio in FIBO_RETRACEMENTS:
        price = swing_high - ratio * swing_range
        results.append({
            "price": round(price, 4),
            "label": f"Fib {ratio*100:.1f}%",
            "color": "#f97316",  # orange
        })

    # Extensions (beyond swing low, measuring from high)
    for ratio in FIBO_EXTENSIONS:
        price_below = swing_low - (ratio - 1.0) * swing_range
        results.append({
            "price": round(price_below, 4),
            "label": f"Ext {ratio*100:.1f}%",
            "color": "#eab308",  # yellow
        })

    # Extension above swing high
    for ratio in FIBO_EXTENSIONS:
        price_above = swing_high + (ratio - 1.0) * swing_range
        results.append({
            "price": round(price_above, 4),
            "label": f"Ext {ratio*100:.1f}% Up",
            "color": "#eab308",  # yellow
        })

    return results


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
# Master function
# ---------------------------------------------------------------------------

def calculate_all_technical(df: pd.DataFrame) -> dict:
    """Run all technical analysis and return structured results."""
    sr_levels = find_horizontal_sr(df)
    fib_levels = find_fibonacci_levels(df)
    ma_df = calculate_moving_averages(df)
    pivot_pts = calculate_pivot_points(df)
    trendlines = calculate_trendlines(df)

    # Build MA data as list of dicts
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
    }
