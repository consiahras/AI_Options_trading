from fastapi import APIRouter, HTTPException
from app.models.schemas import StockEntry, StockListResponse, StockUpdateRequest

router = APIRouter()

# In-memory store — initialized with sensible defaults
_stocks: list[StockEntry] = [
    StockEntry(ticker="AAPL", list_type="owned"),
    StockEntry(ticker="TSLA", list_type="owned"),
    StockEntry(ticker="NVDA", list_type="watchlist"),
    StockEntry(ticker="SPY",  list_type="watchlist"),
]


@router.get("/stocks", response_model=StockListResponse)
def get_stocks():
    return StockListResponse(stocks=_stocks)


@router.post("/stocks", response_model=StockListResponse)
def add_stock(entry: StockEntry):
    ticker = entry.ticker.upper()
    if any(s.ticker == ticker for s in _stocks):
        raise HTTPException(status_code=409, detail=f"{ticker} already in list")
    _stocks.append(StockEntry(ticker=ticker, list_type=entry.list_type))
    return StockListResponse(stocks=_stocks)


@router.patch("/stocks/{ticker}", response_model=StockListResponse)
def update_stock(ticker: str, body: StockUpdateRequest):
    ticker = ticker.upper()
    for i, stock in enumerate(_stocks):
        if stock.ticker == ticker:
            _stocks[i] = StockEntry(
                ticker=stock.ticker,
                list_type=stock.list_type,
                avg_buy_price=body.avg_buy_price if body.avg_buy_price is not None else stock.avg_buy_price,
                quantity=body.quantity       if body.quantity       is not None else stock.quantity,
                target_price=body.target_price if body.target_price is not None else stock.target_price,
            )
            return StockListResponse(stocks=_stocks)
    raise HTTPException(status_code=404, detail=f"{ticker} not found")


@router.delete("/stocks/{ticker}", response_model=StockListResponse)
def delete_stock(ticker: str):
    ticker = ticker.upper()
    global _stocks
    before = len(_stocks)
    _stocks = [s for s in _stocks if s.ticker != ticker]
    if len(_stocks) == before:
        raise HTTPException(status_code=404, detail=f"{ticker} not found")
    return StockListResponse(stocks=_stocks)
