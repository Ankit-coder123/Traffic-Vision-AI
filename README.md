# TrafficVision AI

A smart traffic prediction and congestion management platform for Bangalore — a full-stack portfolio project covering authentication, live traffic monitoring, AI-driven congestion prediction, route optimization, incident reporting, and an AI-driven analytics/alerts dashboard.

This single README documents the whole project, organized milestone by milestone, covering both the backend (FastAPI) and frontend (React) in one place.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy, PostgreSQL, JWT (python-jose), passlib + bcrypt, python-dotenv |
| ML | scikit-learn (RandomForest), pandas, joblib — trained model also powers the live AI recommendation engine (Milestone 3), not just the manual prediction page |
| Routing | OSRM (Open Source Routing Machine) + OpenStreetMap — free, no API key |
| Frontend | React (Vite), Tailwind CSS, Axios, React Router, Leaflet / react-leaflet, Recharts (trend charts), jsPDF + jspdf-autotable (analytics report export) |
| Deployment | Docker + Docker Compose (Postgres, backend, nginx-served frontend build, simulator — 4 containers, one command) |
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
│   │   ├── traffic_model.py        # Shared RandomForest wrapper -- used by both /predict and the AI recommendation engine
│   │   ├── email_utils.py          # Optional SMTP broadcast for new incident reports (see Email Alerts)
│   │   ├── congestion_model.joblib # Trained RandomForest model
│   │   ├── target_encoder.joblib
│   │   └── routers/
│   │       ├── auth.py             # signup/login HTTP endpoints
│   │       ├── traffic.py
│   │       ├── prediction.py
│   │       ├── routes.py
│   │       ├── incidents.py
│   │       └── analytics.py        # Heatmap, trends, road performance, AI-driven alerts
│   ├── simulator.py
│   ├── scripts/benchmark.py         # Real API latency + concurrency benchmark (see Performance Metrics)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js
│   │   ├── context/AuthContext.jsx
│   │   ├── components/ (NavBar, ProtectedRoute, ZoneCard, AlertBell, GoogleSignInButton)
│   │   └── pages/ (Login, Signup, Dashboard, Prediction, Routes, Incidents, Analytics, Profile)
│   ├── Dockerfile               # Multi-stage: npm build -> nginx serve
│   ├── nginx.conf                # SPA routing fallback + asset caching
│   ├── .dockerignore
│   └── .env.example              # VITE_GOOGLE_CLIENT_ID (optional)
├── ml/                              # Model training pipeline (see Milestone 2)
├── docs/ARCHITECTURE.md             # Full DB schema + design notes
├── .env.example                     # GOOGLE_CLIENT_ID for docker-compose (optional)
├── docker-compose.yml                # One-command full-stack deployment (see Docker Deployment)
├── render.yaml                       # Cloud deployment Blueprint (see Cloud Deployment)
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

## Milestone 3 (Week 5–6): Alerts, Analytics Dashboard & AI-Driven Recommendations

**Delivered:**

1. **AI-driven alert system** (`backend/app/traffic_model.py`, `routers/analytics.py`)
   - The congestion-alert half of `GET /analytics/recommendations` is genuinely model-driven, not a fixed threshold rule: for each zone, the last 2–3 live readings are averaged, road occupancy is estimated from vehicle count vs. road-type capacity, and any active accident report on that zone is fed in as a feature — then the **same trained RandomForest classifier** used by `/predict/congestion` scores it. A recommendation fires when the model predicts `"high"` congestion with ≥50% confidence (`critical` severity above 85%).
   - `traffic_model.py` is a shared module so `/predict/congestion` and the recommendation engine can't drift apart into two different copies of the same logic.
   - The other half of the alert feed is incident-derived (`source: "incident"`) — active accident/closure/hazard reports, which stay rule-based since they're direct human reports, not predictions.
   - **Dismissible alerts**: since AI-predicted congestion alerts aren't stored rows the way incidents are, there's nothing to mark "resolved." Instead, `POST /analytics/recommendations/{zone_id}/dismiss` (operator/admin only) records a 30-minute cooldown per zone (`alert_dismissals` table); the alert simply won't be regenerated for that zone until the cooldown expires or conditions genuinely change.
   - `AlertBell.jsx` (top-nav bell icon) polls both incidents and recommendations every 15s and merges them into one dropdown, with a **Dismiss** button on each AI alert.

2. **Analytics dashboard** (`Analytics.jsx`, `routers/analytics.py`)
   - `GET /analytics/summary` — city-wide header cards (zone count, active incidents, 24h prediction count, avg speed, busiest zone)
   - `GET /analytics/heatmap` — latest per-zone congestion reading, rendered as a Leaflet heatmap layer
   - `GET /analytics/trends` — hourly-bucketed congestion trend per zone (or city-wide), rendered with Recharts
   - `GET /analytics/road-performance` — readings grouped by road type (highway/arterial/local) instead of per-zone
   - `GET /analytics/recommendations` — the AI + incident alert feed described above, also shown inline on the Analytics page
   - **Downloadable PDF report** (`handleDownloadReport`, client-side via jsPDF): bundles the city-wide summary, congestion distribution, AI recommendations, road performance, and current heatmap snapshot into one PDF

**New table introduced:** `alert_dismissals`

**New endpoints introduced:**

| Method | Endpoint | Access |
|---|---|---|
| GET | `/analytics/summary` | Authenticated |
| GET | `/analytics/heatmap` | Authenticated |
| GET | `/analytics/trends` | Authenticated |
| GET | `/analytics/road-performance` | Authenticated |
| GET | `/analytics/recommendations` | Authenticated |
| POST | `/analytics/recommendations/{zone_id}/dismiss` | Operator/Admin |

**A note on model scope**: the trained classifier only predicts 3 classes (`low` / `medium` / `high`, inherited from the training dataset's labels), while live `traffic_data.congestion_level` also has a `severe` tier from the simulator's own rule-based labeling. The AI recommendation engine treats `"high"` as its trigger condition since that's the model's ceiling — it can't currently distinguish "high" from "severe" congestion. Worth calling out directly rather than glossing over; retraining with a 4-class target is the natural fix.

---

## Closing the PDF's Module Gaps: Profile Management, Peak-Hour Forecasting, Road Condition Monitoring

A later audit against the PDF's exact "Modules to be Implemented" list turned up three genuinely missing/weak items (not everything was fully covered by Milestones 1-3 as originally built). Closed all three, each with real functional tests, not just written and assumed working.

### Profile Management (User Management Module)

`GET /auth/me` already existed (view your own profile), but there was no way to actually **edit** anything — no PATCH/PUT endpoint at all. Added:

- **`PATCH /auth/me`** — update your display name and/or change your password. Email is deliberately **not** editable here — it's both the login identifier and the key other tables (incidents, saved routes) reference, and changing it safely needs a verification flow (confirm the new address is real, isn't already taken) that's a bigger feature than this project needs right now.
- Changing your password requires your **current** password — verified server-side with `security.verify_password()`, not just trusted from the client.
- New `Profile.jsx` page (reachable by clicking your name in the top-right nav) with separate forms for name and password.
- **Verified with 8 real test cases** through the actual signup→login→JWT flow (not mocked): rename works, wrong current-password is rejected with 401, missing current-password is rejected with 400, the password change actually takes effect (old password stops logging in, new one works), empty name and too-short passwords are rejected with 422, and an unauthenticated request is rejected with 401.

### Peak-Hour Forecasting & Pattern Analysis (Traffic Prediction Module / AI Prediction Module)

**`GET /analytics/peak-hours`** (optional `zone_id`, `days` — defaults to last 30 days) — groups every historical reading by hour-of-day and by day-of-week, and flags whichever ones are *statistically* above the overall average as "peak" (not just the top-N by rank, which would arbitrarily sweep in ties at the baseline — this was caught and fixed during testing, see below). Returns an hourly bar-chart-ready pattern, a day-of-week pattern, and a plain-language summary.

This is deliberately a grouped average over real historical data, not a second ML model — the trained RandomForest already covers "AI-based prediction" elsewhere (`/predict/congestion`, the recommendations engine). This endpoint answers a different question a live per-request model can't: *when* does congestion typically peak, based on what's actually happened at this zone.

Shown on the Analytics page as a 24-bar chart (red = statistically significant peak hour), scoped to whichever zone is selected in the existing trend-chart dropdown.

**Verified with constructed test data, not just plausible-looking output**: seeded a zone with a deliberate pattern (severe congestion at 8-9am, low at 2-3am, medium everywhere else) and asserted the endpoint identified *exactly* hours 8 and 9 as peak — no more, no less. Also tested a perfectly uniform zone (same congestion at every hour) and confirmed it correctly reports **no** peak hours rather than forcing a false one, plus a 404 for an unknown zone and correct city-wide aggregation with no zone filter.

### Road Condition Monitoring (Route Analysis Module)

**`GET /analytics/road-conditions`** — one query per zone that combines the latest live congestion reading with any currently active incident into a single clear status:

| Status | Meaning |
|---|---|
| `closed` | An active `road_closure` incident — always wins, even over severe congestion |
| `impaired` | An active accident/construction/hazard/other incident (passable but degraded) |
| `congested` | No active incident, but the latest reading is high/severe |
| `normal` | No active incident, latest reading is low/medium |

Sorted worst-first so the most actionable zones surface at the top. Shown on the Dashboard as a compact "Road Conditions Needing Attention" panel that only appears when at least one zone isn't `normal` — deliberately not cluttering the live-monitoring view when everything's fine.

**Verified with 5 assertions covering the priority logic specifically**, not just the happy path: a zone with both a closure AND severe congestion correctly resolves to `closed` (closure outranks congestion); a zone with an active incident but *low* congestion still correctly resolves to `impaired` (incident outranks congestion in the other direction too); a zone with a **resolved** incident is correctly treated as if it never happened; and the worst-first sort order was confirmed.

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

## Docker Deployment

The whole stack — Postgres, backend, frontend, and the traffic simulator — runs as one command via `docker-compose.yml` at the project root. This is the Milestone 4 "deploy using Docker" requirement.

**Prerequisites:** Docker + Docker Compose (Docker Desktop on Windows/Mac includes both).

```bash
docker compose up --build
```

This starts four containers:

| Service | What it does | Exposed at |
|---|---|---|
| `db` | PostgreSQL 16, with a healthcheck (`pg_isready`) other services wait on | internal only |
| `backend` | FastAPI app, waits for `db` to be healthy before starting | `http://localhost:8000` |
| `frontend` | Production React build served via nginx (with SPA routing + asset caching configured in `frontend/nginx.conf`) | `http://localhost:5173` |
| `simulator` | Same `simulator.py` used for manual runs, pointed at the `backend` service over the compose network | — (writes to the API) |

The `simulator` service automatically creates the `admin@trafficvision.ai` / `admin123` admin account and seeds all 20 Bangalore zones on first run — no manual setup step needed. Once `docker compose up --build` finishes starting all four containers, open `http://localhost:5173` and log in with those credentials.

**Before deploying this anywhere beyond your own machine**, change two things in `docker-compose.yml`:
- `JWT_SECRET_KEY` (currently `dev-only-secret-change-me`) — generate a real random secret, e.g. `python -c "import secrets; print(secrets.token_hex(32))"`
- `POSTGRES_PASSWORD` / `SIMULATOR_ADMIN_PASSWORD` — currently placeholder values fine only for local/demo use

To stop everything: `docker compose down` (add `-v` to also delete the Postgres volume and start fresh next time).

---

## Cloud Deployment (Render)

Docker gets this running on your own machine; this section gets it running at a public URL, closing out the PDF's "Deploy platform using Docker **and cloud environments**" requirement.

**Render, not Railway**: Railway no longer has a genuinely free tier (a trial credit that expires, then a paid plan). Render gives 750 free hours/month of web service usage, a free managed PostgreSQL database, and free static site hosting — no card required. One real tradeoff to know: Render's free Postgres database expires after 90 days and needs manual recreation. Fine for a demo/portfolio project, not something to build a business on.

### How the pieces map from Docker to Render

Render doesn't run `docker-compose.yml` directly — it deploys each service separately, using the **same Dockerfiles** you already have. `render.yaml` (project root) defines this mapping as a Blueprint, so deployment is mostly automated rather than manually clicking through 4 separate service setups:

| Local (`docker-compose.yml`) | Render (`render.yaml`) |
|---|---|
| `db` container | Render managed PostgreSQL (free tier) |
| `backend` container | Web Service, built from `backend/Dockerfile` |
| `frontend` container (nginx) | **Static Site** — Vite's build output is just static files, so a full nginx container is unnecessary on Render; static sites are free and don't spin down, unlike free web services |
| `simulator` container | Background Worker, same `backend/Dockerfile`, running `python simulator.py` |

### Code changes this required (already done, not something you need to do)

Two things were hardcoded for local dev and needed to become configurable, since "cloud deployment" doesn't just mean pointing a host at your Docker setup unchanged:

- **`frontend/src/api/client.js`** hardcoded `http://localhost:8000` as the backend URL. Now reads `import.meta.env.VITE_API_BASE_URL`, falling back to `localhost:8000` — so local dev, Docker, and Render all keep working with the right target.
- **`backend/app/main.py`**'s CORS `allow_origins` only listed localhost ports. Now also reads an optional `FRONTEND_URL` env var and appends it — so your deployed frontend's real domain is allowed to call the deployed backend, without hardcoding it or breaking local dev's existing localhost origins.
- **`backend/app/database.py`** only understood separate `DB_USER`/`DB_HOST`/etc vars. Render (like most PaaS platforms) provides one `DATABASE_URL` connection string instead — the code now prefers that if it's set, normalizing Render's `postgres://` scheme to the `postgresql://` scheme SQLAlchemy's driver expects, and falls back to the original `DB_*` vars for local/Docker dev exactly as before.

Verified all three: confirmed the CORS origin list correctly includes/excludes the production URL depending on whether `FRONTEND_URL` is set, and confirmed `database.py` builds the right connection string in both the local-dev and Render-style-`DATABASE_URL` cases.

### Deploying

1. Push this repo to GitHub if you haven't already (`git push`).
2. Go to [dashboard.render.com](https://dashboard.render.com), sign up (GitHub login is fastest).
3. **New** → **Blueprint** → connect this repo. Render reads `render.yaml` and shows you all 4 resources it's about to create (1 database + 3 services).
4. Before clicking deploy, Render will prompt for any env var marked `sync: false` in `render.yaml` — currently `GOOGLE_CLIENT_ID`, `SMTP_USER`, `SMTP_PASSWORD` (all optional; leave blank to skip those features, same as local/Docker).
5. Click **Deploy Blueprint**. First build takes a few minutes — Render builds each Docker image and the static site from scratch.
6. Once live, open the `trafficvision-frontend` service's URL (something like `https://trafficvision-frontend.onrender.com`).

**If your service names end up different from the defaults** (`trafficvision-backend`, `trafficvision-frontend`) — Render sometimes appends a suffix if the name's taken — update the hardcoded URLs in `render.yaml` (`FRONTEND_URL`, `VITE_API_BASE_URL`, `API_BASE_URL`) to match your actual service URLs, then redeploy.

**Free-tier cold starts**: free Render web services spin down after 15 minutes of inactivity and take ~30-60 seconds to wake back up on the next request. Expect the first load after idle time to feel slow — not a bug, just the free tier's tradeoff. The frontend (static site) and simulator (background worker) don't have this issue; only the backend web service does.

---

## Google Sign-In (optional)

A "Continue with Google" button on the Login/Signup pages — not required by the project brief, added as an extra convenience. It's entirely optional: leave it unconfigured and the button simply doesn't render, everything else works exactly as before.

**How it works:** the frontend uses Google Identity Services to get a signed ID token directly from Google in the browser, then sends that token to a new `POST /auth/google` endpoint, which verifies it server-side (signature, audience, expiry) and either logs the matching user in or creates a new account on first sign-in. No client secret or OAuth redirect flow needed — just a public Client ID.

**Setup:**

1. Go to [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials), create an **OAuth client ID** → Application type **Web application**.
2. Under **Authorized JavaScript origins**, add `http://localhost:5173` (and your production URL later, if you deploy this beyond local use).
3. Copy the Client ID (looks like `123456-abc.apps.googleusercontent.com`). You do **not** need the client secret for this flow.
4. **Manual (non-Docker) setup:**
   - Backend: add `GOOGLE_CLIENT_ID=<your client id>` to `backend/.env`
   - Frontend: copy `frontend/.env.example` to `frontend/.env`, set `VITE_GOOGLE_CLIENT_ID=<your client id>`, restart `npm run dev`
5. **Docker setup:** copy `.env.example` (project root) to `.env`, set `GOOGLE_CLIENT_ID=<your client id>`, then `docker compose up --build` — Compose reads that `.env` automatically and passes the value to both the backend container and the frontend's build step.

**Design notes worth knowing:**
- Google-created accounts always get `role: "user"` — same restriction as public signup, no path to `operator`/`admin` through this route.
- The `users` table doesn't have a separate "auth provider" column (adding one would need a real migration tool, which this project doesn't have yet — see Known Limitations). Google-only accounts still get a `password_hash` under the hood, just one hashed from a random secret the user never sees, so password login for that account isn't practically possible without knowing that secret.
- Signing in with the same Google account twice reuses the same user row rather than creating duplicates — verified with a functional test (two calls, one user created).

---

## Email Alerts (optional)

When an operator/admin reports an incident, every registered user (all roles — admins, operators, and public users alike) can optionally get an email alert about it. Same philosophy as Google Sign-In: entirely optional, and everything else works identically whether it's configured or not.

**How it works:** `backend/app/email_utils.py` sends one **individual** email per recipient via Gmail's SMTP server, each with the recipient's own address genuinely in the "To" field. It runs as a FastAPI `BackgroundTask`, kicked off *after* the incident report's HTTP response is already sent — so a slow or failing email server never delays or breaks the actual "report an incident" request. If `SMTP_USER`/`SMTP_PASSWORD` aren't set, it's a silent no-op.

**Why individual sends instead of one shared email with everyone in Bcc**: that was the original design (fewer SMTP transactions, cleaner), but real-world testing surfaced a genuine problem — Gmail's SMTP server would accept the message with a clean `250 OK` for every recipient, yet the Bcc'd copies would silently vanish on the receiving end (not Spam, not Promotions, nowhere). This is a known Gmail quirk: mail between two personal Gmail accounts where the visible "To" line isn't the actual recipient (a hallmark of all-Bcc broadcasts) gets treated with more suspicion by Gmail's spam/security engine than a normal one-to-one email. Individual sends with a real "To: recipient" line are the standard, reliably-delivered pattern — confirmed by fixing this exact failure during development. The cost is one SMTP send per recipient instead of one shared send, which is a non-issue at this project's scale (a handful of test/demo users) but would matter for a large user base, where a real transactional email provider (SendGrid, Amazon SES) would be the right call instead of looping raw SMTP.

**Setup — Gmail requires an App Password, not your regular password:**

1. Your Google account needs 2-Step Verification turned on first (myaccount.google.com/security).
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create a new app password (name it anything, e.g. "TrafficVision AI"), and copy the 16-character password it gives you.
3. **Manual (non-Docker) setup:** add to `backend/.env`:
   ```
   SMTP_USER=youraddress@gmail.com
   SMTP_PASSWORD=the-16-char-app-password
   ```
4. **Docker setup:** add the same two lines to the project-root `.env` (same file used for `GOOGLE_CLIENT_ID`), then `docker compose up --build`.

**Design notes worth knowing:**
- Broadcasts to **every** registered user, regardless of role — a deliberate choice for this project, not a technical constraint. A narrower target (just operators/admins, or just the reporter) would be a small, easy change to `incidents.py`'s `report_incident()` if you'd rather scope it down.
- Gmail's regular (non-Workspace) SMTP caps out around ~500 recipients/day — fine for a demo user base, but a real production deployment with many users would need a real transactional email provider (SendGrid, Amazon SES, etc.) instead.
- Per-recipient failures are tracked and logged individually (`server.sendmail()` returns a dict of refused recipients rather than raising an exception — easy to silently miss if you don't check the return value, which an earlier version of this code didn't).
- **The seeded admin account's placeholder email will bounce once SMTP is configured**: `simulator.py` auto-creates a bootstrap admin using `SIMULATOR_ADMIN_EMAIL`, which defaults to `admin@trafficvision.ai` — a domain that was never actually registered, so it isn't a real deliverable inbox. Harmless as long as email alerts aren't configured (they're just skipped entirely), but once `SMTP_USER`/`SMTP_PASSWORD` are set, every incident report tries to email this placeholder and gets a permanent bounce ("recipient server did not accept our requests to connect... timed out" — confirmed via a real bounce notification during testing). Set `SIMULATOR_ADMIN_EMAIL`/`SIMULATOR_ADMIN_PASSWORD` in `.env` to a real email you control **before** the simulator's first run to avoid this entirely. If the placeholder account already exists in your database from an earlier run, updating `.env` alone isn't enough — the existing row needs a direct SQL update too (`UPDATE users SET email = '...' WHERE email = 'admin@trafficvision.ai';`), since these env vars only control what gets *created*, not rows that already exist.
- **Verified with a real functional test, and this one caught a genuine bug during development**: initial testing with two real Gmail accounts showed the sender's own inbox receiving the email while a Bcc'd second account received nothing, anywhere — not Spam, not Promotions. Added return-value checking on `sendmail()` first (confirmed Gmail's server was accepting all recipients with no errors), which ruled out a code bug and pointed to Gmail's own spam engine silently dropping all-Bcc mail between personal accounts. Switched to individual per-recipient sends with a real "To" line, which is the fix now shipped. I could not verify final delivery myself end-to-end — `smtp.gmail.com` isn't reachable from the sandboxed environment this was built in — the person actually running this project confirmed the original bug and the fix through real Gmail accounts.

---

## Full API Reference

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/signup` | Public | Create account (`admin` only for the very first account ever) |
| POST | `/auth/login` | Public | Get a JWT access token |
| POST | `/auth/google` | Public | Sign in / auto-sign-up with a verified Google ID token (optional feature) |
| GET | `/auth/me` | Authenticated | Current user profile |
| PATCH | `/auth/me` | Authenticated | Update your name and/or change your password |
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
| POST | `/incidents` | Operator/Admin | Report a real-world incident (triggers an optional email broadcast — see Email Alerts) |
| GET | `/incidents` | Authenticated | View active incidents |
| PATCH | `/incidents/{id}/resolve` | Operator/Admin | Mark an incident resolved |
| GET | `/analytics/summary` | Authenticated | City-wide snapshot for dashboard header cards |
| GET | `/analytics/heatmap` | Authenticated | Latest congestion reading per zone (map heatmap) |
| GET | `/analytics/trends` | Authenticated | Hourly-bucketed congestion trend per zone |
| GET | `/analytics/road-performance` | Authenticated | Readings grouped by road type (highway/arterial/local) |
| GET | `/analytics/recommendations` | Authenticated | AI-driven congestion alerts + active-incident alerts |
| POST | `/analytics/recommendations/{zone_id}/dismiss` | Operator/Admin | Suppress a zone's AI congestion alert for 30 minutes |
| GET | `/analytics/peak-hours` | Authenticated | Peak-hour forecasting & pattern analysis from real historical data |
| GET | `/analytics/road-conditions` | Authenticated | Per-zone status: closed / impaired / congested / normal |

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

## Performance Metrics

Actual measurements against a real PostgreSQL 16 instance seeded with 10 zones and 400 traffic readings — not estimates. Covers the PDF's "Performance Metrics" and "Example Quantitative Goals" sections point by point. Reproducible yourself via `backend/scripts/benchmark.py`.

### Traffic Prediction Performance

Re-ran `ml/04_train_production_model.py` for current numbers on the held-out test set (1,000 samples, 80/20 split, `random_state=42`):

| Metric | Result |
|---|---|
| **Prediction accuracy** | 99.9% overall |
| **Congestion detection rate** (recall on `high` class — the metric that matters most: did it catch real congestion?) | **100%** — all 633 actual high-congestion test cases correctly flagged, zero missed |
| Precision / Recall / F1, all 3 classes | 0.986–1.000 across the board |

Full confusion matrix (rows = actual, columns = predicted: high / low / medium): only **1 misclassification out of 1,000** test samples (a `low` predicted as `medium`) — zero `high` cases were ever mispredicted as something less severe, which is the direction that would actually matter in a real deployment (missing real congestion is worse than a false alarm).

**Feature importances:**

| Feature | Importance |
|---|---|
| Vehicle Count | 42.2% |
| Road Occupancy % | 27.3% |
| Traffic Speed | 23.3% |
| Accident Report | 5.5% |
| hour / day_of_week / weather / is_rush_hour / is_weekend | ~1.6% combined |

**Read the 99.9% carefully, don't just quote it out of context**: this reflects the training data's structure (see `ml/eda/EDA_SUMMARY.md`) — congestion labels are driven almost entirely by 3 numeric features with a near-deterministic relationship, so a RandomForest fits them very cleanly. It's an honest reflection of this specific (synthetic, Kaggle) dataset, not a claim that real-world traffic prediction is 99.9% solvable. Say this plainly if your mentor asks.

**Route recommendation efficiency**: `backend/scripts/benchmark.py` includes a `/routes/optimize` benchmark, but it depends on the public OSRM routing service (`router.project-osrm.org`) being reachable — it was NOT reachable in the sandboxed environment this project was developed in (network egress restrictions), confirmed with a direct `403` when tested. Run the script yourself locally or via Docker to get a real number for this one; every other metric here was measured for real.

### Analytics Performance

| Endpoint | min | p50 | p95 | max | (ms, n=20) |
|---|---|---|---|---|---|
| `/traffic/zones` | 4.6 | 4.8 | 5.7 | 6.5 | fastest — simple indexed query |
| `/analytics/heatmap` | 11.0 | 11.8 | 13.2 | 13.4 | one row per zone, no aggregation |
| `/analytics/road-performance` | 10.9 | 11.8 | 13.7 | 143.0 | grouped aggregation; the outlier is a cold-cache first query |
| `/analytics/summary` | 13.4 | 14.4 | 17.4 | 25.7 | several counts/averages combined |
| `/analytics/trends` | 16.2 | 17.2 | 18.9 | 19.2 | hourly bucketing across all zones |
| `/predict/congestion` | 23.8 | 25.1 | 26.9 | 30.7 | single live RandomForest inference |
| `/analytics/recommendations` | 183.9 | 193.7 | 204.1 | 227.1 | **~15x slower than the rest — see below** |

**Data processing efficiency** (how fast the system ingests live sensor data): measured **124 readings/second** sequential ingestion throughput via `POST /traffic/data` (100 requests, single connection, no batching). For context, your actual simulator posts 1 reading per zone every 5 seconds — with 20 zones that's ~4 readings/second of real load. Measured capacity is roughly **30x** the actual demand, so ingestion is nowhere close to being a bottleneck at this scale.

**A real finding, not a guess**: `/analytics/recommendations` is dramatically slower than everything else because `get_recommendations()` in `analytics.py` calls the trained ML model **once per zone in a Python loop** — 10 zones means 10 separate `predict_proba()` calls, each with its own feature-row construction. Still fast enough to feel instant at 10 zones (~190ms), but it won't scale linearly forever. Batching all zones' feature rows into a single DataFrame and calling `predict_proba()` once would cut this dramatically — documented here rather than silently fixed, since it's a legitimate "here's what I'd optimize next" talking point.

### System Performance

**Concurrency** (hammering `/analytics/summary` with N simultaneous requests):

| Concurrent requests | Total time | Throughput | Failures |
|---|---|---|---|
| 1 | 17.0ms | 59.0 req/sec | 0 |
| 5 | 208.7ms | 24.0 req/sec | 0 |
| 10 | 312.0ms | 32.1 req/sec | 0 |
| 20 | 595.8ms | 33.6 req/sec | 0 |

Zero failures at every concurrency level. Throughput plateaus around 30–36 req/sec rather than scaling linearly, which is expected on a single-core benchmark environment; a multi-worker Uvicorn/Gunicorn setup would scale further in production.

**Database query optimization — a real gap found and fixed, not just claimed:**

`traffic_data.zone_id` — filtered in 7+ different queries across the app (every zone-specific lookup) — had **no index** before this pass, only `recorded_at` did. Verified the actual impact with `EXPLAIN ANALYZE` on the exact query pattern `get_recommendations()` uses (`WHERE zone_id = ? ORDER BY recorded_at DESC LIMIT 3`):

| | Before | After adding a composite `(zone_id, recorded_at)` index |
|---|---|---|
| Query plan | `Index Scan Backward` on `recorded_at`, then **filtered out 360 of 400 rows** row-by-row | Clean `Index Cond` on `zone_id` — no wasted rows touched |
| Execution time | 0.248ms | 0.099ms |

At only 400 rows the raw millisecond difference looks small, but the *pattern* matters: the old plan was O(n) — it degrades as `traffic_data` grows from hundreds to hundreds of thousands of rows (which it will, since the simulator writes continuously). The new plan is effectively O(log n + k), independent of total table size. Two more missing indexes were found and fixed the same way: `incident_reports.is_resolved` (filtered constantly by both the alerts system and `GET /incidents`) and `saved_routes.user_id` (every "my saved routes" lookup).

**If you already have a running deployment** with data in it: `create_all()` can't add indexes to existing tables (see Known Limitations below on the lack of a migration tool). Apply these manually:
```sql
CREATE INDEX ix_traffic_data_zone_recorded ON traffic_data (zone_id, recorded_at);
CREATE INDEX ix_incident_reports_is_resolved ON incident_reports (is_resolved);
CREATE INDEX ix_saved_routes_user_id ON saved_routes (user_id);
```
A fresh database (or `docker compose down -v` to reset the volume) picks these up automatically via `create_all()`, no manual SQL needed.

**Reproduce all of the above yourself** (numbers depend on your own machine's hardware — don't copy them into a report as if they're universal):
```bash
cd backend
python scripts/benchmark.py
# or against Docker:
BASE_URL=http://localhost:8000 python scripts/benchmark.py
```

---

## Automated Testing

Closes the PDF's "Perform application testing and workflow validation" task (Milestone 4).

An 80+ case `pytest` suite lives in `backend/tests/`, covering every router: auth (signup, login, the bootstrap-admin rule, profile updates), traffic monitoring, congestion prediction (against the real trained model), route optimization (OSRM mocked — see below), incident reporting, and the full analytics module (summary, heatmap, road-performance, trends, AI-driven recommendations, alert dismissal, peak-hour analysis, road-conditions).

Tests run against an isolated in-memory SQLite database, not your real Postgres — nothing you run locally touches production/dev data. `/routes/optimize`'s call to the public OSRM server is monkeypatched with a canned response so the suite doesn't depend on network access or OSRM's uptime.

**Run it:**
```bash
cd backend
pip install -r requirements.txt -r requirements-test.txt
pytest
```

For a coverage report, add `pytest-cov` to `requirements-test.txt` and run `pytest --cov=app`.

A couple of tests (`test_predict_congestion_light_traffic_input` / `..._heavy_traffic_input` in `test_prediction.py`) assert the model's *directionality* on extreme inputs (e.g. near-empty roads shouldn't classify as `"high"`) rather than an exact label, since pinning an exact prediction would make the suite brittle to any future retrain. If either fails, it's worth a look — everything else in the suite is deterministic.

---

## Design Notes & Known Limitations

- **PostgreSQL via SQLAlchemy ORM**: fully decoupled from the specific database engine.
- **No migration tool**: `create_all()` doesn't alter existing tables — a real production gap, would use Alembic in a production system.
- **City-wide congestion proxy**: route ETA adjustment uses an average of recent readings across all zones, not per-route-segment congestion.
- **OSRM public demo server**: not meant for production traffic (no uptime guarantee); self-hosting or a paid provider is the natural upgrade.
- **Polling over WebSockets**: simpler for this project's scope; a documented tradeoff for future real-time work.
- **AI model is 3-class, not 4-class**: predicts `low`/`medium`/`high` only, so it can't distinguish `severe` from `high` congestion the way the simulator's own labeling does (see Milestone 3 above).
- **Weather input is static for AI alerts**: the recommendation engine doesn't have a live weather feed, so it always passes `"Clear"` to the model for that feature — a real integration (e.g. OpenWeatherMap) is the natural next step.
- **Docker Compose secrets are placeholder values**: `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, and the simulator's admin password are hardcoded in `docker-compose.yml` for one-command local/demo convenience — fine for this project's scope, but a real deployment would pull these from a `.env` file (git-ignored) or a secrets manager instead of committing them.
- **`/analytics/recommendations` scales linearly with zone count, not efficiently**: measured at ~180ms for 10 zones because the model runs once per zone in a loop (see Performance Metrics above) — fine at this scale, but batching all zones into one `predict_proba()` call would be the right fix before adding significantly more zones.

---

## UI Responsiveness & Bundle-Size Optimization

Closes the PDF's "Improve UI responsiveness and system optimization" task (Milestone 4).

**Mobile navigation** — `NavBar.jsx` previously had zero responsive handling: 5 nav links, the logo, alert bell, and profile badge were all crammed into one `flex` row with no breakpoints or wrapping strategy, which overflowed/broke on phone-width screens. Now:
- Below `md` breakpoint, the nav links and sign-out button collapse into a hamburger menu (☰ / ✕ toggle, animated open/close)
- The alert bell stays visible at all screen sizes — notifications shouldn't require opening a menu first
- Above `md`, the layout is unchanged from before

**Bundle-size reduction** — verified with real measurements, not estimated. The frontend previously shipped one **1,330.90 KB** JavaScript bundle to *every* visitor, including someone who's only looking at the login page. `Analytics.jsx` alone pulls in jsPDF, Leaflet, and Recharts — none of which a login-page visitor needs yet.

Converted all authenticated routes (`Dashboard`, `Prediction`, `Routes`, `Incidents`, `Analytics`, `Profile`) to `React.lazy()` + `Suspense`, so each becomes its own chunk fetched only when actually navigated to:

| | Before | After |
|---|---|---|
| Login/Signup page initial download | 1,330.90 KB (404 KB gzipped) | **292.58 KB (~95 KB gzipped)** |
| Reduction | — | **~78%** |

Confirmed by inspecting the built `dist/` output directly: `index.html`'s script tag now references only the small initial chunk, and the heavy dependencies (`Analytics-*.js` 402 KB, `jspdf.plugin.autotable-*.js` 429 KB, `leaflet-*.js` 153 KB, `html2canvas-*.js` 199 KB) only appear as separate chunks loaded on navigation. The build's "chunks larger than 500 KB" warning, present since the very first working version of this project, is now gone entirely.

---

## Roadmap

- **Week 7–8 (Milestone 4):** ~~Docker deployment~~ done, ~~cloud deployment~~ done, ~~UI responsiveness & bundle-size optimization~~ done, ~~automated test suite~~ done (see `backend/tests/` — run with `pytest` from `backend/`; see below)
- ~~Profile management~~, ~~Peak-hour forecasting~~, ~~Road condition monitoring~~ — closed, see "Closing the PDF's Module Gaps" above

---

## License

MIT — see [`LICENSE`](LICENSE).
