# Architecture — Week 1 & 2 (Milestone 1)

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
