import logging
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    AnalysisResponse, GreeksData, StrategyRecommendation
)
from app.services import data_fetcher, black_scholes, iv_rank

logger = logging.getLogger(__name__)
router = APIRouter()


def _compute_directional_bias(df: pd.DataFrame) -> str:
    """
    Returns 'bullish', 'bearish', or 'neutral' from MA cross + Stochastic.
    MA50 vs MA200 is the primary signal; Stochastic resolves mixed cases.
    """
    closes = df["Close"]
    highs  = df["High"]
    lows   = df["Low"]

    # MA cross
    ma50  = closes.rolling(50).mean().dropna()
    ma200 = closes.rolling(200).mean().dropna()
    if len(ma50) == 0 or len(ma200) == 0:
        ma_signal = "neutral"
    elif ma50.iloc[-1] > ma200.iloc[-1]:
        ma_signal = "bullish"
    else:
        ma_signal = "bearish"

    # Stochastic (14, 3, 3)
    k_period, d_period = 14, 3
    lowest  = lows.rolling(k_period).min()
    highest = highs.rolling(k_period).max()
    raw_k   = ((closes - lowest) / (highest - lowest + 1e-10) * 100)
    smooth_k = raw_k.rolling(d_period).mean().dropna()
    smooth_d = smooth_k.rolling(d_period).mean().dropna()

    if len(smooth_k) < 2 or len(smooth_d) < 2:
        stoch = "neutral"
    else:
        lk, ld = smooth_k.iloc[-1], smooth_d.iloc[-1]
        pk, pd_ = smooth_k.iloc[-2], smooth_d.iloc[-2]
        if lk > 80:
            stoch = "overbought"
        elif lk < 20:
            stoch = "oversold"
        elif pk < pd_ and lk > ld:
            stoch = "bullish"
        elif pk > pd_ and lk < ld:
            stoch = "bearish"
        else:
            stoch = "neutral"

    # Combine: MA is primary trend, stoch modulates
    if ma_signal == "bullish":
        return "neutral" if stoch in ("overbought", "bearish") else "bullish"
    elif ma_signal == "bearish":
        return "neutral" if stoch in ("oversold", "bullish") else "bearish"
    else:
        if stoch in ("bullish", "oversold"):  return "bullish"
        if stoch in ("bearish", "overbought"): return "bearish"
        return "neutral"


def _ivr_signal(ivr: float, strategy: str) -> str:
    """IVR signal label with the actual IVR number."""
    is_buy = strategy in ("Buy Call", "Buy Put")
    n = f"{ivr:.1f}"
    if ivr < 30:
        return f"Low ✓ ({n})" if is_buy else f"Low ✗ ({n})"
    elif ivr > 50:
        return f"High ✓ ({n})" if not is_buy else f"High ✗ ({n})"
    else:
        return f"Neutral ({n})"


def _recommendation(direction: str, ivr: float, strategy: str) -> str:
    """
    Combined recommendation from directional bias + IV Rank.

    Direction (from MA cross + Stochastic) determines WHICH strategies make
    sense; IVR determines whether IV is cheap (buy) or expensive (sell).
    """
    if strategy == "Buy Call":
        if direction == "bearish":                  return "AVOID"
        if direction == "bullish" and ivr < 30:     return "CONSIDER"
        return "CAUTION"

    elif strategy == "Buy Put":
        if direction == "bullish":                  return "AVOID"
        if direction == "bearish" and ivr < 30:     return "CONSIDER"
        return "CAUTION"

    elif strategy == "Sell CSP":
        if direction == "bearish":                  return "AVOID"
        if direction == "bullish":                  return "CONSIDER"
        if ivr > 50:                                return "CONSIDER"
        return "CAUTION"

    elif strategy == "Sell Covered Call":
        if direction == "bullish":                  return "CAUTION"
        if direction == "bearish" and ivr > 50:     return "CONSIDER"
        if direction == "neutral" and ivr > 50:     return "CONSIDER"
        return "CAUTION"

    return "CAUTION"


def _sr_context(strategy: str, direction: str) -> str:
    """Context message combining strategy type and directional bias."""
    table = {
        ("Buy Call",          "bullish"): "Bullish trend — enter near support",
        ("Buy Call",          "bearish"): "Against trend — wait for reversal",
        ("Buy Call",          "neutral"): "Mixed signals — check nearby support",
        ("Buy Put",           "bearish"): "Bearish trend — enter near resistance",
        ("Buy Put",           "bullish"): "Against trend — wait for reversal",
        ("Buy Put",           "neutral"): "Mixed signals — check resistance",
        ("Sell CSP",          "bullish"): "Bullish — sell put below support",
        ("Sell CSP",          "bearish"): "Bearish trend — avoid assignment risk",
        ("Sell CSP",          "neutral"): "Strike should be below support",
        ("Sell Covered Call", "bullish"): "Bullish trend — selling CC caps upside",
        ("Sell Covered Call", "bearish"): "Bearish — sell call near resistance",
        ("Sell Covered Call", "neutral"): "Strike near resistance is ideal",
    }
    return table.get((strategy, direction), "Review chart levels")


@router.get("/analysis/{ticker}", response_model=AnalysisResponse)
def get_analysis(ticker: str):
    ticker = ticker.upper()

    df = data_fetcher.fetch_historical_data(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    current_price = float(df["Close"].iloc[-1])

    options_chain = data_fetcher.fetch_options_chain(ticker)

    iv, ivr      = iv_rank.calculate_iv_rank(df, options_chain, current_price)
    direction    = _compute_directional_bias(df)
    bs           = black_scholes.calculate_all(current_price, iv)

    logger.info(f"{ticker} — direction={direction} IVR={ivr:.1f} IV={iv*100:.1f}%")

    greeks = GreeksData(
        delta_call=bs["delta_call"],
        delta_put=bs["delta_put"],
        theta_call=bs["theta_call"],
        theta_put=bs["theta_put"],
        gamma=bs["gamma"],
        vega=bs["vega"],
    )

    strategies = []
    for name in ["Buy Call", "Buy Put", "Sell CSP", "Sell Covered Call"]:
        is_call = name in ("Buy Call", "Sell Covered Call")
        prem_val = bs["call_premium"] if is_call else bs["put_premium"]
        strategies.append(StrategyRecommendation(
            strategy=name,
            premium=f"${prem_val:.2f}",
            premium_value=round(prem_val, 2),
            ivr_signal=_ivr_signal(ivr, name),
            sr_context=_sr_context(name, direction),
            recommendation=_recommendation(direction, ivr, name),
        ))

    return AnalysisResponse(
        ticker=ticker,
        current_price=round(current_price, 2),
        iv=round(iv * 100, 2),
        iv_rank=round(ivr, 2),
        call_premium=bs["call_premium"],
        put_premium=bs["put_premium"],
        strike=bs["strike"],
        greeks=greeks,
        strategies=strategies,
    )
