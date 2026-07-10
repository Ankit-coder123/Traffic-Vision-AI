# TrafficVision AI — Backend

FastAPI REST API providing authentication and live traffic monitoring for the TrafficVision AI platform.

## Tech Stack
- **FastAPI** — async web framework with automatic OpenAPI docs
- **SQLAlchemy** — ORM, decoupled from the specific database engine
- **PostgreSQL** — primary datastore
- **python-jose** — JWT creation/validation
- **passlib + bcrypt** — password hashing
- **python-dotenv** — environment-based configuration

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
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

## Seeding data

`simulator.py` creates an admin account, seeds 5 traffic zones, and streams synthetic rush-hour-aware sensor readings via the real `/traffic/data` endpoint (not direct DB writes):

```bash
python simulator.py
```

Default admin credentials created on first run:
- Email: `admin@trafficvision.ai`
- Password: `admin123`

## Project layout

```
app/
├── main.py          # FastAPI app, CORS config, router registration
├── database.py       # Engine/session setup, reads config from .env
├── models.py          # SQLAlchemy ORM models (User, TrafficZone, TrafficData)
├── schemas.py          # Pydantic request/response models
├── auth.py              # Password hashing, JWT issuing/verification, RBAC dependency
└── routers/
    ├── auth.py           # signup / login / me
    └── traffic.py          # zones / live data / history
```

## Running tests manually

There's no automated test suite yet (planned for a later milestone), but the flow can be verified end-to-end:

```bash
# 1. Start the server (separate terminal)
uvicorn app.main:app --reload

# 2. Run the simulator — this exercises signup, login, zone creation, and data ingestion
python simulator.py
```

If both run without errors and `simulator.py` starts printing live readings, the full auth + data pipeline is working.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `password authentication failed for user "postgres"` | `.env` password doesn't match your actual PostgreSQL password | Confirm your real password with `psql` directly, then update `.env` to match exactly |
| `could not translate host name "X@localhost"` | Special character in password wasn't URL-encoded | Already fixed in `database.py` via `quote_plus` — pull latest code |
| `500` on `/auth/signup` | `bcrypt`/`passlib` version mismatch | `pip install "bcrypt==4.0.1" --force-reinstall` |
| Frontend gets CORS errors | Frontend running on a port other than 5173 | Update `allow_origins` in `main.py` |
