"""Automated analysis pipeline — orchestrates data fetching → analysis → insight generation."""
from data.stock_fetcher import fetch_stock_data
from data.news_fetcher import fetch_news
from analysis import analyze_sentiment
from analysis.risk_evaluator import evaluate_risk
from analysis.insight_generator import generate_insight
from data import insert_insight, get_avg_sentiment, get_stock, get_latest_insight, get_news, get_stock_prices


def run_pipeline(ticker: str) -> dict:
    """
    Execute the full investment advisory pipeline for a single stock:
      1. Fetch real-time stock data (prices, P/E, financials)
      2. Fetch financial news from RSS feeds
      3. Run NLP sentiment analysis on news
      4. Evaluate risk using combined metrics
      5. Generate GenAI-powered investment insight
    Returns a comprehensive analysis result dict.
    """
    ticker = ticker.upper().strip()
    result = {"ticker": ticker, "status": "success"}

    # ── Step 1: Fetch stock data ────────────────────────────────────────
    try:
        stock_data = fetch_stock_data(ticker)
        result["stock"] = stock_data
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Failed to fetch stock data: {e}"
        return result

    # ── Step 2: Fetch news ──────────────────────────────────────────────
    try:
        articles = fetch_news(ticker)
        result["news_count"] = len(articles)
    except Exception as e:
        result["news_count"] = 0
        print(f"[PIPELINE] News fetch error for {ticker}: {e}")

    # ── Step 3: Sentiment analysis ──────────────────────────────────────
    try:
        sentiment_summary = analyze_sentiment(ticker)
        result["sentiment"] = sentiment_summary
    except Exception as e:
        sentiment_summary = {"average_sentiment": 0, "overall_label": "Neutral", "articles_analyzed": 0}
        result["sentiment"] = sentiment_summary
        print(f"[PIPELINE] Sentiment error for {ticker}: {e}")

    # ── Step 4: Risk evaluation ─────────────────────────────────────────
    avg_sentiment = get_avg_sentiment(ticker)
    risk_result = evaluate_risk(stock_data, avg_sentiment)
    result["risk"] = risk_result

    # ── Step 5: Generate GenAI insight ──────────────────────────────────
    try:
        insight = generate_insight(stock_data, sentiment_summary, risk_result)
        insight["risk_score"] = risk_result["risk_score"]
        insight["risk_level"] = risk_result["risk_level"]
        insight["sentiment_avg"] = avg_sentiment
        insert_insight(ticker, insight)
        result["insight"] = insight
    except Exception as e:
        result["insight"] = {"recommendation": "HOLD", "summary": f"Unable to generate insight: {e}"}
        print(f"[PIPELINE] Insight generation error for {ticker}: {e}")

    return result


def run_batch_pipeline(tickers: list[str]) -> list[dict]:
    """Run the full pipeline for a list of stock tickers."""
    results = []
    for ticker in tickers:
        try:
            result = run_pipeline(ticker)
            results.append(result)
        except Exception as e:
            results.append({"ticker": ticker, "status": "error", "error": str(e)})
    return results


def get_cached_analysis(ticker: str) -> dict | None:
    """Get the most recent stored analysis for a ticker without re-fetching."""
    stock = get_stock(ticker)
    if not stock:
        return None

    insight = get_latest_insight(ticker)
    news = get_news(ticker, limit=10)
    prices = get_stock_prices(ticker, limit=30)

    return {
        "ticker": ticker,
        "stock": stock,
        "insight": insight,
        "news": news,
        "prices": prices,
    }
