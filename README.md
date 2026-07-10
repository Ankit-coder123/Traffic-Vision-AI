# TrafficVision AI

A smart traffic prediction and congestion management platform — built as a full-stack portfolio project covering authentication, live traffic monitoring, and (in later milestones) AI-driven congestion prediction and route optimization.

> **Milestone status:** Week 1 & 2 — Architecture, Authentication & Live Monitoring ✅ Complete

---

## What this milestone delivers

| Requirement | Status | Where |
|---|---|---|
| System architecture & DB schema design | ✅ | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Backend + frontend environment setup | ✅ | `backend/`, `frontend/` |
| User authentication (JWT) | ✅ | `backend/app/auth.py`, `backend/app/routers/auth.py` |
| Role-based access control (admin / operator) | ✅ | `backend/app/auth.py` (`require_admin`) |
| Live traffic monitoring dashboard | ✅ | `frontend/src/pages/Dashboard.jsx` |
| Congestion tracking workflow | ✅ | `backend/app/routers/traffic.py`, simulated sensor feed |

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · PostgreSQL · JWT (python-jose) · bcrypt (passlib) · Pydantic
**Frontend:** React (Vite) · Tailwind CSS · Axios · React Router · Recharts
**Tooling:** python-dotenv for config, a custom Python data simulator standing in for real traffic sensors

---

## Project Structure

```
TrafficVision-AI/
├── backend/                  # FastAPI REST API
│   ├── app/
│   │   ├── main.py           # App entrypoint, CORS, router registration
│   │   ├── database.py       # PostgreSQL connection (env-based config)
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── auth.py           # JWT creation/validation, password hashing, RBAC
│   │   └── routers/
│   │       ├── auth.py       # /auth/signup, /auth/login, /auth/me
│   │       └── traffic.py    # /traffic/zones, /traffic/live, /traffic/history
│   ├── simulator.py          # Generates realistic fake sensor data
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                 # React dashboard
│   └── src/
│       ├── api/client.js         # Axios instance + JWT interceptor
│       ├── context/AuthContext.jsx
│       ├── components/           # ProtectedRoute, ZoneCard
│       └── pages/                # Login, Dashboard
│
├── docs/
│   └── ARCHITECTURE.md       # DB schema + system design notes
│
└── README.md                 # you are here
```

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (running locally or accessible remotely)

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env            # then edit .env with your PostgreSQL credentials
```

Create the database (one-time):
```bash
psql -U postgres -c "CREATE DATABASE trafficvision;"
```

Run the API:
```bash
uvicorn app.main:app --reload
```
API docs available at `http://localhost:8000/docs`.

### 2. Seed live data

In a second terminal:
```bash
cd backend
source venv/bin/activate
python simulator.py
```
This creates an admin account (`admin@trafficvision.ai` / `admin123`), seeds 5 traffic zones, and streams realistic readings every 5 seconds.

### 3. Frontend setup

In a third terminal:
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173` and log in with the admin credentials above.

Full details, including troubleshooting, are in [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

---

## API Overview

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/signup` | Public | Create a new user |
| POST | `/auth/login` | Public | Get a JWT access token |
| GET | `/auth/me` | Authenticated | Current user profile |
| POST | `/traffic/zones` | Admin only | Register a new traffic zone |
| GET | `/traffic/zones` | Authenticated | List all zones |
| POST | `/traffic/data` | Authenticated | Ingest a sensor reading |
| GET | `/traffic/live` | Authenticated | Latest reading per zone |
| GET | `/traffic/history/{zone_id}` | Authenticated | Last 50 readings for a zone |

Interactive Swagger documentation is auto-generated at `/docs` when the backend is running.

---

## Design Notes & Engineering Decisions

- **PostgreSQL via SQLAlchemy ORM**: the data layer is fully decoupled from the specific database engine — swapping databases only required changing `database.py`, nothing in the models, routers, or business logic.
- **Password URL-encoding**: DB credentials are read from environment variables and URL-encoded (`urllib.parse.quote_plus`) before being used in the connection string, so passwords containing special characters (`@`, `:`, `/`) don't break the connection URL — a real bug caught and fixed during development.
- **Stateless JWT auth**: chosen over server-side sessions for horizontal scalability and a clean separation between the API and frontend.
- **Polling over WebSockets**: the live dashboard polls `/traffic/live` every 5 seconds rather than using WebSockets, favoring implementation simplicity for this milestone's scope; noted as a scaling consideration for future work.
- **Synthetic data simulator**: since no real sensor hardware is available, `simulator.py` generates rush-hour-aware traffic data and pushes it through the same public API a real sensor gateway would use — keeping the ingestion path realistic rather than seeding the DB directly.

---

## Roadmap

- **Week 3–4:** AI-based congestion prediction models, route optimization, ETA estimation
- **Week 5–6:** Alerts & notifications, analytics dashboard with heatmaps and historical trends
- **Week 7–8:** Deployment (Docker/cloud), performance tuning, final polish

---

## License

MIT — see [`LICENSE`](LICENSE).
