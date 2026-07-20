"""
backend_client.py
Drop this file into your Streamlit project root.
"""

import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("API_URL","http://localhost:8000")   # change to production URL when deployed


class BackendClient:
    def __init__(self, token: str | None = None):
        self.base  = BACKEND_URL.rstrip("/")
        self.token = token

    def _auth_headers(self) -> dict:
        """Headers WITH Bearer token — for protected endpoints."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ── Auth ──────────────────────────────────────────────────────────────────

    def register(self, full_name, contact, password,
                 address="", latitude="", longitude=""):
        r = requests.post(
            f"{self.base}/api/auth/register",
            json={
                "full_name":  full_name,
                "contact":    contact,
                "password":   password,
                "address":    address or None,
                "latitude":   latitude or None,
                "longitude":  longitude or None,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def login(self, contact, password):
        r = requests.post(
            f"{self.base}/api/auth/login",
            json={"contact": contact, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    # ── AQI  (PUBLIC — no auth required) ─────────────────────────────────────

    def get_aqi(self, city: str = "indore") -> dict | None:
        """
        Fetch latest AQI for a city.
        Tries WITHOUT auth first (public access).
        Falls back to authenticated request if the route requires a token.
        Returns None only if the backend is unreachable or returns an error.
        """
        url = f"{self.base}/api/aqi/{city}"
        try:
            # Attempt 1: no auth header (works if route is public)
            r = requests.get(url, timeout=12)
            if r.status_code == 401 or r.status_code == 403:
                # Route requires auth — retry with token
                r = requests.get(url, headers=self._auth_headers(), timeout=12)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def get_aqi_history(self, city: str = "indore",
                        pollutant: str | None = None,
                        limit: int = 100) -> list[dict]:
        """
        Fetch historical AQI readings.
        Same public-first, auth-fallback strategy as get_aqi.
        """
        url    = f"{self.base}/api/aqi/{city}/history"
        params = {"limit": limit}
        if pollutant:
            params["pollutant"] = pollutant
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 401 or r.status_code == 403:
                r = requests.get(url, headers=self._auth_headers(),
                                 params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []

    # ── All Stations  (PUBLIC — no auth required) ──────────────────────────────

    def get_all_stations(self) -> dict | None:
        """Fetch real AQI for all CPCB monitoring stations in Indore."""
        url = f"{self.base}/api/aqi/indore/stations"
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    # ── Alerts  (PROTECTED — always needs auth) ───────────────────────────────

    def get_alerts(self, limit: int = 50) -> list[dict]:
        try:
            r = requests.get(
                f"{self.base}/api/users/me/alerts",
                headers=self._auth_headers(),
                params={"limit": limit},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return []

    def log_alert(self, station, pollutant, aqi_value) -> dict | None:
        try:
            r = requests.post(
                f"{self.base}/api/users/me/alerts",
                headers=self._auth_headers(),
                json={"station": station, "pollutant": pollutant,
                      "aqi_value": aqi_value},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    def update_threshold(self, threshold: int) -> dict | None:
        try:
            r = requests.patch(
                f"{self.base}/api/users/me/threshold",
                headers=self._auth_headers(),
                json={"threshold": threshold},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return None


# ── Streamlit-aware wrappers ──────────────────────────────────────────────────

def backend_login(contact: str, password: str) -> bool:
    client = BackendClient()
    try:
        data = client.login(contact, password)
        st.session_state.token         = data["access_token"]
        st.session_state.authenticated = True
        st.session_state.user_name     = data.get("user_name", "")
        st.session_state.user_email    = data.get("user_email") or data.get("user_phone", "")
        st.session_state.user_location = data.get("user_location") or "Indore, MP"
        # Set GPS coords from user's registered location
        if data.get("user_latitude") and data.get("user_longitude"):
            st.session_state.gps_lat     = str(data["user_latitude"])
            st.session_state.gps_lon     = str(data["user_longitude"])
            st.session_state.gps_address = data.get("user_location") or ""
            st.session_state.loc_fetched = True
        return True
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            st.error("Invalid credentials. Please check your email/phone and password.")
        else:
            st.error(f"Login failed: {e}")
        return False
    except requests.ConnectionError:
        st.error("Cannot reach the backend. Is the FastAPI server running on localhost:8000?")
        return False


def backend_register(full_name, contact, password,
                     address="", latitude="", longitude="") -> bool:
    client = BackendClient()
    try:
        data = client.register(full_name, contact, password,
                               address, latitude, longitude)
        st.session_state.token         = data["access_token"]
        st.session_state.authenticated = True
        st.session_state.user_name     = data.get("user_name", full_name.split()[0])
        st.session_state.user_email    = data.get("user_email") or data.get("user_phone", "")
        st.session_state.user_location = (data.get("user_location")
                                          or address or "Indore, MP")
        # Set GPS coords from registration location
        user_lat = data.get("user_latitude") or latitude
        user_lon = data.get("user_longitude") or longitude
        if user_lat and user_lon:
            st.session_state.gps_lat     = str(user_lat)
            st.session_state.gps_lon     = str(user_lon)
            st.session_state.gps_address = address or data.get("user_location") or ""
            st.session_state.loc_fetched = True
        return True
    except requests.HTTPError as e:
        if e.response is not None:
            detail = e.response.json().get("detail", str(e))
            st.error(f"Registration failed: {detail}")
        else:
            st.error(f"Registration failed: {e}")
        return False
    except requests.ConnectionError:
        st.error("Cannot reach the backend. Is the FastAPI server running on localhost:8000?")
        return False