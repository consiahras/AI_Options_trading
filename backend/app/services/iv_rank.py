import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


def _historical_volatility(df: pd.DataFrame, window: int = 30) -> float:
    """Calculate annualised historical volatility from daily close prices."""
    closes = df["Close"].dropna()
    if len(closes) < window + 1:
        return 0.25  # fallback 25%
    log_returns = np.log(closes / closes.shift(1)).dropna()
    recent = log_returns.iloc[-window:]
    hv = float(recent.std() * np.sqrt(252))
    return max(hv, 0.01)


def _iv_from_options_chain(chain: dict, current_price: float) -> Optional[float]:
    """
    Extract near-ATM implied volatility from options chain.
    Uses the average of call+put IV for the strike nearest to current price.
    """
    try:
        calls = chain["calls"]
        puts = chain["puts"]

        # Filter to strikes near ATM (within 10%)
        atm_range = current_price * 0.10
        near_calls = calls[
            (calls["strike"] >= current_price - atm_range) &
            (calls["strike"] <= current_price + atm_range) &
            (calls["impliedVolatility"] > 0)
        ]
        near_puts = puts[
            (puts["strike"] >= current_price - atm_range) &
            (puts["strike"] <= current_price + atm_range) &
            (puts["impliedVolatility"] > 0)
        ]

        ivs = []
        if not near_calls.empty:
            # Pick the call closest to ATM
            near_calls = near_calls.copy()
            near_calls["dist"] = (near_calls["strike"] - current_price).abs()
            best_call = near_calls.nsmallest(1, "dist")
            ivs.append(float(best_call["impliedVolatility"].iloc[0]))

        if not near_puts.empty:
            near_puts = near_puts.copy()
            near_puts["dist"] = (near_puts["strike"] - current_price).abs()
            best_put = near_puts.nsmallest(1, "dist")
            ivs.append(float(best_put["impliedVolatility"].iloc[0]))

        if ivs:
            return float(np.mean(ivs))
        return None
    except Exception as e:
        logger.error(f"Error extracting IV from chain: {e}")
        return None


def _rolling_historical_volatility_series(df: pd.DataFrame, window: int = 30) -> pd.Series:
    """Return a rolling HV series to estimate 52-week IV range."""
    closes = df["Close"].dropna()
    log_returns = np.log(closes / closes.shift(1))
    rolling_hv = log_returns.rolling(window=window).std() * np.sqrt(252)
    return rolling_hv.dropna()


def calculate_iv_rank(
    df: pd.DataFrame,
    options_chain: Optional[dict],
    current_price: float,
) -> tuple[float, float]:
    """
    Calculate current IV and IV Rank (0-100).

    Returns:
        (iv, iv_rank) — both floats
    """
    # 1. Try to get current IV from options chain
    current_iv: Optional[float] = None
    if options_chain is not None:
        current_iv = _iv_from_options_chain(options_chain, current_price)

    # 2. Fall back to 30-day historical volatility
    if current_iv is None or current_iv <= 0:
        current_iv = _historical_volatility(df, window=30)
        logger.info("Using historical volatility as IV fallback")

    # 3. Calculate 52-week IV range using rolling HV series
    rolling_hv = _rolling_historical_volatility_series(df, window=30)

    if len(rolling_hv) < 2:
        return current_iv, 50.0  # no range data, neutral IVR

    iv_52w_low = float(rolling_hv.min())
    iv_52w_high = float(rolling_hv.max())

    # 4. Clamp current_iv so it's within reasonable range
    current_iv = max(current_iv, iv_52w_low)
    current_iv = min(current_iv, iv_52w_high * 1.5)

    # 5. IV Rank
    iv_range = iv_52w_high - iv_52w_low
    if iv_range < 0.001:
        iv_rank = 50.0
    else:
        iv_rank = (current_iv - iv_52w_low) / iv_range * 100.0
        iv_rank = max(0.0, min(100.0, iv_rank))

    return round(current_iv, 4), round(iv_rank, 2)
