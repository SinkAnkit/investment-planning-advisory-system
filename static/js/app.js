/* ══════════════════════════════════════════════════════════════════════
   Investment Planning Advisory System — Dashboard Logic
   ══════════════════════════════════════════════════════════════════════ */

let priceChart = null;
let sentimentChart = null;

// ── Utility Helpers ────────────────────────────────────────────────────

function formatCurrency(val) {
    if (val == null || val === 'N/A') return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    if (Math.abs(num) >= 1e12) return '$' + (num / 1e12).toFixed(2) + 'T';
    if (Math.abs(num) >= 1e9) return '$' + (num / 1e9).toFixed(2) + 'B';
    if (Math.abs(num) >= 1e6) return '$' + (num / 1e6).toFixed(1) + 'M';
    return '$' + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatNumber(val) {
    if (val == null || val === 'N/A') return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (Math.abs(num) >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (Math.abs(num) >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toLocaleString();
}

function formatPercent(val) {
    if (val == null || val === 'N/A') return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    return (num * 100).toFixed(2) + '%';
}

function formatDecimal(val, digits = 2) {
    if (val == null || val === 'N/A') return '—';
    const num = Number(val);
    if (isNaN(num)) return '—';
    return num.toFixed(digits);
}

// ── Loading Animation ──────────────────────────────────────────────────

function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('welcomeSection').style.display = 'none';
    const prev = document.getElementById('previousSection');
    if (prev) prev.style.display = 'none';

    const steps = document.querySelectorAll('.step');
    steps.forEach(s => { s.classList.remove('active', 'done'); });

    let current = 0;
    const interval = setInterval(() => {
        if (current > 0) steps[current - 1].classList.replace('active', 'done');
        if (current < steps.length) {
            steps[current].classList.add('active');
            current++;
        } else {
            clearInterval(interval);
        }
    }, 700);
    window._loadingInterval = interval;
}

function hideLoading() {
    if (window._loadingInterval) clearInterval(window._loadingInterval);
    const steps = document.querySelectorAll('.step');
    steps.forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
    setTimeout(() => {
        document.getElementById('loadingOverlay').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
    }, 500);
}

// ── Core Analysis ──────────────────────────────────────────────────────

async function analyzeStock() {
    const input = document.getElementById('tickerInput');
    const ticker = input.value.trim().toUpperCase();
    if (!ticker) { input.focus(); return; }
    await runAnalysis(ticker);
}

function quickAnalyze(ticker) {
    document.getElementById('tickerInput').value = ticker;
    runAnalysis(ticker);
}

async function runAnalysis(ticker) {
    showLoading();
    try {
        const res = await fetch(`/api/analyze/${ticker}`);
        const data = await res.json();

        if (data.status === 'error') {
            alert(`Error analyzing ${ticker}: ${data.error}`);
            hideLoading();
            return;
        }

        populateDashboard(data);
        hideLoading();
        fetchPriceChart(ticker);
    } catch (err) {
        console.error('Analysis failed:', err);
        alert('Failed to analyze stock. Please check the console for details.');
        hideLoading();
    }
}

// ── Populate Dashboard ─────────────────────────────────────────────────

function populateDashboard(data) {
    const stock = data.stock || {};
    const insight = data.insight || {};
    const sentiment = data.sentiment || {};
    const risk = data.risk || {};

    // Stock header
    document.getElementById('stockName').textContent = stock.name || stock.ticker || '—';
    document.getElementById('stockTicker').textContent = stock.ticker || '—';
    document.getElementById('stockSector').textContent = stock.sector || 'N/A';
    document.getElementById('stockIndustry').textContent = stock.industry || '';

    // Price
    const price = stock.price;
    document.getElementById('stockPrice').textContent = price ? `$${Number(price).toFixed(2)}` : '—';

    // Change
    const prevClose = stock.previous_close;
    const changeEl = document.getElementById('stockChange');
    if (price && prevClose) {
        const changePct = ((price - prevClose) / prevClose * 100);
        const changeAbs = (price - prevClose);
        changeEl.textContent = `${changePct >= 0 ? '▲' : '▼'} $${Math.abs(changeAbs).toFixed(2)} (${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%)`;
        changeEl.className = `stock-change ${changePct >= 0 ? 'positive' : 'negative'}`;
    } else {
        changeEl.textContent = '—';
        changeEl.className = 'stock-change';
    }

    // Key metrics
    document.getElementById('metricMarketCap').textContent = formatCurrency(stock.market_cap);
    document.getElementById('metricPE').textContent = formatDecimal(stock.pe_ratio, 1);
    document.getElementById('metric52High').textContent = stock.week_52_high ? `$${Number(stock.week_52_high).toFixed(2)}` : '—';
    document.getElementById('metric52Low').textContent = stock.week_52_low ? `$${Number(stock.week_52_low).toFixed(2)}` : '—';
    document.getElementById('metricVolume').textContent = formatNumber(stock.volume);
    document.getElementById('metricBeta').textContent = formatDecimal(stock.beta);

    // Financial health
    document.getElementById('finRevenue').textContent = formatCurrency(stock.revenue);
    document.getElementById('finMargin').textContent = formatPercent(stock.profit_margin);
    document.getElementById('finROE').textContent = formatPercent(stock.return_on_equity);
    document.getElementById('finDebt').textContent = stock.debt_to_equity != null ? formatDecimal(stock.debt_to_equity, 1) : '—';
    document.getElementById('finFCF').textContent = formatCurrency(stock.free_cash_flow);
    document.getElementById('finDividend').textContent = formatPercent(stock.dividend_yield);

    // AI Recommendation
    populateRecommendation(insight);

    // Sentiment
    populateSentiment(sentiment);

    // Risk
    populateRisk(risk);

    // News
    populateNews(data);
}

// ── Recommendation Card ────────────────────────────────────────────────

function populateRecommendation(insight) {
    const label = document.getElementById('recLabel');
    const rec = (insight.recommendation || 'HOLD').toUpperCase();
    label.textContent = rec;
    label.className = 'rec-label';

    if (rec.includes('STRONG BUY')) label.classList.add('strong-buy');
    else if (rec.includes('BUY')) label.classList.add('buy');
    else if (rec.includes('STRONG SELL')) label.classList.add('strong-sell');
    else if (rec.includes('SELL')) label.classList.add('sell');
    else label.classList.add('hold');

    // Confidence
    const badge = document.getElementById('confidenceBadge');
    badge.textContent = `${insight.confidence || 'Medium'} Confidence`;

    // Summary
    document.getElementById('recSummary').textContent = insight.summary || 'No insight available.';

    // Key reasons
    const reasonsEl = document.getElementById('recReasons');
    const reasons = insight.key_reasons || [];
    if (reasons.length) {
        reasonsEl.innerHTML = '<h4>✅ Key Reasons</h4>' +
            reasons.map(r => `<div class="reason-item"><span class="reason-icon">▸</span><span>${r}</span></div>`).join('');
    } else {
        reasonsEl.innerHTML = '';
    }

    // Risk warnings
    const warningsEl = document.getElementById('recWarnings');
    const warnings = insight.risk_warnings || [];
    if (warnings.length) {
        warningsEl.innerHTML = '<h4>⚠️ Risk Warnings</h4>' +
            warnings.map(w => `<div class="warning-item"><span class="warning-icon">▸</span><span>${w}</span></div>`).join('');
    } else {
        warningsEl.innerHTML = '';
    }
}

// ── Sentiment ──────────────────────────────────────────────────────────

function populateSentiment(sentiment) {
    const avg = sentiment.average_sentiment || 0;
    const label = sentiment.overall_label || 'Neutral';
    const count = sentiment.articles_analyzed || 0;

    // Value display
    const valEl = document.getElementById('sentimentValue');
    valEl.textContent = avg >= 0 ? `+${avg.toFixed(3)}` : avg.toFixed(3);
    if (avg > 0.05) valEl.style.color = '#4ade80';
    else if (avg < -0.05) valEl.style.color = '#f87171';
    else valEl.style.color = '#fbbf24';

    // Label
    const labelEl = document.getElementById('sentimentLabel');
    labelEl.textContent = label;
    labelEl.style.color = valEl.style.color;

    // Stats
    document.getElementById('sentCount').textContent = count;
    document.getElementById('sentScore').textContent = avg >= 0 ? `+${avg.toFixed(4)}` : avg.toFixed(4);

    // Signal
    const signalEl = document.getElementById('sentSignal');
    if (avg > 0.15) { signalEl.textContent = '🟢 Bullish'; signalEl.style.color = '#4ade80'; }
    else if (avg > 0.05) { signalEl.textContent = '🟡 Mildly Bullish'; signalEl.style.color = '#fbbf24'; }
    else if (avg < -0.15) { signalEl.textContent = '🔴 Bearish'; signalEl.style.color = '#f87171'; }
    else if (avg < -0.05) { signalEl.textContent = '🟠 Mildly Bearish'; signalEl.style.color = '#fb923c'; }
    else { signalEl.textContent = '⚪ Neutral'; signalEl.style.color = '#9ca3c0'; }

    // Draw gauge
    drawSentimentGauge(avg);

    // Sentiment bar chart
    const recent = sentiment.recent_scores || [];
    drawSentimentChart(recent);
}

function drawSentimentGauge(value) {
    const canvas = document.getElementById('sentimentGauge');
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const cx = w / 2, cy = h - 10, r = 85;
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;

    // Track
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 14;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Gradient fill
    const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
    grad.addColorStop(0, '#f87171');
    grad.addColorStop(0.35, '#fb923c');
    grad.addColorStop(0.5, '#fbbf24');
    grad.addColorStop(0.65, '#a3e635');
    grad.addColorStop(1, '#4ade80');

    const normalized = Math.min(1, Math.max(0, (value + 1) / 2));
    const fillAngle = startAngle + normalized * Math.PI;

    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, fillAngle);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 14;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Needle dot
    const dotX = cx + r * Math.cos(fillAngle);
    const dotY = cy + r * Math.sin(fillAngle);
    ctx.beginPath();
    ctx.arc(dotX, dotY, 8, 0, 2 * Math.PI);
    ctx.fillStyle = 'white';
    ctx.shadowColor = 'rgba(99,102,241,0.5)';
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.beginPath();
    ctx.arc(dotX, dotY, 4, 0, 2 * Math.PI);
    ctx.fillStyle = '#6366f1';
    ctx.fill();
}

function drawSentimentChart(recent) {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    if (sentimentChart) sentimentChart.destroy();

    const labels = recent.map((r, i) => r.title ? r.title.substring(0, 25) + '...' : `#${i + 1}`);
    const values = recent.map(r => r.compound || 0);
    const colors = values.map(v => v > 0.05 ? 'rgba(74,222,128,0.75)' : v < -0.05 ? 'rgba(248,113,113,0.75)' : 'rgba(251,191,36,0.75)');
    const borders = values.map(v => v > 0.05 ? 'rgba(74,222,128,1)' : v < -0.05 ? 'rgba(248,113,113,1)' : 'rgba(251,191,36,1)');

    sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderColor: borders,
                borderWidth: 1,
                borderRadius: 6,
                barPercentage: 0.55,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(14,14,38,0.95)',
                    borderColor: 'rgba(99,102,241,0.3)',
                    borderWidth: 1,
                    titleFont: { family: "'Inter', sans-serif", size: 11 },
                    bodyFont: { family: "'JetBrains Mono', monospace", size: 13, weight: '700' },
                    padding: 12, cornerRadius: 10,
                    callbacks: {
                        title: (items) => {
                            const idx = items[0].dataIndex;
                            return recent[idx]?.title || `Article ${idx + 1}`;
                        },
                        label: (c) => `Score: ${c.raw >= 0 ? '+' : ''}${c.raw.toFixed(3)}`
                    }
                }
            },
            scales: {
                x: { display: false },
                y: {
                    min: -1, max: 1,
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: '#7c82a6', font: { size: 11, weight: '600' } }
                }
            }
        }
    });
}

// ── Risk ───────────────────────────────────────────────────────────────

function populateRisk(risk) {
    const score = risk.risk_score || 0;
    const level = (risk.risk_level || 'Medium').toLowerCase();
    const factors = risk.factors || [];

    // Badge
    const badge = document.getElementById('riskBadge');
    badge.textContent = risk.risk_level || 'Medium';
    badge.className = `risk-badge ${level}`;

    // Score number
    document.getElementById('riskScoreNumber').textContent = score.toFixed(3);
    const scoreEl = document.getElementById('riskScoreNumber');
    if (level === 'low') scoreEl.style.color = '#4ade80';
    else if (level === 'high') scoreEl.style.color = '#f87171';
    else scoreEl.style.color = '#fbbf24';

    // Bar + marker
    const pct = score * 100;
    document.getElementById('riskBarFill').style.width = `${pct}%`;
    document.getElementById('riskBarMarker').style.left = `${pct}%`;

    // Factors
    const container = document.getElementById('riskFactors');
    container.innerHTML = factors.map(f => {
        const dotLevel = f.score > 0.6 ? 'high' : f.score > 0.3 ? 'medium' : 'low';
        return `<div class="risk-factor">
            <div class="risk-dot ${dotLevel}"></div>
            <div><strong>${f.name}</strong> (${f.score.toFixed(2)})<br><span style="font-size:0.78rem; opacity:0.75">${f.detail}</span></div>
        </div>`;
    }).join('');
}

// ── News Feed ──────────────────────────────────────────────────────────

function populateNews(data) {
    const feed = document.getElementById('newsFeed');
    const sentRecent = (data.sentiment && data.sentiment.recent_scores) || [];

    if (!sentRecent.length) {
        feed.innerHTML = '<div class="news-empty">No recent news articles found for this ticker</div>';
        return;
    }

    feed.innerHTML = sentRecent.map(item => {
        const score = item.compound || 0;
        let sentClass = 'neutral', sentText = 'Neutral';
        if (score > 0.05) { sentClass = 'positive'; sentText = `+${score.toFixed(2)}`; }
        if (score > 0.25) sentText = `↑ ${score.toFixed(2)}`;
        if (score < -0.05) { sentClass = 'negative'; sentText = score.toFixed(2); }
        if (score < -0.25) sentText = `↓ ${score.toFixed(2)}`;

        return `<div class="news-item">
            <div class="news-title">${item.title || 'Untitled'}</div>
            <span class="news-sentiment ${sentClass}">${sentText}</span>
        </div>`;
    }).join('');
}

// ── Price Chart ────────────────────────────────────────────────────────

async function fetchPriceChart(ticker) {
    try {
        const res = await fetch(`/api/prices/${ticker}`);
        const data = await res.json();
        drawPriceChart(data.prices || []);
    } catch (err) {
        console.error('Price chart error:', err);
    }
}

function drawPriceChart(prices) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();

    const sorted = [...prices].reverse();
    const labels = sorted.map(p => {
        const d = new Date(p.date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const closes = sorted.map(p => p.close);

    const isUp = closes.length >= 2 && closes[closes.length - 1] >= closes[0];
    const lineColor = isUp ? '#4ade80' : '#f87171';
    const fillColor = isUp ? 'rgba(74,222,128,0.08)' : 'rgba(248,113,113,0.08)';

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                data: closes,
                borderColor: lineColor,
                backgroundColor: fillColor,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: lineColor,
                pointHoverBorderColor: 'white',
                pointHoverBorderWidth: 2,
                borderWidth: 2.5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(14,14,38,0.95)',
                    borderColor: 'rgba(99,102,241,0.3)',
                    borderWidth: 1,
                    titleFont: { family: "'Inter', sans-serif", size: 12, weight: '600' },
                    bodyFont: { family: "'JetBrains Mono', monospace", size: 14, weight: '700' },
                    padding: 14, cornerRadius: 12,
                    displayColors: false,
                    callbacks: { label: (c) => `  $${c.raw.toFixed(2)}` }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#7c82a6', font: { size: 11, weight: '600' }, maxTicksLimit: 7 }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: {
                        color: '#7c82a6', font: { size: 11, weight: '600' },
                        callback: v => '$' + v.toFixed(0)
                    }
                }
            }
        }
    });
}

// ── Event Listeners ────────────────────────────────────────────────────

document.getElementById('tickerInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') analyzeStock();
});

document.getElementById('tickerInput').addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
});
