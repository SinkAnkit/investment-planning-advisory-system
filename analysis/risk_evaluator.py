"""Risk evaluation engine — combines financial metrics and sentiment to score risk."""
from config import RISK_THRESHOLDS


def evaluate_risk(stock_data: dict, avg_sentiment: float) -> dict:
    """
    Evaluate a stock's risk profile using structured financial data
    and unstructured sentiment signals.

    Factors scored (0-1 each, weighted):
      - P/E Ratio vs sector norms
      - Price volatility (52-week range %)
      - Debt-to-Equity ratio
      - Sentiment polarity
      - Profit margin health
      - Beta (market sensitivity)

    Returns a risk dict with score, level, and factor breakdown.
    """
    factors = []
    weights = []

    # ── P/E Ratio Risk ──────────────────────────────────────────────────
    pe = stock_data.get("pe_ratio")
    if pe is not None:
        if pe > RISK_THRESHOLDS["pe_high"]:
            score = min(1.0, (pe - RISK_THRESHOLDS["pe_high"]) / 30)
            factors.append({"name": "High P/E Ratio", "score": score,
                            "detail": f"P/E of {pe:.1f} is above the {RISK_THRESHOLDS['pe_high']} threshold — stock may be overvalued"})
        elif pe < RISK_THRESHOLDS["pe_low"]:
            score = 0.3
            factors.append({"name": "Low P/E Ratio", "score": score,
                            "detail": f"P/E of {pe:.1f} is below {RISK_THRESHOLDS['pe_low']} — could indicate undervaluation or declining earnings"})
        else:
            score = 0.0
            factors.append({"name": "P/E Ratio", "score": score,
                            "detail": f"P/E of {pe:.1f} is within normal range"})
        weights.append(0.2)
    else:
        factors.append({"name": "P/E Ratio", "score": 0.5, "detail": "P/E data unavailable"})
        weights.append(0.1)

    # ── Volatility (52-week range) ──────────────────────────────────────
    high_52 = stock_data.get("week_52_high")
    low_52 = stock_data.get("week_52_low")
    price = stock_data.get("price")
    if high_52 and low_52 and price and high_52 > 0:
        range_pct = (high_52 - low_52) / high_52
        if range_pct > 0.5:
            score = min(1.0, range_pct)
            factors.append({"name": "High Volatility", "score": score,
                            "detail": f"52-week range of {range_pct:.0%} indicates significant price swings"})
        else:
            score = range_pct * 0.5
            factors.append({"name": "Volatility", "score": score,
                            "detail": f"52-week range of {range_pct:.0%} is moderate"})
        weights.append(0.2)
    else:
        factors.append({"name": "Volatility", "score": 0.5, "detail": "Volatility data unavailable"})
        weights.append(0.1)

    # ── Debt-to-Equity ──────────────────────────────────────────────────
    dte = stock_data.get("debt_to_equity")
    if dte is not None:
        dte_val = dte / 100 if dte > 10 else dte  # Finnhub sometimes returns as %
        if dte_val > RISK_THRESHOLDS["debt_equity_high"]:
            score = min(1.0, dte_val / 4)
            factors.append({"name": "High Debt", "score": score,
                            "detail": f"Debt-to-equity of {dte_val:.2f} exceeds safe threshold of {RISK_THRESHOLDS['debt_equity_high']}"})
        else:
            score = dte_val / (RISK_THRESHOLDS["debt_equity_high"] * 2)
            factors.append({"name": "Debt Level", "score": score,
                            "detail": f"Debt-to-equity of {dte_val:.2f} is manageable"})
        weights.append(0.2)
    else:
        factors.append({"name": "Debt Level", "score": 0.5, "detail": "Debt data unavailable"})
        weights.append(0.1)

    # ── Sentiment Risk ──────────────────────────────────────────────────
    if avg_sentiment < RISK_THRESHOLDS["sentiment_negative"]:
        score = min(1.0, abs(avg_sentiment))
        factors.append({"name": "Negative Sentiment", "score": score,
                        "detail": f"Average news sentiment of {avg_sentiment:.3f} indicates bearish market mood"})
    elif avg_sentiment > RISK_THRESHOLDS["sentiment_positive"]:
        score = 0.0
        factors.append({"name": "Positive Sentiment", "score": score,
                        "detail": f"Average news sentiment of {avg_sentiment:.3f} indicates bullish market mood"})
    else:
        score = 0.3
        factors.append({"name": "Neutral Sentiment", "score": score,
                        "detail": f"Average news sentiment of {avg_sentiment:.3f} is neutral"})
    weights.append(0.2)

    # ── Profit Margin ───────────────────────────────────────────────────
    margin = stock_data.get("profit_margin")
    if margin is not None:
        if margin < 0:
            score = min(1.0, abs(margin))
            factors.append({"name": "Negative Margins", "score": score,
                            "detail": f"Profit margin of {margin:.1%} — company is unprofitable"})
        elif margin < 0.05:
            score = 0.5
            factors.append({"name": "Thin Margins", "score": score,
                            "detail": f"Profit margin of {margin:.1%} is razor-thin"})
        else:
            score = max(0, 0.3 - margin)
            factors.append({"name": "Profit Margin", "score": score,
                            "detail": f"Profit margin of {margin:.1%} is healthy"})
        weights.append(0.15)
    else:
        factors.append({"name": "Profit Margin", "score": 0.5, "detail": "Margin data unavailable"})
        weights.append(0.05)

    # ── Beta (Market Sensitivity) ───────────────────────────────────────
    beta = stock_data.get("beta")
    if beta is not None:
        if beta > 1.5:
            score = min(1.0, (beta - 1) / 2)
            factors.append({"name": "High Beta", "score": score,
                            "detail": f"Beta of {beta:.2f} — stock is significantly more volatile than the market"})
        elif beta < 0.5:
            score = 0.1
            factors.append({"name": "Low Beta", "score": score,
                            "detail": f"Beta of {beta:.2f} — stock moves less than the market"})
        else:
            score = (beta - 0.5) / 2
            factors.append({"name": "Beta", "score": score,
                            "detail": f"Beta of {beta:.2f} — moderate market correlation"})
        weights.append(0.05)
    else:
        factors.append({"name": "Beta", "score": 0.5, "detail": "Beta data unavailable"})
        weights.append(0.05)

    # ── Compute weighted risk score ─────────────────────────────────────
    total_weight = sum(weights)
    risk_score = sum(f["score"] * w for f, w in zip(factors, weights)) / total_weight if total_weight > 0 else 0.5
    risk_score = round(risk_score, 3)

    if risk_score >= 0.65:
        risk_level = "High"
    elif risk_score >= 0.35:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "factors": factors,
    }
