from typing import Literal, Optional
from pydantic import BaseModel


class StockEntry(BaseModel):
    ticker: str
    list_type: Literal["owned", "watchlist"]


class StockListResponse(BaseModel):
    stocks: list[StockEntry]


class PriceData(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class SRLevel(BaseModel):
    price: float
    level_type: str
    color: str
    label: Optional[str] = None


class MAData(BaseModel):
    date: str
    ma50: Optional[float] = None
    ma100: Optional[float] = None
    ma200: Optional[float] = None


class PivotPoints(BaseModel):
    P: float
    R1: float
    R2: float
    S1: float
    S2: float


class FibonacciLevel(BaseModel):
    price: float
    label: str
    color: str


class Trendline(BaseModel):
    slope: float
    intercept: float
    start_date: str
    end_date: str
    line_type: str  # "resistance" or "support"
    color: str


class StochasticPoint(BaseModel):
    date: str
    k: Optional[float] = None
    d: Optional[float] = None


class PivotMarker(BaseModel):
    date: str
    price: float
    type: str  # "high" or "low"


class ChartResponse(BaseModel):
    ticker: str
    prices: list[PriceData]
    sr_levels: list[SRLevel]
    ma_data: list[MAData]
    pivot_points: Optional[PivotPoints] = None
    fibonacci_levels: list[FibonacciLevel]
    trendlines: list[Trendline]
    stochastic: list[StochasticPoint] = []
    pivot_markers: list[PivotMarker] = []


class GreeksData(BaseModel):
    delta_call: float
    delta_put: float
    theta_call: float
    theta_put: float
    gamma: float
    vega: float


class StrategyRecommendation(BaseModel):
    strategy: str
    premium: str
    premium_value: float
    ivr_signal: str
    sr_context: str
    recommendation: str


class AnalysisResponse(BaseModel):
    ticker: str
    current_price: float
    iv: float
    iv_rank: float
    call_premium: float
    put_premium: float
    strike: float
    greeks: GreeksData
    strategies: list[StrategyRecommendation]
