"""FastAPI application — serves API endpoints and the web dashboard."""
import json
from pathlib import Path
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from data import init_db, get_all_stocks, get_stock, get_news, get_latest_insight, get_stock_prices
from pipeline import run_pipeline, run_batch_pipeline, get_cached_analysis

# ── App setup ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Investment Planning Advisory System",
    description="GenAI-based real-time stock analysis with NLP sentiment and AI-powered investment insights",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup():
    """Initialize the database on startup."""
    init_db()


# ── Dashboard ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard page."""
    stocks = get_all_stocks()
    return templates.TemplateResponse(request, "index.html", {"stocks": stocks})


# ── API Endpoints ───────────────────────────────────────────────────────

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    """Run the full analysis pipeline for a single stock ticker."""
    try:
        result = run_pipeline(ticker.upper())
        # Clean non-serializable data
        if "stock" in result and "history" in result.get("stock", {}):
            result["stock"].pop("history", None)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)


@app.get("/api/batch")
async def batch_analyze(tickers: str = Query("AAPL,GOOGL,MSFT", description="Comma-separated tickers")):
    """Run the pipeline for multiple stock tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) > 10:
        return JSONResponse(content={"error": "Maximum 10 tickers per batch"}, status_code=400)
    try:
        results = run_batch_pipeline(ticker_list)
        # Clean non-serializable
        for r in results:
            if "stock" in r and "history" in r.get("stock", {}):
                r["stock"].pop("history", None)
        return JSONResponse(content={"results": results})
    except Exception as e:
        return JSONResponse(content={"status": "error", "error": str(e)}, status_code=500)


@app.get("/api/stocks")
async def list_stocks():
    """List all previously analyzed stocks."""
    stocks = get_all_stocks()
    return JSONResponse(content={"stocks": stocks})


@app.get("/api/stock/{ticker}")
async def get_stock_detail(ticker: str):
    """Get detailed cached data for a stock."""
    data = get_cached_analysis(ticker.upper())
    if not data:
        return JSONResponse(content={"error": "Stock not found. Run /api/analyze/{ticker} first."}, status_code=404)
    return JSONResponse(content=data)


@app.get("/api/news/{ticker}")
async def get_stock_news(ticker: str):
    """Get news articles with sentiment scores for a ticker."""
    news = get_news(ticker.upper(), limit=20)
    return JSONResponse(content={"ticker": ticker.upper(), "news": news})


@app.get("/api/insights/{ticker}")
async def get_stock_insights(ticker: str):
    """Get the latest GenAI-generated investment insight."""
    insight = get_latest_insight(ticker.upper())
    if not insight:
        return JSONResponse(content={"error": "No insights found. Run /api/analyze/{ticker} first."}, status_code=404)
    return JSONResponse(content={"ticker": ticker.upper(), "insight": insight})


@app.get("/api/prices/{ticker}")
async def get_prices(ticker: str, limit: int = 30):
    """Get historical price data for charting."""
    prices = get_stock_prices(ticker.upper(), limit=limit)
    return JSONResponse(content={"ticker": ticker.upper(), "prices": prices})


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok", "service": "Investment Planning Advisory System"})
