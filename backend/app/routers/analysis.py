import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    AnalysisResponse, GreeksData, StrategyRecommendation
)
from app.services import data_fetcher, black_scholes, iv_rank

logger = logging.getLogger(__name__)
router = APIRouter()


def _ivr_signal(ivr: float, strategy: str) -> str:
    """Return signal string based on IVR and strategy type."""
    is_buy = strategy in ("Buy Call", "Buy Put")
    is_sell = strategy in ("Sell CSP", "Sell Covered Call")

    if ivr < 30:
        return "Low IV ✓" if is_buy else "Low IV ✗"
    elif ivr > 50:
        return "High IV ✓" if is_sell else "High IV ✗"
    else:
        return "Neutral IV"


def _recommendation(ivr: float, strategy: str) -> str:
    is_buy = strategy in ("Buy Call", "Buy Put")
    is_sell = strategy in ("Sell CSP", "Sell Covered Call")

    if ivr < 30:
        return "CONSIDER" if is_buy else "AVOID"
    elif ivr > 50:
        return "CONSIDER" if is_sell else "AVOID"
    else:
        return "CAUTION"


def _sr_context(strategy: str) -> str:
    """Generic S/R context message per strategy."""
    contexts = {
        "Buy Call": "Check for nearby support",
        "Buy Put": "Check for nearby resistance",
        "Sell CSP": "Strike should be below support",
        "Sell Covered Call": "Strike near resistance is ideal",
    }
    return contexts.get(strategy, "Review chart levels")


@router.get("/analysis/{ticker}", response_model=AnalysisResponse)
def get_analysis(ticker: str):
    ticker = ticker.upper()

    df = data_fetcher.fetch_historical_data(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    current_price = float(df["Close"].iloc[-1])

    # Fetch options chain (may be None for some tickers)
    options_chain = data_fetcher.fetch_options_chain(ticker)

    # Calculate IV and IV Rank
    iv, ivr = iv_rank.calculate_iv_rank(df, options_chain, current_price)

    # Calculate Black-Scholes premiums and Greeks
    bs = black_scholes.calculate_all(current_price, iv)

    greeks = GreeksData(
        delta_call=bs["delta_call"],
        delta_put=bs["delta_put"],
        theta_call=bs["theta_call"],
        theta_put=bs["theta_put"],
        gamma=bs["gamma"],
        vega=bs["vega"],
    )

    strategies_names = ["Buy Call", "Buy Put", "Sell CSP", "Sell Covered Call"]
    strategies = []
    for name in strategies_names:
        is_call = name in ("Buy Call", "Sell Covered Call")
        prem_val = bs["call_premium"] if is_call else bs["put_premium"]
        rec = _recommendation(ivr, name)
        strategies.append(StrategyRecommendation(
            strategy=name,
            premium=f"${prem_val:.2f}",
            premium_value=round(prem_val, 2),
            ivr_signal=_ivr_signal(ivr, name),
            sr_context=_sr_context(name),
            recommendation=rec,
        ))

    return AnalysisResponse(
        ticker=ticker,
        current_price=round(current_price, 2),
        iv=round(iv * 100, 2),   # expressed as percentage
        iv_rank=round(ivr, 2),
        call_premium=bs["call_premium"],
        put_premium=bs["put_premium"],
        strike=bs["strike"],
        greeks=greeks,
        strategies=strategies,
    )
