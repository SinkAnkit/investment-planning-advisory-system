"""Fetch real-time stock market data using Finnhub API."""
import time
import requests
from datetime import datetime, timedelta
from data import upsert_stock, upsert_stock_prices
from config import FINNHUB_API_KEY

_BASE_URL = "https://finnhub.io/api/v1"


def _fh_get(endpoint: str, params: dict | None = None) -> dict | list:
    """Make an authenticated GET request to Finnhub."""
    params = params or {}
    params["token"] = FINNHUB_API_KEY
    resp = requests.get(f"{_BASE_URL}{endpoint}", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch comprehensive stock data from Finnhub:
      - Current price, P/E ratio, market cap, volume  (quote + profile + metrics)
      - 30-day historical prices                       (stock/candle)
    Returns a summary dict and stores everything in SQLite.
    """
    ticker = ticker.upper().strip()

    # ── Fetch from three endpoints in sequence ──────────────────────────
    quote = _fh_get("/quote", {"symbol": ticker})
    profile = _fh_get("/stock/profile2", {"symbol": ticker})
    metrics = _fh_get("/stock/metric", {"symbol": ticker, "metric": "all"})

    m = metrics.get("metric", {}) if isinstance(metrics, dict) else {}

    # Validate we got real data
    if not profile or not profile.get("name"):
        # Finnhub returns {} for invalid tickers
        raise ValueError(
            f"No data found for ticker '{ticker}'. "
            "Please check the symbol is a valid US stock ticker (e.g. AAPL, MSFT, GOOGL)."
        )

    # ── Build stock_data dict (same shape as before) ────────────────────
    stock_data = {
        "ticker": ticker,
        "name": profile.get("name", ticker),
        "sector": profile.get("finnhubIndustry", "N/A"),
        "industry": profile.get("finnhubIndustry", "N/A"),
        "market_cap": profile.get("marketCapitalization"),  # in millions
        "pe_ratio": m.get("peNormalizedAnnual") or m.get("peTTM"),
        "forward_pe": m.get("peAnnual"),
        "price": quote.get("c"),         # current price
        "previous_close": quote.get("pc"),
        "day_high": quote.get("h"),
        "day_low": quote.get("l"),
        "week_52_high": m.get("52WeekHigh"),
        "week_52_low": m.get("52WeekLow"),
        "volume": None,  # Finnhub quote doesn't provide volume in free tier
        "avg_volume": m.get("10DayAverageTradingVolume"),
        "dividend_yield": m.get("dividendYieldIndicatedAnnual"),
        "beta": m.get("beta"),
        "debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
        "revenue": m.get("revenuePerShareTTM"),
        "profit_margin": m.get("netProfitMarginTTM"),
        "return_on_equity": m.get("roeTTM"),
        "free_cash_flow": m.get("freeCashFlowPerShareTTM"),
    }

    # Convert market cap from millions to raw number for consistency
    if stock_data["market_cap"] is not None:
        stock_data["market_cap"] = stock_data["market_cap"] * 1_000_000

    # Convert avg_volume from millions to raw number
    if stock_data["avg_volume"] is not None:
        stock_data["avg_volume"] = int(stock_data["avg_volume"] * 1_000_000)

    # Convert percentage metrics to decimals (Finnhub returns as %)
    for key in ("profit_margin", "return_on_equity", "dividend_yield"):
        if stock_data[key] is not None:
            stock_data[key] = stock_data[key] / 100

    # Store in database
    upsert_stock(stock_data)

    # ── Historical prices (30 days) ─────────────────────────────────────
    price_rows = _fetch_candles(ticker, days=30)
    if price_rows:
        upsert_stock_prices(ticker, price_rows)

    stock_data["history"] = price_rows
    return stock_data


def _fetch_candles(ticker: str, days: int = 30) -> list[dict]:
    """Fetch daily OHLCV candles from Finnhub."""
    now = datetime.utcnow()
    to_ts = int(now.timestamp())
    from_ts = int((now - timedelta(days=days)).timestamp())

    data = _fh_get("/stock/candle", {
        "symbol": ticker,
        "resolution": "D",
        "from": from_ts,
        "to": to_ts,
    })

    if data.get("s") != "ok":
        return []

    rows = []
    for i in range(len(data.get("t", []))):
        rows.append({
            "date": datetime.utcfromtimestamp(data["t"][i]).strftime("%Y-%m-%d"),
            "open": round(data["o"][i], 2),
            "high": round(data["h"][i], 2),
            "low": round(data["l"][i], 2),
            "close": round(data["c"][i], 2),
            "volume": int(data["v"][i]),
        })
    return rows


def fetch_price_history(ticker: str, period: str = "1mo") -> list[dict]:
    """Fetch price history for a given period (1mo, 3mo, 1y)."""
    days_map = {"1mo": 30, "3mo": 90, "1y": 365}
    days = days_map.get(period, 30)
    return _fetch_candles(ticker.upper(), days=days)
