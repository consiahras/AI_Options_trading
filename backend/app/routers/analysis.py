import logging
from typing import Optional
import pandas as pd
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    AnalysisResponse, GreeksData, StrategyRecommendation
)
from app.services import data_fetcher, black_scholes, iv_rank
from app.services.technical import find_fibonacci_levels, find_cluster_sr_levels

logger = logging.getLogger(__name__)
router = APIRouter()


def _compute_signals(df: pd.DataFrame) -> tuple[str, dict]:
    """Return (direction, stoch_info). direction = bullish | bearish | neutral."""
    closes = df["Close"]
    highs  = df["High"]
    lows   = df["Low"]

    ma50  = closes.rolling(50).mean().dropna()
    ma200 = closes.rolling(200).mean().dropna()

    if len(ma50) == 0 or len(ma200) == 0:
        direction = "neutral"
    elif ma50.iloc[-1] > ma200.iloc[-1]:
        direction = "bullish"
    else:
        direction = "bearish"

    k_period, d_period = 14, 3
    lowest   = lows.rolling(k_period).min()
    highest  = highs.rolling(k_period).max()
    raw_k    = ((closes - lowest) / (highest - lowest + 1e-10) * 100)
    smooth_k = raw_k.rolling(d_period).mean().dropna()
    smooth_d = smooth_k.rolling(d_period).mean().dropna()

    if len(smooth_k) < 2 or len(smooth_d) < 2:
        return direction, {"signal": "neutral", "k": None, "d": None}

    k_val  = float(smooth_k.iloc[-1])
    d_val  = float(smooth_d.iloc[-1])
    pk_val = float(smooth_k.iloc[-2])
    pd_val = float(smooth_d.iloc[-2])

    if k_val > 80:
        sig = "overbought"
    elif k_val < 20:
        sig = "oversold"
    elif pk_val < pd_val and k_val > d_val:
        sig = "bullish_cross"
    elif pk_val > pd_val and k_val < d_val:
        sig = "bearish_cross"
    else:
        sig = "neutral"

    return direction, {"signal": sig, "k": k_val, "d": d_val}


def _levels(current_price: float, fib_list: list[dict], cluster_list: list[dict]) -> dict:
    """Find nearest resistance/support and proximity flags."""
    prices = [f["price"] for f in fib_list] + [c["price"] for c in cluster_list]

    margin = 0.005
    above  = [p for p in prices if p > current_price * (1 + margin)]
    below  = [p for p in prices if p < current_price * (1 - margin)]

    resistance = min(above) if above else None
    support    = max(below) if below else None

    near_pct = 0.03
    near_resistance = resistance is not None and (resistance - current_price) / current_price <= near_pct
    near_support    = support    is not None and (current_price - support)    / current_price <= near_pct

    fib_100 = max((f["price"] for f in fib_list), default=None)
    at_new_high = fib_100 is not None and current_price >= fib_100 * 0.99

    return {
        "resistance":      resistance,
        "support":         support,
        "near_resistance": near_resistance,
        "near_support":    near_support,
        "at_new_high":     at_new_high,
    }


def _ivr_signal(ivr: float, strategy: str) -> str:
    is_buy = strategy in ("Buy Call", "Buy Put")
    n = f"{ivr:.1f}"
    if ivr < 30:
        return f"Low ✓ ({n})" if is_buy else f"Low ✗ ({n})"
    elif ivr > 50:
        return f"High ✓ ({n})" if not is_buy else f"High ✗ ({n})"
    return f"Neutral ({n})"


def _stoch_label(stoch: dict) -> str:
    sig = stoch.get("signal", "neutral")
    k   = stoch.get("k")
    ks  = f" K={k:.0f}" if k is not None else ""
    return {
        "overbought":    f"Overbought{ks}",
        "oversold":      f"Oversold{ks}",
        "bullish_cross": f"Bullish cross{ks}",
        "bearish_cross": f"Bearish cross{ks}",
        "neutral":       f"Neutral{ks}",
    }.get(sig, f"Neutral{ks}")


def _build_strategies(
    S: float,
    iv: float,
    ivr: float,
    direction: str,
    stoch: dict,
    is_owned: bool,
    target_price: Optional[float],
    lvl: dict,
) -> list[StrategyRecommendation]:

    stoch_sig = stoch.get("signal", "neutral")
    sl = _stoch_label(stoch)

    res = lvl["resistance"]
    sup = lvl["support"]
    nr  = lvl["near_resistance"]
    ns  = lvl["near_support"]
    anh = lvl["at_new_high"]

    def bs_call(K: float) -> float:
        return black_scholes.calculate_at_strike(S, K, iv)["call_premium"]

    def bs_put(K: float) -> float:
        return black_scholes.calculate_at_strike(S, K, iv)["put_premium"]

    strategies = []

    # ── BUY CALL ──────────────────────────────────────────────────────────────
    bc_K = S  # always ATM for calls
    if direction == "bullish":
        if anh or nr:
            res_str = f"${res:.0f}" if res else "resistance"
            bc_rec = "AVOID"
            bc_ctx = f"At/near {res_str} resistance — upside capped. {sl}"
        elif stoch_sig == "overbought":
            bc_rec = "CAUTION"
            bc_ctx = f"Bullish but {sl} — wait for pullback before buying calls"
        else:
            bc_rec = "CONSIDER"
            bc_ctx = f"Bullish trend, room to run. {sl}"
    elif direction == "bearish":
        if stoch_sig in ("oversold", "bullish_cross") and ns:
            sup_str = f"${sup:.0f}" if sup else "support"
            bc_rec = "CAUTION"
            bc_ctx = f"Bearish but {sl} near {sup_str} support — bounce play, high risk"
        else:
            bc_rec = "AVOID"
            bc_ctx = f"Bearish trend ({sl}) — calls go against direction"
    else:
        bc_rec = "CAUTION"
        bc_ctx = f"Mixed signals ({sl}) — wait for trend confirmation"

    bc_prem = bs_call(bc_K)
    strategies.append(StrategyRecommendation(
        strategy="Buy Call",
        premium=f"${bc_prem:.2f}",
        premium_value=round(bc_prem, 2),
        strike_label=f"ATM ${bc_K:.0f}",
        ivr_signal=_ivr_signal(ivr, "Buy Call"),
        sr_context=bc_ctx,
        recommendation=bc_rec,
    ))

    # ── BUY PUT ───────────────────────────────────────────────────────────────
    if direction == "bullish" and (nr or anh):
        # Fade the resistance — price the put at the resistance level
        bp_K = res if res else S
        bp_rec = "CONSIDER"
        res_str = f"${bp_K:.0f}"
        if stoch_sig == "overbought":
            bp_ctx = f"Overbought near {res_str} resistance — strong fade signal"
        else:
            bp_ctx = f"Near {res_str} resistance ({sl}) — potential reversal, sell the high"
    elif direction == "bearish":
        bp_K = S  # ATM put for directional bearish bet
        if stoch_sig == "overbought":
            bp_rec = "CONSIDER"
            bp_ctx = f"Bearish + {sl} — resuming downtrend, good put timing"
        elif stoch_sig in ("oversold", "bullish_cross"):
            bp_rec = "CAUTION"
            bp_ctx = f"Bearish but {sl} — bounce risk, puts may be early"
        else:
            bp_rec = "CAUTION"
            bp_ctx = f"Bearish trend ({sl}) — puts reasonable but premium is elevated"
    else:
        bp_K = S
        bp_rec = "AVOID"
        bp_ctx = f"Bullish trend with room to run ({sl}) — avoid puts"

    bp_prem = bs_put(bp_K)
    strategies.append(StrategyRecommendation(
        strategy="Buy Put",
        premium=f"${bp_prem:.2f}",
        premium_value=round(bp_prem, 2),
        strike_label=f"${bp_K:.0f}",
        ivr_signal=_ivr_signal(ivr, "Buy Put"),
        sr_context=bp_ctx,
        recommendation=bp_rec,
    ))

    # ── SELL CSP ──────────────────────────────────────────────────────────────
    if direction == "bearish":
        # Strike = target price if set, otherwise just below support
        if target_price is not None:
            csp_K = min(target_price, sup) if sup and sup < target_price else target_price
        else:
            csp_K = sup if sup else round(S * 0.95, 2)

        csp_ivr = _ivr_signal(ivr, "Sell CSP")
        csp_K_str = f"${csp_K:.0f}"
        tp_str = f" (your target ${target_price:.0f})" if target_price else " (no target set)"

        if stoch_sig in ("oversold", "bullish_cross"):
            csp_rec = "CONSIDER"
            csp_ctx = f"Sell CSP at {csp_K_str}{tp_str} — {sl} suggests bounce; collect premium while targeting entry"
        elif stoch_sig == "overbought":
            csp_rec = "AVOID"
            csp_ctx = f"{sl} in bear trend — more downside likely; skip CSP for now"
        else:
            csp_rec = "CONSIDER" if target_price else "CAUTION"
            csp_ctx = f"Bear trend — sell CSP at {csp_K_str}{tp_str}. {sl}"

    elif direction == "bullish":
        csp_K = sup if sup else round(S * 0.97, 2)
        csp_ivr = _ivr_signal(ivr, "Sell CSP")
        csp_rec = "AVOID"
        csp_ctx = f"Bull market — CSP below support ${csp_K:.0f} is low-probability assignment; wait for pullback. {sl}"

    else:
        csp_K = sup if sup else round(S * 0.95, 2)
        csp_ivr = _ivr_signal(ivr, "Sell CSP")
        csp_rec = "CAUTION"
        tp_s = f"target ${target_price:.0f}" if target_price else "set a target price"
        csp_ctx = f"Mixed signals — CSP at ${csp_K:.0f} if you want to own here ({tp_s}). {sl}"

    csp_prem = bs_put(csp_K)
    strategies.append(StrategyRecommendation(
        strategy="Sell CSP",
        premium=f"${csp_prem:.2f}",
        premium_value=round(csp_prem, 2),
        strike_label=f"${csp_K:.0f}",
        ivr_signal=csp_ivr,
        sr_context=csp_ctx,
        recommendation=csp_rec,
    ))

    # ── SELL COVERED CALL ─────────────────────────────────────────────────────
    if is_owned:
        cc_K = res if res else round(S * 1.05, 2)
        cc_K_str = f"${cc_K:.0f}"
        cc_ivr = _ivr_signal(ivr, "Sell Covered Call")

        if direction == "bullish":
            if stoch_sig == "overbought" or nr or anh:
                cc_rec = "CONSIDER"
                cc_ctx = f"Sell CC at {cc_K_str} resistance — {sl} confirms timing"
            else:
                cc_rec = "CAUTION"
                cc_ctx = f"Bullish trend still active — CC at {cc_K_str} caps upside. {sl}"
        elif direction == "bearish":
            cc_rec = "CONSIDER"
            if stoch_sig == "overbought":
                cc_ctx = f"Bear + {sl} — great CC entry at {cc_K_str} resistance"
            else:
                cc_ctx = f"Bear trend — sell CC at {cc_K_str} to reduce cost basis. {sl}"
        else:
            cc_rec = "CAUTION"
            cc_ctx = f"Mixed signals — CC at {cc_K_str} generates income but may cap a breakout. {sl}"
    else:
        cc_K = res if res else round(S * 1.05, 2)
        cc_ivr = _ivr_signal(ivr, "Sell Covered Call")
        cc_rec = "AVOID"
        cc_ctx = "No shares owned — covered call requires holding the underlying stock"

    cc_prem = bs_call(cc_K)
    strategies.append(StrategyRecommendation(
        strategy="Sell Covered Call",
        premium=f"${cc_prem:.2f}",
        premium_value=round(cc_prem, 2),
        strike_label=f"${cc_K:.0f}",
        ivr_signal=cc_ivr,
        sr_context=cc_ctx,
        recommendation=cc_rec,
    ))

    return strategies


@router.get("/analysis/{ticker}", response_model=AnalysisResponse)
def get_analysis(
    ticker: str,
    list_type: str = "watchlist",
    target_price: Optional[float] = None,
):
    ticker = ticker.upper()

    df = data_fetcher.fetch_historical_data(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    current_price    = float(df["Close"].iloc[-1])
    options_chain    = data_fetcher.fetch_options_chain(ticker)
    iv, ivr          = iv_rank.calculate_iv_rank(df, options_chain, current_price)
    direction, stoch = _compute_signals(df)
    bs_atm           = black_scholes.calculate_all(current_price, iv)

    fib_list     = find_fibonacci_levels(df)
    cluster_list = find_cluster_sr_levels(df)
    lvl          = _levels(current_price, fib_list, cluster_list)

    is_owned = list_type == "owned"

    logger.info(
        f"{ticker} — direction={direction} stoch={stoch['signal']} "
        f"IVR={ivr:.1f} IV={iv*100:.1f}% owned={is_owned} target={target_price} "
        f"resistance={lvl['resistance']} support={lvl['support']}"
    )

    greeks = GreeksData(
        delta_call=bs_atm["delta_call"],
        delta_put=bs_atm["delta_put"],
        theta_call=bs_atm["theta_call"],
        theta_put=bs_atm["theta_put"],
        gamma=bs_atm["gamma"],
        vega=bs_atm["vega"],
    )

    strategies = _build_strategies(
        S=current_price,
        iv=iv,
        ivr=ivr,
        direction=direction,
        stoch=stoch,
        is_owned=is_owned,
        target_price=target_price,
        lvl=lvl,
    )

    return AnalysisResponse(
        ticker=ticker,
        current_price=round(current_price, 2),
        iv=round(iv * 100, 2),
        iv_rank=round(ivr, 2),
        call_premium=bs_atm["call_premium"],
        put_premium=bs_atm["put_premium"],
        strike=bs_atm["strike"],
        greeks=greeks,
        strategies=strategies,
    )
