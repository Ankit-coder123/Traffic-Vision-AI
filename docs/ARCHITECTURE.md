# Architecture — Milestones 1, 2 & 3 (Week 1–6)

## System Overview

```
┌─────────────────┐        HTTPS/REST         ┌──────────────────┐
│  React Frontend  │  ─────────────────────▶  │  FastAPI Backend  │
│  (Vite, Tailwind) │  ◀─────────────────────  │   (JWT auth)      │
└─────────────────┘         JSON               └────────┬─────────┘
                                                          │ SQLAlchemy ORM
                                                          ▼
                                                 ┌──────────────────┐
                                                 │   PostgreSQL DB   │
                                                 └──────────────────┘
                                                          ▲
                                                          │ REST calls
                                                 ┌──────────────────┐
                                                 │  simulator.py      │
                                                 │  (synthetic sensor │
                                                 │   data generator)  │
                                                 └──────────────────┘
```

The simulator deliberately talks to the backend over the **same public REST API** a real sensor gateway would use (`POST /traffic/data`), rather than writing to the database directly. This keeps the ingestion path realistic and means swapping in real hardware later requires no backend changes.

---

## Database Schema

```
users
├── id               PK
├── name
├── email             UNIQUE
├── password_hash      bcrypt hash, never plaintext
├── role               enum: 'admin' | 'operator'
└── created_at

traffic_zones
├── id               PK
├── name              e.g. "MG Road Junction"
├── latitude
├── longitude
├── road_type          enum-like: 'highway' | 'arterial' | 'local'
└── created_at

traffic_data
├── id               PK
├── zone_id           FK → traffic_zones.id
├── vehicle_count
├── avg_speed_kmph
├── congestion_level    enum: 'low' | 'medium' | 'high' | 'severe'
└── recorded_at         indexed — queried heavily for "latest per zone"
```

**Design rationale:**
- `traffic_zones` and `traffic_data` are split because a zone is a low-frequency, mostly-static entity, while readings are a high-frequency time series. Keeping them separate avoids bloating the zones table and mirrors how real sensor deployments are modeled (one physical location → many readings over time).
- `recorded_at` is indexed since the dashboard's most common query is "give me the latest reading per zone," which benefits from sorting/filtering on this column.
- Roles are stored directly on `users` rather than a separate roles/permissions table — appropriate for the current two-role scope (admin/operator); would be normalized into a proper RBAC table set if roles/permissions grew more complex.

---

## Milestone 2 additions to the schema

```
traffic_predictions
├── id               PK
├── zone_id           FK → traffic_zones.id (nullable)
├── vehicle_count, avg_speed_kmph, road_occupancy_pct, weather_condition
├── predicted_congestion  'low' | 'medium' | 'high'
├── confidence            model's probability for the predicted class
├── predicted_by_user_id  FK → users.id
└── created_at             indexed -- acts as a prediction "report" trail

incident_reports
├── id               PK
├── zone_id           FK → traffic_zones.id
├── incident_type      accident | road_closure | construction | hazard | other
├── severity            minor | moderate | major
├── description
├── reported_by_user_id  FK → users.id
├── is_resolved            0/1 flag
└── created_at

saved_routes
├── id               PK
├── user_id           FK → users.id
├── label              e.g. "Home to Office"
├── origin_zone_id      FK → traffic_zones.id
├── destination_zone_id FK → traffic_zones.id
└── created_at
```

`users.role` now has three values: `admin` / `operator` / `user`, enforced via a **bootstrap-admin pattern** — only the very first account ever created (`users` table empty) can self-assign `admin` through `POST /auth/signup`; every signup after that is capped at `operator`/`user` regardless of what the request asks for. This closes a real privilege-escalation vulnerability that existed in an earlier version of the endpoint.

## Milestone 3 additions — Alerts, Analytics & AI Insights

```
alert_dismissals
├── id                   PK
├── zone_id                FK → traffic_zones.id
├── dismissed_by_user_id    FK → users.id
├── dismissed_at
└── expires_at              indexed -- cooldown window, defaults to 30 min
```

**Alert system** (`GET /analytics/recommendations`, `AlertBell.jsx`): two independent sources feed one combined alert list.
- **Incidents** (`source: "incident"`) — direct human reports (accidents, closures, hazards) from `incident_reports`, resolved manually via `PATCH /incidents/{id}/resolve`.
- **Congestion predictions** (`source: "congestion"`) — genuinely model-driven, not a fixed threshold rule. For each zone, the last few live readings are averaged and fed into the same trained `RandomForestClassifier` used by `/predict/congestion` (factored into a shared `app/traffic_model.py` module so both call sites stay in sync). If the model predicts `"high"` congestion with ≥50% confidence, a recommendation is raised, with severity escalating to `critical` above 85% confidence. Active accident reports for a zone are fed into the model as the `Accident_Report` feature, so a reported accident nudges the prediction.
- Since congestion predictions aren't stored rows, "resolving" one isn't a status flip — `POST /analytics/recommendations/{zone_id}/dismiss` instead records a time-boxed suppression window in `alert_dismissals`; the recommendation simply won't be regenerated for that zone until the cooldown expires.

**Analytics dashboard** (`Analytics.jsx`): congestion heatmap (`GET /analytics/heatmap`), hourly trend charts (`GET /analytics/trends`), road-type performance breakdown (`GET /analytics/road-performance`), and a client-side PDF export (`handleDownloadReport`, via jsPDF) that bundles the city-wide summary, AI recommendations, road performance, and heatmap snapshot into a single downloadable report.

## Authentication Flow

1. Client submits credentials to `POST /auth/login`.
2. Server verifies the password against the stored bcrypt hash.
3. On success, server issues a JWT containing the user ID and an expiry claim, signed with a server-side secret.
4. Client stores the token and attaches it as `Authorization: Bearer <token>` on all subsequent requests.
5. Protected routes use a FastAPI dependency (`get_current_user`) that decodes and validates the token on every request; admin-only routes additionally check `role == admin` via `require_admin`.

JWTs are stateless by design — no server-side session store is required, which keeps the API horizontally scalable.

---

## Known Limitations & Future Improvements

- **Secret management**: the JWT signing secret is currently a hardcoded placeholder in `auth.py`. In production this would be loaded from an environment variable or a secrets manager.
- **Token lifecycle**: tokens are valid for a flat 24 hours with no refresh mechanism. A production system would use short-lived access tokens paired with refresh tokens.
- **Polling vs. real-time push**: the dashboard polls every 5 seconds rather than using WebSockets/SSE. Acceptable at current scale; would need revisiting for high-concurrency or lower-latency requirements.
- **Single-database coupling in dev**: `DATABASE_URL` construction currently assumes PostgreSQL; the ORM abstraction means switching engines again would still only touch `database.py`.
- **No schema migration tool**: `Base.metadata.create_all()` creates tables that don't exist but never alters existing ones. Adding a column or enum value requires a full schema drop/recreate in development. A production system would use Alembic to generate proper `ALTER TABLE` migrations instead.
- **City-wide congestion proxy for routing**: route ETA adjustment currently uses an average of recent congestion readings across *all* zones, not congestion mapped to the specific road segments in each candidate route. A more precise version would match route geometry to nearby zones.
- **OSRM public demo server**: used for route optimization since it requires no billing/API key, but it's not meant for production traffic (undocumented rate limits, no uptime guarantee). Self-hosting OSRM or switching to a paid provider (Google Maps, Mapbox) is the natural production upgrade — swapping providers only touches `routers/routes.py`.
- **Prediction model trained on a synthetic Kaggle dataset**: EDA revealed the dataset's congestion labels are driven almost entirely by vehicle count, occupancy, and speed, with weather and time-of-day contributing very little (~1% feature importance each). The model correctly reflects this; validating against real-world or longer-running self-generated data is the natural next step for a more realistic accuracy figure. Full discussion in the root `README.md` (Milestone 2 section) and `ml/eda/EDA_SUMMARY.md`.
- **Model only predicts 3 classes**: the trained classifier's target is `low` / `medium` / `high` (from the training dataset), while live `traffic_data.congestion_level` also has a `severe` tier. The AI-driven recommendation engine treats `"high"` as the trigger condition since that's the model's ceiling — it can't distinguish "high" from "severe" the way the simulator's own rule-based labeling does. Retraining with a 4-class target (or bucketing `severe` into `high` at the label level) would close this gap.
