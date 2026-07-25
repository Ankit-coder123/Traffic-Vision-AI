# TrafficVision AI — Frontend

React dashboard for live traffic monitoring, AI congestion prediction, route optimization, and incident reporting — built with Vite and Tailwind CSS.

## Tech Stack
- **React 18 + Vite** — fast dev server, minimal config
- **Tailwind CSS** — utility-first styling, custom "control room" theme
- **React Router** — client-side routing with protected routes
- **Axios** — HTTP client with JWT-attaching interceptors
- **Leaflet / react-leaflet** — interactive route maps over OpenStreetMap tiles

## Setup

```bash
npm install
npm run dev
```

Runs at `http://localhost:5173`. Requires the backend running at `http://localhost:8000` (see `../backend/README.md`).

> If you're pulling an update that added new dependencies (e.g. Leaflet), always re-run `npm install` even if `node_modules` already exists — skipping it causes silent "module not found" errors.

## Accounts

- **Bootstrap admin** (created by `simulator.py`): `admin@trafficvision.ai` / `admin123`
- **New users** can self-register via the Signup page, choosing between **Public User** and **Traffic Operator**. Admin can never be self-assigned through the public signup form.

## Pages

| Route | Access | Purpose |
|---|---|---|
| `/login` | Public | Sign in |
| `/signup` | Public | Create an account (User or Operator), with live password strength meter |
| `/dashboard` | All roles | Live monitoring — 22 Bangalore zone cards, polling every 5s |
| `/prediction` | All roles | Congestion forecasting — sliders, weather, time-of-day, scenario presets |
| `/routes` | All roles | Route optimization — origin/destination, map, saved routes |
| `/incidents` | All roles view; Operator/Admin can report | Active incident list + report form |

## Design

The dashboard uses a dark "traffic control console" visual identity rather than a generic admin template — signal colors (green/amber/orange/red) encode congestion level, and live-pulse indicators signal real-time data. Theme tokens are defined in `tailwind.config.js` under the `console` and `signal` color groups. Role badges in the nav bar (Admin/Operator/User) use distinct colors and icons so the logged-in account's permissions are visible at a glance.

## Project layout

```
src/
├── api/client.js              # Axios instance, JWT interceptor, auto-logout on 401
│                                 # exposes authApi, trafficApi, predictionApi, routesApi, incidentsApi
├── context/AuthContext.jsx    # Global auth state (user, login, signup, logout)
├── components/
│   ├── NavBar.jsx             # Role badges + role-based nav link visibility
│   ├── ProtectedRoute.jsx     # Route guard for authenticated pages
│   └── ZoneCard.jsx           # Per-zone live status card
└── pages/
    ├── Login.jsx / Signup.jsx
    ├── Dashboard.jsx          # Live monitoring
    ├── Prediction.jsx         # Congestion forecasting UI
    ├── Routes.jsx             # Route optimization + Leaflet map + saved routes
    └── Incidents.jsx          # Incident reporting (role-conditional) + viewing
```

## Notes on implementation choices

- **Polling, not WebSockets**: `Dashboard.jsx` polls the backend every 5 seconds via `setInterval`. Simpler to implement/debug for this project's scope; a documented tradeoff for future real-time work.
- **Tailwind dynamic classes**: congestion-level styling uses lookup objects of full literal class strings (see `ZoneCard.jsx`, `Prediction.jsx`) rather than template-string-constructed classes, since Tailwind's compiler can't resolve dynamically built class names at build time.
- **Role-based UI, backed by real server-side checks**: hiding the "Report Incident" form or the "Incidents" nav link from non-operator roles is a UX convenience, not the actual security boundary — the backend independently rejects unauthorized requests (`403`) regardless of what the frontend shows.
- **Leaflet marker icon fix**: Leaflet's default marker icons break under Vite's bundler unless explicitly re-pointed at packaged asset URLs — handled at the top of `Routes.jsx`, not a config mistake if you see it there.

## Build for production

```bash
npm run build
```

Output goes to `dist/`. Verified to build cleanly with no errors or warnings.
