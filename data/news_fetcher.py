"""Fetch financial news from RSS feeds."""
import feedparser
from datetime import datetime
from data import insert_news
from config import NEWS_FEEDS


def fetch_news(ticker: str) -> list[dict]:
    """
    Fetch financial news headlines for a stock ticker from RSS feeds.
    Returns list of article dicts and stores them in SQLite.
    """
    articles = []

    for feed_url_template in NEWS_FEEDS:
        feed_url = feed_url_template.format(ticker=ticker)
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # Limit to 10 per feed
                pub_date = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_date = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        pub_date = entry.get("published", "")

                article = {
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],
                    "link": entry.get("link", ""),
                    "published_at": pub_date,
                    "source": feed.feed.get("title", "Unknown"),
                }
                articles.append(article)
        except Exception as e:
            print(f"[NEWS] Error fetching {feed_url}: {e}")

    # De-duplicate by title
    seen = set()
    unique_articles = []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique_articles.append(a)

    # Store in database
    if unique_articles:
        insert_news(ticker, unique_articles)

    return unique_articles
