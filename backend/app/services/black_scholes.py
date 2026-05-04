import math
import logging
from scipy.stats import norm

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.0525  # 5.25% US 3-month T-bill
DAYS_TO_EXPIRY = 30
T = DAYS_TO_EXPIRY / 365.0


def _round_to_strike(price: float) -> float:
    """Round price to a reasonable ATM strike."""
    if price >= 100:
        return round(price / 5) * 5
    elif price >= 20:
        return round(price)
    else:
        return round(price * 2) / 2


def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if sigma <= 0 or T <= 0:
        return 0.0
    return (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))


def _d2(d1_val: float, sigma: float, T: float) -> float:
    return d1_val - sigma * math.sqrt(T)


def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes call option price."""
    if sigma <= 0 or T <= 0:
        return max(S - K, 0.0)
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(d1, sigma, T)
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes put option price."""
    if sigma <= 0 or T <= 0:
        return max(K - S, 0.0)
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(d1, sigma, T)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def delta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if sigma <= 0 or T <= 0:
        return 1.0 if S > K else 0.0
    d1 = _d1(S, K, T, r, sigma)
    return norm.cdf(d1)


def delta_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if sigma <= 0 or T <= 0:
        return -1.0 if S < K else 0.0
    d1 = _d1(S, K, T, r, sigma)
    return norm.cdf(d1) - 1.0


def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if sigma <= 0 or T <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))


def theta_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Theta for call, expressed per day."""
    if sigma <= 0 or T <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(d1, sigma, T)
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
    term2 = -r * K * math.exp(-r * T) * norm.cdf(d2)
    return (term1 + term2) / 365.0


def theta_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Theta for put, expressed per day."""
    if sigma <= 0 or T <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    d2 = _d2(d1, sigma, T)
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
    term2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
    return (term1 + term2) / 365.0


def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Vega (per 1% change in vol), expressed as dollar per 1% move."""
    if sigma <= 0 or T <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return S * norm.pdf(d1) * math.sqrt(T) / 100.0


def calculate_all(S: float, sigma: float) -> dict:
    """Calculate all premiums and Greeks for ATM strike at 30 days."""
    K = _round_to_strike(S)
    r = RISK_FREE_RATE
    t = T

    cp = call_price(S, K, t, r, sigma)
    pp = put_price(S, K, t, r, sigma)
    dc = delta_call(S, K, t, r, sigma)
    dp = delta_put(S, K, t, r, sigma)
    gm = gamma(S, K, t, r, sigma)
    tc = theta_call(S, K, t, r, sigma)
    tp = theta_put(S, K, t, r, sigma)
    vg = vega(S, K, t, r, sigma)

    return {
        "strike": K,
        "call_premium": round(cp, 4),
        "put_premium": round(pp, 4),
        "delta_call": round(dc, 4),
        "delta_put": round(dp, 4),
        "gamma": round(gm, 6),
        "theta_call": round(tc, 4),
        "theta_put": round(tp, 4),
        "vega": round(vg, 4),
    }
