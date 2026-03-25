"""SQLite database layer — schema initialization and CRUD operations."""
import sqlite3
import json
from datetime import datetime
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            industry TEXT,
            market_cap REAL,
            pe_ratio REAL,
            forward_pe REAL,
            price REAL,
            previous_close REAL,
            day_high REAL,
            day_low REAL,
            week_52_high REAL,
            week_52_low REAL,
            volume INTEGER,
            avg_volume INTEGER,
            dividend_yield REAL,
            beta REAL,
            debt_to_equity REAL,
            revenue REAL,
            profit_margin REAL,
            return_on_equity REAL,
            free_cash_flow REAL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            UNIQUE(ticker, date),
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        );

        CREATE TABLE IF NOT EXISTS financial_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            link TEXT,
            published_at TEXT,
            source TEXT,
            fetched_at TEXT,
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        );

        CREATE TABLE IF NOT EXISTS sentiment_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            news_id INTEGER,
            compound REAL,
            positive REAL,
            negative REAL,
            neutral REAL,
            label TEXT,
            analyzed_at TEXT,
            FOREIGN KEY (ticker) REFERENCES stocks(ticker),
            FOREIGN KEY (news_id) REFERENCES financial_news(id)
        );

        CREATE TABLE IF NOT EXISTS investment_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            recommendation TEXT,
            confidence TEXT,
            summary TEXT,
            key_reasons TEXT,
            risk_warnings TEXT,
            risk_score REAL,
            risk_level TEXT,
            sentiment_avg REAL,
            generated_at TEXT,
            FOREIGN KEY (ticker) REFERENCES stocks(ticker)
        );
    """)
    conn.commit()
    conn.close()


# ── Stock CRUD ──────────────────────────────────────────────────────────

def upsert_stock(data: dict):
    """Insert or update a stock record."""
    conn = get_connection()
    data["updated_at"] = datetime.utcnow().isoformat()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    updates = ", ".join([f"{k}=excluded.{k}" for k in data.keys()])
    conn.execute(
        f"INSERT INTO stocks ({cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(ticker) DO UPDATE SET {updates}",
        list(data.values()),
    )
    conn.commit()
    conn.close()


def upsert_stock_prices(ticker: str, rows: list[dict]):
    """Bulk insert historical price rows."""
    conn = get_connection()
    for row in rows:
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices (ticker, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticker, row["date"], row["open"], row["high"], row["low"], row["close"], row["volume"]),
        )
    conn.commit()
    conn.close()


def insert_news(ticker: str, articles: list[dict]):
    """Insert news articles, skip duplicates by link."""
    conn = get_connection()
    for a in articles:
        try:
            conn.execute(
                "INSERT INTO financial_news (ticker, title, summary, link, published_at, source, fetched_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker, a["title"], a.get("summary", ""), a["link"],
                 a.get("published_at", ""), a.get("source", ""), datetime.utcnow().isoformat()),
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()


def insert_sentiment(ticker: str, news_id: int, scores: dict):
    """Insert a sentiment score record."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO sentiment_scores (ticker, news_id, compound, positive, negative, neutral, label, analyzed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (ticker, news_id, scores["compound"], scores["pos"], scores["neg"],
         scores["neu"], scores["label"], datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def insert_insight(ticker: str, insight: dict):
    """Insert a generated investment insight."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO investment_insights "
        "(ticker, recommendation, confidence, summary, key_reasons, risk_warnings, risk_score, risk_level, sentiment_avg, generated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            ticker,
            insight.get("recommendation", ""),
            insight.get("confidence", ""),
            insight.get("summary", ""),
            json.dumps(insight.get("key_reasons", [])),
            json.dumps(insight.get("risk_warnings", [])),
            insight.get("risk_score", 0),
            insight.get("risk_level", ""),
            insight.get("sentiment_avg", 0),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


# ── Query helpers ───────────────────────────────────────────────────────

def get_stock(ticker: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM stocks WHERE ticker = ?", (ticker,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_stocks() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM stocks ORDER BY ticker").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_stock(ticker: str):
    """Delete a stock and all related records."""
    conn = get_connection()
    conn.execute("DELETE FROM sentiment_scores WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM financial_news WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM investment_insights WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM stock_prices WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM stocks WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()


def get_stock_prices(ticker: str, limit: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM stock_prices WHERE ticker = ? ORDER BY date DESC LIMIT ?",
        (ticker, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_news(ticker: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT fn.*, ss.compound, ss.label as sentiment_label "
        "FROM financial_news fn "
        "LEFT JOIN sentiment_scores ss ON fn.id = ss.news_id "
        "WHERE fn.ticker = ? ORDER BY fn.fetched_at DESC LIMIT ?",
        (ticker, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_insight(ticker: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM investment_insights WHERE ticker = ? ORDER BY generated_at DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["key_reasons"] = json.loads(d.get("key_reasons", "[]"))
        d["risk_warnings"] = json.loads(d.get("risk_warnings", "[]"))
        return d
    return None


def get_unscored_news(ticker: str) -> list[dict]:
    """Get news articles that haven't been sentiment-scored yet."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT fn.* FROM financial_news fn "
        "LEFT JOIN sentiment_scores ss ON fn.id = ss.news_id "
        "WHERE fn.ticker = ? AND ss.id IS NULL",
        (ticker,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_avg_sentiment(ticker: str) -> float:
    """Get average compound sentiment for a ticker."""
    conn = get_connection()
    row = conn.execute(
        "SELECT AVG(compound) as avg_compound FROM sentiment_scores WHERE ticker = ?",
        (ticker,),
    ).fetchone()
    conn.close()
    return row["avg_compound"] if row and row["avg_compound"] is not None else 0.0
