import time
import logging
from typing import Optional
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

_cache: dict = {}
CACHE_TTL = 15 * 60  # 15 minutes in seconds


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    return (time.time() - _cache[key]["timestamp"]) < CACHE_TTL


def _set_cache(key: str, data) -> None:
    _cache[key] = {"data": data, "timestamp": time.time()}


def _get_cache(key: str):
    return _cache[key]["data"]


def fetch_historical_data(ticker: str) -> Optional[pd.DataFrame]:
    """Fetch 1 year of daily OHLCV data for a ticker."""
    cache_key = f"hist_{ticker}"
    if _is_cache_valid(cache_key):
        return _get_cache(cache_key)

    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y", interval="1d", auto_adjust=True)
        if df.empty:
            logger.warning(f"No historical data found for {ticker}")
            return None
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        _set_cache(cache_key, df)
        return df
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        return None


def fetch_current_price(ticker: str) -> Optional[float]:
    """Get the most recent closing price."""
    df = fetch_historical_data(ticker)
    if df is None or df.empty:
        return None
    return float(df["Close"].iloc[-1])


def fetch_options_chain(ticker: str) -> Optional[dict]:
    """Fetch the nearest-expiry options chain for IV extraction."""
    cache_key = f"options_{ticker}"
    if _is_cache_valid(cache_key):
        return _get_cache(cache_key)

    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            logger.warning(f"No options data for {ticker}")
            _set_cache(cache_key, None)
            return None

        # Pick the expiration closest to 30 days out
        import datetime
        today = datetime.date.today()
        target = today + datetime.timedelta(days=30)

        best_exp = min(
            expirations,
            key=lambda e: abs((datetime.date.fromisoformat(e) - target).days)
        )

        chain = stock.option_chain(best_exp)
        result = {
            "expiration": best_exp,
            "calls": chain.calls,
            "puts": chain.puts,
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Error fetching options chain for {ticker}: {e}")
        _set_cache(cache_key, None)
        return None


def fetch_ticker_info(ticker: str) -> dict:
    """Fetch basic info for a ticker."""
    cache_key = f"info_{ticker}"
    if _is_cache_valid(cache_key):
        return _get_cache(cache_key)

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        _set_cache(cache_key, info)
        return info
    except Exception as e:
        logger.error(f"Error fetching info for {ticker}: {e}")
        return {}
