import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChartResponse, PriceData, SRLevel, MAData, PivotPoints, FibonacciLevel, Trendline
from app.services import data_fetcher, technical

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chart/{ticker}", response_model=ChartResponse)
def get_chart(ticker: str):
    ticker = ticker.upper()

    df = data_fetcher.fetch_historical_data(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    # Build price list
    prices = []
    for idx, row in df.iterrows():
        prices.append(PriceData(
            date=idx.strftime("%Y-%m-%d"),
            open=round(float(row["Open"]), 4),
            high=round(float(row["High"]), 4),
            low=round(float(row["Low"]), 4),
            close=round(float(row["Close"]), 4),
            volume=float(row["Volume"]),
        ))

    # Technical analysis
    tech = technical.calculate_all_technical(df)

    sr_levels = [
        SRLevel(
            price=lvl["price"],
            level_type=lvl["level_type"],
            color=lvl["color"],
            label=lvl.get("label"),
        )
        for lvl in tech["sr_levels"]
    ]

    ma_data = [
        MAData(
            date=ma["date"],
            ma50=ma["ma50"],
            ma100=ma["ma100"],
            ma200=ma["ma200"],
        )
        for ma in tech["ma_data"]
    ]

    pivot_points = None
    if tech["pivot_points"]:
        pp = tech["pivot_points"]
        pivot_points = PivotPoints(
            P=pp["P"], R1=pp["R1"], R2=pp["R2"], S1=pp["S1"], S2=pp["S2"]
        )
        # Add pivot levels as SR levels (cyan)
        for label, price in [("PP", pp["P"]), ("R1", pp["R1"]), ("R2", pp["R2"]),
                              ("S1", pp["S1"]), ("S2", pp["S2"])]:
            sr_levels.append(SRLevel(price=price, level_type="pivot", color="#06b6d4", label=label))

    fibonacci_levels = [
        FibonacciLevel(price=fib["price"], label=fib["label"], color=fib["color"])
        for fib in tech["fibonacci_levels"]
    ]

    trendlines = [
        Trendline(
            slope=tl["slope"],
            intercept=tl["intercept"],
            start_date=tl["start_date"],
            end_date=tl["end_date"],
            line_type=tl["line_type"],
            color=tl["color"],
        )
        for tl in tech["trendlines"]
    ]

    return ChartResponse(
        ticker=ticker,
        prices=prices,
        sr_levels=sr_levels,
        ma_data=ma_data,
        pivot_points=pivot_points,
        fibonacci_levels=fibonacci_levels,
        trendlines=trendlines,
    )
