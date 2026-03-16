#!/usr/bin/env python3
"""Relational Memory — Vector Visualization v2.

Renders the 7D vector as radar chart, signal history as timeline,
memory layers, drift detection, and multi-user comparison.

Usage:
    python visualize.py --user florian
    python visualize.py --user florian sohn    # comparison
    python visualize.py --user florian -o report.html
    python visualize.py                         # list available users
"""

import json
import sys
import webbrowser
import tempfile
from pathlib import Path

LAYER_NAMES = ("base_tone", "patterns", "anchors")


def get_memory_dir() -> Path:
    return Path.home() / ".relational_memory"


def list_users() -> list[str]:
    d = get_memory_dir()
    if not d.exists():
        return []
    return sorted(x.name for x in d.iterdir() if x.is_dir() and (x / "vector.json").exists())


def load_data(user_id: str) -> dict:
    base = get_memory_dir() / user_id

    vector = None
    vp = base / "vector.json"
    if vp.exists():
        try:
            vector = json.loads(vp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    log = []
    lp = base / "signal_log.json"
    if lp.exists():
        try:
            log = json.loads(lp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    layers = {}
    layers_dir = base / "layers"
    if layers_dir.exists():
        for name in LAYER_NAMES:
            lf = layers_dir / f"{name}.md"
            if lf.exists():
                try:
                    layers[name] = lf.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeDecodeError):
                    pass

    return {"user_id": user_id, "vector": vector, "signal_log": log, "layers": layers}


def generate_html(users_data: list[dict]) -> str:
    mode = "compare" if len(users_data) > 1 else "single"
    title = " vs ".join(u["user_id"] for u in users_data)
    return (
        HTML_TEMPLATE
        .replace("__TITLE__", title)
        .replace("'__MODE__'", json.dumps(mode))
        .replace("'__USERS_DATA__'", json.dumps(users_data, ensure_ascii=False))
    )


def main():
    import argparse
    p = argparse.ArgumentParser(description="Relational Memory — Vector Visualization")
    p.add_argument("--user", "-u", nargs="+", help="User ID(s) — one for detail, two+ for comparison")
    p.add_argument("--output", "-o", help="Save HTML to file instead of opening in browser")
    args = p.parse_args()

    if not args.user:
        users = list_users()
        if not users:
            print(f"No data found in {get_memory_dir()}")
            sys.exit(1)
        print("Available users:")
        for u in users:
            print(f"  {u}")
        print(f"\nUsage: python {sys.argv[0]} --user <id> [<id2>]")
        sys.exit(0)

    users_data = []
    for uid in args.user:
        data = load_data(uid)
        if not data["vector"]:
            print(f"No vector.json found for '{uid}'")
            sys.exit(1)
        users_data.append(data)

    html = generate_html(users_data)

    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Saved: {args.output}")
    else:
        label = "_vs_".join(u["user_id"] for u in users_data)
        tmp = Path(tempfile.gettempdir()) / f"relational_memory_{label}.html"
        tmp.write_text(html, encoding="utf-8")
        webbrowser.open(tmp.as_uri())
        print(f"Opened: {tmp}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relational Memory — __TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0d1117;--card:#161b22;--border:#30363d;
  --text:#e6edf3;--muted:#8b949e;--accent:#d4a574;
}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;padding:2rem;line-height:1.6;
}
.container{max-width:1200px;margin:0 auto}
header{margin-bottom:2rem;padding-bottom:1.5rem;border-bottom:1px solid var(--border)}
header h1{font-size:1.5rem;font-weight:600;color:var(--accent);margin-bottom:.5rem}
.meta{display:flex;gap:1.5rem;color:var(--muted);font-size:.875rem;flex-wrap:wrap;align-items:center}
.badge{background:rgba(212,165,116,.15);color:var(--accent);padding:.15rem .7rem;border-radius:12px;font-weight:500}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:1.5rem}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1.5rem;margin-bottom:1.5rem}
.card h2{font-size:.75rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:1rem}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:.5rem}
.card-header h2{margin-bottom:0}

/* Dimension bars */
.dim-row{display:flex;align-items:center;margin-bottom:.85rem}
.dim-label{width:105px;font-size:.85rem;color:var(--muted);flex-shrink:0}
.dim-bar-wrap{flex:1;position:relative;height:20px;margin:0 .75rem}
.dim-bar-bg{position:absolute;inset:0;background:#21262d;border-radius:4px}
.dim-range{position:absolute;top:0;height:100%;border-radius:4px}
.dim-bar{position:absolute;top:0;left:0;height:100%;border-radius:4px;transition:width .6s ease}
.dim-value{width:38px;text-align:right;font-size:.85rem;font-variant-numeric:tabular-nums;flex-shrink:0}
.dim-delta{width:55px;text-align:right;font-size:.75rem;flex-shrink:0}
.dim-delta.up{color:#34d399}
.dim-delta.down{color:#f87171}
.dim-delta.neutral{color:var(--muted)}

/* Toggle buttons */
.toggle-group{display:flex;gap:2px;background:#21262d;border-radius:6px;padding:2px}
.toggle-btn{
  padding:.35rem .75rem;border:none;background:transparent;color:var(--muted);
  font-size:.8rem;cursor:pointer;border-radius:4px;transition:all .2s;
}
.toggle-btn.active{background:var(--border);color:var(--text)}
.toggle-btn:hover:not(.active){color:var(--text)}

/* Session cards */
.session-card{background:#21262d;border-radius:6px;margin-bottom:.5rem;overflow:hidden}
.session-hdr{
  padding:.65rem 1rem;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;font-size:.85rem;transition:background .15s;user-select:none;
}
.session-hdr:hover{background:#30363d}
.session-hdr .arrow{transition:transform .2s;color:var(--muted)}
.session-hdr .arrow.open{transform:rotate(90deg)}
.session-dots{display:flex;gap:4px;align-items:center}
.dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.session-body{padding:0 1rem 1rem;display:none}
.session-body.open{display:block}
.evidence{margin-bottom:.75rem;padding-bottom:.75rem;border-bottom:1px solid #30363d}
.evidence:last-child{margin-bottom:0;padding-bottom:0;border-bottom:none}
.evidence-dim{font-weight:600;font-size:.8rem;margin-bottom:.25rem;display:flex;align-items:center;gap:.5rem}
.evidence-val{font-weight:400;color:var(--muted);font-variant-numeric:tabular-nums}
.evidence-text{font-size:.8rem;color:var(--muted);line-height:1.5}

/* Canvas containers */
.chart-wrap{position:relative;width:100%}
.chart-wrap.radar{max-width:400px;margin:0 auto}

/* Drift banner */
.drift-banner{
  background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.25);
  border-radius:8px;padding:1rem 1.5rem;margin-bottom:1.5rem;font-size:.85rem;
}
.drift-banner strong{color:#f87171;font-size:.8rem;text-transform:uppercase;letter-spacing:.05em}
.drift-item{margin-top:.5rem;display:flex;align-items:center;gap:.75rem;font-size:.8rem;color:var(--muted)}
.drift-dim{font-weight:600;width:90px}
.drift-arrow{font-size:1rem}
.drift-arrow.up{color:#f87171}
.drift-arrow.down{color:#34d399}

/* Layers */
.layer-desc{font-size:.75rem;color:var(--muted);margin-bottom:1rem;font-style:italic}
.layer-text{font-size:.85rem;line-height:1.8;color:var(--muted);white-space:pre-wrap}
.layer-empty{color:var(--muted);font-style:italic;font-size:.85rem}
.pattern-item{
  padding:.6rem 0;border-bottom:1px solid rgba(48,54,61,.5);font-size:.85rem;line-height:1.6;
}
.pattern-item:last-child{border-bottom:none}
.pattern-trigger{color:var(--text)}
.pattern-arrow{color:var(--accent);margin:0 .25rem}
.pattern-action{color:var(--muted)}
.anchor-item{
  position:relative;padding-left:1.5rem;margin-bottom:.85rem;font-size:.85rem;line-height:1.6;
}
.anchor-item::before{
  content:'';position:absolute;left:0;top:.45rem;width:8px;height:8px;
  border-radius:50%;background:var(--accent);
}
.anchor-title{color:var(--text);font-weight:600}
.anchor-time{color:var(--muted);font-size:.75rem;margin-left:.5rem}
.anchor-desc{display:block;color:var(--muted);margin-top:.15rem}

/* Correction badge */
.correction-badge{
  background:rgba(251,191,36,.15);color:#fbbf24;padding:.1rem .5rem;
  border-radius:4px;font-size:.7rem;font-weight:600;margin-left:.5rem;
}

/* Compare mode */
.compare-legend{display:flex;gap:1.5rem;margin-bottom:1.5rem}
.compare-legend-item{display:flex;align-items:center;gap:.5rem;font-size:.85rem}
.compare-dot{width:12px;height:12px;border-radius:50%}
.dim-group-label{font-size:.8rem;color:var(--muted);margin-bottom:.35rem}
.dim-group{margin-bottom:1rem}
.dim-user-label{width:70px;font-size:.75rem;flex-shrink:0;text-align:right;padding-right:.5rem}
.user-tabs{display:flex;gap:2px;background:#21262d;border-radius:6px;padding:2px;margin-right:.5rem}
.user-tab{
  padding:.35rem .75rem;border:none;background:transparent;color:var(--muted);
  font-size:.8rem;cursor:pointer;border-radius:4px;transition:all .2s;
}
.user-tab.active{background:var(--border);color:var(--text)}
</style>
</head>
<body>
<div class="container">

  <header>
    <h1>Relational Memory</h1>
    <div class="meta">
      <span class="badge" id="userId"></span>
      <span id="sessionInfo"></span>
      <span id="lastUpdated"></span>
    </div>
  </header>

  <div id="driftBanner" class="drift-banner" style="display:none">
    <strong>Drift Warning</strong>
    <div id="driftDetails"></div>
  </div>

  <div id="compareLegend" class="compare-legend" style="display:none"></div>

  <div class="grid">
    <div class="card">
      <h2>Current Vector</h2>
      <div class="chart-wrap radar"><canvas id="radar"></canvas></div>
    </div>
    <div class="card">
      <h2>Dimensions</h2>
      <div id="dims"></div>
    </div>
  </div>

  <div class="card" id="layersCard">
    <div class="card-header">
      <h2>Memory Layers</h2>
      <div style="display:flex;gap:.5rem;align-items:center">
        <div class="user-tabs" id="layerUserTabs" style="display:none"></div>
        <div class="toggle-group" id="layerTabs"></div>
      </div>
    </div>
    <div id="layerContent"></div>
  </div>

  <div class="card" id="timelineCard">
    <div class="card-header">
      <h2>Timeline</h2>
      <div class="toggle-group">
        <button class="toggle-btn active" data-mode="raw">Raw Signals</button>
        <button class="toggle-btn" data-mode="ema">EMA Vector</button>
        <button class="toggle-btn" data-mode="both">Both</button>
      </div>
    </div>
    <div class="chart-wrap"><canvas id="timeline"></canvas></div>
  </div>

  <div class="card" id="sessionsCard">
    <h2>Session Details</h2>
    <div id="sessions"></div>
  </div>

</div>

<script>
// ── Data (embedded by Python) ──────────────────────────────
const MODE = '__MODE__';
const USERS = '__USERS_DATA__';

// ── Constants ──────────────────────────────────────────────
const DIMS = ['formality','warmth','humor','depth','trust','energy','resilience'];
const LABELS = {
  formality:'Formality', warmth:'Warmth', humor:'Humor',
  depth:'Depth', trust:'Trust', energy:'Energy', resilience:'Resilience'
};
const COLORS = {
  formality:'#818cf8', warmth:'#f87171', humor:'#fbbf24',
  depth:'#a78bfa', trust:'#34d399', energy:'#fb923c', resilience:'#22d3ee'
};
const USER_COLORS = ['#d4a574','#58a6ff','#a78bfa','#34d399'];
const ALPHA_NORMAL = 0.9;
const ALPHA_CORRECTION = 0.5;
const DRIFT_THRESHOLD = 0.25;
const MIN_SESSIONS_DRIFT = 5;

// ── Helpers ────────────────────────────────────────────────
function fmt(v) { return v.toFixed(2); }
function fmtDate(iso) {
  if (!iso) return '\u2014';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'})
    + ' ' + d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
}
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function computeEma(log) {
  const history = [];
  const v = {}; DIMS.forEach(d => v[d] = 0.5);
  log.forEach(entry => {
    const corrs = entry.signals?._explicit_corrections;
    const corrDims = new Set();
    if (Array.isArray(corrs)) corrs.forEach(c => { if (DIMS.includes(c.dimension)) corrDims.add(c.dimension); });
    DIMS.forEach(d => {
      if (entry.signals && entry.signals[d]) {
        const alpha = corrDims.has(d) ? ALPHA_CORRECTION : ALPHA_NORMAL;
        v[d] = alpha * v[d] + (1 - alpha) * entry.signals[d].value;
      }
    });
    history.push({...v});
  });
  return history;
}

function getStats(log) {
  const stats = {};
  DIMS.forEach(dim => {
    const vals = log.map(e => e.signals?.[dim]?.value).filter(v => v != null);
    stats[dim] = vals.length ? {
      min: Math.min(...vals), max: Math.max(...vals),
      avg: vals.reduce((a,b) => a+b, 0) / vals.length
    } : { min: 0.5, max: 0.5, avg: 0.5 };
  });
  return stats;
}

function computeBaseline(log) {
  if (log.length < MIN_SESSIONS_DRIFT) return null;
  const sums = {}; const counts = {};
  DIMS.forEach(d => { sums[d] = 0; counts[d] = 0; });
  log.forEach(entry => {
    DIMS.forEach(d => {
      const v = entry.signals?.[d]?.value;
      if (v != null) { sums[d] += v; counts[d]++; }
    });
  });
  const baseline = {};
  let ok = true;
  DIMS.forEach(d => { if (counts[d] > 0) baseline[d] = sums[d] / counts[d]; else ok = false; });
  return ok ? baseline : null;
}

function detectDrift(vectorVals, baseline) {
  if (!baseline) return [];
  return DIMS
    .filter(d => Math.abs(vectorVals[d] - baseline[d]) >= DRIFT_THRESHOLD)
    .map(d => ({
      dimension: d, baseline: baseline[d], current: vectorVals[d],
      drift: vectorVals[d] - baseline[d],
      direction: vectorVals[d] > baseline[d] ? 'higher' : 'lower'
    }));
}

function hasCorrections(entry) {
  const c = entry.signals?._explicit_corrections;
  return Array.isArray(c) && c.length > 0;
}

// ── Primary user data ─────────────────────────────────────
const user = USERS[0];
const vector = user.vector;
const signalLog = user.signal_log;
const layers = user.layers || {};
const emaHistory = computeEma(signalLog);
const stats = getStats(signalLog);
const baseline = computeBaseline(signalLog);
const driftAlerts = detectDrift(vector.values, baseline);

// ── Header ────────────────────────────────────────────────
if (MODE === 'single') {
  document.getElementById('userId').textContent = user.user_id;
  document.getElementById('sessionInfo').textContent = vector.session_count + ' Sessions';
  document.getElementById('lastUpdated').textContent = 'Updated ' + fmtDate(vector.last_updated);
} else {
  document.getElementById('userId').textContent = USERS.map(u => u.user_id).join(' vs ');
  document.getElementById('sessionInfo').textContent = USERS.map(u => u.vector.session_count + 's').join(' / ');
  document.getElementById('lastUpdated').textContent = '';
  const legend = document.getElementById('compareLegend');
  legend.style.display = 'flex';
  USERS.forEach((u, i) => {
    legend.innerHTML += '<div class="compare-legend-item"><span class="compare-dot" style="background:' + USER_COLORS[i] + '"></span>' + escHtml(u.user_id) + ' (' + u.vector.session_count + ' sessions)</div>';
  });
}

// ── Drift Banner (single mode) ────────────────────────────
if (driftAlerts.length > 0 && MODE === 'single') {
  const banner = document.getElementById('driftBanner');
  banner.style.display = 'block';
  const details = document.getElementById('driftDetails');
  driftAlerts.forEach(a => {
    const arrow = a.direction === 'higher' ? '\u2191' : '\u2193';
    const cls = a.direction === 'higher' ? 'up' : 'down';
    details.innerHTML += '<div class="drift-item">'
      + '<span class="drift-dim" style="color:' + COLORS[a.dimension] + '">' + LABELS[a.dimension] + '</span>'
      + '<span class="drift-arrow ' + cls + '">' + arrow + ' ' + fmt(Math.abs(a.drift)) + '</span>'
      + '<span>baseline ' + fmt(a.baseline) + ' \u2192 current ' + fmt(a.current) + '</span>'
      + '</div>';
  });
}

// ── Radar Chart ───────────────────────────────────────────
const radarDatasets = [{
  label: MODE === 'compare' ? USERS[0].user_id : 'Current',
  data: DIMS.map(d => vector.values[d]),
  fill: true,
  backgroundColor: USER_COLORS[0] + '20',
  borderColor: USER_COLORS[0],
  borderWidth: 2,
  pointBackgroundColor: USER_COLORS[0],
  pointBorderColor: '#0d1117',
  pointBorderWidth: 2,
  pointRadius: 5,
  pointHoverRadius: 7,
}];

if (baseline && MODE === 'single') {
  radarDatasets.push({
    label: 'Baseline',
    data: DIMS.map(d => baseline[d]),
    fill: false,
    backgroundColor: 'transparent',
    borderColor: '#8b949e',
    borderWidth: 1,
    borderDash: [4, 4],
    pointBackgroundColor: '#8b949e',
    pointBorderColor: 'transparent',
    pointRadius: 3,
    pointHoverRadius: 5,
  });
}

if (MODE === 'compare') {
  USERS.slice(1).forEach((u, i) => {
    radarDatasets.push({
      label: u.user_id,
      data: DIMS.map(d => u.vector.values[d]),
      fill: true,
      backgroundColor: USER_COLORS[i+1] + '15',
      borderColor: USER_COLORS[i+1],
      borderWidth: 2,
      borderDash: [6, 3],
      pointBackgroundColor: USER_COLORS[i+1],
      pointBorderColor: '#0d1117',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
    });
  });
}

new Chart(document.getElementById('radar'), {
  type: 'radar',
  data: { labels: DIMS.map(d => LABELS[d]), datasets: radarDatasets },
  options: {
    responsive: true,
    scales: {
      r: {
        min: 0, max: 1,
        ticks: { stepSize: 0.2, color: '#8b949e', backdropColor: 'transparent', font: { size: 10 } },
        grid: { color: '#30363d' },
        angleLines: { color: '#30363d' },
        pointLabels: { color: '#e6edf3', font: { size: 12 } }
      }
    },
    plugins: {
      legend: {
        display: radarDatasets.length > 1,
        labels: { color: '#e6edf3', usePointStyle: true, padding: 12, font: { size: 11 } }
      },
      tooltip: {
        callbacks: {
          label: ctx => (ctx.dataset.label || '') + ': ' + fmt(ctx.raw)
        }
      }
    }
  }
});

// ── Dimension Bars ────────────────────────────────────────
(function renderDims() {
  const el = document.getElementById('dims');

  if (MODE === 'compare') {
    DIMS.forEach(dim => {
      const group = document.createElement('div');
      group.className = 'dim-group';
      group.innerHTML = '<div class="dim-group-label">' + LABELS[dim] + '</div>';
      USERS.forEach((u, i) => {
        const val = u.vector.values[dim];
        const row = document.createElement('div');
        row.className = 'dim-row';
        row.innerHTML = '<span class="dim-user-label" style="color:' + USER_COLORS[i] + '">' + escHtml(u.user_id) + '</span>'
          + '<div class="dim-bar-wrap"><div class="dim-bar-bg"></div>'
          + '<div class="dim-bar" style="width:' + (val*100) + '%;background:' + USER_COLORS[i] + '"></div></div>'
          + '<span class="dim-value">' + fmt(val) + '</span>';
        group.appendChild(row);
      });
      el.appendChild(group);
    });
    return;
  }

  // Single mode: delta from last session
  const prevEma = emaHistory.length >= 2 ? emaHistory[emaHistory.length - 2] : null;
  DIMS.forEach(dim => {
    const val = vector.values[dim];
    const s = stats[dim];
    const prev = prevEma ? prevEma[dim] : 0.5;
    const delta = val - prev;
    const cls = delta > 0.03 ? 'up' : delta < -0.03 ? 'down' : 'neutral';
    const sign = delta > 0 ? '+' : '';

    const row = document.createElement('div');
    row.className = 'dim-row';
    row.innerHTML = '<span class="dim-label">' + LABELS[dim] + '</span>'
      + '<div class="dim-bar-wrap"><div class="dim-bar-bg"></div>'
      + '<div class="dim-range" style="left:' + (s.min*100) + '%;width:' + ((s.max-s.min)*100) + '%;background:' + COLORS[dim] + '15"></div>'
      + '<div class="dim-bar" style="width:' + (val*100) + '%;background:' + COLORS[dim] + '"></div></div>'
      + '<span class="dim-value">' + fmt(val) + '</span>'
      + '<span class="dim-delta ' + cls + '">' + sign + fmt(delta) + '</span>';
    el.appendChild(row);
  });
})();

// ── Memory Layers ─────────────────────────────────────────
(function renderLayers() {
  const allUsers = MODE === 'compare' ? USERS.filter(u => u.layers && Object.keys(u.layers).length > 0) :
    (Object.keys(layers).length > 0 ? [user] : []);

  if (allUsers.length === 0) {
    document.getElementById('layerContent').innerHTML = '<p class="layer-empty">No layers generated yet. Run sleep-time condensation after 5+ sessions.</p>';
    document.getElementById('layerTabs').style.display = 'none';
    return;
  }

  let currentUser = allUsers[0];
  let currentLayer = 'base_tone';

  const LAYER_LABELS = { base_tone: 'Base Tone', patterns: 'Patterns', anchors: 'Anchors' };
  const LAYER_DESC = {
    base_tone: 'How the AI understands who you are',
    patterns: 'Learned response patterns',
    anchors: 'Key moments in the relationship'
  };

  // User tabs (compare mode)
  if (MODE === 'compare' && allUsers.length > 1) {
    const userTabs = document.getElementById('layerUserTabs');
    userTabs.style.display = 'flex';
    allUsers.forEach((u, i) => {
      const btn = document.createElement('button');
      btn.className = 'user-tab' + (i === 0 ? ' active' : '');
      btn.textContent = u.user_id;
      btn.addEventListener('click', () => {
        userTabs.querySelectorAll('.user-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentUser = u;
        render();
      });
      userTabs.appendChild(btn);
    });
  }

  // Layer type tabs
  const tabContainer = document.getElementById('layerTabs');
  ['base_tone', 'patterns', 'anchors'].forEach((name, i) => {
    const btn = document.createElement('button');
    btn.className = 'toggle-btn' + (i === 0 ? ' active' : '');
    btn.textContent = LAYER_LABELS[name];
    btn.addEventListener('click', () => {
      tabContainer.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentLayer = name;
      render();
    });
    tabContainer.appendChild(btn);
  });

  function render() {
    const el = document.getElementById('layerContent');
    const content = currentUser.layers?.[currentLayer];

    if (!content) {
      el.innerHTML = '<p class="layer-empty">No ' + LAYER_LABELS[currentLayer].toLowerCase() + ' generated yet.</p>';
      return;
    }

    let html = '<p class="layer-desc">' + LAYER_DESC[currentLayer] + '</p>';

    if (currentLayer === 'patterns') {
      const lines = content.split('\n').filter(l => l.trim());
      lines.forEach(line => {
        const parts = line.split(' \u2192 ');
        if (parts.length >= 2) {
          html += '<div class="pattern-item">'
            + '<span class="pattern-trigger">' + escHtml(parts[0].trim()) + '</span>'
            + '<span class="pattern-arrow">\u2192</span>'
            + '<span class="pattern-action">' + escHtml(parts.slice(1).join(' \u2192 ').trim()) + '</span>'
            + '</div>';
        } else {
          html += '<div class="pattern-item"><span class="pattern-action">' + escHtml(line.trim()) + '</span></div>';
        }
      });
    } else if (currentLayer === 'anchors') {
      const lines = content.split('\n').filter(l => l.trim());
      lines.forEach(line => {
        const tsMatch = line.match(/\((\d{4}-\d{2}-\d{2}[T\d:-]*)\)/);
        const dashParts = line.split(' \u2014 ');
        let title = dashParts[0].trim();
        const desc = dashParts.length > 1 ? dashParts.slice(1).join(' \u2014 ').trim() : '';
        const time = tsMatch ? tsMatch[1].substring(0, 10) : '';
        if (tsMatch) title = title.replace(/\s*\([^)]+\)\s*/, ' ').trim();

        html += '<div class="anchor-item">'
          + '<span class="anchor-title">' + escHtml(title) + '</span>'
          + (time ? '<span class="anchor-time">' + time + '</span>' : '')
          + (desc ? '<span class="anchor-desc">' + escHtml(desc) + '</span>' : '')
          + '</div>';
      });
    } else {
      html += '<div class="layer-text">' + escHtml(content) + '</div>';
    }

    el.innerHTML = html;
  }

  render();
})();

// ── Timeline Chart (single mode) ──────────────────────────
if (MODE === 'single') {
  const sessionLabels = signalLog.map((_, i) => 'S' + (i + 1));

  function makeRawDatasets() {
    return DIMS.map(dim => ({
      label: LABELS[dim],
      data: signalLog.map(e => e.signals?.[dim]?.value ?? null),
      borderColor: COLORS[dim],
      backgroundColor: COLORS[dim] + '33',
      tension: 0.3,
      pointRadius: signalLog.map(e => hasCorrections(e) ? 8 : 5),
      pointStyle: signalLog.map(e => hasCorrections(e) ? 'triangle' : 'circle'),
      pointHoverRadius: 8,
      borderWidth: 2,
      _dimKey: dim,
      _type: 'raw',
    }));
  }

  function makeEmaDatasets() {
    return DIMS.map(dim => ({
      label: LABELS[dim] + ' (EMA)',
      data: emaHistory.map(h => h[dim]),
      borderColor: COLORS[dim],
      backgroundColor: 'transparent',
      tension: 0.4,
      pointRadius: 3,
      pointHoverRadius: 6,
      borderWidth: 2,
      borderDash: [6, 3],
      _dimKey: dim,
      _type: 'ema',
    }));
  }

  const timelineChart = new Chart(document.getElementById('timeline'), {
    type: 'line',
    data: { labels: sessionLabels, datasets: makeRawDatasets() },
    options: {
      responsive: true,
      interaction: { mode: 'nearest', intersect: true },
      scales: {
        y: {
          min: 0, max: 1,
          ticks: { stepSize: 0.2, color: '#8b949e', font: { size: 11 } },
          grid: { color: '#21262d' }
        },
        x: {
          ticks: { color: '#8b949e', font: { size: 11 } },
          grid: { color: '#21262d' }
        }
      },
      plugins: {
        legend: {
          labels: { color: '#e6edf3', usePointStyle: true, pointStyle: 'circle', padding: 16, font: { size: 11 } }
        },
        tooltip: {
          backgroundColor: '#1c2128',
          titleColor: '#e6edf3',
          bodyColor: '#8b949e',
          borderColor: '#30363d',
          borderWidth: 1,
          padding: 12,
          bodyFont: { size: 12 },
          callbacks: {
            title: ctx => {
              const i = ctx[0].dataIndex;
              let t = 'Session ' + (i + 1) + ' \u2014 ' + fmtDate(signalLog[i]?.timestamp);
              if (hasCorrections(signalLog[i])) t += ' \u26a0 correction';
              return t;
            },
            afterBody: ctx => {
              const i = ctx[0].dataIndex;
              const dim = ctx[0].dataset._dimKey;
              if (!dim) return '';
              const type = ctx[0].dataset._type;
              if (type === 'ema') return '\nEMA value after ' + (i + 1) + ' sessions';
              const ev = signalLog[i]?.signals?.[dim]?.signal;
              if (!ev) return '';
              const short = ev.length > 120 ? ev.slice(0, 117) + '...' : ev;
              return '\n' + short;
            }
          }
        }
      }
    }
  });

  // Toggle buttons
  document.querySelectorAll('[data-mode]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-mode]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.mode;
      if (mode === 'raw') timelineChart.data.datasets = makeRawDatasets();
      else if (mode === 'ema') timelineChart.data.datasets = makeEmaDatasets();
      else timelineChart.data.datasets = [...makeRawDatasets(), ...makeEmaDatasets()];
      timelineChart.update();
    });
  });

  // ── Session Details ───────────────────────────────────────
  (function renderSessions() {
    const el = document.getElementById('sessions');
    if (!signalLog.length) { el.innerHTML = '<p style="color:var(--muted)">No sessions recorded yet.</p>'; return; }

    signalLog.forEach((entry, i) => {
      const card = document.createElement('div');
      card.className = 'session-card';

      const corrected = hasCorrections(entry);
      const dots = DIMS.map(d => {
        const v = entry.signals?.[d]?.value ?? 0.5;
        return '<span class="dot" style="background:' + COLORS[d] + ';opacity:' + (0.3 + v * 0.7) + '" title="' + LABELS[d] + ': ' + fmt(v) + '"></span>';
      }).join('');

      const hdr = document.createElement('div');
      hdr.className = 'session-hdr';
      hdr.innerHTML = '<span><strong>Session ' + (i + 1) + '</strong> &nbsp; ' + fmtDate(entry.timestamp)
        + (corrected ? '<span class="correction-badge">\u26a0 correction</span>' : '')
        + '</span>'
        + '<span style="display:flex;align-items:center;gap:.75rem">'
        + '<span class="session-dots">' + dots + '</span>'
        + '<span class="arrow">&#9654;</span></span>';

      const body = document.createElement('div');
      body.className = 'session-body';

      // Show corrections first if present
      if (corrected) {
        const corrs = entry.signals._explicit_corrections;
        const corrDiv = document.createElement('div');
        corrDiv.className = 'evidence';
        let corrHtml = '<div class="evidence-dim" style="color:#fbbf24">Explicit Corrections</div>';
        corrs.forEach(c => {
          corrHtml += '<div class="evidence-text" style="margin-bottom:.25rem">'
            + '<strong>' + escHtml(c.dimension || '') + '</strong>: ' + escHtml(c.description || c.signal || '') + '</div>';
        });
        corrDiv.innerHTML = corrHtml;
        body.appendChild(corrDiv);
      }

      DIMS.forEach(dim => {
        const sig = entry.signals?.[dim];
        if (!sig) return;
        const ev = document.createElement('div');
        ev.className = 'evidence';
        ev.innerHTML = '<div class="evidence-dim" style="color:' + COLORS[dim] + '">'
          + LABELS[dim] + ' <span class="evidence-val">' + fmt(sig.value) + '</span></div>'
          + '<div class="evidence-text">' + escHtml(sig.signal || '\u2014') + '</div>';
        body.appendChild(ev);
      });

      hdr.addEventListener('click', () => {
        body.classList.toggle('open');
        hdr.querySelector('.arrow').classList.toggle('open');
      });

      card.appendChild(hdr);
      card.appendChild(body);
      el.appendChild(card);
    });
  })();

} else {
  // Compare mode: hide timeline and sessions
  document.getElementById('timelineCard').style.display = 'none';
  document.getElementById('sessionsCard').style.display = 'none';
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
