from fastapi import APIRouter, HTTPException
from app.models.schemas import StockEntry, StockListResponse

router = APIRouter()

# In-memory store — initialized with sensible defaults
_stocks: list[StockEntry] = [
    StockEntry(ticker="AAPL", list_type="owned"),
    StockEntry(ticker="TSLA", list_type="owned"),
    StockEntry(ticker="NVDA", list_type="watchlist"),
    StockEntry(ticker="SPY", list_type="watchlist"),
]


@router.get("/stocks", response_model=StockListResponse)
def get_stocks():
    return StockListResponse(stocks=_stocks)


@router.post("/stocks", response_model=StockListResponse)
def add_stock(entry: StockEntry):
    ticker = entry.ticker.upper()
    # Avoid duplicates
    existing = [s for s in _stocks if s.ticker == ticker]
    if existing:
        raise HTTPException(status_code=409, detail=f"{ticker} already in list")
    _stocks.append(StockEntry(ticker=ticker, list_type=entry.list_type))
    return StockListResponse(stocks=_stocks)


@router.delete("/stocks/{ticker}", response_model=StockListResponse)
def delete_stock(ticker: str):
    ticker = ticker.upper()
    global _stocks
    before = len(_stocks)
    _stocks = [s for s in _stocks if s.ticker != ticker]
    if len(_stocks) == before:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    return StockListResponse(stocks=_stocks)
