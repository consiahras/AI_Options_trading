import csv
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.models.schemas import StockEntry, StockListResponse, StockUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Data files live in backend/data/ — mounted as a volume so changes survive restarts
DATA_DIR       = Path(__file__).parent.parent.parent / "data"
PORTFOLIO_FILE = DATA_DIR / "portfolio.csv"
WATCHLIST_FILE = DATA_DIR / "watchlist.csv"


def _load_stocks() -> list[StockEntry]:
    stocks: list[StockEntry] = []

    if PORTFOLIO_FILE.exists():
        try:
            with open(PORTFOLIO_FILE, newline='') as f:
                for row in csv.DictReader(f):
                    ticker = row.get('ticker', '').strip().upper()
                    if not ticker:
                        continue
                    qty  = row.get('quantity', '').strip()
                    abp  = row.get('avg_buy_price', '').strip()
                    stocks.append(StockEntry(
                        ticker=ticker,
                        list_type='owned',
                        quantity=float(qty)  if qty  else None,
                        avg_buy_price=float(abp) if abp  else None,
                    ))
        except Exception as e:
            logger.error(f"Failed to load portfolio.csv: {e}")

    if WATCHLIST_FILE.exists():
        try:
            with open(WATCHLIST_FILE, newline='') as f:
                for row in csv.DictReader(f):
                    ticker = row.get('ticker', '').strip().upper()
                    if not ticker:
                        continue
                    tp = row.get('target_price', '').strip()
                    stocks.append(StockEntry(
                        ticker=ticker,
                        list_type='watchlist',
                        target_price=float(tp) if tp else None,
                    ))
        except Exception as e:
            logger.error(f"Failed to load watchlist.csv: {e}")

    return stocks


def _save_stocks(stocks: list[StockEntry]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    owned     = [s for s in stocks if s.list_type == 'owned']
    watchlist = [s for s in stocks if s.list_type == 'watchlist']

    try:
        with open(PORTFOLIO_FILE, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['ticker', 'quantity', 'avg_buy_price'])
            w.writeheader()
            for s in owned:
                w.writerow({
                    'ticker':        s.ticker,
                    'quantity':      '' if s.quantity       is None else s.quantity,
                    'avg_buy_price': '' if s.avg_buy_price  is None else s.avg_buy_price,
                })
    except Exception as e:
        logger.error(f"Failed to save portfolio.csv: {e}")

    try:
        with open(WATCHLIST_FILE, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['ticker', 'target_price'])
            w.writeheader()
            for s in watchlist:
                w.writerow({
                    'ticker':       s.ticker,
                    'target_price': '' if s.target_price is None else s.target_price,
                })
    except Exception as e:
        logger.error(f"Failed to save watchlist.csv: {e}")


# Load on startup
_stocks: list[StockEntry] = _load_stocks()


@router.get("/stocks", response_model=StockListResponse)
def get_stocks():
    return StockListResponse(stocks=_stocks)


@router.post("/stocks", response_model=StockListResponse)
def add_stock(entry: StockEntry):
    ticker = entry.ticker.upper()
    if any(s.ticker == ticker for s in _stocks):
        raise HTTPException(status_code=409, detail=f"{ticker} already in list")
    _stocks.append(StockEntry(ticker=ticker, list_type=entry.list_type))
    _save_stocks(_stocks)
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
                quantity=body.quantity           if body.quantity       is not None else stock.quantity,
                target_price=body.target_price   if body.target_price   is not None else stock.target_price,
            )
            _save_stocks(_stocks)
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
    _save_stocks(_stocks)
    return StockListResponse(stocks=_stocks)
