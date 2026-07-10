# TrafficVision AI — Frontend

React dashboard for live traffic monitoring, built with Vite and Tailwind CSS.

## Tech Stack
- **React 18 + Vite** — fast dev server, minimal config
- **Tailwind CSS** — utility-first styling, custom "control room" theme
- **React Router** — client-side routing with protected routes
- **Axios** — HTTP client with JWT-attaching interceptors
- **Recharts** — planned for historical data charts (Week 3+)

## Setup

```bash
npm install
npm run dev
```

Runs at `http://localhost:5173`. Requires the backend running at `http://localhost:8000` (see `../backend/README.md`).

## Login

Use the admin account created by the backend's `simulator.py`:
- Email: `admin@trafficvision.ai`
- Password: `admin123`

## Design

The dashboard uses a dark "traffic control console" visual identity rather than a generic admin template — signal colors (green/amber/orange/red) encode congestion level, and live-pulse indicators signal real-time data. Theme tokens are defined in `tailwind.config.js` under the `console` and `signal` color groups.

## Project layout

```
src/
├── api/client.js              # Axios instance, JWT interceptor, auto-logout on 401
├── context/AuthContext.jsx    # Global auth state (user, login, logout)
├── components/
│   ├── ProtectedRoute.jsx     # Route guard for authenticated pages
│   └── ZoneCard.jsx           # Per-zone live status card
└── pages/
    ├── Login.jsx              # Auth screen
    └── Dashboard.jsx          # Polls /traffic/live every 5s, renders zone grid
```

## Notes on implementation choices

- **Polling, not WebSockets**: `Dashboard.jsx` polls the backend every 5 seconds via `setInterval`. Simpler to implement/debug for this milestone; a documented tradeoff for future real-time work.
- **Tailwind dynamic classes**: congestion-level styling uses a lookup object of full literal class strings (see `ZoneCard.jsx`) rather than template-string-constructed classes, since Tailwind's compiler can't resolve dynamically built class names at build time.

## Build for production

```bash
npm run build
```

Output goes to `dist/`. Verified to build cleanly with no errors or warnings.
