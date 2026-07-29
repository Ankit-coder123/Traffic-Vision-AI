# TrafficVision AI

A smart traffic prediction and congestion management platform for Bangalore — a full-stack portfolio project covering authentication, live traffic monitoring, AI-driven congestion prediction, route optimization, and incident reporting.

This single README documents the whole project, organized milestone by milestone, covering both the backend (FastAPI) and frontend (React) in one place.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, JWT (python-jose), passlib + bcrypt, python-dotenv |
| ML | scikit-learn (RandomForest), pandas, joblib |
| Routing | OSRM (Open Source Routing Machine) + OpenStreetMap — free, no API key |
| Frontend | React (Vite), Tailwind CSS, Axios, React Router, Leaflet / react-leaflet |
| Tooling | Custom Python data simulator standing in for real traffic sensors |

---

## Project Structure

```
TrafficVision-AI/
├── backend/
│   ├── app/
│   │   ├── main.py                 # App entrypoint, CORS, router registration
│   │   ├── database.py             # PostgreSQL connection (env-based config)
│   │   ├── models.py               # SQLAlchemy ORM models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── security.py             # JWT + password utilities (see note below on why this isn't named auth.py)
│   │   ├── congestion_model.joblib # Trained RandomForest model
│   │   ├── target_encoder.joblib
│   │   └── routers/
│   │       ├── auth.py             # signup/login HTTP endpoints
│   │       ├── traffic.py
│   │       ├── prediction.py
│   │       ├── routes.py
│   │       └── incidents.py
│   ├── simulator.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── api/client.js
│       ├── context/AuthContext.jsx
│       ├── components/ (NavBar, ProtectedRoute, ZoneCard)
│       └── pages/ (Login, Signup, Dashboard, Prediction, Routes, Incidents)
├── ml/                              # Model training pipeline (see Milestone 2)
├── docs/ARCHITECTURE.md             # Full DB schema + design notes
└── README.md                        # you are here
```

---

## A note on `security.py` (formerly a duplicate `auth.py`)

Earlier in development, both the JWT/password utilities file and the router file were named `auth.py` (one at `backend/app/auth.py`, the other at `backend/app/routers/auth.py`). Despite being two genuinely different files, this identical naming repeatedly led to their contents getting mixed up during editing — the same bug recurring across many sessions:
```
AttributeError: module 'app.auth' has no attribute 'get_current_user'
```

**Permanent fix**: `backend/app/auth.py` was renamed to `backend/app/security.py`, and every router (`auth.py`, `traffic.py`, `prediction.py`, `routes.py`, `incidents.py`) was updated to `from app import security` and call `security.hash_password(...)`, `security.get_current_user`, etc. There is now only **one** file named `auth.py` in the whole project (the router), so this entire class of mistake is no longer possible.

If you're working from an older clone, delete `app/auth.py` and add `app/security.py` with the content in the **Reference** section near the bottom of this document, then update the 5 router files' imports the same way.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+

---

## Milestone 1 (Week 1–2): Architecture, Auth & RBAC, Live Monitoring

**Delivered:**
- System architecture & PostgreSQL database schema design
- FastAPI backend with JWT authentication
- Role-based access control (originally admin/operator)
- Live traffic monitoring dashboard (React, polling every 5s)
- Congestion tracking workflow with a synthetic sensor data simulator

**Core tables introduced:** `users`, `traffic_zones`, `traffic_data`

**Core endpoints introduced:**

| Method | Endpoint | Access |
|---|---|---|
| POST | `/auth/signup` | Public |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Authenticated |
| POST | `/traffic/zones` | Admin only |
| GET | `/traffic/zones` | Authenticated |
| POST | `/traffic/data` | Authenticated |
| GET | `/traffic/live` | Authenticated |
| GET | `/traffic/history/{zone_id}` | Authenticated |

---

## Milestone 2 (Week 3–4): Congestion Prediction, Route Optimization, Roles, Incidents

**Delivered:**

1. **Dataset & model training** (`ml/` folder)
   - **Source:** [Smart Mobility Traffic Dataset](https://www.kaggle.com/datasets/ziya07/smart-mobility-traffic-dataset) (Kaggle, ziya07) — 5,000 records with vehicle counts, speed, road occupancy, traffic light state, weather, accident reports, sentiment, ride-sharing demand, parking availability, emissions, and energy consumption, labeled with a 3-class `Traffic_Condition` target (Low/Medium/High). Chosen over the platform's own simulator output because it includes external/contextual features (weather, accidents, sentiment) the simulator doesn't generate.
   - **Pipeline** (run in order from `ml/`): `01_explore_data.py` → `02_preprocess.py` → `03_train_model.py` → `04_train_production_model.py`. Place the downloaded CSV at `ml/data/smart_mobility_traffic.csv` first.
   - Full EDA — class distribution, correlation heatmap, feature importance (see `ml/eda/EDA_SUMMARY.md`)
   - Trained a RandomForest classifier; a **production-scoped** version (`04_train_production_model.py`) was retrained using only the features the live system can actually supply (vehicle count, speed, occupancy, weather, time) rather than the dataset's full feature set (which includes sentiment, emissions, ride-sharing demand — data this platform doesn't collect). Model artifacts: `congestion_model.joblib`, `target_encoder.joblib`, `weather_encoder.joblib` (copied into `backend/app/` for serving).
   - **Honest finding on accuracy**: ~99.9% accuracy on a held-out test split — unusually high for a real-world traffic task, and worth acknowledging directly. `Vehicle_Count`, `Road_Occupancy_%`, and `Traffic_Speed_kmh` alone account for ~83–90% of feature importance combined, while weather and time-of-day each contribute under 1.5%. This strongly suggests the dataset's `Traffic_Condition` label was generated as a near-deterministic function of those three columns rather than sourced from messy real-world observations — in genuinely noisy real-world data, 75–90% accuracy would be more typical and more trustworthy. **How to present this well**: frame the high accuracy as proof the modeling pipeline works correctly end-to-end (data loading → feature engineering → training → evaluation), while being upfront that validating against real-world or longer-running self-generated data is the natural next step for a more realistic figure.

2. **Congestion prediction API + UI**
   - `POST /predict/congestion` — takes vehicle count, speed, occupancy, weather, hour, weekday/weekend
   - `GET /predict/reports` — every prediction is logged as a report
   - Frontend `/prediction` page: sliders, weather dropdown, time-of-day selector, quick-scenario presets (Free Flow / Moderate / Rush Hour / Storm Gridlock)

3. **Route optimization**
   - `POST /routes/optimize` — calls OSRM for alternate routes between two zones, ranks them by a congestion-adjusted ETA (using a city-wide average of recent congestion as a proxy multiplier)
   - Chosen over Google Maps specifically because it needs no billing/API key — OpenStreetMap is one of the three tech-stack options named in the original project spec
   - Frontend `/routes` page: origin/destination pickers, clickable route list, interactive Leaflet map with route polylines
   - **Saved Routes**: any authenticated user can save an origin/destination pair (`POST /routes/saved`, `GET /routes/saved`, `DELETE /routes/saved/{id}`) for quick reuse

4. **Three-role system + security fix**
   - Roles: `admin`, `operator`, `user` (previously just admin/operator)
   - Public self-registration (`/signup` page) lets new users choose **Public User** or **Traffic Operator** — never **Admin**
   - **Bootstrap-admin pattern**: only the very first account ever created can self-assign `admin`; every signup after that is capped at operator/user regardless of what role is requested. This closed a real privilege-escalation gap where the original endpoint let anyone pass `"role": "admin"`.
   - Live password strength meter on signup (length + character variety heuristic)

5. **Incident reporting**
   - `POST /incidents` — operators/admins only (`require_operator_or_admin` dependency)
   - `GET /incidents` — any authenticated role can view active incidents
   - `PATCH /incidents/{id}/resolve` — operator/admin marks resolved
   - Frontend `/incidents` page: report form (hidden for regular users), active incident list with severity badges

6. **Role visibility & city scoping**
   - Nav bar shows a distinct colored badge per role (Admin/Operator/User) and hides nav links a role can't use
   - All 22 traffic zones are real Bangalore locations (previously scattered across 4 different Indian cities — a real bug this fix caught, since cross-city "routes" were meaningless)

**New tables introduced:** `traffic_predictions`, `incident_reports`, `saved_routes`

**New endpoints introduced:**

| Method | Endpoint | Access |
|---|---|---|
| POST | `/predict/congestion` | Authenticated |
| GET | `/predict/reports` | Authenticated |
| POST | `/routes/optimize` | Authenticated |
| POST | `/routes/saved` | Authenticated |
| GET | `/routes/saved` | Authenticated |
| DELETE | `/routes/saved/{id}` | Authenticated |
| POST | `/incidents` | Operator/Admin |
| GET | `/incidents` | Authenticated |
| PATCH | `/incidents/{id}/resolve` | Operator/Admin |

**Roles & permissions:**

| Role | Zones (write) | Predict / Routes | Report incidents | View incidents |
|---|:---:|:---:|:---:|:---:|
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `operator` | ❌ | ✅ | ✅ | ✅ |
| `user` | ❌ | ✅ | ❌ | ✅ |

---

## Setup & Running

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install "bcrypt==4.0.1" --force-reinstall

cp .env.example .env            # then edit .env with your PostgreSQL credentials
```

`.env` fields:
```
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trafficvision
```
> Passwords with special characters (`@`, `:`, `/`, `#`) are safe — `database.py` URL-encodes them automatically.

Create the database (one-time):
```bash
psql -U postgres -c "CREATE DATABASE trafficvision;"
```

Run the API:
```bash
uvicorn app.main:app --reload
```
Docs at `http://localhost:8000/docs`.

> **Schema changes require a full reset.** `Base.metadata.create_all()` only creates tables that don't exist — it never alters existing ones. After pulling any update that changes `models.py`:
> ```bash
> psql -U postgres -d trafficvision -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
> ```

### 2. Simulator (seeds data)

In a second terminal:
```bash
cd backend
source venv/bin/activate
python simulator.py
```
Creates a bootstrap admin (`admin@trafficvision.ai` / `admin123`), seeds 22 Bangalore zones, streams live readings every 5s.

### 3. Frontend

In a third terminal:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. Log in as admin, or sign up as a new Public User / Traffic Operator.

---

## Full API Reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/signup` | Public | Create account (`admin` only for the very first account ever) |
| POST | `/auth/login` | Public | Get a JWT access token |
| GET | `/auth/me` | Authenticated | Current user profile |
| POST | `/traffic/zones` | Admin only | Register a new traffic zone |
| GET | `/traffic/zones` | Authenticated | List all zones |
| POST | `/traffic/data` | Authenticated | Ingest a sensor reading |
| GET | `/traffic/live` | Authenticated | Latest reading per zone |
| GET | `/traffic/history/{zone_id}` | Authenticated | Last 50 readings for a zone |
| POST | `/predict/congestion` | Authenticated | Predict congestion from live traffic metrics |
| GET | `/predict/reports` | Authenticated | Recent prediction history |
| POST | `/routes/optimize` | Authenticated | Alternate routes + congestion-adjusted ETA |
| POST | `/routes/saved` | Authenticated | Save an origin/destination pair |
| GET | `/routes/saved` | Authenticated | List your saved routes |
| DELETE | `/routes/saved/{id}` | Authenticated | Remove a saved route |
| POST | `/incidents` | Operator/Admin | Report a real-world incident |
| GET | `/incidents` | Authenticated | View active incidents |
| PATCH | `/incidents/{id}/resolve` | Operator/Admin | Mark an incident resolved |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `AttributeError: module 'app.auth' has no attribute 'get_current_user'` | Working from an old clone where `app/auth.py` and `app/routers/auth.py` still share a name | Pull the latest code — this was permanently fixed by renaming `app/auth.py` to `app/security.py` (see note near the top of this document) |
| `password authentication failed for user "postgres"` | `.env` password doesn't match your actual PostgreSQL password | Confirm with `psql` directly, update `.env` to match |
| `could not translate host name "X@localhost"` | Special character in password wasn't URL-encoded | Already handled by `quote_plus` in `database.py` |
| `500` on `/auth/signup` | `bcrypt`/`passlib` version mismatch | `pip install "bcrypt==4.0.1" --force-reinstall` |
| `column "X" does not exist` / `UndefinedColumn` | `models.py` changed but DB wasn't reset | Full schema reset (see Setup section above) |
| Frontend "module not found" after pulling an update | New npm dependency (e.g. Leaflet) wasn't installed | Re-run `npm install`, even if `node_modules` exists |
| Route optimization returns `502` | OSRM's public demo server unreachable | Retry; for production, self-host OSRM or switch providers |
| `uvicorn: command not found` after activating venv | `pip install -r requirements.txt` never completed (often because it was run from the wrong folder) | `cd` into `backend` first, confirm with `pwd`, then reinstall |

---

## Reference: `app/security.py` (correct, complete content)

If this file ever gets corrupted or mixed up with the router file, replace its entire contents with exactly this:

```python
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != models.UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def require_operator_or_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in (models.UserRole.admin, models.UserRole.operator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator or admin privileges required",
        )
    return current_user
```

---

## Design Notes & Known Limitations

- **PostgreSQL via SQLAlchemy ORM**: fully decoupled from the specific database engine.
- **No migration tool**: `create_all()` doesn't alter existing tables — a real production gap, would use Alembic in a production system.
- **City-wide congestion proxy**: route ETA adjustment uses an average of recent readings across all zones, not per-route-segment congestion.
- **OSRM public demo server**: not meant for production traffic (no uptime guarantee); self-hosting or a paid provider is the natural upgrade.
- **Polling over WebSockets**: simpler for this project's scope; a documented tradeoff for future real-time work.

---

## Roadmap

- **Week 5–6 (Milestone 3):** Analytics dashboard with heatmaps and historical trend analysis, building on incident reports and prediction history already being logged
- **Week 7–8:** Deployment (Docker/cloud), performance tuning, final polish

---

## License

MIT — see [`LICENSE`](LICENSE).
