import logging
import numpy as np
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)


def _historical_volatility(df: pd.DataFrame, window: int = 30) -> float:
    """Annualised historical volatility from daily closes."""
    closes = df["Close"].dropna()
    if len(closes) < window + 1:
        return 0.25
    log_returns = np.log(closes / closes.shift(1)).dropna()
    hv = float(log_returns.iloc[-window:].std() * np.sqrt(252))
    return max(hv, 0.01)


def _iv_from_options_chain(chain: dict, current_price: float) -> Optional[float]:
    """Near-ATM implied volatility averaged from closest call + put."""
    try:
        calls = chain["calls"]
        puts  = chain["puts"]
        atm_range = current_price * 0.10

        near_calls = calls[
            (calls["strike"] >= current_price - atm_range) &
            (calls["strike"] <= current_price + atm_range) &
            (calls["impliedVolatility"] > 0.01)
        ].copy()
        near_puts = puts[
            (puts["strike"] >= current_price - atm_range) &
            (puts["strike"] <= current_price + atm_range) &
            (puts["impliedVolatility"] > 0.01)
        ].copy()

        ivs = []
        if not near_calls.empty:
            near_calls["dist"] = (near_calls["strike"] - current_price).abs()
            ivs.append(float(near_calls.nsmallest(1, "dist")["impliedVolatility"].iloc[0]))
        if not near_puts.empty:
            near_puts["dist"] = (near_puts["strike"] - current_price).abs()
            ivs.append(float(near_puts.nsmallest(1, "dist")["impliedVolatility"].iloc[0]))

        return float(np.mean(ivs)) if ivs else None
    except Exception as e:
        logger.error(f"Error extracting IV from chain: {e}")
        return None


def _rolling_hv_series(df: pd.DataFrame, window: int = 30) -> pd.Series:
    """Rolling annualised HV series — used for the 52-week range."""
    closes = df["Close"].dropna()
    log_returns = np.log(closes / closes.shift(1))
    return (log_returns.rolling(window=window).std() * np.sqrt(252)).dropna()


def calculate_iv_rank(
    df: pd.DataFrame,
    options_chain: Optional[dict],
    current_price: float,
) -> tuple[float, float]:
    """
    Returns (pricing_iv, iv_rank).

    pricing_iv — options chain IV (or HV fallback) used in Black-Scholes.
    iv_rank    — 0-100, position of current rolling HV within its 52-week
                 HV range. Consistent measurement: no apples-vs-oranges
                 comparison between options IV and historical HV range.
    """
    # Pricing IV (best estimate for Black-Scholes)
    pricing_iv: Optional[float] = None
    if options_chain is not None:
        pricing_iv = _iv_from_options_chain(options_chain, current_price)
    if not pricing_iv or pricing_iv <= 0:
        pricing_iv = _historical_volatility(df, window=30)
        logger.info("Using HV as pricing IV fallback")

    # Rolling HV series for rank calculation (keeps measurement consistent)
    rolling_hv = _rolling_hv_series(df, window=30)

    if len(rolling_hv) < 10:
        return round(pricing_iv, 4), 50.0

    current_hv  = float(rolling_hv.iloc[-1])
    iv_52w_low  = float(rolling_hv.min())
    iv_52w_high = float(rolling_hv.max())
    iv_range    = iv_52w_high - iv_52w_low

    if iv_range < 0.001:
        return round(pricing_iv, 4), 50.0

    iv_rank = (current_hv - iv_52w_low) / iv_range * 100.0
    iv_rank = max(0.0, min(100.0, iv_rank))

    logger.info(
        f"IVR — pricing_iv={pricing_iv:.3f} current_hv={current_hv:.3f} "
        f"range=[{iv_52w_low:.3f}, {iv_52w_high:.3f}] IVR={iv_rank:.1f}"
    )
    return round(pricing_iv, 4), round(iv_rank, 2)
