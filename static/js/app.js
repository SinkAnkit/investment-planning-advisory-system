/* ══════════════════════════════════════════════════════════════════════
   Investment Planning Advisory System — Terminal UI Logic
   ══════════════════════════════════════════════════════════════════════ */

let priceChart = null;
let sentimentChart = null;

/* ── Helpers ────────────────────────────────────────────────────────── */

function fmt$(val) {
    if (val == null || val === 'N/A') return '—';
    const n = Number(val);
    if (isNaN(n)) return '—';
    if (Math.abs(n) >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
    if (Math.abs(n) >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
    return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtN(val) {
    if (val == null || val === 'N/A') return '—';
    const n = Number(val);
    if (isNaN(n)) return '—';
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M';
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
    return n.toLocaleString();
}

function fmtP(val) {
    if (val == null) return '—';
    return (Number(val) * 100).toFixed(2) + '%';
}

function fmtD(val, d = 2) {
    if (val == null) return '—';
    return Number(val).toFixed(d);
}

/* ── Loading ────────────────────────────────────────────────────────── */

function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('mainContent').style.display = 'none';
    document.getElementById('welcomeSection').style.display = 'none';

    // Pipeline sidebar
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById('pipe' + i);
        if (el) { el.classList.remove('active', 'done'); }
    }
    // Loading terminal lines
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById('ls' + i);
        if (el) { el.classList.remove('active', 'done'); }
    }

    let step = 1;
    const interval = setInterval(() => {
        if (step > 1) {
            const prev = document.getElementById('ls' + (step - 1));
            const prevPipe = document.getElementById('pipe' + (step - 1));
            if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
            if (prevPipe) { prevPipe.classList.remove('active'); prevPipe.classList.add('done'); }
        }
        if (step <= 5) {
            const cur = document.getElementById('ls' + step);
            const curPipe = document.getElementById('pipe' + step);
            if (cur) cur.classList.add('active');
            if (curPipe) curPipe.classList.add('active');
            step++;
        } else {
            clearInterval(interval);
        }
    }, 600);
    window._loadingInterval = interval;
}

function hideLoading() {
    if (window._loadingInterval) clearInterval(window._loadingInterval);
    for (let i = 1; i <= 5; i++) {
        const el = document.getElementById('ls' + i);
        const pipe = document.getElementById('pipe' + i);
        if (el) { el.classList.remove('active'); el.classList.add('done'); }
        if (pipe) { pipe.classList.remove('active'); pipe.classList.add('done'); }
    }
    setTimeout(() => {
        document.getElementById('loadingOverlay').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
    }, 400);
}

/* ── Core ───────────────────────────────────────────────────────────── */

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
            alert(`Error: ${data.error}`);
            hideLoading();
            return;
        }
        populate(data);
        hideLoading();
        fetchPriceChart(ticker);
    } catch (err) {
        console.error(err);
        alert('Analysis failed. Check console.');
        hideLoading();
    }
}

/* ── Populate All ───────────────────────────────────────────────────── */

function populate(data) {
    const s = data.stock || {};
    const ins = data.insight || {};
    const sen = data.sentiment || {};
    const r = data.risk || {};

    // Stock bar
    document.getElementById('stockTicker').textContent = s.ticker || '—';
    document.getElementById('stockName').textContent = s.name || s.ticker || '—';
    document.getElementById('stockSector').textContent = s.sector || '';

    // Price
    document.getElementById('stockPrice').textContent = s.price ? `$${Number(s.price).toFixed(2)}` : '—';
    const changeEl = document.getElementById('stockChange');
    if (s.price && s.previous_close) {
        const pct = ((s.price - s.previous_close) / s.previous_close * 100);
        const abs = Math.abs(s.price - s.previous_close);
        changeEl.textContent = `${pct >= 0 ? '▲' : '▼'} $${abs.toFixed(2)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
        changeEl.className = `sb-change ${pct >= 0 ? 'up' : 'down'}`;
    } else {
        changeEl.textContent = '—';
        changeEl.className = 'sb-change';
    }

    // Metrics strip
    document.getElementById('metricMarketCap').textContent = fmt$(s.market_cap);
    document.getElementById('metricPE').textContent = fmtD(s.pe_ratio, 1);
    document.getElementById('metric52High').textContent = s.week_52_high ? `$${Number(s.week_52_high).toFixed(2)}` : '—';
    document.getElementById('metric52Low').textContent = s.week_52_low ? `$${Number(s.week_52_low).toFixed(2)}` : '—';
    document.getElementById('metricVolume').textContent = fmtN(s.volume);
    document.getElementById('metricBeta').textContent = fmtD(s.beta);

    // Financials
    document.getElementById('finRevenue').textContent = fmt$(s.revenue);
    document.getElementById('finMargin').textContent = fmtP(s.profit_margin);
    document.getElementById('finROE').textContent = fmtP(s.return_on_equity);
    document.getElementById('finDebt').textContent = s.debt_to_equity != null ? fmtD(s.debt_to_equity, 1) : '—';
    document.getElementById('finFCF').textContent = fmt$(s.free_cash_flow);
    document.getElementById('finDividend').textContent = fmtP(s.dividend_yield);

    buildRec(ins);
    buildSentiment(sen);
    buildRisk(r);
    buildNews(data);
}

/* ── Recommendation ─────────────────────────────────────────────────── */

function buildRec(ins) {
    const rec = (ins.recommendation || 'HOLD').toUpperCase();
    const el = document.getElementById('recLabel');
    el.textContent = rec;
    el.className = 'rec-signal';
    if (rec.includes('STRONG BUY')) el.classList.add('strong-buy');
    else if (rec.includes('BUY')) el.classList.add('buy');
    else if (rec.includes('STRONG SELL')) el.classList.add('strong-sell');
    else if (rec.includes('SELL')) el.classList.add('sell');
    else el.classList.add('hold');

    const badge = document.getElementById('confidenceBadge');
    badge.textContent = (ins.confidence || 'MEDIUM').toUpperCase();
    badge.className = 'ph-badge';
    if (ins.confidence === 'High') badge.classList.add('green');
    else if (ins.confidence === 'Low') badge.classList.add('red');
    else badge.classList.add('amber');

    document.getElementById('recSummary').textContent = ins.summary || '—';

    const reasons = ins.key_reasons || [];
    document.getElementById('recReasons').innerHTML = reasons.length ?
        '<h4>KEY REASONS</h4>' + reasons.map(r => `<div class="reason-item"><span>▸</span><span>${r}</span></div>`).join('') : '';

    const warnings = ins.risk_warnings || [];
    document.getElementById('recWarnings').innerHTML = warnings.length ?
        '<h4>RISK WARNINGS</h4>' + warnings.map(w => `<div class="warning-item"><span>▸</span><span>${w}</span></div>`).join('') : '';
}

/* ── Sentiment ──────────────────────────────────────────────────────── */

function buildSentiment(sen) {
    const avg = sen.average_sentiment || 0;
    const label = sen.overall_label || 'Neutral';

    const scoreEl = document.getElementById('sentimentValue');
    scoreEl.textContent = avg >= 0 ? `+${avg.toFixed(3)}` : avg.toFixed(3);
    scoreEl.style.color = avg > 0.05 ? '#00d47e' : avg < -0.05 ? '#f85149' : '#d29922';

    const labelEl = document.getElementById('sentimentLabel');
    labelEl.textContent = label.toUpperCase();
    labelEl.className = 'ph-badge';
    labelEl.classList.add(avg > 0.05 ? 'green' : avg < -0.05 ? 'red' : 'amber');

    document.getElementById('sentCount').textContent = sen.articles_analyzed || 0;
    document.getElementById('sentScore').textContent = avg >= 0 ? `+${avg.toFixed(4)}` : avg.toFixed(4);

    const signalEl = document.getElementById('sentSignal');
    if (avg > 0.15) { signalEl.textContent = 'BULLISH'; signalEl.style.color = '#00d47e'; }
    else if (avg > 0.05) { signalEl.textContent = 'MILDLY BULLISH'; signalEl.style.color = '#d29922'; }
    else if (avg < -0.15) { signalEl.textContent = 'BEARISH'; signalEl.style.color = '#f85149'; }
    else if (avg < -0.05) { signalEl.textContent = 'MILDLY BEARISH'; signalEl.style.color = '#d29922'; }
    else { signalEl.textContent = 'NEUTRAL'; signalEl.style.color = '#8b949e'; }

    drawSentimentBars(sen.recent_scores || []);
}

function drawSentimentBars(recent) {
    const ctx = document.getElementById('sentimentChart').getContext('2d');
    if (sentimentChart) sentimentChart.destroy();

    const labels = recent.map((r, i) => r.title ? r.title.substring(0, 20) + '...' : `#${i + 1}`);
    const vals = recent.map(r => r.compound || 0);
    const colors = vals.map(v => v > 0.05 ? 'rgba(0,212,126,0.65)' : v < -0.05 ? 'rgba(248,81,73,0.65)' : 'rgba(210,153,34,0.65)');
    const borders = vals.map(v => v > 0.05 ? '#00d47e' : v < -0.05 ? '#f85149' : '#d29922');

    sentimentChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ data: vals, backgroundColor: colors, borderColor: borders, borderWidth: 1, borderRadius: 3, barPercentage: 0.5 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#161b22', borderColor: '#30363d', borderWidth: 1,
                    titleFont: { family: "'Space Grotesk'", size: 11 },
                    bodyFont: { family: "'IBM Plex Mono'", size: 12, weight: '700' },
                    padding: 10, cornerRadius: 6,
                    callbacks: {
                        title: (items) => recent[items[0].dataIndex]?.title || '',
                        label: (c) => `Score: ${c.raw >= 0 ? '+' : ''}${c.raw.toFixed(3)}`
                    }
                }
            },
            scales: {
                x: { display: false },
                y: { min: -1, max: 1, grid: { color: 'rgba(48,54,61,0.5)' }, ticks: { color: '#6e7681', font: { size: 10, family: "'IBM Plex Mono'" } } }
            }
        }
    });
}

/* ── Risk ───────────────────────────────────────────────────────────── */

function buildRisk(risk) {
    const score = risk.risk_score || 0;
    const level = (risk.risk_level || 'Medium').toLowerCase();

    const badge = document.getElementById('riskBadge');
    badge.textContent = (risk.risk_level || 'MEDIUM').toUpperCase();
    badge.className = 'ph-badge';
    badge.classList.add(level === 'low' ? 'green' : level === 'high' ? 'red' : 'amber');

    const numEl = document.getElementById('riskScoreNumber');
    numEl.textContent = score.toFixed(3);
    numEl.style.color = level === 'low' ? '#00d47e' : level === 'high' ? '#f85149' : '#d29922';

    const pct = score * 100;
    document.getElementById('riskBarFill').style.width = `${pct}%`;
    document.getElementById('riskBarMarker').style.left = `${pct}%`;

    const factors = risk.factors || [];
    document.getElementById('riskFactors').innerHTML = factors.map(f => {
        const dot = f.score > 0.6 ? 'high' : f.score > 0.3 ? 'medium' : 'low';
        return `<div class="risk-factor"><div class="risk-dot ${dot}"></div><div><strong>${f.name}</strong> (${f.score.toFixed(2)})<br><span style="font-size:0.75rem;color:#8b949e">${f.detail}</span></div></div>`;
    }).join('');
}

/* ── News ───────────────────────────────────────────────────────────── */

function buildNews(data) {
    const feed = document.getElementById('newsFeed');
    const recent = (data.sentiment && data.sentiment.recent_scores) || [];
    if (!recent.length) { feed.innerHTML = '<div class="news-empty">No news found</div>'; return; }

    feed.innerHTML = recent.map(item => {
        const sc = item.compound || 0;
        let cls = 'neu', txt = '0.00';
        if (sc > 0.05) { cls = 'pos'; txt = `+${sc.toFixed(2)}`; }
        else if (sc < -0.05) { cls = 'neg'; txt = sc.toFixed(2); }
        return `<div class="news-item"><div class="news-title">${item.title || 'Untitled'}</div><span class="news-sent ${cls}">${txt}</span></div>`;
    }).join('');
}

/* ── Price Chart ────────────────────────────────────────────────────── */

async function fetchPriceChart(ticker) {
    try {
        const res = await fetch(`/api/prices/${ticker}`);
        const data = await res.json();
        drawPriceChart(data.prices || []);
    } catch (err) { console.error(err); }
}

function drawPriceChart(prices) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();

    const sorted = [...prices].reverse();
    const labels = sorted.map(p => new Date(p.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    const closes = sorted.map(p => p.close);
    const isUp = closes.length >= 2 && closes[closes.length - 1] >= closes[0];
    const color = isUp ? '#00d47e' : '#f85149';
    const fill = isUp ? 'rgba(0,212,126,0.06)' : 'rgba(248,81,73,0.06)';

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                data: closes, borderColor: color, backgroundColor: fill,
                fill: true, tension: 0.3, pointRadius: 0,
                pointHoverRadius: 5, pointHoverBackgroundColor: color,
                pointHoverBorderColor: '#f0f6fc', pointHoverBorderWidth: 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#161b22', borderColor: '#30363d', borderWidth: 1,
                    titleFont: { family: "'Space Grotesk'", size: 11 },
                    bodyFont: { family: "'IBM Plex Mono'", size: 13, weight: '700' },
                    padding: 10, cornerRadius: 6, displayColors: false,
                    callbacks: { label: c => `  $${c.raw.toFixed(2)}` }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#6e7681', font: { size: 10, family: "'IBM Plex Mono'" }, maxTicksLimit: 7 } },
                y: { grid: { color: 'rgba(48,54,61,0.4)' }, ticks: { color: '#6e7681', font: { size: 10, family: "'IBM Plex Mono'" }, callback: v => '$' + v.toFixed(0) } }
            }
        }
    });
}

/* ── Events ─────────────────────────────────────────────────────────── */

document.getElementById('tickerInput').addEventListener('keydown', e => { if (e.key === 'Enter') analyzeStock(); });
document.getElementById('tickerInput').addEventListener('input', e => { e.target.value = e.target.value.toUpperCase(); });
