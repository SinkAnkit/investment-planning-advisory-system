"""NLP Sentiment Analysis using VADER — optimized for financial text."""
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from data import get_unscored_news, insert_sentiment, get_avg_sentiment

# Download VADER lexicon on first use
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", quiet=True)

# Extend VADER with finance-specific terms
FINANCE_LEXICON = {
    "bull": 2.0, "bullish": 2.5, "buy": 1.5, "upgrade": 2.0, "outperform": 2.0,
    "rally": 2.0, "surge": 2.5, "soar": 2.5, "boom": 2.0, "profit": 1.5,
    "gains": 1.5, "growth": 1.5, "beat": 1.5, "exceeds": 1.5, "breakout": 2.0,
    "dividend": 1.0, "recovery": 1.5, "momentum": 1.0, "upside": 1.5,
    "bear": -2.0, "bearish": -2.5, "sell": -1.5, "downgrade": -2.0,
    "underperform": -2.0, "crash": -3.0, "plunge": -2.5, "slump": -2.0,
    "decline": -1.5, "loss": -1.5, "debt": -1.0, "miss": -1.5, "recession": -2.5,
    "layoff": -2.0, "layoffs": -2.0, "bankruptcy": -3.5, "default": -2.5,
    "investigation": -1.5, "lawsuit": -1.5, "fraud": -3.0, "overvalued": -1.5,
    "undervalued": 1.5, "volatile": -1.0, "volatility": -1.0, "risk": -0.5,
}


def _get_analyzer() -> SentimentIntensityAnalyzer:
    """Create a VADER analyzer with finance-specific lexicon additions."""
    sia = SentimentIntensityAnalyzer()
    sia.lexicon.update(FINANCE_LEXICON)
    return sia


def classify_sentiment(compound: float) -> str:
    """Map a compound score to a human-readable label."""
    if compound >= 0.25:
        return "Very Positive"
    elif compound >= 0.05:
        return "Positive"
    elif compound <= -0.25:
        return "Very Negative"
    elif compound <= -0.05:
        return "Negative"
    return "Neutral"


def analyze_sentiment(ticker: str) -> dict:
    """
    Run sentiment analysis on all un-scored news for a ticker.
    Returns aggregate sentiment summary.
    """
    sia = _get_analyzer()
    unscored = get_unscored_news(ticker)
    results = []

    for article in unscored:
        text = f"{article['title']}. {article.get('summary', '')}"
        scores = sia.polarity_scores(text)
        scores["label"] = classify_sentiment(scores["compound"])
        insert_sentiment(ticker, article["id"], scores)
        results.append({
            "title": article["title"],
            "compound": scores["compound"],
            "label": scores["label"],
        })

    avg_sentiment = get_avg_sentiment(ticker)
    overall_label = classify_sentiment(avg_sentiment)

    return {
        "ticker": ticker,
        "articles_analyzed": len(results),
        "average_sentiment": round(avg_sentiment, 4),
        "overall_label": overall_label,
        "recent_scores": results[:10],
    }
