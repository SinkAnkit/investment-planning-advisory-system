"""GenAI-powered investment insight generator using Google Gemini."""
import json
from config import GEMINI_API_KEY

_genai = None


def _get_model():
    """Lazy-load the Gemini model."""
    global _genai
    if _genai is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            _genai = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as e:
            print(f"[GEMINI] Failed to initialize: {e}")
            _genai = None
    return _genai


def _build_prompt(stock_data: dict, sentiment_summary: dict, risk_result: dict) -> str:
    """Build a structured prompt for Gemini with all analysis data."""
    ticker = stock_data.get("ticker", "UNKNOWN")
    name = stock_data.get("name", ticker)

    prompt = f"""You are an expert financial analyst AI. Analyze the following stock data and provide a comprehensive investment advisory.

## Stock: {name} ({ticker})

### Market Data
- Current Price: ${stock_data.get('price', 'N/A')}
- P/E Ratio: {stock_data.get('pe_ratio', 'N/A')}
- Forward P/E: {stock_data.get('forward_pe', 'N/A')}
- Market Cap: {stock_data.get('market_cap', 'N/A')}
- 52-Week High: ${stock_data.get('week_52_high', 'N/A')}
- 52-Week Low: ${stock_data.get('week_52_low', 'N/A')}
- Volume: {stock_data.get('volume', 'N/A')}
- Beta: {stock_data.get('beta', 'N/A')}

### Financial Health
- Revenue: ${stock_data.get('revenue', 'N/A')}
- Profit Margin: {stock_data.get('profit_margin', 'N/A')}
- Return on Equity: {stock_data.get('return_on_equity', 'N/A')}
- Debt-to-Equity: {stock_data.get('debt_to_equity', 'N/A')}
- Free Cash Flow: ${stock_data.get('free_cash_flow', 'N/A')}
- Dividend Yield: {stock_data.get('dividend_yield', 'N/A')}

### Sentiment Analysis
- Average Sentiment Score: {sentiment_summary.get('average_sentiment', 0)}
- Overall Label: {sentiment_summary.get('overall_label', 'Neutral')}
- Articles Analyzed: {sentiment_summary.get('articles_analyzed', 0)}

### Risk Assessment
- Risk Score: {risk_result.get('risk_score', 'N/A')} (0=lowest, 1=highest)
- Risk Level: {risk_result.get('risk_level', 'N/A')}

Respond ONLY with valid JSON in this exact format (no markdown, no code fences):
{{
    "recommendation": "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "STRONG SELL",
    "confidence": "High" | "Medium" | "Low",
    "summary": "A 2-3 sentence executive summary of the investment thesis",
    "key_reasons": ["reason 1", "reason 2", "reason 3", "reason 4"],
    "risk_warnings": ["warning 1", "warning 2", "warning 3"]
}}"""
    return prompt


def _fallback_insight(stock_data: dict, sentiment_summary: dict, risk_result: dict) -> dict:
    """Generate rule-based insights when Gemini is unavailable."""
    risk_score = risk_result.get("risk_score", 0.5)
    avg_sentiment = sentiment_summary.get("average_sentiment", 0)
    pe = stock_data.get("pe_ratio")
    margin = stock_data.get("profit_margin")
    ticker = stock_data.get("ticker", "UNKNOWN")
    name = stock_data.get("name", ticker)

    # Determine recommendation based on combined signals
    score = 0
    reasons = []
    warnings = []

    # Sentiment signal
    if avg_sentiment > 0.15:
        score += 2
        reasons.append(f"Positive market sentiment ({avg_sentiment:.3f}) suggests bullish outlook")
    elif avg_sentiment < -0.15:
        score -= 2
        warnings.append(f"Negative market sentiment ({avg_sentiment:.3f}) indicates bearish pressure")
    else:
        reasons.append("Market sentiment is neutral — no strong directional bias from news")

    # Risk signal
    if risk_score < 0.35:
        score += 1
        reasons.append(f"Low risk profile ({risk_score:.2f}) indicates stability")
    elif risk_score > 0.65:
        score -= 1
        warnings.append(f"High risk score ({risk_score:.2f}) warrants caution")

    # P/E signal
    if pe is not None:
        if pe < 15:
            score += 1
            reasons.append(f"P/E ratio of {pe:.1f} suggests potential undervaluation")
        elif pe > 35:
            score -= 1
            warnings.append(f"P/E ratio of {pe:.1f} may indicate the stock is overvalued")

    # Margin signal
    if margin is not None:
        if margin > 0.15:
            score += 1
            reasons.append(f"Strong profit margin of {margin:.1%} demonstrates operational efficiency")
        elif margin < 0:
            score -= 1
            warnings.append(f"Negative profit margin of {margin:.1%} — company is currently unprofitable")

    if not warnings:
        warnings.append("Past performance does not guarantee future results")
        warnings.append("Always conduct your own due diligence before investing")

    # Map score to recommendation
    if score >= 3:
        rec, conf = "STRONG BUY", "High"
    elif score >= 1:
        rec, conf = "BUY", "Medium"
    elif score <= -3:
        rec, conf = "STRONG SELL", "High"
    elif score <= -1:
        rec, conf = "SELL", "Medium"
    else:
        rec, conf = "HOLD", "Medium"

    summary = (
        f"{name} ({ticker}) currently shows a {risk_result.get('risk_level', 'Medium').lower()} risk profile "
        f"with {sentiment_summary.get('overall_label', 'Neutral').lower()} market sentiment. "
        f"Based on combined fundamental and sentiment analysis, the stock is rated as {rec}."
    )

    return {
        "recommendation": rec,
        "confidence": conf,
        "summary": summary,
        "key_reasons": reasons[:4],
        "risk_warnings": warnings[:3],
    }


def generate_insight(stock_data: dict, sentiment_summary: dict, risk_result: dict) -> dict:
    """
    Generate investment insight using Gemini AI.
    Falls back to rule-based analysis if Gemini is unavailable.
    """
    model = _get_model()

    if model and GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
        try:
            prompt = _build_prompt(stock_data, sentiment_summary, risk_result)
            response = model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            insight = json.loads(text)
            # Validate expected keys
            for key in ("recommendation", "confidence", "summary", "key_reasons", "risk_warnings"):
                if key not in insight:
                    raise ValueError(f"Missing key: {key}")
            return insight
        except Exception as e:
            print(f"[GEMINI] Error generating insight: {e}")

    # Fallback to rule-based
    return _fallback_insight(stock_data, sentiment_summary, risk_result)
