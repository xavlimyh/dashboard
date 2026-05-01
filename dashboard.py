import os
import json
import pandas as pd
import numpy as np
from datetime import date, datetime
import streamlit as st
import streamlit.components.v1 as components
from data import load_all_data, MYDICT

# ── Config ──────────────────────────────────────────────────────────────────
TODAY = date.today()
CHART_START_DATE = "2025-01-01"

# ── Data (cached) ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_data():
    return load_all_data()

combined_df = get_data()

pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.float_format", "{:,.2f}".format)


# ── Ticker rows builder ───────────────────────────────────────────────────────
def build_ticker_rows(df: pd.DataFrame) -> str:

    # ── Derived series ─────────────────────────────────────────────────────
    df = df.copy()
    df["2Y10Y"] = df["DGS10"] - df["DGS2"]
    df["CPI_YOY"] = df["CPIAUCSL"].dropna().pct_change(12) * 100
    df["PCE_YOY"] = df["PCEPI"].dropna().pct_change(12) * 100
    df["NFP_MOM"] = df["PAYEMS"].dropna().diff(1)

    LOOKBACK = 1260

    tickers = [
        # (sym, name, col, fmt, section, prev_offset, direction)
        ("GDP",       "Real GDP QoQ",           "A191RL1Q225SBEA",  "pct",        "Macro",       1, 1 ),
        ("CPI",       "US CPI YoY",             "CPI_YOY",          "pct",        "Macro",       1, -1),
        ("PCE",       "US PCE YoY",             "PCE_YOY",          "pct",        "Macro",       1, -1),
        ("UNRATE",    "Unemployment",           "UNRATE",           "pct",        "Macro",       1, -1),
        ("NFP",       "Non-farm Payrolls",      "NFP_MOM",          "kppl",       "Macro",       1, 1 ),
        ("FFR",       "Fed Funds Rate",         "DFEDTARU",         "pct",        "Rates",       1, 1 ),
        ("SOFR",      "SOFR",                   "SOFR",             "pct",        "Rates",       5, 1 ),
        ("YLDCURVE",  "Yield Curve",            "__YIELDCURVE__",   "yc",         "Rates",       0, 1 ),
        ("DGS2",      "US 2Y Treasury",         "DGS2",             "pct",        "Rates",       5, 1 ),
        ("DGS10",     "US 10Y Treasury",        "DGS10",            "pct",        "Rates",       5, 1 ),
        ("2Y10Y",     "2Y10Y Spread",           "2Y10Y",            "pct",        "Rates",       5, 1 ),
        ("SPX",       "S&P 500",                "^GSPC",            "idx",        "Equities",    5, 1 ),
        ("^IXIC",     "NASDAQ Composite",       "^IXIC",            "idx",        "Equities",    5, 1 ),
        ("^N225",     "Nikkei 225",             "^N225",            "idx",        "Equities",    5, 1 ),
        ("FTSE",      "FTSE 100",               "^FTSE",            "idx",        "Equities",    5, 1 ),
        ("VIX",       "CBOE Volatility Index",  "^VIX",             "idx_twodp",  "Equities",    5, 1 ),
        ("EURUSD=X",  "EUR/USD",                "EURUSD=X",         "idx_twodp",  "FX",          5, 1 ),
        ("GBPUSD=X",  "GBP/USD",                "GBPUSD=X",         "idx_twodp",  "FX",          5, 1 ),
        ("USDJPY=X",  "USD/JPY",                "USDJPY=X",         "idx_twodp",  "FX",          5, 1 ),
        ("GC=F",      "CME Gold Futures",       "GC=F",             "idx",        "Commodities", 5, 1 ),
        ("SI=F",      "CME Silver Futures",     "SI=F",             "idx_twodp",  "Commodities", 5, 1 ),
        ("BZ=F",      "Brent Crude Oil",        "BZ=F",             "idx_twodp",  "Commodities", 5, 1 ),
        ("CL=F",      "WTI Crude Oil",          "CL=F",             "idx_twodp",  "Commodities", 5, 1 )

    ]

    YC_LABELS = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
    YC_COLS   = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]

    rows = []
    for sym, name, col, fmt, section, prev_offset, direction in tickers:

        # ── Yield curve snapshot ──────────────────────────────────────────
        if col == "__YIELDCURVE__":
            yc_vals, yc_date = [], None
            for yc_col in YC_COLS:
                if yc_col in df.columns:
                    s = df[yc_col].dropna()
                    if len(s):
                        yc_vals.append(round(float(s.iloc[-1]), 4))
                        if yc_date is None:
                            yc_date = s.index[-1].strftime("%d %b %y")
                    else:
                        yc_vals.append(None)
                else:
                    yc_vals.append(None)
            rows.append({
                "type": "yieldcurve",
                "sym": "YLDCURVE",
                "name": "Yield Curve",
                "section": section,
                "maturities": YC_LABELS,
                "vals": yc_vals,
                "latestDate": yc_date or "",
            })
            continue

        # ── Regular series ────────────────────────────────────────────────
        if col not in df.columns:
            continue
        series = df[col].dropna().tail(LOOKBACK)
        if len(series) < 2:
            continue

        vals          = [round(v, 4) for v in series.tolist()]
        dates_iso     = [d.strftime("%Y-%m-%d") for d in series.index]
        dates_display = [d.strftime("%d %b %y")  for d in series.index]
        latest        = vals[-1]
        latest_date   = dates_display[-1]
        prev_idx      = max(0, len(vals) - 1 - prev_offset)
        prev_val      = vals[prev_idx]
        prev_date     = dates_display[prev_idx]
        chg_abs       = round(latest - prev_val, 4)
        chg_pct       = round((chg_abs / prev_val * 100), 2) if prev_val else 0

        rows.append({
            "type": "series",
            "sym": sym, "name": name, "fmt": fmt, "section": section,
            "vals": vals, "dates": dates_iso,
            "latest": latest, "latestDate": latest_date,
            "prevVal": prev_val, "prevDate": prev_date,
            "chgAbs": chg_abs, "chgPct": chg_pct, "dir": direction,
        })

    data_json = json.dumps(rows)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    background: #0e1117; color: #e0e0e0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px; overflow: visible; height: auto;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ border-bottom: 1px solid #2a2d35; }}
  th {{
    padding: 7px 14px; font-size: 10px; font-weight: 500;
    color: #6b7280; text-transform: uppercase; letter-spacing: 0.06em; white-space: nowrap;
  }}
  th.r {{ text-align: right; }}
  tr.section-row td {{
    padding: 14px 6px; font-size: 12px; font-weight: 700; color: #e5e7eb;
    text-transform: uppercase; letter-spacing: 0.08em; background: #1f2937;
  }}
  tr.ticker-row {{
    border-bottom: 1px solid #1a1d24; cursor: pointer; transition: background 0.1s;
  }}
  tr.ticker-row:hover {{ background: #161921; }}
  tr.ticker-row.active {{ background: #161921; }}
  td {{ padding: 9px 14px; vertical-align: middle; white-space: nowrap; }}
  td.r {{ text-align: right; }}
  .sym  {{ font-weight: 600; font-size: 13px; color: #f0f0f0; }}
  .val  {{ font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; color: #f0f0f0; }}
  .dt   {{ font-size: 11px; color: #6b7280; }}
  .prev {{ font-size: 12px; color: #9ca3af; display: block; font-variant-numeric: tabular-nums; }}
  .pos  {{ color: #22c55e; font-size: 12px; font-variant-numeric: tabular-nums; }}
  .neg  {{ color: #ef4444; font-size: 12px; font-variant-numeric: tabular-nums; }}
  .neu  {{ color: #6b7280; font-size: 12px; }}
  .spark-wrap {{ width: 120px; height: 36px; margin-left: auto; position: relative; }}
  tr.expand-row {{ display: none; }}
  tr.expand-row.open {{ display: table-row; }}
  .expand-inner {{
    padding: 14px 14px 18px; background: #12151c; border-bottom: 1px solid #2a2d35;
  }}
  .expand-header {{
    display: flex; align-items: center; justify-content: flex-end; margin-bottom: 10px;
  }}
  .expand-hint {{ font-size: 11px; color: #4b5563; }}
  .full-wrap {{ position: relative; width: 100%; height: 180px; }}
  .controls {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 14px 10px; border-bottom: 1px solid #2a2d35;
  }}
  .ctrl-group {{ display: flex; align-items: center; gap: 8px; }}
  .ctrl-label {{ font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }}
  input[type="date"] {{
    background: #1a1d24; color: #e0e0e0; border: 1px solid #2a2d35;
    border-radius: 5px; padding: 3px 7px; font-size: 12px; outline: none; cursor: pointer;
  }}
  input[type="date"]:hover {{ border-color: #4b5563; }}
  input[type="date"]:focus {{ border-color: #636efa; }}
  .btn {{
    background: #1a1d24; color: #c0c0c0; border: 1px solid #2a2d35;
    border-radius: 5px; padding: 3px 10px; font-size: 12px; cursor: pointer;
    transition: background 0.1s, border-color 0.1s;
  }}
  .btn:hover {{ background: #23272f; border-color: #4b5563; color: #e0e0e0; }}
  .btn:active {{ background: #2a2d35; }}
</style>
</head>
<body>

<div class="controls">
  <div class="ctrl-group">
    <span class="ctrl-label">From</span>
    <input type="date" id="global-date" value="{CHART_START_DATE}">
    <button class="btn" onclick="applyGlobalDate()">Apply to all charts</button>
  </div>
  <div class="ctrl-group">
    <button class="btn" onclick="expandAllRows()">Expand all</button>
    <button class="btn" onclick="closeAllRows()">Close all</button>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th style="width:140px">Name</th>
      <th class="r" style="width:100px">Value</th>
      <th class="r" style="width:90px">Date</th>
      <th class="r" style="width:130px">Prev / Change</th>
      <th class="r" style="width:134px">Trend</th>
    </tr>
  </thead>
  <tbody id="tb"></tbody>
</table>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const ROWS = {data_json};
const GLOBAL_DEFAULT = '{CHART_START_DATE}';

function fmtVal(v, fmt) {{
  if (fmt === 'pct')  return v.toFixed(2) + '%';
  if (fmt === 'idx')  return Math.round(v).toLocaleString('en-US');
  if (fmt === 'idxtwodp') return v.toFixed(2);
  if (fmt === 'kppl') return (v >= 0 ? '+' : '') + Math.round(v).toLocaleString('en-US') + 'K';
  return v.toFixed(2);
}}

function fmtChg(abs, pct, fmt) {{
  const sign = abs >= 0 ? '+' : '';
  if (fmt === 'pct')  return sign + abs.toFixed(2) + '%';
  if (fmt === 'idx')  return sign + Math.round(abs).toLocaleString('en-US') + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)';
  if (fmt === 'idxtwodp') return sign + Math.round(abs).toLocaleString('en-US') + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)';
  if (fmt === 'kppl') return sign + Math.round(abs).toLocaleString('en-US') + 'K';
  return sign + abs.toFixed(2) + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)';
}}

function fmtLabel(iso) {{
  const [y, m, d] = iso.split('-');
  const mon = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${{d}} ${{mon[parseInt(m,10)-1]}} ${{y.slice(2)}}`;
}}

function filterByDate(r, startDate) {{
  const labels = [], vals = [];
  for (let i = 0; i < r.dates.length; i++) {{
    if (r.dates[i] >= startDate) {{ labels.push(fmtLabel(r.dates[i])); vals.push(r.vals[i]); }}
  }}
  return {{ labels, vals }};
}}

const sparkCharts = {{}};
const fullCharts  = {{}};
const chartDates  = {{}};

/* ── Build table ── */
const tb = document.getElementById('tb');
let lastSection = null;

ROWS.forEach(r => {{
  if (r.section !== lastSection) {{
    lastSection = r.section;
    const sr = document.createElement('tr');
    sr.className = 'section-row';
    sr.innerHTML = `<td colspan="5">${{r.section}}</td>`;
    tb.appendChild(sr);
  }}

  const sparkId = 'sp-' + r.sym;
  const fullId  = 'fl-' + r.sym;
  const expId   = 'ex-' + r.sym;

  /* ── Yield Curve row ── */
  if (r.type === 'yieldcurve') {{
    /* slope drives line colour: green = normal, red = inverted */
    const t10 = r.vals[7], t2 = r.vals[4];
    const slope = (t10 != null && t2 != null) ? t10 - t2 : null;
    const lineClr = (slope == null || slope >= 0) ? '#22c55e' : '#ef4444';

    const row = document.createElement('tr');
    row.className = 'ticker-row';
    row.innerHTML = `
      <td><div class="sym">${{r.name}}</div></td>
      <td class="r"></td>
      <td class="r"><span class="dt">${{r.latestDate}}</span></td>
      <td class="r"></td>
      <td class="r">
        <div class="spark-wrap">
          <canvas id="${{sparkId}}" role="img" aria-label="Yield curve sparkline"></canvas>
        </div>
      </td>`;

    const expRow = document.createElement('tr');
    expRow.className = 'expand-row';
    expRow.id = expId;
    expRow.innerHTML = `
      <td colspan="5" class="expand-inner">
        <div class="full-wrap">
          <canvas id="${{fullId}}" role="img" aria-label="Yield curve chart"></canvas>
        </div>
      </td>`;

    tb.appendChild(row);
    tb.appendChild(expRow);

    row.addEventListener('click', () => {{
      const isOpen = expRow.classList.contains('open');
      expRow.classList.toggle('open', !isOpen);
      row.classList.toggle('active', !isOpen);
      if (!isOpen && !fullCharts[r.sym]) {{
        setTimeout(() => buildYCFull(r, fullId, lineClr), 40);
      }}
      sendHeightSlow();
    }});

    setTimeout(() => buildYCSpark(r, sparkId, lineClr), 60);
    return;
  }}

  /* ── Regular series row ── */
  const signedChange = r.chgAbs * (r.dir || 1);
  const cls     = signedChange > 0 ? 'pos' : signedChange < 0 ? 'neg' : 'neu';
  const arrow   = r.chgAbs > 0 ? '▲ ' : r.chgAbs < 0 ? '▼ ' : '— ';
  const lineClr = signedChange >= 0 ? '#22c55e' : '#ef4444';

  const row = document.createElement('tr');
  row.className = 'ticker-row';
  row.innerHTML = `
    <td><div class="sym">${{r.name}}</div></td>
    <td class="r"><span class="val">${{fmtVal(r.latest, r.fmt)}}</span></td>
    <td class="r"><span class="dt">${{r.latestDate}}</span></td>
    <td class="r">
      <span class="prev">${{fmtVal(r.prevVal, r.fmt)}} <span style="font-size:10px;color:#4b5563">${{r.prevDate}}</span></span>
      <span class="${{cls}}">${{arrow}}${{fmtChg(r.chgAbs, r.chgPct, r.fmt)}}</span>
    </td>
    <td class="r">
      <div class="spark-wrap">
        <canvas id="${{sparkId}}" role="img" aria-label="Sparkline for ${{r.sym}}"></canvas>
      </div>
    </td>`;

  const expRow = document.createElement('tr');
  expRow.className = 'expand-row';
  expRow.id = expId;
  expRow.innerHTML = `
    <td colspan="5" class="expand-inner">
      <div class="expand-header">
        <div style="display:flex;align-items:center;gap:8px" onclick="event.stopPropagation()">
          <span class="expand-hint">From</span>
          <input type="date" id="date-${{r.sym}}" value="{CHART_START_DATE}"
            oninput="refreshChart('${{r.sym}}', this.value)">
        </div>
      </div>
      <div class="full-wrap">
        <canvas id="${{fullId}}" role="img" aria-label="Full chart for ${{r.sym}}"></canvas>
      </div>
    </td>`;

  tb.appendChild(row);
  tb.appendChild(expRow);

  row.addEventListener('click', () => {{
    const isOpen = expRow.classList.contains('open');
    expRow.classList.toggle('open', !isOpen);
    row.classList.toggle('active', !isOpen);
    if (!isOpen && !fullCharts[r.sym]) {{
      setTimeout(() => buildFull(r, fullId, lineClr), 40);
    }}
    sendHeightSlow();
  }});

  setTimeout(() => buildSpark(r, sparkId, lineClr), 60);
}});

/* ── Global controls ── */
function applyGlobalDate() {{
  const date = document.getElementById('global-date').value;
  if (!date) return;
  ROWS.forEach(r => {{
    if (r.type === 'yieldcurve') return;
    chartDates[r.sym] = date;
    const inp = document.getElementById('date-' + r.sym);
    if (inp) inp.value = date;
    if (fullCharts[r.sym]) refreshChart(r.sym, date);
    if (sparkCharts[r.sym]) refreshSpark(r.sym, date);
  }});
}}

function expandAllRows() {{
  document.querySelectorAll('.expand-row').forEach(expRow => {{
    if (expRow.classList.contains('open')) return;
    expRow.classList.add('open');
    expRow.previousElementSibling.classList.add('active');
    const sym = expRow.id.replace('ex-', '');
    const r = ROWS.find(x => x.sym === sym);
    if (!r) return;
    if (r.type === 'yieldcurve') {{
      if (!fullCharts[sym]) {{
        const t10 = r.vals[7], t2 = r.vals[4];
        const slope = (t10 != null && t2 != null) ? t10 - t2 : null;
        const lineClr = (slope == null || slope >= 0) ? '#22c55e' : '#ef4444';
        setTimeout(() => buildYCFull(r, 'fl-' + sym, lineClr), 40);
      }}
    }} else {{
      if (!fullCharts[sym]) {{
        const lineClr = (r.chgAbs * (r.dir || 1)) >= 0 ? '#22c55e' : '#ef4444';
        setTimeout(() => buildFull(r, 'fl-' + sym, lineClr), 40);
      }}
    }}
  }});
  [200, 500, 900, 1500].forEach(t => setTimeout(sendHeight, t));
}}

function closeAllRows() {{
  document.querySelectorAll('.expand-row.open').forEach(expRow => {{
    expRow.classList.remove('open');
    expRow.previousElementSibling.classList.remove('active');
  }});
  sendHeightSlow();
  setTimeout(sendHeight, 150);
}}

new ResizeObserver(sendHeight).observe(document.body);
[100, 300, 600, 1200].forEach(t => setTimeout(sendHeight, t));

/* ── Yield curve chart builders ── */
function buildYCSpark(r, id, color) {{
  const ctx = document.getElementById(id);
  if (!ctx || sparkCharts[r.sym]) return;
  sparkCharts[r.sym] = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: r.maturities,
      datasets: [{{
        data: r.vals.map(v => v ?? 0),
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false, animation: false, events: [],
      plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }} }},
      scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
    }}
  }});
}}

function buildYCFull(r, id, color) {{
  const ctx = document.getElementById(id);
  if (!ctx || fullCharts[r.sym]) return;
  const fillColor = color === '#22c55e' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)';
  fullCharts[r.sym] = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: r.maturities,
      datasets: [{{
        data: r.vals.map(v => v ?? 0),
        borderColor: color,
        borderWidth: 1.5,
        pointRadius: 3,
        pointBackgroundColor: color,
        fill: true,
        backgroundColor: fillColor,
        tension: 0,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          mode: 'index', intersect: false,
          backgroundColor: '#1e2128', titleColor: '#9ca3af', bodyColor: '#f0f0f0',
          borderColor: '#2a2d35', borderWidth: 1,
          callbacks: {{
            title: items => r.maturities[items[0].dataIndex] + ' Treasury',
            label: c => '  ' + c.parsed.y.toFixed(2) + '%',
          }}
        }}
      }},
      scales: {{
        x: {{
          grid: {{ color: 'rgba(255,255,255,0.05)' }},
          ticks: {{ color: '#4b5563', font: {{ size: 11 }} }}
        }},
        y: {{
          position: 'right',
          grid: {{ color: 'rgba(255,255,255,0.05)' }},
          ticks: {{ color: '#4b5563', callback: v => v.toFixed(2) + '%' }}
        }}
      }}
    }}
  }});
}}

/* ── Regular series chart builders ── */
function buildSpark(r, id, color) {{
  const ctx = document.getElementById(id);
  if (!ctx || sparkCharts[r.sym]) return;
  const perRowInput = document.getElementById('date-' + r.sym);
  const startDate = chartDates[r.sym]
                    || (perRowInput && perRowInput.value)
                    || document.getElementById('global-date').value
                    || GLOBAL_DEFAULT;
  if (perRowInput && !perRowInput.value) perRowInput.value = startDate;
  const {{ labels, vals }} = filterByDate(r, startDate);
  sparkCharts[r.sym] = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{ data: vals, borderColor: color, borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false, animation: false, events: [],
      plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }} }},
      scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
    }}
  }});
}}

function buildFull(r, id, color) {{
  const ctx = document.getElementById(id);
  if (!ctx || fullCharts[r.sym]) return;
  const perRowInput = document.getElementById('date-' + r.sym);
  const startDate = chartDates[r.sym]
                    || (perRowInput && perRowInput.value)
                    || document.getElementById('global-date').value
                    || GLOBAL_DEFAULT;
  if (perRowInput && !perRowInput.value) perRowInput.value = startDate;
  const {{ labels, vals }} = filterByDate(r, startDate);
  const fillColor = color === '#22c55e' ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)';

  function tickFmt(v) {{
    if (r.fmt === 'pct')  return v.toFixed(2) + '%';
    if (r.fmt === 'idx')  return Math.round(v).toLocaleString('en-US');
    if (r.fmt === 'kppl') return Math.round(v / 1000) + 'k';
    return v.toFixed(2);
  }}

  fullCharts[r.sym] = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{ data: vals, borderColor: color, borderWidth: 1.5, pointRadius: 0, fill: true, backgroundColor: fillColor, tension: 0 }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          mode: 'index', intersect: false,
          backgroundColor: '#1e2128', titleColor: '#9ca3af', bodyColor: '#f0f0f0',
          borderColor: '#2a2d35', borderWidth: 1,
          callbacks: {{ label: c => ' ' + fmtVal(c.parsed.y, r.fmt) }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#4b5563', maxTicksLimit: 8, maxRotation: 0 }} }},
        y: {{ position: 'right', grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#4b5563', callback: tickFmt }} }}
      }}
    }}
  }});
}}

function refreshSpark(sym, startDate) {{
  if (!startDate) return;
  const chart = sparkCharts[sym];
  const r = ROWS.find(x => x.sym === sym);
  if (!chart || !r || r.type === 'yieldcurve') return;
  const {{ labels, vals }} = filterByDate(r, startDate);
  if (!vals.length) return;
  chart.data.labels = labels;
  chart.data.datasets[0].data = vals;
  chart.update();
}}

function refreshChart(sym, startDate) {{
  if (!startDate) return;
  chartDates[sym] = startDate;
  const chart = fullCharts[sym];
  const r = ROWS.find(x => x.sym === sym);
  if (!chart || !r || r.type === 'yieldcurve') return;
  const {{ labels, vals }} = filterByDate(r, startDate);
  chart.data.labels = labels;
  chart.data.datasets[0].data = vals;
  chart.update();
  refreshSpark(sym, startDate);
}}

</script>
</body>
</html>
"""
    return html


# ── Streamlit layout ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Macro Dashboard", layout="wide", page_icon="📊")

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 2160px !important; }
</style>
""", unsafe_allow_html=True)

st.title("Macro Dashboard")
st.markdown("""
<style>
h1 {
    font-size: 42px !important;
    font-weight: 700 !important;
    font-family: "Inter", sans-serif;
    color: #f0f0f0;
}
</style>
""", unsafe_allow_html=True)
st.markdown(
    f"<div style='color:#888;font-family:Segoe UI;font-size:0.82rem;margin-bottom:1.5rem'>"
    f"Last updated: {datetime.now().strftime('%d %b %Y %H:%M')}</div>",
    unsafe_allow_html=True,
)

ticker_html = build_ticker_rows(combined_df)

N_ROWS     = 12
N_SECTIONS = 3
ROW_H      = 58
SEC_H      = 44
HEADER_H   = 44
BUFFER     = 3000
table_height = HEADER_H + N_ROWS * ROW_H + N_SECTIONS * SEC_H + BUFFER

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(ticker_html)

components.html(ticker_html, height=table_height, scrolling=False)

# python -m streamlit run C:\Users\xavie\NUS\Coding\Dashboard\dashboard.py --server.runOnSave true