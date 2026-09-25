"""
AQI Sentinel — Login / Registration Page
Run with: streamlit run login.py
"""

import streamlit as st
import streamlit.components.v1 as components
import re

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AQI Sentinel · Sign In",
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

/* Inputs */
.stTextInput > label, .stSelectbox > label {
    font-size:.78rem!important; text-transform:uppercase!important;
    letter-spacing:.1em!important; color:var(--muted)!important; margin-bottom:.3rem!important;
}
.stTextInput input {
    background:var(--card2)!important; border:1px solid var(--border)!important;
    border-radius:9px!important; color:var(--text)!important;
    font-size:.9rem!important; transition:border-color .2s!important;
}
.stTextInput input:focus { border-color:var(--blue)!important; }

/* Buttons */
.stButton > button {
    width:100%!important; background:linear-gradient(130deg,#0ea5e9,#0d9488)!important;
    color:white!important; border:none!important; border-radius:10px!important;
    padding:.65rem 1rem!important; font-size:.92rem!important; font-weight:600!important;
    cursor:pointer!important; transition:opacity .2s,transform .1s!important; margin-top:.3rem!important;
}
.stButton > button:hover  { opacity:.9!important; transform:translateY(-1px)!important; }
.stButton > button:active { transform:translateY(0)!important; }

/* Location result box */
.loc-result {
    background:var(--card2); border:1px solid var(--border); border-radius:10px;
    padding:.8rem 1rem; font-size:.84rem; display:flex; align-items:flex-start; gap:.6rem;
    margin:.5rem 0 .4rem 0;
}
.loc-result.success { border-color:rgba(74,222,128,.4); background:rgba(74,222,128,.05); }
.loc-result.error   { border-color:rgba(248,113,113,.4); background:rgba(248,113,113,.05); }
.loc-result.loading { border-color:rgba(56,189,248,.3);  background:rgba(56,189,248,.04); }
.loc-addr { font-weight:500; color:var(--text); line-height:1.45; }
.loc-coords { font-family:'Space Mono',monospace; font-size:.7rem; color:var(--muted); margin-top:.2rem; }

/* Divider */
.divider {
    display:flex; align-items:center; gap:.75rem; margin:1rem 0;
    color:var(--muted); font-size:.76rem;
}
.divider::before,.divider::after { content:''; flex:1; height:1px; background:var(--border); }

/* Banners */
.err-box {
    background:rgba(248,113,113,.08); border:1px solid rgba(248,113,113,.3);
    border-radius:8px; padding:.65rem .9rem; color:var(--red); font-size:.83rem; margin-bottom:.6rem;
}
.ok-box {
    background:rgba(74,222,128,.08); border:1px solid rgba(74,222,128,.3);
    border-radius:8px; padding:.65rem .9rem; color:var(--green); font-size:.83rem; margin-bottom:.6rem;
}
.auth-footer { text-align:center; font-size:.73rem; color:var(--muted); margin-top:1.2rem; line-height:1.6; }
.auth-footer a { color:var(--blue); text-decoration:none; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ─────────────────────────────────────────────────────────────────
def valid_email(e):
    return re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", e.strip()) is not None

def valid_phone(p):
    return re.match(r"^[6-9]\d{9}$", p.strip()) is not None



# ─── Geolocation iframe component ────────────────────────────────────────────
# This is the ONLY reliable way to access browser GPS from Streamlit.
# The iframe posts the coordinates back to the parent via postMessage,
# which Streamlit's component system captures as a return value.
GEO_COMPONENT = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: 'DM Sans', sans-serif;
    background: transparent;
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 2px;
  }
  button {
    width: 100%;
    padding: 11px 16px;
    background: linear-gradient(130deg, #0ea5e9, #0d9488);
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: opacity .2s;
  }
  button:hover    { opacity: 0.88; }
  button:disabled { opacity: 0.55; cursor: not-allowed; }
  #status {
    font-size: 12.5px;
    padding: 10px 13px;
    border-radius: 8px;
    border: 1px solid #1a2540;
    background: #141e2e;
    color: #94a3b8;
    display: none;
    line-height: 1.6;
  }
  #status.show    { display: block; }
  #status.loading { border-color: rgba(56,189,248,.4);  color: #38bdf8; }
  #status.success { border-color: rgba(74,222,128,.4);  color: #4ade80; background: rgba(74,222,128,.05); }
  #status.error   { border-color: rgba(248,113,113,.4); color: #f87171; background: rgba(248,113,113,.05); }
  .addr-line { color: #dde3ef; font-size: 13px; font-weight: 600; margin-bottom: 3px; }
  .coord-line { font-family: monospace; font-size: 10.5px; opacity: .55; }
  .spinner {
    display: inline-block;
    width: 11px; height: 11px;
    border: 2px solid rgba(56,189,248,.3);
    border-top-color: #38bdf8;
    border-radius: 50%;
    animation: spin .7s linear infinite;
    vertical-align: middle;
    margin-right: 4px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<button id="btn" onclick="startDetection()">
  📍 Detect My Exact Location
</button>
<div id="status"></div>

<script>
  function setStatus(cls, html) {
    var s = document.getElementById('status');
    s.className = 'show ' + cls;
    s.innerHTML = html;
  }

  function buildAddress(a) {
    /* Build a clean, human-readable address from Nominatim address fields.
       Priority order matches how Google Maps displays addresses. */
    var parts = [];

    // House / plot number
    if (a.house_number)   parts.push(a.house_number);

    // Street / road
    var road = a.road || a.pedestrian || a.footway || a.path || '';
    if (road) parts.push(road);

    // Micro-area: named complex, society, building
    var micro = a.building || a.residential || '';
    if (micro) parts.push(micro);

    // Neighbourhood / colony / mohalla
    var area = a.neighbourhood || a.suburb || a.quarter || a.hamlet || '';
    if (area) parts.push(area);

    // Sub-district / zone
    var zone = a.city_district || a.subdistrict || '';
    if (zone && zone !== area) parts.push(zone);

    // City / town / village
    var city = a.city || a.town || a.village || a.county || '';
    if (city) parts.push(city);

    // State
    if (a.state) parts.push(a.state);

    // Pincode
    if (a.postcode) parts.push(a.postcode);

    return parts.filter(Boolean).join(', ');
  }

  function startDetection() {
    var btn = document.getElementById('btn');

    if (!navigator.geolocation) {
      setStatus('error', '❌ Geolocation not supported by your browser.');
      return;
    }

    btn.disabled = true;
    btn.textContent = '🔄 Detecting…';
    setStatus('loading', '<span class="spinner"></span> Waiting for GPS signal — please allow location when prompted…');

    navigator.geolocation.getCurrentPosition(
      function(pos) {
        var lat = pos.coords.latitude;
        var lon = pos.coords.longitude;
        var acc = Math.round(pos.coords.accuracy);

        setStatus('loading',
          '<span class="spinner"></span> GPS acquired (' + acc + 'm accuracy) · Resolving address…'
        );

        /* ── Reverse geocode via Nominatim (free, no key, street-level) ── */
        var url = 'https://nominatim.openstreetmap.org/reverse'
                + '?lat=' + lat
                + '&lon=' + lon
                + '&format=json'
                + '&zoom=18'          /* zoom=18 → building level */
                + '&addressdetails=1'
                + '&accept-language=en';

        fetch(url, { headers: { 'User-Agent': 'AQISentinel/1.0' } })
          .then(function(r) { return r.json(); })
          .then(function(data) {
            var a       = data.address || {};
            var address = buildAddress(a);

            if (!address) address = data.display_name || (lat.toFixed(5) + ', ' + lon.toFixed(5));

            /* Show resolved address in the iframe */
            setStatus('success',
              '<div class="addr-line">📍 ' + address + '</div>' +
              '<div class="coord-line">🛰 ' + lat.toFixed(6) + ', ' + lon.toFixed(6) +
              ' &nbsp;·&nbsp; accuracy: ' + acc + 'm</div>'
            );

            btn.textContent = '✅ Location Detected';
            btn.disabled = false;

            /* Send clean address string + coords back to Python */
            window.parent.postMessage({
              type:  'streamlit:setComponentValue',
              value: {
                status:  'success',
                address: address,
                lat:     lat.toFixed(6),
                lon:     lon.toFixed(6),
                acc:     acc
              }
            }, '*');
          })
          .catch(function(err) {
            /* Nominatim failed — still send raw coords, Python will handle */
            var fallback = lat.toFixed(5) + ', ' + lon.toFixed(5);
            setStatus('success',
              '<div class="addr-line">📍 ' + fallback + '</div>' +
              '<div class="coord-line">Address lookup failed — coordinates saved</div>'
            );
            btn.textContent = '✅ Location Detected';
            btn.disabled = false;
            window.parent.postMessage({
              type:  'streamlit:setComponentValue',
              value: { status: 'success', address: fallback, lat: lat.toFixed(6), lon: lon.toFixed(6), acc: acc }
            }, '*');
          });
      },
      function(err) {
        btn.disabled = false;
        btn.textContent = '📍 Detect My Exact Location';
        var msgs = {
          1: '❌ Permission denied — click Allow when your browser asks, then try again.',
          2: '❌ Position unavailable — ensure GPS/location is enabled on your device.',
          3: '❌ Timed out — GPS signal too weak indoors. Try near a window or enter manually.',
        };
        setStatus('error', msgs[err.code] || '❌ Error: ' + err.message);
        window.parent.postMessage({
          type:  'streamlit:setComponentValue',
          value: { status: 'denied', address: '', lat: '', lon: '', acc: 0 }
        }, '*');
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  }
</script>
</body>
</html>
"""

# ─── Brand Hero ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="brand-hero">
    <span class="brand-icon">🌫️</span>
    <div class="brand-name">AQI Sentinel</div>
    <div class="brand-tagline">Real-time air quality intelligence · Indore, Madhya Pradesh</div>
    <div class="aqi-pills">
        <span class="aqi-pill" style="background:rgba(74,222,128,.12);color:#4ade80;border:1px solid rgba(74,222,128,.3);">Good 0–50</span>
        <span class="aqi-pill" style="background:rgba(251,191,36,.12);color:#fbbf24;border:1px solid rgba(251,191,36,.3);">Moderate 100–200</span>
        <span class="aqi-pill" style="background:rgba(248,113,113,.12);color:#f87171;border:1px solid rgba(248,113,113,.3);">Severe 400+</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Mode switcher ────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)
with col_l:
    if st.button("Sign In", key="btn_mode_login", use_container_width=True):
        st.session_state.mode = "login"
        st.rerun()
with col_r:
    if st.button("Create Account", key="btn_mode_reg", use_container_width=True):
        st.session_state.mode = "register"
        st.rerun()

st.markdown("<div style='height:.15rem'></div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  LOGIN
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.mode == "login":

    with st.form("login_form"):
        st.markdown("<div style='font-size:.95rem;font-weight:600;margin-bottom:1.1rem;'>Welcome back 👋</div>", unsafe_allow_html=True)
        email_or_phone = st.text_input("Email or Phone Number", placeholder="yourname@email.com  or  9876543210")
        password       = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted      = st.form_submit_button("Sign In →", use_container_width=True)

    if submitted:
        if not email_or_phone or not password:
            st.markdown('<div class="err-box">⚠️ Please fill in all fields.</div>', unsafe_allow_html=True)
        elif len(password) < 6:
            st.markdown('<div class="err-box">⚠️ Password must be at least 6 characters.</div>', unsafe_allow_html=True)
        else:
            st.session_state.authenticated = True
            st.session_state.user_name     = email_or_phone.split("@")[0].replace(".", " ").title()
            st.session_state.user_email    = email_or_phone
            st.session_state.user_location = st.session_state.gps_address or "Indore, MP"
            st.switch_page("pages/dashboard.py")

    st.markdown('<div class="divider">or</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="auth-footer">
        Forgot password? <a href="#">Reset it here</a><br>
        Don't have an account? Click <b>Create Account</b> above.
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
#  REGISTER
# ════════════════════════════════════════════════════════════════════════════════
else:

    # ── Location method toggle (outside form so it can control what renders) ──
    st.markdown("""
    <div style='font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;
         color:#4b5a72;margin:.3rem 0 .5rem 0;'>📍 Location Access</div>
    """, unsafe_allow_html=True)

    # Styled two-option toggle using columns
    loc_col1, loc_col2 = st.columns(2)

    if "loc_method" not in st.session_state:
        st.session_state.loc_method = "gps"   # default to GPS

    with loc_col1:
        gps_active = st.session_state.loc_method == "gps"
        gps_style  = (
            "background:rgba(56,189,248,.12);border:1.5px solid rgba(56,189,248,.5);color:#38bdf8;"
            if gps_active else
            "background:#0f1623;border:1px solid #1a2540;color:#4b5a72;"
        )
        st.markdown(f"""
        <div style='{gps_style} border-radius:9px; padding:.6rem .9rem;
             text-align:center; font-size:.84rem; font-weight:600;
             cursor:pointer; transition:all .2s;'>
            📡 Auto-detect GPS
        </div>""", unsafe_allow_html=True)
        if st.button("📡 Use GPS", key="btn_gps", use_container_width=True):
            st.session_state.loc_method  = "gps"
            st.session_state.loc_fetched = False   # allow re-fetch
            st.rerun()

    with loc_col2:
        man_active = st.session_state.loc_method == "manual"
        man_style  = (
            "background:rgba(45,212,191,.12);border:1.5px solid rgba(45,212,191,.5);color:#2dd4bf;"
            if man_active else
            "background:#0f1623;border:1px solid #1a2540;color:#4b5a72;"
        )
        st.markdown(f"""
        <div style='{man_style} border-radius:9px; padding:.6rem .9rem;
             text-align:center; font-size:.84rem; font-weight:600;
             cursor:pointer; transition:all .2s;'>
            ✏️ Enter Manually
        </div>""", unsafe_allow_html=True)
        if st.button("✏️ Enter Manually", key="btn_manual", use_container_width=True):
            st.session_state.loc_method = "manual"
            st.rerun()

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    # ── GPS mode ─────────────────────────────────────────────────────────────
    if st.session_state.loc_method == "gps":

        # Info note
        st.markdown("""
        <div style='font-size:.75rem;color:#4b5a72;
             background:#0f1623;border:1px solid #1a2540;border-radius:8px;
             padding:.6rem .9rem;margin-bottom:.5rem;line-height:1.55;'>
            🔒 Your browser will ask for location permission. GPS gives
            <b style="color:#dde3ef;">street-level accuracy</b> (house number + road).
            Location is only used to find your nearest AQI station.
        </div>""", unsafe_allow_html=True)

        # Show already-resolved address
        if st.session_state.gps_address:
            st.markdown(f"""
            <div class="loc-result success">
                <span style="font-size:1.2rem">✅</span>
                <div>
                    <div class="loc-addr">{st.session_state.gps_address}</div>
                    <div class="loc-coords">🛰 {st.session_state.gps_lat},  {st.session_state.gps_lon}</div>
                </div>
            </div>""", unsafe_allow_html=True)

            # Allow re-detection
            if st.button("🔄 Re-detect Location", key="btn_redetect"):
                st.session_state.gps_address = ""
                st.session_state.gps_lat     = ""
                st.session_state.gps_lon     = ""
                st.session_state.loc_fetched = False
                st.rerun()
        else:
            # Render the GPS iframe component
            geo_result = components.html(GEO_COMPONENT, height=115, scrolling=False)

            if geo_result and isinstance(geo_result, dict):
                status  = geo_result.get("status", "")
                address = geo_result.get("address", "").strip()
                lat     = geo_result.get("lat", "")
                lon     = geo_result.get("lon", "")

                if status == "success" and address and not st.session_state.loc_fetched:
                    # Address already resolved by JS/Nominatim — save directly
                    st.session_state.gps_address = address
                    st.session_state.gps_lat     = str(lat)
                    st.session_state.gps_lon     = str(lon)
                    st.session_state.loc_fetched = True
                    st.rerun()

                elif status == "denied":
                    st.markdown("""
                    <div class="loc-result error">
                        ❌ &nbsp; Location permission denied. Switch to
                        <b>Enter Manually</b> above to type your address.
                    </div>""", unsafe_allow_html=True)

    # ── Manual mode ───────────────────────────────────────────────────────────
    else:
        st.markdown("""
        <div style='font-size:.75rem;color:#4b5a72;margin-bottom:.4rem;'>
            Type your full address including street, area, and city.
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

    # ── Main registration form ────────────────────────────────────────────────
    with st.form("register_form"):
        st.markdown("<div style='font-size:.95rem;font-weight:600;margin-bottom:1.1rem;'>Create your account</div>", unsafe_allow_html=True)

        full_name = st.text_input("Full Name", placeholder="e.g. Ravi Sharma")
        contact   = st.text_input("Email or Mobile Number", placeholder="yourname@email.com  or  9876543210")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            password = st.text_input("Password", type="password", placeholder="Min. 8 characters")
        with col_p2:
            confirm  = st.text_input("Confirm Password", type="password", placeholder="Re-enter")

        st.markdown("""
        <div style='font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;
             color:#4b5a72;margin:.7rem 0 .3rem 0;'>📍 Address</div>
        """, unsafe_allow_html=True)

        addr_placeholder = (
            "e.g. 42 MG Road, Vijay Nagar, Indore, MP"
            if st.session_state.loc_method == "manual"
            else "Auto-filled from GPS — or edit here"
        )
        manual_address = st.text_input(
            "Your Address",
            value=st.session_state.gps_address,
            placeholder=addr_placeholder,
            label_visibility="collapsed",
        )

        agree     = st.checkbox("I agree to the Terms of Service and Privacy Policy")
        submitted = st.form_submit_button("Create Account →", use_container_width=True)

    # ── Submission handler ────────────────────────────────────────────────────
    if submitted:
        errors = []
        if not full_name.strip():
            errors.append("Full name is required.")
        if not contact.strip():
            errors.append("Email or phone number is required.")
        elif not valid_email(contact) and not valid_phone(contact):
            errors.append("Enter a valid email or 10-digit Indian mobile number.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if not manual_address.strip():
            errors.append("Please provide your location — use GPS or enter manually.")
        if not agree:
            errors.append("Please accept the Terms of Service to continue.")

        if errors:
            for e in errors:
                st.markdown(f'<div class="err-box">⚠️ {e}</div>', unsafe_allow_html=True)
        else:
            final_location = manual_address.strip() or st.session_state.gps_address or "Indore, MP"
            st.session_state.authenticated = True
            st.session_state.user_name     = full_name.strip().split()[0].capitalize()
            st.session_state.user_email    = contact.strip()
            st.session_state.user_location = final_location
            st.markdown(f'<div class="ok-box">✅ Welcome, {full_name.split()[0]}! Redirecting…</div>', unsafe_allow_html=True)
            st.switch_page("pages/dashboard.py")

    st.markdown("""
    <div class="auth-footer">
        Already have an account? Click <b>Sign In</b> above.
    </div>""", unsafe_allow_html=True)