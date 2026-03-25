"""Fetch real-time stock market data using yfinance."""
import yfinance as yf
from data import upsert_stock, upsert_stock_prices


def fetch_stock_data(ticker: str) -> dict:
    """
    Fetch comprehensive stock data:
      - Current price, P/E ratio, market cap, volume
      - Financial statements (revenue, margins, cash flow)
      - 30-day historical prices
    Returns a summary dict and stores everything in SQLite.
    """
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    # ── Core metrics ────────────────────────────────────────────────────
    stock_data = {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "previous_close": info.get("previousClose"),
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "week_52_high": info.get("fiftyTwoWeekHigh"),
        "week_52_low": info.get("fiftyTwoWeekLow"),
        "volume": info.get("volume"),
        "avg_volume": info.get("averageVolume"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue": info.get("totalRevenue"),
        "profit_margin": info.get("profitMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "free_cash_flow": info.get("freeCashflow"),
    }

    # Store in database
    upsert_stock(stock_data)

    # ── Historical prices (30 days) ─────────────────────────────────────
    hist = stock.history(period="1mo")
    price_rows = []
    for date_idx, row in hist.iterrows():
        price_rows.append({
            "date": date_idx.strftime("%Y-%m-%d"),
            "open": round(row["Open"], 2),
            "high": round(row["High"], 2),
            "low": round(row["Low"], 2),
            "close": round(row["Close"], 2),
            "volume": int(row["Volume"]),
        })
    if price_rows:
        upsert_stock_prices(ticker, price_rows)

    stock_data["history"] = price_rows
    return stock_data
