"""
AQI EWS — Login / Registration Page
Run with: streamlit run login.py
"""

import streamlit as st
import streamlit.components.v1 as components
import re

# ── All backend API calls go through backend_client ──────────────────────────
from backend_client import backend_login, backend_register

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AQI-EWS · Sign In",
    page_icon="🌫️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Session state defaults ───────────────────────────────────────────────────
for key, default in [
    ("authenticated",   False),
    ("mode",            "login"),
    ("user_name",       ""),
    ("user_email",      ""),
    ("token",           ""),
    ("user_location",   ""),
    ("gps_address",     ""),
    ("gps_lat",         ""),
    ("gps_lon",         ""),
    ("loc_fetched",     False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Redirect if already logged in ───────────────────────────────────────────
if st.session_state.authenticated:
    st.switch_page("pages/dashboard.py")

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg:     #080d18; --card:   #0f1623; --card2:  #141e2e;
    --border: #1a2540; --blue:   #38bdf8; --teal:   #2dd4bf;
    --green:  #4ade80; --amber:  #fbbf24; --red:    #f87171;
    --muted:  #4b5a72; --text:   #dde3ef;
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
#MainMenu, footer, header,
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"] { visibility:hidden!important; display:none!important; }

.main .block-container { padding-top:0!important; padding-bottom:2rem!important; max-width:480px!important; }

body::before {
    content:''; position:fixed; inset:0; z-index:-1;
    background:
        radial-gradient(ellipse 80% 50% at 20% 10%, rgba(56,189,248,.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(45,212,191,.05) 0%, transparent 60%),
        #080d18;
}

.brand-hero { text-align:center; padding:2.5rem 0 1.5rem 0; }
.brand-icon  { font-size:2.8rem; display:block; margin-bottom:.5rem; filter:drop-shadow(0 0 18px rgba(56,189,248,.4)); }
.brand-name  {
    font-family:'Space Mono',monospace; font-size:1.6rem; font-weight:700;
    background:linear-gradient(130deg,var(--blue),var(--teal));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}
.brand-tagline { font-size:.82rem; color:var(--muted); margin-top:.3rem; }
.aqi-pills { display:flex; gap:.5rem; justify-content:center; flex-wrap:wrap; margin-top:.9rem; }
.aqi-pill  { font-size:.7rem; padding:.2rem .65rem; border-radius:20px; font-weight:600; }

.stTextInput > label { font-size:.78rem!important; text-transform:uppercase!important;
    letter-spacing:.1em!important; color:var(--muted)!important; margin-bottom:.3rem!important; }
.stTextInput input {
    background:var(--card2)!important; border:1px solid var(--border)!important;
    border-radius:9px!important; color:var(--text)!important;
    font-size:.9rem!important; transition:border-color .2s!important; }
.stTextInput input:focus { border-color:var(--blue)!important; }

.stButton > button {
    width:100%!important; background:linear-gradient(130deg,#0ea5e9,#0d9488)!important;
    color:white!important; border:none!important; border-radius:10px!important;
    padding:.65rem 1rem!important; font-size:.92rem!important; font-weight:600!important;
    cursor:pointer!important; transition:opacity .2s,transform .1s!important; margin-top:.3rem!important; }
.stButton > button:hover  { opacity:.9!important; transform:translateY(-1px)!important; }
.stButton > button:active { transform:translateY(0)!important; }

.loc-result {
    background:var(--card2); border:1px solid var(--border); border-radius:10px;
    padding:.8rem 1rem; font-size:.84rem; display:flex; align-items:flex-start; gap:.6rem;
    margin:.5rem 0 .4rem 0; }
.loc-result.success { border-color:rgba(74,222,128,.4); background:rgba(74,222,128,.05); }
.loc-result.error   { border-color:rgba(248,113,113,.4); background:rgba(248,113,113,.05); }
.loc-addr { font-weight:500; color:var(--text); line-height:1.45; }
.loc-coords { font-family:'Space Mono',monospace; font-size:.7rem; color:var(--muted); margin-top:.2rem; }

.err-box {
    background:rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.3);
    color:var(--red); border-radius:9px; padding:.65rem 1rem;
    font-size:.84rem; margin:.3rem 0; }
</style>
""", unsafe_allow_html=True)

# ─── Brand hero ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-hero">
    <span class="brand-icon">🌫️</span>
    <div class="brand-name">AQI EWS</div>
    <div class="brand-tagline">Early Warning System · Indore, Madhya Pradesh</div>
    <div class="aqi-pills">
        <span class="aqi-pill" style="background:rgba(74,222,128,.12);color:#4ade80;border:1px solid rgba(74,222,128,.3);">● Good 0–50</span>
        <span class="aqi-pill" style="background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.3);">● Moderate 51–200</span>
        <span class="aqi-pill" style="background:rgba(248,113,113,.12);color:#f87171;border:1px solid rgba(248,113,113,.3);">● Poor 201+</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Validators ───────────────────────────────────────────────────────────────
def valid_email(s):
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", s.strip()))

def valid_phone(s):
    return bool(re.match(r"^[6-9]\d{9}$", s.strip()))

# ─── GPS iframe ───────────────────────────────────────────────────────────────
GEO_COMPONENT = """
<!DOCTYPE html><html><head>
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:'DM Sans',sans-serif;background:transparent;display:flex;flex-direction:column;gap:7px;padding:1px;}
  button{width:100%;padding:10px 14px;background:linear-gradient(130deg,#0ea5e9,#0d9488);
         color:white;border:none;border-radius:9px;font-size:13px;font-weight:600;
         cursor:pointer;display:flex;align-items:center;justify-content:center;gap:7px;}
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
  var micro=a.building||a.residential||'';if(micro)p.push(micro);
  var area=a.neighbourhood||a.suburb||a.quarter||'';if(area)p.push(area);
  var zone=a.city_district||a.subdistrict||'';if(zone&&zone!==area)p.push(zone);
  var city=a.city||a.town||a.village||'';if(city)p.push(city);
  if(a.state)p.push(a.state);
  if(a.postcode)p.push(a.postcode);
  return p.filter(Boolean).join(', ');
}
function go(){
  var btn=document.getElementById('btn');
  if(!navigator.geolocation){ss('error','❌ Geolocation not supported.');return;}
  btn.disabled=true;btn.textContent='🔄 Detecting…';
  ss('loading','<span class="sp"></span>Waiting for GPS — allow location when prompted…');
  navigator.geolocation.getCurrentPosition(
    function(pos){
      var lat=pos.coords.latitude,lon=pos.coords.longitude,acc=Math.round(pos.coords.accuracy);
      ss('loading','<span class="sp"></span>GPS acquired ('+acc+'m) · Resolving address…');
      fetch('https://nominatim.openstreetmap.org/reverse?lat='+lat+'&lon='+lon
            +'&format=json&zoom=18&addressdetails=1&accept-language=en',
            {headers:{'User-Agent':'AQIEWS/1.0'}})
        .then(function(r){return r.json();})
        .then(function(d){
          var addr=buildAddr(d.address||{})||d.display_name||(lat.toFixed(5)+', '+lon.toFixed(5));
          ss('success','<div class="addr">📍 '+addr+'</div><div class="coord">🛰 '+lat.toFixed(6)+', '+lon.toFixed(6)+' · accuracy: '+acc+'m</div>');
          btn.textContent='✅ Location Detected';btn.disabled=false;
          window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'success',address:addr,lat:lat.toFixed(6),lon:lon.toFixed(6),acc:acc}},'*');
        })
        .catch(function(){
          var fb=lat.toFixed(5)+', '+lon.toFixed(5);
          ss('success','<div class="addr">📍 '+fb+'</div>');
          btn.textContent='✅ Location Detected';btn.disabled=false;
          window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'success',address:fb,lat:lat.toFixed(6),lon:lon.toFixed(6),acc:acc}},'*');
        });
    },
    function(err){
      btn.disabled=false;btn.textContent='📍 Detect My Location';
      var m={1:'❌ Permission denied.',2:'❌ Position unavailable.',3:'❌ Timed out.'};
      ss('error',m[err.code]||'❌ '+err.message);
      window.parent.postMessage({type:'streamlit:setComponentValue',value:{status:'denied',address:'',lat:'',lon:''}},'*');
    },
    {enableHighAccuracy:true,timeout:15000,maximumAge:0}
  );
}
</script></body></html>
"""

# ─── Mode switcher ────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)
with col_l:
    if st.button("🔑 Sign In", use_container_width=True,
                 type="primary" if st.session_state.mode == "login" else "secondary"):
        st.session_state.mode = "login"; st.rerun()
with col_r:
    if st.button("📝 Register", use_container_width=True,
                 type="primary" if st.session_state.mode == "register" else "secondary"):
        st.session_state.mode = "register"; st.rerun()

st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "login":
    with st.form("login_form"):
        st.markdown("<div style='font-size:.95rem;font-weight:600;margin-bottom:1.1rem;'>Welcome back</div>",
                    unsafe_allow_html=True)
        contact  = st.text_input("Email or Mobile Number", placeholder="yourname@email.com  or  9876543210")
        password = st.text_input("Password", type="password", placeholder="Your password")
        submitted = st.form_submit_button("Sign In →", use_container_width=True)

    if submitted:
        if not contact.strip() or not password.strip():
            st.markdown('<div class="err-box">⚠️ Please fill in all fields.</div>', unsafe_allow_html=True)
        else:
            with st.spinner("Signing in…"):
                # backend_login stores token + user info in session_state, shows error on failure
                if backend_login(contact.strip(), password):
                    st.switch_page("pages/dashboard.py")

    st.markdown("""
    <div style='text-align:center;margin-top:1.2rem;font-size:.82rem;color:#4b5a72;'>
        New to AQI-EWS? Click <b style="color:#38bdf8;">Register</b> above to create an account.
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════════════════════════
else:
    # ── Location method toggle ────────────────────────────────────────────────
    st.markdown("""<div style='font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;
         color:#4b5a72;margin:.3rem 0 .5rem 0;'>📍 Location Access</div>""", unsafe_allow_html=True)

    if "loc_method" not in st.session_state:
        st.session_state.loc_method = "gps"

    loc_col1, loc_col2 = st.columns(2)
   
    # ── GPS section ───────────────────────────────────────────────────────────
    if st.session_state.loc_method == "gps":
        st.markdown("""<div style='font-size:.75rem;color:#4b5a72;background:#0f1623;
             border:1px solid #1a2540;border-radius:8px;padding:.6rem .9rem;margin-bottom:.5rem;line-height:1.55;'>
            🔒 Your browser will ask for location permission. GPS gives
            <b style="color:#dde3ef;">street-level accuracy</b>.
            Location is only used to find your nearest AQI station.</div>""", unsafe_allow_html=True)

        if st.session_state.gps_address:
            st.markdown(f"""<div class="loc-result success">
                <span style="font-size:1.2rem">✅</span>
                <div>
                    <div class="loc-addr">{st.session_state.gps_address}</div>
                    <div class="loc-coords">🛰 {st.session_state.gps_lat},  {st.session_state.gps_lon}</div>
                </div></div>""", unsafe_allow_html=True)
            if st.button("🔄 Re-detect Location", key="btn_redetect"):
                st.session_state.gps_address = ""; st.session_state.gps_lat = ""
                st.session_state.gps_lon = ""; st.session_state.loc_fetched = False; st.rerun()
        else:
            geo_result = components.html(GEO_COMPONENT, height=115, scrolling=False)
            if geo_result and isinstance(geo_result, dict):
                status  = geo_result.get("status", "")
                address = geo_result.get("address", "").strip()
                if status == "success" and address and not st.session_state.loc_fetched:
                    st.session_state.gps_address = address
                    st.session_state.gps_lat     = str(geo_result.get("lat", ""))
                    st.session_state.gps_lon     = str(geo_result.get("lon", ""))
                    st.session_state.loc_fetched = True
                    st.rerun()
                elif status == "denied":
                    st.markdown("""<div class="loc-result error">
                        ❌ &nbsp; Location permission denied. Switch to <b>Enter Manually</b>.
                    </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style='font-size:.75rem;color:#4b5a72;margin-bottom:.4rem;'>
            Type your full address including street, area, and city.</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

    # ── Registration form ─────────────────────────────────────────────────────
    with st.form("register_form"):
        st.markdown("<div style='font-size:.95rem;font-weight:600;margin-bottom:1.1rem;'>Create your account</div>",
                    unsafe_allow_html=True)
        full_name = st.text_input("Full Name", placeholder="e.g. Ravi Sharma")
        contact   = st.text_input("Email or Mobile Number", placeholder="yourname@email.com  or  9876543210")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            password = st.text_input("Password", type="password", placeholder="Min. 6 characters")
        with col_p2:
            confirm  = st.text_input("Confirm Password", type="password", placeholder="Re-enter")
        st.markdown("""<div style='font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;
             color:#4b5a72;margin:.7rem 0 .3rem 0;'>📍 Address</div>""", unsafe_allow_html=True)
        addr_placeholder = ("e.g. 42 MG Road, Vijay Nagar, Indore, MP"
                            if st.session_state.loc_method == "manual"
                            else "Auto-filled from GPS — or edit here")
        manual_address = st.text_input("Your Address", value=st.session_state.gps_address,
                                       placeholder=addr_placeholder, label_visibility="collapsed")
        agree     = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button("Create Account →", use_container_width=True)

    if submitted:
        errors = []
        if not full_name.strip():                                   errors.append("Full name is required.")
        if not contact.strip():                                     errors.append("Email or phone is required.")
        elif not valid_email(contact) and not valid_phone(contact): errors.append("Enter a valid email or 10-digit Indian mobile number.")
        if len(password) < 6:                                       errors.append("Password must be at least 6 characters.")
        if password != confirm:                                     errors.append("Passwords do not match.")
        final_location = manual_address.strip() or st.session_state.gps_address
        if not final_location:                                      errors.append("Please provide your location.")
        if not agree:                                               errors.append("Please accept the Terms of Service.")

        if errors:
            for e in errors:
                st.markdown(f'<div class="err-box">⚠️ {e}</div>', unsafe_allow_html=True)
        else:
            with st.spinner("Creating your account…"):
                if backend_register(
                    full_name.strip(), contact.strip(), password,
                    final_location or "Indore, MP",
                    st.session_state.gps_lat, st.session_state.gps_lon,
                ):
                    st.switch_page("pages/dashboard.py")