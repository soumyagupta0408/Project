# AQI Sentinel — Python + MySQL Backend

FastAPI backend for the AQI Sentinel Streamlit dashboard.

## Tech Stack

| Layer        | Technology                          |
|-------------|--------------------------------------|
| Framework   | FastAPI 0.111                        |
| ORM         | SQLAlchemy 2.0                       |
| Migrations  | Alembic                              |
| Database    | MySQL 8+ (via PyMySQL driver)        |
| Auth        | JWT (python-jose) + bcrypt passwords |
| HTTP client | httpx (async CPCB API calls)         |
| Python      | 3.8+                                 |

---

## Project Structure

```
aqi_sentinel_backend/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   └── security.py          # Password hashing + JWT
│   ├── db/
│   │   └── session.py           # Engine + SessionLocal + Base
│   ├── models/
│   │   ├── user.py              # users table
│   │   ├── alert.py             # alert_logs table
│   │   └── aqi_reading.py       # aqi_readings table (cache)
│   ├── schemas/
│   │   ├── auth.py              # Register / Login / TokenResponse
│   │   └── aqi.py               # AQIResponse / AlertLogOut
│   ├── services/
│   │   ├── user_service.py      # User CRUD + auth
│   │   ├── aqi_service.py       # CPCB fetch + DB cache logic
│   │   └── alert_service.py     # Alert log CRUD
│   └── api/
│       ├── deps.py              # Auth dependency (get_current_user)
│       └── routes/
│           ├── auth.py          # /api/auth/*
│           ├── aqi.py           # /api/aqi/*
│           └── users.py         # /api/users/*
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py      # Creates all 3 tables
├── backend_client.py            # Drop into Streamlit project
├── alembic.ini
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Create MySQL database

```sql
CREATE DATABASE aqi_sentinel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aqi_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON aqi_sentinel.* TO 'aqi_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in DB_PASSWORD, SECRET_KEY, DATA_GOV_API_KEY
```

Generate a secure SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Install dependencies

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run database migrations

```bash
# Apply the initial migration (creates all tables)
alembic upgrade head

# Future schema changes — auto-generate a new migration:
alembic revision --autogenerate -m "add column X"
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now live at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

---

## API Endpoints

### Auth
| Method | URL                   | Auth | Description              |
|--------|-----------------------|------|--------------------------|
| POST   | `/api/auth/register`  | ❌   | Create account           |
| POST   | `/api/auth/login`     | ❌   | Get JWT token            |
| GET    | `/api/auth/me`        | ✅   | Current user profile     |

### AQI Data
| Method | URL                        | Auth | Description                        |
|--------|----------------------------|------|------------------------------------|
| GET    | `/api/aqi/{city}`          | ✅   | Live AQI (cached in DB, 5 min TTL) |
| GET    | `/api/aqi/{city}/history`  | ✅   | Historical readings from DB        |

### Users & Alerts
| Method | URL                          | Auth | Description               |
|--------|------------------------------|------|---------------------------|
| PATCH  | `/api/users/me/threshold`    | ✅   | Update alert threshold     |
| GET    | `/api/users/me/alerts`       | ✅   | List alert history         |
| POST   | `/api/users/me/alerts`       | ✅   | Log a threshold breach     |

---

## Connecting to Streamlit

Copy `backend_client.py` into your Streamlit project root, then:

**In `login.py`** — replace the mock login/register handlers:
```python
from backend_client import backend_login, backend_register

# In login form submitted block:
if backend_login(email_or_phone, password):
    st.switch_page("pages/dashboard.py")

# In register form submitted block:
if backend_register(full_name, contact, password, manual_address,
                    st.session_state.gps_lat, st.session_state.gps_lon):
    st.switch_page("pages/dashboard.py")
```

**In `dashboard.py`** — replace `get_aqi_data()`:
```python
from backend_client import BackendClient

@st.cache_data(ttl=300, show_spinner=False)
def get_aqi_data():
    client = BackendClient(token=st.session_state.get("token"))
    data = client.get_aqi("indore")
    if data and data["readings"]:
        return data["readings"], None
    return None, "no_data"
```

---

## Database Schema

### `users`
| Column           | Type         | Notes                        |
|------------------|--------------|------------------------------|
| id               | INT PK       | Auto-increment               |
| full_name        | VARCHAR(120) |                              |
| email            | VARCHAR(180) | Unique, nullable             |
| phone            | VARCHAR(15)  | Unique, nullable             |
| hashed_password  | VARCHAR(255) | bcrypt                       |
| address          | TEXT         | From GPS or manual entry     |
| latitude         | VARCHAR(20)  |                              |
| longitude        | VARCHAR(20)  |                              |
| alert_threshold  | INT          | Default 150                  |
| is_active        | BOOL         | Soft-delete flag             |
| created_at       | DATETIME     |                              |
| updated_at       | DATETIME     | Auto-updated on save         |

### `alert_logs`
| Column       | Type        | Notes                     |
|--------------|-------------|---------------------------|
| id           | INT PK      |                           |
| user_id      | INT FK      | → users.id (CASCADE)      |
| station      | VARCHAR(120)|                           |
| pollutant    | VARCHAR(20) | PM2.5, PM10, NO2 …        |
| aqi_value    | FLOAT       |                           |
| threshold    | INT         | User's threshold at time  |
| severity     | VARCHAR(20) | Low / Moderate / High     |
| message      | TEXT        |                           |
| triggered_at | DATETIME    | Indexed                   |

### `aqi_readings`
| Column        | Type        | Notes                       |
|---------------|-------------|-----------------------------|
| id            | INT PK      |                             |
| city          | VARCHAR(80) | Indexed                     |
| station       | VARCHAR(160)|                             |
| pollutant_id  | VARCHAR(20) | PM2.5, PM10 …               |
| pollutant_min | FLOAT       |                             |
| pollutant_max | FLOAT       |                             |
| pollutant_avg | FLOAT       |                             |
| unit          | VARCHAR(20) | µg/m³                       |
| recorded_at   | DATETIME    | From CPCB API, indexed      |
| fetched_at    | DATETIME    | When we cached it           |

Unique constraint: `(city, station, pollutant_id, recorded_at)`

---

## Production Notes

- Set `APP_ENV=production` in `.env` to disable SQLAlchemy echo logging
- Use `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app` instead of `uvicorn --reload`
- Store `.env` securely — never commit it to git (it's already in `.gitignore`)
- The `DATA_GOV_API_KEY` never leaves the backend — the Streamlit frontend never sees it
