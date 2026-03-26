"""Configuration for the Investment Advisory System."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "investadvisor.db"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Default tickers to monitor
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]

# RSS News Feed URLs for financial news
NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
]

# Risk thresholds
RISK_THRESHOLDS = {
    "pe_high": 35,
    "pe_low": 10,
    "volatility_high": 0.04,
    "debt_equity_high": 2.0,
    "sentiment_negative": -0.15,
    "sentiment_positive": 0.15,
}
