# TrafficVision AI — Backend

FastAPI REST API providing authentication, live traffic monitoring, AI congestion prediction, route optimization, and incident reporting for the TrafficVision AI platform (Bangalore).

## Tech Stack
- **FastAPI** — async web framework with automatic OpenAPI docs
- **SQLAlchemy** — ORM, decoupled from the specific database engine
- **PostgreSQL** — primary datastore
- **python-jose** — JWT creation/validation
- **passlib + bcrypt** — password hashing
- **python-dotenv** — environment-based configuration
- **scikit-learn + joblib + pandas** — congestion prediction model, served from a pre-trained `.joblib` file
- **requests** — calls to the OSRM routing service

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install "bcrypt==4.0.1" --force-reinstall
```

Copy the environment template and fill in your PostgreSQL credentials:
```bash
cp .env.example .env
```

`.env` fields:
```
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trafficvision
```

> Passwords containing special characters (`@`, `:`, `/`, `#`) are supported — `database.py` URL-encodes the password automatically before building the connection string.

Create the database (one-time):
```bash
psql -U postgres -c "CREATE DATABASE trafficvision;"
```

Run the server:
```bash
uvicorn app.main:app --reload
```

Tables are created automatically on first startup via `Base.metadata.create_all()`. Interactive API docs: `http://localhost:8000/docs`.

> **Note on schema changes:** `create_all()` only creates tables/types that don't exist yet — it never alters existing ones. If you pull an update that changes `models.py` (new columns, new enum values), do a full reset rather than expecting it to migrate automatically:
> ```bash
> psql -U postgres -d trafficvision -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
> ```
> This is a known limitation of using `create_all()` instead of a proper migration tool like Alembic — acceptable for active development, worth naming as a real production gap if asked.

## Seeding data

`simulator.py` creates a **bootstrap admin account**, seeds **22 real Bangalore traffic zones**, and streams synthetic rush-hour-aware sensor readings via the real `/traffic/data` endpoint (not direct DB writes):

```bash
python simulator.py
```

Default admin credentials created on first run:
- Email: `admin@trafficvision.ai`
- Password: `admin123`

Only the **very first account ever created** can become admin — this is enforced server-side (see Security notes below), not just a simulator convention.

## Project layout

```
app/
├── main.py                     # FastAPI app, CORS config, router registration
├── database.py                 # Engine/session setup, reads config from .env
├── models.py                   # SQLAlchemy ORM models
├── schemas.py                  # Pydantic request/response models
├── auth.py                     # Password hashing, JWT issuing/verification, RBAC dependencies
├── congestion_model.joblib     # Trained RandomForest congestion prediction model
├── target_encoder.joblib       # Label encoder for the model's output classes
└── routers/
    ├── auth.py                 # signup / login / me
    ├── traffic.py               # zones / live data / history
    ├── prediction.py             # congestion prediction + prediction reports
    ├── routes.py                   # route optimization + saved routes
    └── incidents.py                 # incident reporting + viewing
```

## Data models

| Table | Purpose |
|---|---|
| `users` | Accounts — role is one of `admin` / `operator` / `user` |
| `traffic_zones` | 22 Bangalore locations being monitored |
| `traffic_data` | Time-series sensor readings per zone |
| `traffic_predictions` | Logged congestion predictions (a "report" trail) |
| `incident_reports` | Manually reported accidents/closures/hazards, tied to a zone |
| `saved_routes` | A user's saved origin→destination pairs |

## Roles & permissions

| Role | Zones (write) | Predict / Routes | Report incidents | View incidents |
|---|:---:|:---:|:---:|:---:|
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `operator` | ❌ | ✅ | ✅ | ✅ |
| `user` | ❌ | ✅ | ❌ | ✅ |

**Bootstrap-admin pattern**: `POST /auth/signup` only allows `role: "admin"` to succeed if the `users` table is currently empty (i.e., you're creating the very first account). Every signup after that is capped to `operator`/`user` regardless of what role is requested in the payload — this closes a real privilege-escalation gap where any member of the public could otherwise self-assign admin.

## API Overview

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
| POST | `/predict/congestion` | Authenticated | Predict congestion (vehicle count, speed, occupancy, weather, hour, weekday/weekend) |
| GET | `/predict/reports` | Authenticated | Recent prediction history |
| POST | `/routes/optimize` | Authenticated | Alternate routes via OSRM, ranked by congestion-adjusted ETA |
| POST | `/routes/saved` | Authenticated | Save an origin/destination pair |
| GET | `/routes/saved` | Authenticated | List your own saved routes |
| DELETE | `/routes/saved/{id}` | Authenticated | Remove a saved route |
| POST | `/incidents` | Operator/Admin | Report a real-world incident |
| GET | `/incidents` | Authenticated | View active incidents (everyone can view) |
| PATCH | `/incidents/{id}/resolve` | Operator/Admin | Mark an incident resolved |

## Running tests manually

There's no automated test suite yet (planned for a later milestone), but the flow can be verified end-to-end:

```bash
# 1. Start the server (separate terminal)
uvicorn app.main:app --reload

# 2. Run the simulator — this exercises signup, login, zone creation, and data ingestion
python simulator.py
```

If both run without errors and `simulator.py` starts printing live readings, the full auth + data pipeline is working. For the prediction and routing endpoints specifically, use `/docs` (Swagger UI) to try them interactively.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `password authentication failed for user "postgres"` | `.env` password doesn't match your actual PostgreSQL password | Confirm your real password with `psql` directly, then update `.env` to match exactly |
| `could not translate host name "X@localhost"` | Special character in password wasn't URL-encoded | Already fixed in `database.py` via `quote_plus` |
| `500` on `/auth/signup` | `bcrypt`/`passlib` version mismatch | `pip install "bcrypt==4.0.1" --force-reinstall` |
| `column "X" does not exist` / `UndefinedColumn` | `models.py` changed but the DB schema wasn't migrated (`create_all()` doesn't alter existing tables) | Full reset: `psql -U postgres -d trafficvision -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"`, then restart the server |
| `AttributeError: module 'app.auth' has no attribute 'X'` on startup | `app/auth.py` and `app/routers/auth.py` are two different files with similar names and got mixed up while editing | Re-check `app/auth.py` contains password/JWT utilities (`hash_password`, `get_current_user`, etc.), not the signup/login endpoints |
| Frontend gets CORS errors | Frontend running on a port other than 5173 | Update `allow_origins` in `main.py` |
| Route optimization returns `502` | OSRM's public demo server unreachable (network/rate limit) | Retry; for production, self-host OSRM or switch providers |
