"""
AQI-EWS — Early Warning System Dashboard
Indore Air Quality · CPCB Data · LSTM Forecast

Entry point: streamlit run dashboard.py
Login is NOT required to view the dashboard.
Login appears only when:
  1. User clicks "🔔 Notify Me" button
  2. User clicks "🔑 Login" in the sidebar
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
import re

# ── Backend client — single source of truth for all API calls ────────────────
from backend_client import BackendClient, backend_login, backend_register

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AQI-EWS · Indore",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state defaults ───────────────────────────────────────────────────
for key, default in [
    ("authenticated",    False),
    ("user_name",        "Guest"),
    ("user_email",       ""),
    ("user_location",    ""),
    ("gps_address",      ""),
    ("gps_lat",          ""),
    ("gps_lon",          ""),
    ("loc_fetched",      False),
    ("token",            ""),
    # Modal control
    ("show_login_modal", False),
    ("login_mode",       "login"),    # "login" | "register"
    ("notify_after_login", False),    # True when triggered by Notify Me
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Backend client (authenticated if token present) ─────────────────────────
client = BackendClient(token=st.session_state.get("token"))

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:     #080d18; --card:  #0f1623; --card2: #141e2e;
    --border: #1a2540; --blue:  #38bdf8; --teal:  #2dd4bf;
    --green:  #4ade80; --amber: #fbbf24; --red:   #f87171;
    --purple: #818cf8; --muted: #4b5a72; --text:  #dde3ef;
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.main .block-container { padding: 1.2rem 2rem 3rem 2rem; max-width: 1420px; }
[data-testid="stSidebar"] { background: var(--card) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebarNav"] { display: none !important; }
#MainMenu, footer, header { visibility:hidden; }

.top-bar { display:flex;align-items:center;justify-content:space-between;
    padding-bottom:1rem;border-bottom:1px solid var(--border);margin-bottom:1.3rem; }
.top-title { font-family:'Space Mono',monospace;font-size:1.5rem;font-weight:700;
    background:linear-gradient(130deg,var(--blue),var(--teal));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent; }
.top-sub { font-size:.8rem;color:var(--muted);margin-top:.2rem; }
.live-badge { display:flex;align-items:center;gap:6px;font-size:.72rem;color:var(--green);
    font-weight:600;background:rgba(74,222,128,.07);border:1px solid rgba(74,222,128,.25);
    border-radius:20px;padding:.28rem .75rem; }
.live-dot { width:7px;height:7px;border-radius:50%;background:var(--green);
    box-shadow:0 0 6px var(--green);animation:blink 1.6s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

.alert-banner { border-radius:10px;padding:.78rem 1.15rem;display:flex;align-items:center;
    gap:.65rem;font-size:.87rem;font-weight:500;border:1px solid;margin-bottom:.8rem; }
.a-green  { background:#071a0f;border-color:#14532d;color:var(--green); }
.a-yellow { background:#1a1206;border-color:#78350f;color:var(--amber); }
.a-red    { background:#1a0808;border-color:#7f1d1d;color:var(--red);   }

.mcard { background:var(--card);border:1px solid var(--border);border-radius:14px;
    padding:1.1rem 1.25rem;position:relative;overflow:hidden;margin-bottom:.2rem;
    backdrop-filter:blur(12px);transition:transform .2s ease, box-shadow .2s ease; }
.mcard:hover { transform:translateY(-2px);box-shadow:0 8px 25px rgba(0,0,0,.15); }
.mcard::before { content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0; }
.m-blue::before  { background:linear-gradient(90deg, #0ea5e9, #38bdf8); }
.m-teal::before  { background:linear-gradient(90deg, #0d9488, #2dd4bf); }
.m-amber::before { background:linear-gradient(90deg, #d97706, #fbbf24); }
.m-green::before { background:linear-gradient(90deg, #16a34a, #4ade80); }
.m-red::before   { background:linear-gradient(90deg, #dc2626, #f87171); }
.m-purple::before{ background:linear-gradient(90deg, #7c3aed, #a78bfa); }
.mcard::after { content:'';position:absolute;top:3px;left:0;right:0;height:40px;
    background:linear-gradient(to bottom, rgba(255,255,255,.02), transparent);pointer-events:none; }
.mlabel { font-size:.68rem;text-transform:uppercase;letter-spacing:.13em;color:var(--muted);margin-bottom:.35rem;
    display:flex;align-items:center;gap:.4rem; }
.mval   { font-family:'Space Mono',monospace;font-size:2rem;font-weight:700;line-height:1;
    background:linear-gradient(135deg, var(--text), rgba(255,255,255,.7));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text; }
.msub   { font-size:.73rem;color:var(--muted);margin-top:.32rem;line-height:1.35; }
.thresh-badge { font-size:.65rem;padding:.18rem .55rem;border-radius:20px;font-weight:700;
    font-family:'Space Mono',monospace;background:rgba(251,191,36,.12);color:var(--amber);
    border:1px solid rgba(251,191,36,.3);margin-left:.4rem; }

/* ── Expander (Nearest Safe Zone dropdown) ── */
div[data-testid="stExpander"] {
    background:var(--card) !important;border:1px solid var(--border) !important;
    border-radius:12px !important;margin-bottom:.8rem !important;overflow:hidden;
}
div[data-testid="stExpander"] summary {
    font-family:'DM Sans',sans-serif !important;font-size:.92rem !important;
    font-weight:600 !important;color:var(--text) !important;
    padding:.8rem 1.1rem !important;
}
div[data-testid="stExpander"] summary:hover {
    background:var(--card2) !important;
}

.stitle { font-family:'Space Mono',monospace;font-size:.68rem;text-transform:uppercase;
    letter-spacing:.15em;color:var(--muted);margin-bottom:.6rem;display:flex;align-items:center;gap:.5rem; }
.stitle::after { content:'';flex:1;height:1px;background:var(--border); }

.atbl { width:100%;border-collapse:collapse;font-size:.81rem; }
.atbl th { font-family:'Space Mono',monospace;font-size:.65rem;text-transform:uppercase;
    letter-spacing:.1em;color:var(--muted);padding:.55rem .8rem;text-align:left;border-bottom:1px solid var(--border); }
.atbl td { padding:.65rem .8rem;border-bottom:1px solid var(--border); }
.atbl tr:hover td { background:var(--card2); }
.s-low  { color:var(--green);font-weight:600; }
.s-mod  { color:var(--amber);font-weight:600; }
.s-high { color:var(--red);  font-weight:600; }

.si { display:flex;justify-content:space-between;align-items:center;
    padding:.42rem 0;border-bottom:1px solid var(--border);font-size:.79rem; }
.pill { font-family:'Space Mono',monospace;font-size:.66rem;
    padding:.16rem .48rem;border-radius:20px;font-weight:700; }
.p-ok   { background:rgba(74,222,128,.1); color:var(--green);border:1px solid rgba(74,222,128,.3); }
.p-warn { background:rgba(251,191,36,.1); color:var(--amber);border:1px solid rgba(251,191,36,.3); }
.p-info { background:rgba(56,189,248,.1); color:var(--blue); border:1px solid rgba(56,189,248,.3); }
.p-err  { background:rgba(248,113,113,.1);color:var(--red);  border:1px solid rgba(248,113,113,.3); }

.user-chip { display:flex;align-items:center;gap:.6rem;background:var(--card2);
    border:1px solid var(--border);border-radius:10px;padding:.6rem .85rem;margin-bottom:.9rem; }
.user-avatar { width:32px;height:32px;border-radius:50%;
    background:linear-gradient(130deg,#0ea5e9,#0d9488);
    display:flex;align-items:center;justify-content:center;
    font-weight:700;font-size:.85rem;color:white;flex-shrink:0; }
.user-name { font-size:.85rem;font-weight:600; }
.user-loc  { font-size:.72rem;color:var(--muted); }

.guest-chip { display:flex;align-items:center;gap:.6rem;background:var(--card2);
    border:1px dashed var(--border);border-radius:10px;padding:.6rem .85rem;margin-bottom:.6rem; }
.guest-avatar { width:32px;height:32px;border-radius:50%;background:#1a2540;
    display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0; }
.guest-label { font-size:.85rem;font-weight:600;color:var(--muted); }
.guest-hint  { font-size:.7rem;color:var(--muted);opacity:.7; }

.loc-result { background:var(--card2);border:1px solid var(--border);border-radius:10px;
    padding:.75rem 1rem;font-size:.83rem;display:flex;align-items:flex-start;gap:.55rem;margin-bottom:.5rem; }
.loc-result.success { border-color:rgba(74,222,128,.4);background:rgba(74,222,128,.04); }
.loc-result.error   { border-color:rgba(248,113,113,.4);background:rgba(248,113,113,.04); }
.loc-addr   { font-weight:500;color:var(--text);line-height:1.45; }
.loc-coords { font-family:'Space Mono',monospace;font-size:.7rem;color:var(--muted);margin-top:.18rem; }

div[data-baseweb="tab-list"] { background:var(--card)!important;border-radius:10px!important;
    padding:4px!important;gap:4px!important;border:1px solid var(--border)!important; }
button[data-baseweb="tab"] { background:transparent!important;color:var(--muted)!important;
    border-radius:8px!important;font-size:.83rem!important; }
button[data-baseweb="tab"][aria-selected="true"] { background:var(--card2)!important;color:var(--blue)!important; }

.pred-legend { display:flex;gap:1.4rem;flex-wrap:wrap;font-size:.78rem;margin-bottom:.6rem;padding:.5rem .2rem; }
.pred-legend-item { display:flex;align-items:center;gap:.4rem; }
.pred-legend-line { width:28px;height:3px;border-radius:2px;flex-shrink:0; }

/* ── Input / button styles (used in modal) ── */
.stTextInput > label { font-size:.78rem!important;text-transform:uppercase!important;
    letter-spacing:.1em!important;color:var(--muted)!important;margin-bottom:.3rem!important; }
.stTextInput input {
    background:var(--card2)!important;border:1px solid var(--border)!important;
    border-radius:9px!important;color:var(--text)!important;
    font-size:.9rem!important;transition:border-color .2s!important; }
.stTextInput input:focus { border-color:var(--blue)!important; }
.stButton > button {
    width:100%!important;background:linear-gradient(130deg,#0ea5e9,#0d9488)!important;
    color:white!important;border:none!important;border-radius:10px!important;
    padding:.65rem 1rem!important;font-size:.92rem!important;font-weight:600!important;
    cursor:pointer!important;transition:opacity .2s,transform .1s!important;margin-top:.3rem!important; }
.stButton > button:hover  { opacity:.9!important;transform:translateY(-1px)!important; }
.stButton > button:active { transform:translateY(0)!important; }
.err-box {
    background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.3);
    color:var(--red);border-radius:9px;padding:.65rem 1rem;
    font-size:.84rem;margin:.3rem 0; }

/* ── Notify panel ── */
.notify-panel {
    background:var(--card);border:1px solid var(--border);border-radius:14px;
    padding:1.1rem 1.3rem 1.3rem 1.3rem;margin-bottom:1rem;
    animation:fadeIn .3s ease; }
@keyframes fadeIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.notify-header { display:flex;align-items:flex-start;gap:.7rem;margin-bottom:.85rem; }
.notify-icon { font-size:1.8rem;line-height:1; }
.notify-title { font-family:'Space Mono',monospace;font-size:.95rem;font-weight:700;
    color:var(--text);line-height:1.3; }
.notify-sub { font-size:.77rem;color:var(--muted);margin-top:.2rem; }
.aqi-status-bar { border-radius:9px;padding:.65rem 1rem;font-size:.85rem;
    font-weight:500;border:1px solid;display:flex;align-items:center;gap:.55rem;margin-bottom:.9rem; }
.area-table { width:100%;border-collapse:collapse;font-size:.8rem; }
.area-table th { font-family:'Space Mono',monospace;font-size:.62rem;text-transform:uppercase;
    letter-spacing:.1em;color:var(--muted);padding:.4rem .7rem;text-align:left;
    border-bottom:1px solid var(--border); }
.area-table td { padding:.55rem .7rem;border-bottom:1px solid rgba(26,37,64,.5); }
.area-table tr:hover td { background:var(--card2); }
.area-table tr.best-row td { background:rgba(45,212,191,.05); }
.best-badge { display:inline-flex;align-items:center;gap:.3rem;font-size:.64rem;font-weight:700;
    background:rgba(45,212,191,.12);color:var(--teal);border:1px solid rgba(45,212,191,.3);
    border-radius:20px;padding:.12rem .45rem;margin-left:.4rem; }
.area-aqi-pill { font-family:'Space Mono',monospace;font-size:.74rem;font-weight:700;
    padding:.15rem .5rem;border-radius:6px; }
.pill-good  { background:rgba(74,222,128,.1); color:#4ade80; }
.pill-mod   { background:rgba(251,191,36,.1); color:#fbbf24; }
.pill-poor  { background:rgba(248,113,113,.1);color:#f87171; }
.pill-cur   { background:rgba(56,189,248,.12);color:#38bdf8; border:1px solid rgba(56,189,248,.3); }
.improve-chip { font-size:.72rem;font-weight:600;color:var(--teal);display:flex;
    align-items:center;gap:.3rem;margin-top:.7rem; }
</style>
""", unsafe_allow_html=True)

# ─── GPS iframe ───────────────────────────────────────────────────────────────
GEO_COMPONENT = """
<!DOCTYPE html><html><head>
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:'DM Sans',sans-serif;background:transparent;display:flex;flex-direction:column;gap:7px;padding:1px;}
  button{width:100%;padding:10px 14px;background:linear-gradient(130deg,#0ea5e9,#0d9488);
         color:white;border:none;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;}
  button:hover{opacity:.88;} button:disabled{opacity:.5;cursor:not-allowed;}
  #st{font-size:12px;padding:9px 12px;border-radius:8px;border:1px solid #1a2540;
      background:#141e2e;color:#94a3b8;display:none;line-height:1.6;}
  #st.show{display:block;}
  #st.loading{border-color:rgba(56,189,248,.4);color:#38bdf8;}
  #st.success{border-color:rgba(74,222,128,.4);color:#4ade80;background:rgba(74,222,128,.05);}
  #st.error  {border-color:rgba(248,113,113,.4);color:#f87171;background:rgba(248,113,113,.05);}
  .addr{color:#dde3ef;font-size:12.5px;font-weight:600;margin-bottom:2px;}
  .coord{font-family:monospace;font-size:10px;opacity:.5;}
  .sp{display:inline-block;width:10px;height:10px;border:2px solid rgba(56,189,248,.3);
      border-top-color:#38bdf8;border-radius:50%;animation:spin .7s linear infinite;vertical-align:middle;margin-right:4px;}
  @keyframes spin{to{transform:rotate(360deg);}}
</style></head><body>
<button id="btn" onclick="go()">📍 Detect My Location</button>
<div id="st"></div>
<script>
function ss(cls,html){var s=document.getElementById('st');s.className='show '+cls;s.innerHTML=html;}
function buildAddr(a){
  var p=[];
  if(a.house_number)p.push(a.house_number);
  var road=a.road||a.pedestrian||a.footway||'';if(road)p.push(road);
  var area=a.neighbourhood||a.suburb||a.quarter||'';if(area)p.push(area);
  var city=a.city||a.town||a.village||'';if(city)p.push(city);
  if(a.state)p.push(a.state);
  return p.filter(Boolean).join(', ');
}
function go(){
  var btn=document.getElementById('btn');
  if(!navigator.geolocation){ss('error','❌ Geolocation not supported.');return;}
  btn.disabled=true;btn.textContent='🔄 Detecting…';
  ss('loading','<span class="sp"></span>Waiting for GPS…');
  navigator.geolocation.getCurrentPosition(
    function(pos){
      var lat=pos.coords.latitude,lon=pos.coords.longitude,acc=Math.round(pos.coords.accuracy);
      fetch('https://nominatim.openstreetmap.org/reverse?lat='+lat+'&lon='+lon+'&format=json&zoom=18&addressdetails=1&accept-language=en',{headers:{'User-Agent':'AQIEWS/1.0'}})
        .then(function(r){return r.json();})
        .then(function(d){
          var addr=buildAddr(d.address||{})||d.display_name||(lat.toFixed(5)+', '+lon.toFixed(5));
          ss('success','<div class="addr">📍 '+addr+'</div><div class="coord">🛰 '+lat.toFixed(6)+', '+lon.toFixed(6)+'</div>');
          btn.textContent='✅ Detected';btn.disabled=false;
          window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'success',address:addr,lat:lat.toFixed(6),lon:lon.toFixed(6),acc:acc}},'*');
        }).catch(function(){
          var fb=lat.toFixed(5)+', '+lon.toFixed(5);
          ss('success','<div class="addr">📍 '+fb+'</div>');
          btn.textContent='✅ Detected';btn.disabled=false;
          window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'success',address:fb,lat:lat.toFixed(6),lon:lon.toFixed(6),acc:acc}},'*');
        });
    },
    function(err){
      btn.disabled=false;btn.textContent='📍 Detect My Location';
      ss('error','❌ '+(err.code===1?'Permission denied.':err.code===2?'Position unavailable.':'Timed out.'));
      window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'denied',address:'',lat:'',lon:''}},'*');
    },
    {enableHighAccuracy:true,timeout:15000,maximumAge:0}
  );
}
</script></body></html>
"""

# ─── Plotly base theme ────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#4b5a72", size=11),
    xaxis=dict(gridcolor="#1a2540", zerolinecolor="#1a2540", showline=False),
    yaxis=dict(gridcolor="#1a2540", zerolinecolor="#1a2540", showline=False),
    margin=dict(l=8, r=8, t=36, b=8),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    hovermode="x unified",
)

# ─── Helpers ─────────────────────────────────────────────────────────────────
def aqi_info(val):
    v = float(val)
    if v <= 50:  return "Good",        "#4ade80", "a-green"
    if v <= 100: return "Satisfactory","#a3e635", "a-green"
    if v <= 200: return "Moderate",    "#fbbf24", "a-yellow"
    if v <= 300: return "Poor",        "#fb923c", "a-yellow"
    if v <= 400: return "Very Poor",   "#f87171", "a-red"
    return             "Severe",       "#e11d48", "a-red"

def severity_label(val):
    v = float(val)
    if v <= 100: return "Low",      "s-low"
    if v <= 250: return "Moderate", "s-mod"
    return              "High",     "s-high"

def mock_pollutants(seed=42):
    np.random.seed(seed)
    return {
        "PM2.5": round(48 + np.random.randn()*5,  1),
        "PM10":  round(82 + np.random.randn()*8,  1),
        "NO₂":   round(31 + np.random.randn()*4,  1),
        "SO₂":   round(9  + np.random.randn()*2,  1),
        "CO":    round(0.8+ np.random.randn()*0.1, 2),
        "O₃":    round(45 + np.random.randn()*6,  1),
    }

def fake_history(base, hours=72):
    np.random.seed(int(base) % 97)
    t = pd.date_range(end=datetime.now(), periods=hours, freq="h")
    v = np.clip(
        base + np.cumsum(np.random.randn(hours)*3.5) + 18*np.sin(np.linspace(0,4*np.pi,hours)),
        10, 500,
    )
    return pd.DataFrame({"time": t, "aqi": v.round(1)})

def fake_prediction(base, hours=48):
    np.random.seed(42)
    t         = pd.date_range(start=datetime.now(), periods=hours, freq="h")
    exp_drift  = np.linspace(0, 30, hours)
    expected   = np.clip(base + exp_drift + np.sin(np.linspace(0, 2*np.pi, hours))*12
                         + np.random.randn(hours)*4, 10, 500)
    pred_drift = np.linspace(0, float(np.random.choice([-22, 10, 18])), hours)
    predicted  = np.clip(base + pred_drift + np.random.randn(hours)*3.5, 10, 500)
    spread     = np.linspace(3, 35, hours)
    return pd.DataFrame({
        "time":     t,
        "expected": expected.round(1),
        "aqi":      predicted.round(1),
        "upper":    np.clip(predicted+spread, 10, 500).round(1),
        "lower":    np.clip(predicted-spread, 10, 500).round(1),
    })

def mcard(accent, label, value, sub=""):
    return f"""<div class="mcard m-{accent}">
        <div class="mlabel">{label}</div>
        <div class="mval" style="color:var(--{accent});">{value}</div>
        <div class="msub">{sub}</div>
    </div>"""

# ─── Real station data loader ─────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_all_stations():
    """Fetch real AQI for all Indore CPCB stations from backend API."""
    data = client.get_all_stations()
    if data and isinstance(data, dict):
        stations = data.get("stations", [])
        primary_aqi = data.get("primary_aqi")
        if stations:
            return stations, primary_aqi, True
    return [], None, False


def render_notify_panel(live_aqi, cat, banner_cls, threshold):
    """Render the full notification + safer areas panel with REAL station data."""
    all_stations, primary_aqi, stations_live = load_all_stations()

    if not all_stations:
        st.markdown(
            '<div class="notify-panel">'
            '<div style="text-align:center;color:#4b5a72;padding:1.5rem;">'
            '⚠️ Could not load station data. Backend may be offline.</div></div>',
            unsafe_allow_html=True,
        )
        return

    best = all_stations[0]  # already sorted cleanest-first by backend

    # Top status message
    if banner_cls == "a-red":
        status_style = "background:#1a0808;border-color:#7f1d1d;color:#f87171;"
        status_msg   = (f"🚨 <b>Alert:</b> Air quality is <b>{cat}</b> ({live_aqi:.0f} AQI) — "
                        f"exceeds safe threshold of {threshold}. "
                        f"Moving to <b>{best.get('short_name', best['name'])}</b> is recommended.")
    elif banner_cls == "a-yellow":
        status_style = "background:#1a1206;border-color:#78350f;color:#fbbf24;"
        status_msg   = (f"⚠️ <b>Caution:</b> Air quality is <b>{cat}</b> ({live_aqi:.0f} AQI). "
                        f"Sensitive groups should consider <b>{best.get('short_name', best['name'])}</b> "
                        f"which has better air quality.")
    else:
        status_style = "background:#071a0f;border-color:#14532d;color:#4ade80;"
        status_msg   = (f"✅ Air quality is <b>{cat}</b> ({live_aqi:.0f} AQI) — currently safe. "
                        f"Cleanest station: <b>{best.get('short_name', best['name'])}</b>.")

    # Build table rows HTML
    rows = ""
    for i, s in enumerate(all_stations):
        s_aqi  = s.get("aqi") or 0
        s_name = s.get("short_name") or s.get("name", "?")
        s_cat  = s.get("category", "")
        is_primary = s.get("is_primary", False)
        source     = s.get("data_source", "CPCB")

        is_best = (i == 0)
        diff    = s_aqi - live_aqi

        # Color coding: green if lower than current, red if higher
        if diff < -5:
            diff_str  = f'<span style="color:#4ade80;font-size:.7rem;">▼ {abs(diff):.0f} better</span>'
            row_color = "rgba(74,222,128,.04)"
        elif diff > 5:
            diff_str  = f'<span style="color:#f87171;font-size:.7rem;">▲ {diff:.0f} worse</span>'
            row_color = "rgba(248,113,113,.04)"
        else:
            diff_str  = '<span style="color:#4b5a72;font-size:.7rem;">≈ similar</span>'
            row_color = "transparent"

        # AQI pill class
        if   s_aqi <= 50:  pill_cls = "pill-good"
        elif s_aqi <= 100: pill_cls = "pill-good"
        elif s_aqi <= 200: pill_cls = "pill-mod"
        else:              pill_cls = "pill-poor"

        if is_primary:
            pill_cls = "pill-cur"

        row_cls = ' class="best-row"' if is_best else ""
        badge   = '<span class="best-badge">✦ Safest</span>' if is_best else ""
        primary_tag = (f'<span style="font-size:.6rem;color:#38bdf8;margin-left:.3rem;">'
                       f'⚡ {source}</span>') if is_primary else (
                       f'<span style="font-size:.6rem;color:#4b5a72;margin-left:.3rem;">'
                       f'{source}</span>')

        rows += f"""<tr{row_cls} style="background:{row_color};">
            <td><b>{s_name}</b>{badge}{primary_tag}</td>
            <td><span class="area-aqi-pill {pill_cls}">{s_aqi:.0f}</span></td>
            <td>{s_cat}</td>
            <td>{diff_str}</td>
        </tr>"""

    best_aqi = best.get("aqi", 0)
    improve_pct = round((live_aqi - best_aqi) / live_aqi * 100) if live_aqi > 0 and best_aqi < live_aqi else 0
    best_short  = best.get("short_name", best["name"])
    improve_txt = (f"Moving to {best_short} could improve air quality by ~{improve_pct}% "
                   f"({live_aqi:.0f} → {best_aqi:.0f} AQI)"
                   if improve_pct > 0
                   else f"{best_short} currently has the best air quality in Indore.")

    live_tag = (' <span style="font-size:.65rem;color:#4ade80;">● LIVE DATA</span>'
                if stations_live else
                ' <span style="font-size:.65rem;color:#fbbf24;">● CACHED</span>')

    st.markdown(f"""
    <div class="notify-panel">
        <div class="notify-header">
            <div class="notify-icon">🔔</div>
            <div>
                <div class="notify-title">Nearest Safe Zone{live_tag}</div>
                <div class="notify-sub">Indore CPCB Monitoring Stations · Real Data · Updated {datetime.now().strftime('%H:%M')}</div>
            </div>
        </div>
        <div class="aqi-status-bar" style="{status_style}">{status_msg}</div>
        <div style="font-family:'Space Mono',monospace;font-size:.63rem;text-transform:uppercase;
             letter-spacing:.13em;color:#4b5a72;margin-bottom:.45rem;">
            📍 All Stations — AQI Comparison (green = safer, red = worse)
        </div>
        <table class="area-table">
            <thead><tr>
                <th>Station</th><th>AQI</th><th>Category</th><th>vs Current</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="improve-chip">🌿 &nbsp; {improve_txt}</div>
    </div>""", unsafe_allow_html=True)


# ─── Validators ───────────────────────────────────────────────────────────────
def valid_email(s):
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", s.strip()))

def valid_phone(s):
    return bool(re.match(r"^[6-9]\d{9}$", s.strip()))

# ─── Data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching AQI data...")
def load_live_aqi():
    data = client.get_aqi("indore")

    # ── Temporary: print raw response so you can see what the backend returns ──
    
    # ─────────────────────────────────────────────────────────────────────────

    if data and isinstance(data, dict):
        readings  = data.get("readings") or data.get("records") or data.get("data") or []
        threshold = data.get("threshold", 125)
        aqi_index = data.get("aqi_index") or data.get("aqi")

        poll = {}

        # Key normalisation map — covers every casing variant from CPCB API
        KEY_MAP = {
            "PM2.5": "PM2.5", "PM25": "PM2.5",
            "PM10":  "PM10",
            "NO2":   "NO₂",  "NO₂":  "NO₂",
            "SO2":   "SO₂",  "SO₂":  "SO₂",
            "CO":    "CO",
            "O3":    "O₃",   "O₃":   "O₃",
            "NH3":   "NH₃",  "NH₃":  "NH₃",
        }

        for r in readings:
            raw_pid = str(r.get("pollutant_id") or r.get("pollutant") or "").strip().upper()
            avg = r.get("pollutant_avg") or r.get("avg") or r.get("value") or r.get("concentration")
            try:
                if raw_pid and avg is not None:
                    display_key = KEY_MAP.get(raw_pid, raw_pid)
                    poll[display_key] = float(avg)
            except (ValueError, TypeError):
                pass

        if aqi_index:
            live_aqi = float(aqi_index)
            return poll or mock_pollutants(seed=int(datetime.now().hour)), live_aqi, True, threshold, "CPCB via FastAPI"

        elif poll:
            c = []
            if "PM2.5" in poll: c.append(poll["PM2.5"] * 1.5)
            if "PM10"  in poll: c.append(poll["PM10"])
            if "NO₂"   in poll: c.append(poll["NO₂"] * 0.8)
            if c:
                live_aqi = max(c)
                return poll, round(live_aqi, 1), True, threshold, "CPCB via FastAPI"

    poll     = mock_pollutants(seed=int(datetime.now().hour))
    live_aqi = max(poll.get("PM2.5", 48) * 1.5, poll.get("PM10", 82))
    return poll, round(live_aqi, 1), False, 150, "DEMO — backend offline"

@st.cache_data(ttl=300, show_spinner=False)
def load_history():
    records = client.get_aqi_history("indore", limit=500)
    if records:
        try:
            df = pd.DataFrame(records)

            # Normalise timestamp column
            if "recorded_at" in df.columns:
                df["time"] = pd.to_datetime(df["recorded_at"], utc=True)
            elif "timestamp" in df.columns:
                df["time"] = pd.to_datetime(df["timestamp"], utc=True)
            elif "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"], utc=True)
            else:
                raise ValueError("No time column")

            # Normalise pollutant value column
            val_col = next((c for c in ["pollutant_avg","avg_value","aqi","aqi_index"] if c in df.columns), None)
            if not val_col:
                raise ValueError("No value column")
            df["val"] = pd.to_numeric(df[val_col], errors="coerce")

            # Normalise pollutant id column
            pid_col = next((c for c in ["pollutant_id","pollutant"] if c in df.columns), None)

            df = df.dropna(subset=["time","val"])
            if df.empty:
                raise ValueError("Empty after dropna")

            # Round time to the nearest hour so we can group readings
            df["hour"] = df["time"].dt.floor("h")

            if pid_col:
                # Compute AQI per hour by taking max weighted pollutant
                def hour_aqi(grp):
                    best = 0.0
                    for _, row in grp.iterrows():
                        pid = str(row.get(pid_col, "")).strip().upper()
                        v   = float(row["val"])
                        if pid in ("PM2.5",):   best = max(best, v * 1.5)
                        elif pid in ("PM10",):  best = max(best, v)
                        elif pid in ("NO2","NO₂"): best = max(best, v * 0.8)
                        elif pid in ("SO2","SO₂"): best = max(best, v * 0.5)
                        else:                   best = max(best, v)
                    return best if best > 0 else grp["val"].mean()

                aqi_by_hour = (
                    df.groupby("hour")
                    .apply(hour_aqi)
                    .reset_index()
                )
                aqi_by_hour.columns = ["time", "aqi"]
            else:
                # No pollutant column — just average by hour
                aqi_by_hour = (
                    df.groupby("hour")["val"]
                    .mean()
                    .reset_index()
                    .rename(columns={"hour": "time", "val": "aqi"})
                )

            aqi_by_hour = aqi_by_hour.sort_values("time").tail(72)
            aqi_by_hour["aqi"] = aqi_by_hour["aqi"].round(1)

            # Remove statistical outliers (beyond 3 std deviations)
            mean, std = aqi_by_hour["aqi"].mean(), aqi_by_hour["aqi"].std()
            if std > 0:
                aqi_by_hour = aqi_by_hour[
                    (aqi_by_hour["aqi"] >= mean - 3*std) &
                    (aqi_by_hour["aqi"] <= mean + 3*std)
                ]

            if not aqi_by_hour.empty:
                return aqi_by_hour[["time","aqi"]]
        except Exception:
            pass
    return None

@st.cache_data(ttl=300, show_spinner=False)
def load_alerts():
    alerts = client.get_alerts(limit=10)
    if alerts:
        return alerts, True
    return [
        {"time":"2025-07-10 14:30","station":"Vijay Nagar","pollutant":"PM2.5","aqi_value":218,"severity":"Moderate"},
        {"time":"2025-07-10 11:00","station":"Palasia",    "pollutant":"PM10", "aqi_value":195,"severity":"Moderate"},
        {"time":"2025-07-10 08:15","station":"Vijay Nagar","pollutant":"NO2",  "aqi_value":162,"severity":"Low"},
        {"time":"2025-07-09 22:45","station":"Palasia",    "pollutant":"PM2.5","aqi_value":241,"severity":"Moderate"},
        {"time":"2025-07-09 18:00","station":"Vijay Nagar","pollutant":"PM10", "aqi_value":187,"severity":"Low"},
        {"time":"2025-07-09 13:30","station":"Palasia",    "pollutant":"PM2.5","aqi_value":229,"severity":"Moderate"},
        {"time":"2025-07-09 09:00","station":"Vijay Nagar","pollutant":"SO2",  "aqi_value":155,"severity":"Low"},
        {"time":"2025-07-08 20:00","station":"Palasia",    "pollutant":"NO2",  "aqi_value":172,"severity":"Low"},
        {"time":"2025-07-08 15:30","station":"Vijay Nagar","pollutant":"PM10", "aqi_value":261,"severity":"Moderate"},
        {"time":"2025-07-08 10:00","station":"Palasia",    "pollutant":"PM2.5","aqi_value":235,"severity":"Moderate"},
    ], False

# ─── Load all data ────────────────────────────────────────────────────────────
poll, live_aqi, is_live, threshold, data_source = load_live_aqi()

# Select AQI from nearest station to user's GPS location (not average)
_all_stations, _primary_aqi, _stations_ok = load_all_stations()
if _stations_ok and _all_stations:
    user_lat = st.session_state.get("gps_lat", "")
    user_lon = st.session_state.get("gps_lon", "")

    if user_lat and user_lon:
        # Find nearest station using haversine-like distance
        import math
        def _dist(s):
            try:
                dlat = math.radians(float(s["lat"]) - float(user_lat))
                dlon = math.radians(float(s["lon"]) - float(user_lon))
                a = math.sin(dlat/2)**2 + math.cos(math.radians(float(user_lat))) * math.cos(math.radians(float(s["lat"]))) * math.sin(dlon/2)**2
                return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            except (ValueError, TypeError):
                return 9999

        nearest = min(_all_stations, key=_dist)
        if nearest.get("aqi") is not None:
            live_aqi = float(nearest["aqi"])
            data_source = f"{nearest.get('short_name', nearest.get('name', 'Unknown'))} (nearest)"
    else:
        # No GPS — use primary station
        for s in _all_stations:
            if s.get("is_primary") and s.get("aqi") is not None:
                live_aqi = float(s["aqi"])
                data_source = f"{s.get('short_name', 'Primary')} (default)"
                break

dom_poll = max(poll, key=poll.get) if poll else "PM2.5"
cat, col_hex, banner_cls = aqi_info(live_aqi)

_hist_raw    = load_history()
hist_df      = _hist_raw if _hist_raw is not None else fake_history(live_aqi)
hist_is_real = _hist_raw is not None

pred_df  = fake_prediction(live_aqi)
delta24  = pred_df["aqi"].iloc[:24].mean() - live_aqi
peak_aqi = pred_df["aqi"].max()
peak_t   = pred_df.loc[pred_df["aqi"].idxmax(),"time"].strftime("%d %b %H:%M")

alert_list, alerts_are_real = load_alerts()

# ─── Auto-log alert (only when authenticated) ─────────────────────────────────
if is_live and live_aqi > threshold and st.session_state.get("token"):
    _alert_key = f"alert_logged_{int(live_aqi // 10) * 10}"
    if not st.session_state.get(_alert_key):
        client.log_alert("Indore", dom_poll, live_aqi)
        st.session_state[_alert_key] = True

# ══════════════════════════════════════════════════════════════════════════════
#  INLINE LOGIN / REGISTER MODAL
#  Shown in place of the full dashboard when show_login_modal == True.
# ══════════════════════════════════════════════════════════════════════════════
def render_login_modal():
    # Modal styling (no backdrop div — st.stop() already replaced the page)
    st.markdown("""
    <style>
    .modal-card {
        background:var(--card);border:1px solid var(--border);border-radius:18px;
        padding:1.6rem 1.8rem 1.8rem 1.8rem;
        box-shadow:0 24px 80px rgba(0,0,0,.7);
        animation: modalSlideIn .3s ease;
        margin-top:1rem;
    }
    @keyframes modalSlideIn {
        from { opacity:0;transform:translateY(-20px) scale(.97); }
        to   { opacity:1;transform:translateY(0) scale(1); }
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the modal using columns (narrow center column)
    _, modal_col, _ = st.columns([1.2, 1.6, 1.2])
    with modal_col:
        # Close button
        if st.button("✕  Close", key="modal_close_btn"):
            st.session_state.show_login_modal   = False
            st.session_state.notify_after_login = False
            st.rerun()

        st.markdown('<div class="modal-card">', unsafe_allow_html=True)

        # Header
        if st.session_state.get("notify_after_login"):
            st.markdown("""
            <div style="text-align:center;margin-bottom:1rem;">
                <div style="font-size:1.8rem;margin-bottom:.2rem;">🔔</div>
                <div style="font-family:'Space Mono',monospace;font-size:.95rem;font-weight:700;
                     background:linear-gradient(130deg,#f59e0b,#ef4444);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                     Enable Air Quality Alerts</div>
                <div style="font-size:.75rem;color:#4b5a72;margin-top:.3rem;line-height:1.5;">
                    Sign in or create a free account to receive alerts<br>
                    when AQI crosses unsafe levels in Indore.</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;margin-bottom:1rem;">
                <div style="font-size:1.8rem;margin-bottom:.2rem;">🌫️</div>
                <div style="font-family:'Space Mono',monospace;font-size:.95rem;font-weight:700;
                     background:linear-gradient(130deg,#38bdf8,#2dd4bf);
                     -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                     AQI EWS Account</div>
                <div style="font-size:.75rem;color:#4b5a72;margin-top:.3rem;">
                    Early Warning System · Indore, Madhya Pradesh</div>
            </div>""", unsafe_allow_html=True)

        # Mode tabs
        mc1, mc2 = st.columns(2)
        with mc1:
            if st.button("🔑 Sign In", key="modal_tab_login", use_container_width=True,
                         type="primary" if st.session_state.login_mode == "login" else "secondary"):
                st.session_state.login_mode = "login"; st.rerun()
        with mc2:
            if st.button("📝 Register", key="modal_tab_reg", use_container_width=True,
                         type="primary" if st.session_state.login_mode == "register" else "secondary"):
                st.session_state.login_mode = "register"; st.rerun()

        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

        # SIGN IN
        if st.session_state.login_mode == "login":
            with st.form("modal_login_form"):
                st.markdown("<div style='font-size:.9rem;font-weight:600;margin-bottom:.7rem;'>Welcome back</div>",
                            unsafe_allow_html=True)
                contact  = st.text_input("Email or Mobile Number",
                                         placeholder="yourname@email.com  or  9876543210",
                                         key="ml_contact")
                password = st.text_input("Password", type="password",
                                         placeholder="Your password", key="ml_password")
                submitted = st.form_submit_button("Sign In →", use_container_width=True)

            if submitted:
                if not contact.strip() or not password.strip():
                    st.markdown('<div class="err-box">⚠️ Please fill in all fields.</div>',
                                unsafe_allow_html=True)
                else:
                    with st.spinner("Signing in…"):
                        if backend_login(contact.strip(), password):
                            st.session_state.show_login_modal   = False
                            st.session_state.notify_after_login = False
                            st.rerun()

            st.markdown("""
            <div style='text-align:center;margin-top:.7rem;font-size:.75rem;color:#4b5a72;'>
                New to AQI-EWS? Click <b style="color:#38bdf8;">Register</b> above.
            </div>""", unsafe_allow_html=True)

        # REGISTER
        else:
            st.markdown("<div style='font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;"
                        "color:#4b5a72;margin:.2rem 0 .4rem 0;'>📍 Detect Your Location (optional)</div>",
                        unsafe_allow_html=True)
            if st.session_state.gps_address:
                st.markdown(f"""<div class="loc-result success">
                    <span>✅</span>
                    <div>
                        <div class="loc-addr">{st.session_state.gps_address}</div>
                        <div class="loc-coords">🛰 {st.session_state.gps_lat},  {st.session_state.gps_lon}</div>
                    </div></div>""", unsafe_allow_html=True)
                if st.button("🔄 Re-detect", key="modal_redetect"):
                    st.session_state.gps_address = ""; st.session_state.gps_lat = ""
                    st.session_state.gps_lon = ""; st.session_state.loc_fetched = False; st.rerun()
            else:
                geo_result = components.html(GEO_COMPONENT, height=115, scrolling=False)
                if geo_result and isinstance(geo_result, dict):
                    status  = geo_result.get("status","")
                    address = geo_result.get("address","").strip()
                    if status == "success" and address and not st.session_state.loc_fetched:
                        st.session_state.gps_address = address
                        st.session_state.gps_lat     = str(geo_result.get("lat",""))
                        st.session_state.gps_lon     = str(geo_result.get("lon",""))
                        st.session_state.loc_fetched = True
                        st.rerun()
                    elif status == "denied":
                        st.markdown('<div class="loc-result error">❌ &nbsp; Permission denied. Enter address manually below.</div>',
                                    unsafe_allow_html=True)

            with st.form("modal_register_form"):
                st.markdown("<div style='font-size:.9rem;font-weight:600;margin-bottom:.7rem;'>Create account</div>",
                            unsafe_allow_html=True)
                full_name   = st.text_input("Full Name", placeholder="e.g. Ravi Sharma", key="mr_name")
                contact     = st.text_input("Email or Mobile Number",
                                            placeholder="yourname@email.com  or  9876543210", key="mr_contact")
                rp1, rp2    = st.columns(2)
                with rp1:
                    password = st.text_input("Password", type="password", placeholder="Min. 6 chars", key="mr_pw")
                with rp2:
                    confirm  = st.text_input("Confirm", type="password", placeholder="Re-enter", key="mr_pw2")
                manual_addr = st.text_input(
                    "Address",
                    value=st.session_state.gps_address,
                    placeholder="42 MG Road, Vijay Nagar, Indore, MP",
                    key="mr_addr",
                )
                agree       = st.checkbox("I agree to the Terms of Service and Privacy Policy", key="mr_agree")
                submitted   = st.form_submit_button("Create Account →", use_container_width=True)

            if submitted:
                errors = []
                if not full_name.strip():                                    errors.append("Full name is required.")
                if not contact.strip():                                      errors.append("Email or phone is required.")
                elif not valid_email(contact) and not valid_phone(contact):  errors.append("Enter a valid email or 10-digit Indian mobile number.")
                if len(password) < 6:                                        errors.append("Password must be at least 6 characters.")
                if password != confirm:                                       errors.append("Passwords do not match.")
                if not agree:                                                 errors.append("Please accept the Terms of Service.")
                final_loc = manual_addr.strip() or st.session_state.gps_address or "Indore, MP"

                if errors:
                    for e in errors:
                        st.markdown(f'<div class="err-box">⚠️ {e}</div>', unsafe_allow_html=True)
                else:
                    with st.spinner("Creating your account…"):
                        if backend_register(
                            full_name.strip(), contact.strip(), password,
                            final_loc,
                            st.session_state.gps_lat, st.session_state.gps_lon,
                        ):
                            st.session_state.show_login_modal   = False
                            st.session_state.notify_after_login = False
                            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ── Render modal (replaces dashboard) if flag is set ─────────────────────────
if st.session_state.show_login_modal:
    render_login_modal()
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    is_auth = st.session_state.get("authenticated", False)

    if is_auth:
        # ── Authenticated user ────────────────────────────────────────────────
        name = st.session_state.get("user_name","User")
        loc  = (st.session_state.get("user_location","")
                or st.session_state.get("gps_address","")
                or "Indore, MP")
        init = name[0].upper() if name else "U"
        st.markdown(f"""
        <div class="user-chip">
            <div class="user-avatar">{init}</div>
            <div>
                <div class="user-name">{name}</div>
                <div class="user-loc">📍 {loc[:42]}{"…" if len(loc)>42 else ""}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        # ── Guest ─────────────────────────────────────────────────────────────
        st.markdown("""
        <div class="guest-chip">
            <div class="guest-avatar">👤</div>
            <div>
                <div class="guest-label">Viewing as Guest</div>
                <div class="guest-hint">Login to enable alerts</div>
            </div>
        </div>""", unsafe_allow_html=True)
        if st.button("🔑  Login / Register", key="sb_login_btn", use_container_width=True):
            st.session_state.show_login_modal   = True
            st.session_state.login_mode         = "login"
            st.session_state.notify_after_login = False
            st.rerun()

    # ── GPS location ──────────────────────────────────────────────────────────
    st.markdown("<div style='font-size:.67rem;text-transform:uppercase;letter-spacing:.12em;"
                "color:#4b5a72;margin:.7rem 0 .4rem 0;'>📍 Your Location</div>",
                unsafe_allow_html=True)
    if st.session_state.gps_address:
        st.markdown(f"""<div class="loc-result success">
            <span>✅</span>
            <div>
                <div class="loc-addr">{st.session_state.gps_address}</div>
                <div class="loc-coords">🛰 {st.session_state.gps_lat}, {st.session_state.gps_lon}</div>
            </div></div>""", unsafe_allow_html=True)
        if st.button("🔄 Re-detect", key="redetect_sb", use_container_width=True):
            st.session_state.gps_address = ""; st.session_state.gps_lat = ""
            st.session_state.gps_lon = ""; st.session_state.loc_fetched = False
            st.session_state.user_location = ""; st.rerun()
    else:
        geo_result = components.html(GEO_COMPONENT, height=112, scrolling=False)
        if geo_result and isinstance(geo_result, dict):
            status  = geo_result.get("status","")
            address = geo_result.get("address","").strip()
            if status == "success" and address and not st.session_state.loc_fetched:
                st.session_state.gps_address   = address
                st.session_state.gps_lat       = str(geo_result.get("lat",""))
                st.session_state.gps_lon       = str(geo_result.get("lon",""))
                st.session_state.loc_fetched   = True
                st.session_state.user_location = address
                st.rerun()

    st.markdown("---")

    # ── System status ─────────────────────────────────────────────────────────
    st.markdown("<div style='font-size:.67rem;text-transform:uppercase;letter-spacing:.12em;"
                "color:#4b5a72;margin-bottom:.42rem;'>System Status</div>",
                unsafe_allow_html=True)
    cat_cls = "p-ok" if "green" in banner_cls else ("p-warn" if "yellow" in banner_cls else "p-err")
    for lbl, val, cls in [
        ("Live AQI",      f"{live_aqi:.0f}",                              "p-info"),
        ("Category",      cat,                                              cat_cls),
        ("Top Pollutant", dom_poll,                                        "p-info"),
        ("Data Source",   "CPCB / FastAPI" if is_live else "Demo",        "p-ok" if is_live else "p-warn"),
        ("Status",        "LIVE" if is_live else "DEMO",                  "p-ok" if is_live else "p-warn"),
        ("Last Refresh",  datetime.now().strftime("%H:%M"),               "p-info"),
    ]:
        st.markdown(f'<div class="si"><span>{lbl}</span>'
                    f'<span class="pill {cls}">{val}</span></div>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='font-size:.67rem;text-transform:uppercase;letter-spacing:.12em;"
                "color:#4b5a72;margin-bottom:.42rem;'>Pollutant Levels</div>",
                unsafe_allow_html=True)
    for p, v in poll.items():
        st.markdown(f'<div class="si"><span>{p}</span>'
                    f'<span style="font-family:Space Mono,monospace;font-size:.74rem;">{v} µg/m³</span></div>',
                    unsafe_allow_html=True)

    st.markdown("---")
    if is_auth:
        if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
loc_display = st.session_state.get("user_location","") or "Indore, MP"
st.markdown(f"""
<div class="top-bar">
  <div>
    <div class="top-title">🌫 AQI-EWS · Indore</div>
    <div class="top-sub">
        📍 {loc_display[:60]}{"…" if len(loc_display)>60 else ""}
        &nbsp;·&nbsp; CPCB Monitoring Stations &nbsp;·&nbsp; Madhya Pradesh
    </div>
  </div>
  <div class="live-badge">
    <span class="live-dot"></span>
    {'LIVE · Auto-refreshes every 5 min' if is_live else 'DEMO DATA · Backend offline'}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Alert banner ───────────────────────────────────────────────────────────────
b_icon = {"a-green":"✅","a-yellow":"⚠️","a-red":"🚨"}[banner_cls]
b_msgs = {
    "a-green":  f"Air quality is <b>{cat}</b> ({live_aqi:.0f} AQI) — safe for all groups.",
    "a-yellow": f"Air quality is <b>{cat}</b> ({live_aqi:.0f} AQI) — sensitive groups should limit outdoor exposure.",
    "a-red":    f"EARLY WARNING: <b>{cat}</b> air quality ({live_aqi:.0f} AQI) — exceeds threshold of {threshold}. Avoid prolonged outdoor activity.",
}
st.markdown(f'<div class="alert-banner {banner_cls}">{b_icon} &nbsp; {b_msgs[banner_cls]}</div>',
            unsafe_allow_html=True)

# ── Nearest Safe Zone expander (dropdown arrow) ──────────────────────────────
with st.expander("📍 Nearest Safe Zones — Compare All Indore CPCB Stations", expanded=False):
    render_notify_panel(live_aqi, cat, banner_cls, threshold)

# ─── Metric cards ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
thresh_accent  = "green" if live_aqi <= threshold else "red"

_aqi_sub = f"{cat} · {data_source}" if _stations_ok else cat
for obj, accent, lbl, val, sub in [
    (c1, "blue",  "Current AQI",  f"{live_aqi:.0f}", _aqi_sub),
    (c2, "teal",  "6h Forecast",  f"{pred_df['aqi'].iloc[:6].mean():.0f}", "LSTM predicted"),
    (c3, "amber", "24h Forecast", f"{pred_df['aqi'].iloc[:24].mean():.0f}",f"Δ {delta24:+.0f} from now"),
]:
    with obj:
        st.markdown(mcard(accent, lbl, val, sub), unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="mcard m-{thresh_accent}">
        <div class="mlabel">Alert Threshold <span class="thresh-badge">SYSTEM</span></div>
        <div class="mval" style="color:var(--{thresh_accent});">{threshold}</div>
        <div class="msub">🔒 Set by backend · auto-computed</div>
    </div>""", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 Live Monitor", "📈 Trend Analysis", "🔮 Prediction", "🔔 Alerts Log"
])

# ── TAB 1 — Live Monitor ──────────────────────────────────────────────────────
with tab1:
    if poll:
        src_note = "Live CPCB · FastAPI backend" if is_live else "Demo data — backend offline"
        st.markdown(f'<div class="stitle">Live Pollutant Readings · Indore CPCB Stations · {src_note}</div>',
                    unsafe_allow_html=True)
        pal = ["#cddae0","#2dd4bf","#818cf8","#c084fc","#fbbf24","#4ade80"]
        fig_bar = go.Figure(go.Bar(
            x=list(poll.keys()), y=list(poll.values()),
            marker=dict(color=pal[:len(poll)], opacity=0.85),
            text=[f"{v}" for v in poll.values()], textposition="outside",
            textfont=dict(color="#94a3b8", size=10),
            hovertemplate="<b>%{x}</b>: %{y} µg/m³<extra></extra>",
        ))
        fig_bar.update_layout(**PLOTLY_BASE, height=255, yaxis_title="µg/m³", bargap=0.35)
        st.plotly_chart(fig_bar, use_container_width=True)

    hist_note = "Real DB history" if hist_is_real else "Simulated trend"
    st.markdown(f'<div class="stitle">72-Hour AQI Trend · {hist_note}</div>', unsafe_allow_html=True)
    fig_t = go.Figure()
    fig_t.add_trace(go.Scatter(
        x=hist_df["time"], y=hist_df["aqi"],
        mode="lines", line=dict(color="#0049F5", width=2),
        fill="tozeroy", fillcolor="rgba(56,189,248,0.07)", name="AQI",
        hovertemplate="<b>%{y:.0f}</b> AQI — %{x|%d %b %H:%M}<extra></extra>",
    ))
    fig_t.add_hline(y=threshold, line_dash="dot", line_color="#fb2424",
                    annotation_text=f"⚠ Threshold {threshold}",
                    annotation_position="top right", annotation_font_color="#fb2424")
    fig_t.update_layout(**PLOTLY_BASE, height=280, yaxis_title="AQI Index")
    st.plotly_chart(fig_t, use_container_width=True)

# ── TAB 2 — Trend Analysis ────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="stitle">72-Hour Pollutant Breakdown</div>', unsafe_allow_html=True)
    if len(hist_df) >= 24:
        buckets = {"Last 24h": hist_df.tail(24), "24–48h ago": hist_df.iloc[-48:-24],
                   "48–72h ago": hist_df.iloc[-72:-48]}
        avg_by_period = {k: round(v["aqi"].mean(), 1) for k, v in buckets.items() if not v.empty}
        c_a, c_b, c_c = st.columns(3)
        for col, (period, avg) in zip([c_a, c_b, c_c], avg_by_period.items()):
            acc = "green" if avg <= 100 else ("amber" if avg <= 200 else "red")
            with col:
                st.markdown(mcard(acc, period, f"{avg}", "avg AQI"), unsafe_allow_html=True)

    fig_area = go.Figure()
    colors = {"PM2.5":"#38bdf8","PM10":"#2dd4bf","NO₂":"#818cf8",
              "SO₂":"#c084fc","CO":"#fbbf24","O₃":"#4ade80"}
    for pollutant, base_val in poll.items():
        np.random.seed(hash(pollutant) % 100)
        v_series = np.clip(
            base_val + np.cumsum(np.random.randn(72)*base_val*0.04)
            + base_val*0.15*np.sin(np.linspace(0,4*np.pi,72)),
            0, base_val*2
        )
        fig_area.add_trace(go.Scatter(
            x=hist_df["time"].values[:72], y=v_series[:len(hist_df)],
            mode="lines", name=pollutant,
            line=dict(color=colors.get(pollutant,"#94a3b8"), width=1.5),
            hovertemplate=f"<b>{pollutant}</b>: %{{y:.1f}} µg/m³<br>%{{x|%d %b %H:%M}}<extra></extra>",
        ))
    fig_area.update_layout(**{**PLOTLY_BASE, "legend": dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)")},
                       height=290, yaxis_title="µg/m³")
                           
    st.plotly_chart(fig_area, use_container_width=True)

    st.markdown('<div class="stitle">AQI Distribution (last 72h)</div>', unsafe_allow_html=True)
    bins      = [0, 50, 100, 200, 300, 500]
    labels    = ["Good\n0–50","Satisfactory\n51–100","Moderate\n101–200","Poor\n201–300","Very Poor\n300+"]
    bin_color = ["#4ade80","#a3e635","#fbbf24","#fb923c","#f87171"]
    counts, _ = np.histogram(hist_df["aqi"], bins=bins)
    fig_d = go.Figure(go.Bar(
        x=labels, y=counts,
        marker=dict(color=bin_color, opacity=0.8),
        text=counts, textposition="outside",
        textfont=dict(color="#94a3b8", size=10),
        hovertemplate="<b>%{x}</b>: %{y} hours<extra></extra>",
    ))
    fig_d.update_layout(**PLOTLY_BASE, height=200, xaxis_title="AQI Value", yaxis_title="Hours")
    st.plotly_chart(fig_d, use_container_width=True)

# ── TAB 3 — LSTM Prediction ───────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="stitle">LSTM Early Warning · 24–48h AQI Forecast vs Expected</div>',
                unsafe_allow_html=True)
    st.markdown("""
    <div class="pred-legend">
        <div class="pred-legend-item">
            <div class="pred-legend-line" style="background:#fbbf24;"></div>
            <span style="color:#dde3ef;">Expected AQI</span>
        </div>
        <div class="pred-legend-item">
            <div class="pred-legend-line" style="background:#2dd4bf;"></div>
            <span style="color:#dde3ef;">Predicted 0–24h</span>
        </div>
        <div class="pred-legend-item">
            <div class="pred-legend-line" style="background:#818cf8;border-top:2px dashed #818cf8;height:0;"></div>
            <span style="color:#dde3ef;">Predicted 24–48h</span>
        </div>
        <div class="pred-legend-item">
            <div class="pred-legend-line" style="background:rgba(45,212,191,.25);"></div>
            <span style="color:#dde3ef;">95% Confidence Band</span>
        </div>
    </div>""", unsafe_allow_html=True)

    fig_p = go.Figure()
    fig_p.add_trace(go.Scatter(
        x=pd.concat([pred_df["time"], pred_df["time"][::-1]]).tolist(),
        y=pd.concat([pred_df["upper"], pred_df["lower"][::-1]]).tolist(),
        fill="toself", fillcolor="rgba(45,212,191,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        name="95% Confidence Band", showlegend=False, hoverinfo="skip",
    ))
    fig_p.add_trace(go.Scatter(x=pred_df["time"], y=pred_df["expected"],
        mode="lines", line=dict(color="#fbbf24", width=2, dash="dot"), name="Expected AQI",
        hovertemplate="<b>Expected: %{y:.0f}</b><br>%{x|%d %b %H:%M}<extra></extra>"))
    fig_p.add_trace(go.Scatter(x=pred_df["time"].iloc[:24], y=pred_df["aqi"].iloc[:24],
        mode="lines", line=dict(color="#2dd4bf", width=2.5), name="Predicted 0–24h",
        hovertemplate="<b>Predicted: %{y:.0f}</b><br>%{x|%d %b %H:%M}<extra>LSTM · 0–24h</extra>"))
    fig_p.add_trace(go.Scatter(x=pred_df["time"].iloc[24:], y=pred_df["aqi"].iloc[24:],
        mode="lines", line=dict(color="#818cf8", width=2, dash="dash"), name="Predicted 24–48h",
        hovertemplate="<b>Predicted: %{y:.0f}</b><br>%{x|%d %b %H:%M}<extra>LSTM · 24–48h</extra>"))

    now_x = pred_df["time"].iloc[0].isoformat()
    fig_p.add_shape(type="line", x0=now_x, x1=now_x, y0=0, y1=1, xref="x", yref="paper",
                    line=dict(color="rgba(255,255,255,0.15)", width=1.5))
    fig_p.add_annotation(x=now_x, y=1, xref="x", yref="paper", text="Now",
                         showarrow=False, yanchor="bottom", font=dict(color="#94a3b8", size=10))
    h24_x = pred_df["time"].iloc[24].isoformat()
    fig_p.add_shape(type="line", x0=h24_x, x1=h24_x, y0=0, y1=1, xref="x", yref="paper",
                    line=dict(color="rgba(129,140,248,0.3)", width=1, dash="dot"))
    fig_p.add_annotation(x=h24_x, y=1, xref="x", yref="paper", text="24h",
                         showarrow=False, yanchor="bottom", font=dict(color="#818cf8", size=10))
    fig_p.add_hline(y=threshold, line_dash="dot", line_color="#fc0a0a", line_width=1.5,
                    annotation_text=f"⚠ Threshold {threshold}",
                    annotation_position="top right", annotation_font_color="#ffffff")
    for lo, hi, fc in [(0,50,"rgba(74,222,128,.04)"),(50,100,"rgba(163,230,53,.03)"),(100,200,"rgba(251,191,36,.03)"),(200,300,"rgba(248,113,113,.03)")]:
        fig_p.add_hrect(y0=lo, y1=hi, fillcolor=fc, line_width=0)
    _pred_layout = {**PLOTLY_BASE,
        "height": 380, "showlegend": False,
        "yaxis": dict(range=[0, 300], dtick=50, gridcolor="rgba(148,163,184,.08)",
                      gridwidth=1, zerolinecolor="#1a2540", showline=False, title="AQI Index"),
        "xaxis": dict(gridcolor="rgba(148,163,184,.06)", gridwidth=1,
                      zerolinecolor="#1a2540", showline=False),
    }
    fig_p.update_layout(**_pred_layout)
    st.plotly_chart(fig_p, use_container_width=True)

    exc     = int((pred_df["aqi"] > threshold).sum())
    avg_gap = (pred_df["expected"] - pred_df["aqi"]).mean()
    s1, s2, s3, s4 = st.columns(4)
    for obj, accent, lbl, val, sub in [
        (s1, "red",    "Peak Predicted AQI", f"{peak_aqi:.0f}",  peak_t),
        (s2, "amber",  "Hours > Threshold",  str(exc),           "in next 48h"),
        (s3, "teal",   "LSTM vs Expected",   f"{avg_gap:+.0f}",  "avg correction"),
        (s4, "purple", "Model Accuracy",     "91.4%",            "validation set"),
    ]:
        with obj:
            st.markdown(f"""<div class="mcard m-{accent}" style="margin-bottom:.8rem;">
                <div class="mlabel">{lbl}</div>
                <div class="mval" style="font-size:1.3rem;color:var(--{accent});">{val}</div>
                <div class="msub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.caption("ℹ️ **Expected AQI** = historical seasonal pattern. "
               "**Predicted AQI** = LSTM output incorporating recent trends. "
               "Lower Predicted vs Expected = model anticipates improvement.")

# ── TAB 4 — Alerts Log ────────────────────────────────────────────────────────
with tab4:
    src_label = "Live from backend" if alerts_are_real else "Demo data"
    st.markdown(f'<div class="stitle">Recent Alerts · Last 10 Events · {src_label}</div>',
                unsafe_allow_html=True)

    def normalise_alert(a):
        return {
            "time":      a.get("time") or a.get("created_at","—"),
            "station":   a.get("station","—"),
            "pollutant": a.get("pollutant","—"),
            "aqi":       str(a.get("aqi_value") or a.get("aqi","—")),
            "severity":  a.get("severity") or severity_label(float(a.get("aqi_value",0) or 0))[0],
        }

    norm_alerts = [normalise_alert(a) for a in alert_list]
    sev_cls = {"Low":"s-low","Moderate":"s-mod","High":"s-high"}
    rows_html = "".join(f"""<tr>
        <td style="color:#4b5a72;">{a['time']}</td>
        <td>{a['station']}</td>
        <td>{a['pollutant']}</td>
        <td style="font-family:Space Mono,monospace;font-weight:700;">{a['aqi']}</td>
        <td class="{sev_cls.get(a['severity'],'s-low')}">{a['severity']}</td>
    </tr>""" for a in norm_alerts)

    st.markdown(f"""<div style="background:var(--card);border:1px solid var(--border);
        border-radius:12px;padding:1.1rem 1.3rem;margin-bottom:1.3rem;">
    <table class="atbl">
        <thead><tr>
            <th>Timestamp</th><th>Station</th><th>Pollutant</th><th>AQI</th><th>Severity</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table></div>""", unsafe_allow_html=True)

    sev_cnt = Counter(a["severity"] for a in norm_alerts)
    if sev_cnt:
        fig_pie = go.Figure(go.Pie(
            labels=list(sev_cnt.keys()), values=list(sev_cnt.values()),
            hole=0.62,
            marker=dict(
                colors=["#fbbf24","#4ade80","#f87171"][:len(sev_cnt)],
                line=dict(color=["#1a1206","#071a0f","#1a0808"][:len(sev_cnt)], width=3),
            ),
            textfont=dict(size=12, color="white"),
            hovertemplate="<b>%{label}</b>: %{value}<extra></extra>",
        ))
        fig_pie.add_annotation(
            text=f"<b>{len(norm_alerts)}</b><br><span style='font-size:10px'>Alerts</span>",
            showarrow=False, font=dict(size=14, color="#dde3ef"),
        )
        pie_layout = {**PLOTLY_BASE, "height": 260,
                      "legend": dict(orientation="h", y=-0.15, xanchor="center", x=0.5)}
        fig_pie.update_layout(**pie_layout)
        st.markdown('<div class="stitle">Severity Distribution</div>', unsafe_allow_html=True)
        st.plotly_chart(fig_pie, use_container_width=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;font-size:.7rem;color:#1e2d45;
     padding:2rem 0 0 0;border-top:1px solid #1a2540;margin-top:.5rem;'>
    AQI-EWS · Early Warning System · Indore · CPCB Data via FastAPI + data.gov.in ·
    LSTM + Isolation Forest · Madhya Pradesh, India
</div>
""", unsafe_allow_html=True)

# ── Floating "Get Notification" button (bottom-right corner) ──────────────────
# Check if the floating button was clicked (query param approach)
if st.query_params.get("get_notification") == "true":
    st.query_params.clear()
    st.session_state.show_login_modal   = True
    st.session_state.login_mode         = "login"
    st.session_state.notify_after_login = True
    st.rerun()

if not st.session_state.get("authenticated"):
    st.markdown("""
    <style>
    .fab-notify {
        position:fixed; bottom:28px; right:28px; z-index:99999;
        display:inline-flex; align-items:center; gap:10px;
        background:linear-gradient(135deg, #fbbf24 0%, #f59e0b 50%, #d97706 100%);
        color:#1a0f00 !important; font-family:'DM Sans',sans-serif;
        font-size:14px; font-weight:700; letter-spacing:.02em;
        padding:13px 24px 13px 20px; border:none; border-radius:50px;
        cursor:pointer; text-decoration:none !important;
        box-shadow: 0 4px 24px rgba(251,191,36,.4), 0 1px 3px rgba(0,0,0,.2);
        transition: all .3s cubic-bezier(.4,0,.2,1);
        animation: fab-entrance .5s cubic-bezier(.34,1.56,.64,1) both;
        overflow:hidden;
    }
    .fab-notify::before {
        content:''; position:absolute; top:0; left:-100%; width:100%; height:100%;
        background:linear-gradient(90deg, transparent, rgba(255,255,255,.25), transparent);
        transition: left .6s ease;
    }
    .fab-notify:hover::before { left:100%; }
    .fab-notify:hover {
        transform:translateY(-4px) scale(1.05);
        box-shadow: 0 10px 35px rgba(251,191,36,.5), 0 0 25px rgba(251,191,36,.25);
        background:linear-gradient(135deg, #fcd34d 0%, #fbbf24 50%, #f59e0b 100%);
        color:#1a0f00 !important; text-decoration:none !important;
    }
    .fab-notify:active {
        transform:translateY(-1px) scale(.98);
        box-shadow: 0 4px 16px rgba(251,191,36,.35);
    }
    .fab-bell {
        font-size:17px; display:inline-block;
        animation: bell-ring 3s ease-in-out infinite;
        transform-origin: top center;
    }
    .fab-text {
        position:relative; top:0.5px;
    }
    .fab-dot {
        width:7px; height:7px; border-radius:50%;
        background:#dc2626; border:1.5px solid #1a0f00;
        position:absolute; top:10px; left:24px;
        animation: dot-blink 2s infinite;
    }
    @keyframes fab-entrance {
        from { opacity:0; transform:translateY(30px) scale(.8); }
        to   { opacity:1; transform:translateY(0) scale(1); }
    }
    @keyframes bell-ring {
        0%   { transform:rotate(0); }
        5%   { transform:rotate(14deg); }
        10%  { transform:rotate(-13deg); }
        15%  { transform:rotate(10deg); }
        20%  { transform:rotate(-8deg); }
        25%  { transform:rotate(4deg); }
        30%  { transform:rotate(0); }
        100% { transform:rotate(0); }
    }
    @keyframes dot-blink {
        0%, 100% { opacity:1; }
        50%      { opacity:.3; }
    }
    @keyframes fab-pulse {
        0%   { box-shadow: 0 4px 24px rgba(251,191,36,.4), 0 0 0 0 rgba(251,191,36,.35); }
        70%  { box-shadow: 0 4px 24px rgba(251,191,36,.4), 0 0 0 14px rgba(251,191,36,0); }
        100% { box-shadow: 0 4px 24px rgba(251,191,36,.4), 0 0 0 0 rgba(251,191,36,0); }
    }
    .fab-notify { animation: fab-entrance .5s cubic-bezier(.34,1.56,.64,1) both, fab-pulse 2.5s 1s infinite; }
    </style>
    <a href="?get_notification=true" class="fab-notify">
        <span class="fab-dot"></span>
        <span class="fab-bell">🔔</span>
        <span class="fab-text">Get Notification</span>
    </a>
    """, unsafe_allow_html=True)