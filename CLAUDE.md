# AI Options Trading — Project Reference

## Project Overview

A self-hosted options trading analysis tool focused on 4 strategies:
- **Buy Call** — bullish, enter when IV is LOW
- **Buy Put** — bearish, enter when IV is LOW
- **Sell Cash-Secured Put (CSP)** — neutral/bullish, enter when IV is HIGH
- **Sell Covered Call (CC)** — neutral/slightly bullish, enter when IV is HIGH

The app calculates 30-day option premiums using Black-Scholes, overlays technical analysis on a stock price chart, and gives a recommendation per strategy based on IV Rank and support/resistance context.

---

## Architecture

Two Docker containers orchestrated with **Docker Compose**:

```
docker-compose.yml
├── frontend/     (React — serves the GUI on port 3000)
└── backend/      (Python FastAPI — all calculations on port 8000)
```

The frontend talks to the backend via REST API. Both containers run together with a single `docker-compose up`.

### Why Docker Compose (not Kubernetes or standalone)
- Lightweight for local use and single-board computers (e.g., Arduino/Raspberry Pi)
- Easy to migrate: copy the repo, run `docker-compose up`, done
- Each service can be updated or restarted independently

---

## Tech Stack

### Frontend
- **React** (Vite build tooling)
- **Recharts** or **Lightweight Charts (TradingView)** for the stock chart
- **Tailwind CSS** for modern styling
- No external state management — React Context is sufficient

### Backend
- **Python 3.12**
- **FastAPI** — REST API framework
- **yfinance** — free stock data (1 year of daily OHLCV, no API key needed)
- **pandas / numpy** — data manipulation
- **scipy** — Black-Scholes normal distribution calculations
- **ta** (Technical Analysis library) — MAs, Pivot Points, Fibonacci

### Data Source
- **Yahoo Finance via yfinance** (free, no key required)
- Provides up to 1 year of daily historical data reliably
- Options chain data also available via yfinance

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER — App name, last updated timestamp                  │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  LEFT PANEL  │           MAIN CHART AREA                   │
│  (sidebar)   │   Stock price chart (1 year daily OHLCV)    │
│              │   with S/R overlays (coloured dots/lines)   │
│  ┌────────┐  │                                              │
│  │ MY     │  ├──────────────────────────────────────────────┤
│  │ STOCKS │  │                                              │
│  └────────┘  │         ANALYSIS PANEL (below chart)        │
│  ┌────────┐  │   30-day option premiums + recommendation   │
│  │ WATCH  │  │   per strategy (Buy Call / Put / CSP / CC)  │
│  │ LIST   │  │                                              │
│  └────────┘  │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

Clicking any stock in the sidebar triggers a full recalculation and re-renders the chart and analysis panel for that ticker.

---

## Chart Overlays — Support & Resistance Levels

Each overlay type has a distinct colour. All are rendered on the same chart simultaneously.

| Level Type | Colour | Method |
|---|---|---|
| Horizontal S/R | Red (resistance) / Green (support) | Local price pivot highs/lows |
| Fibonacci Retracements | Orange | 23.6%, 38.2%, 50%, 61.8%, 78.6% of last major swing |
| Fibonacci Extensions | Yellow | 127.2%, 161.8% above/below swing |
| Moving Average 50 | Blue | 50-day SMA |
| Moving Average 100 | Purple | 100-day SMA |
| Moving Average 200 | White / Light grey | 200-day SMA |
| Pivot Points | Cyan | Classic daily pivot (P, R1, R2, S1, S2) |
| Trendlines | Magenta | Least-squares fit through pivot highs/lows |

---

## Options Calculation — Black-Scholes

Inputs per stock (auto-fetched):
- `S` — current stock price
- `K` — strike price (ATM = current price, also show ±5% strikes)
- `T` — 30 days = 30/365
- `r` — risk-free rate (US 3-month T-bill, fetched or hardcoded as ~5.25%)
- `σ` — implied volatility (derived from yfinance options chain or calculated from 30-day historical vol)

Outputs:
- Call premium (theoretical)
- Put premium (theoretical)
- IV Rank (IVR) — current IV vs 52-week IV range
- Delta, Theta (main Greeks shown to user)

### IV Rank Interpretation
- IVR > 50 → IV relatively HIGH → recommend **Sell CSP** or **Sell Covered Call**
- IVR < 30 → IV relatively LOW → recommend **Buy Call** or **Buy Put** (direction dependent)
- 30–50 → neutral, show both but flag caution

---

## Analysis Panel Output (per stock)

For each of the 4 strategies, show:

```
Strategy         | Premium (30d ATM) | IVR Signal | S/R Context      | Recommendation
Buy Call         | $X.XX             | Low ✓      | Near support ✓   | CONSIDER
Buy Put          | $X.XX             | Low ✓      | Near resistance  | CONSIDER
Sell CSP         | $X.XX             | High ✓     | Strike below S/R | CONSIDER
Sell Covered Call| $X.XX             | High ✓     | Strike at R ✓    | CONSIDER
```

---

## API Endpoints (Backend)

```
GET  /api/stock/{ticker}          — price, IV, options chain, greeks
GET  /api/chart/{ticker}          — OHLCV + all S/R levels calculated
GET  /api/analysis/{ticker}       — full recommendation summary
GET  /api/stocks                  — list of saved stocks (owned + watchlist)
POST /api/stocks                  — add a stock to owned or watchlist
DELETE /api/stocks/{ticker}       — remove a stock
```

---

## Project Structure

```
AI_Options_trading/
├── CLAUDE.md
├── docker-compose.yml
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Sidebar.jsx          — owned stocks + watchlist
│       │   ├── StockChart.jsx       — main chart with S/R overlays
│       │   └── AnalysisPanel.jsx    — premium table + recommendations
│       └── api/
│           └── client.js            — fetch calls to backend
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    └── app/
        ├── main.py                  — FastAPI app entrypoint
        ├── routers/
        │   ├── stocks.py
        │   ├── chart.py
        │   └── analysis.py
        ├── services/
        │   ├── data_fetcher.py      — yfinance wrapper
        │   ├── black_scholes.py     — premium + greeks calculations
        │   ├── iv_rank.py           — IVR calculation
        │   └── technical.py        — S/R levels, Fibonacci, MAs, Pivots
        └── models/
            └── schemas.py           — Pydantic response models
```

---

## Docker Compose

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped
```

Run the full app:
```bash
docker-compose up --build
```

Access at: `http://localhost:3000`

---

## Migration Guide

### Moving to a New Machine (Windows / Mac / Linux)
1. Clone the repo
2. Install Docker Desktop
3. Run `docker-compose up --build`
4. Done — no other dependencies

### Moving to Raspberry Pi / Arduino (ARM)
> Note: "Arduino" boards (Uno, Nano) do not run Docker. Assume **Raspberry Pi** (ARM64) or similar single-board Linux computer.

1. Install Docker on the Pi: `curl -fsSL https://get.docker.com | sh`
2. Clone the repo onto the Pi (via SSH or USB)
3. In `docker-compose.yml`, ensure platform is set:
   ```yaml
   platform: linux/arm64
   ```
4. Build on the Pi directly: `docker-compose up --build`
5. Access from any device on the same network: `http://<pi-ip>:3000`

**Considerations for low-resource boards:**
- yfinance calls are slow — add caching (TTL ~15 minutes) to avoid hammering Yahoo
- Use `uvicorn --workers 1` in the backend Dockerfile to limit memory
- Frontend bundle should be served as static files via nginx (not dev server) in production

### Moving to Cloud (AWS / GCP / DigitalOcean)
1. Push images to a container registry (Docker Hub or ECR)
2. Deploy with the same `docker-compose.yml` on any Linux VM
3. Set `VITE_API_URL` to the backend's public IP or domain
4. Add a reverse proxy (nginx or Traefik) with HTTPS if exposing publicly

---

## Key Rules for Development

- **No mock data in production** — always fetch live from yfinance
- **Backend owns all calculations** — frontend only renders, never calculates
- **One docker-compose up** must start the entire app — no manual steps
- **Free data sources only** — no paid API keys required to run the app
- **Black-Scholes for pricing** — binomial trees only if American early-exercise is added later
