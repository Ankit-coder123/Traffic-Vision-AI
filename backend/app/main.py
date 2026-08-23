import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, traffic, prediction, routes, incidents, analytics

# Creates tables in trafficvision.db if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TrafficVision AI",
    description="Smart Traffic Prediction & Congestion Management System API",
    version="0.1.0",
)

# Allow the React frontend (running on a different port, or a different
# domain entirely once deployed) to call this API.
_extra_origin = os.getenv("FRONTEND_URL")  # e.g. https://trafficvision-ai.onrender.com
_allow_origins = [
    "http://localhost:5173",
    "http://localhost:5174",  # Vite falls back to this if 5173 is already in use
    "http://localhost:5175",  # ...and this if both are taken
]
if _extra_origin:
    _allow_origins.append(_extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(traffic.router)
app.include_router(prediction.router)
app.include_router(routes.router)
app.include_router(incidents.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {"message": "TrafficVision AI backend is running"}


@app.on_event("startup")
def _maybe_start_simulator():
    """Render's free plan doesn't support Background Worker services (only
    Web Services and Static Sites) -- so trafficvision-simulator can't be
    deployed as its own service without a paid plan. Since simulator.py
    only ever talks to the API over plain HTTP (never imports backend
    internals directly), we can run its exact same loop in a background
    thread inside this web service process instead: it POSTs to
    http://localhost:8000 rather than a separate 'backend' container, but
    the simulation logic itself is completely unchanged.

    Only enabled via RUN_SIMULATOR=true (set on Render; left unset in
    docker-compose.yml, which still runs the simulator as its own
    container locally -- both approaches are equally valid, this one just
    fits Render's free tier).
    """
    if os.getenv("RUN_SIMULATOR", "false").lower() != "true":
        return

    def _run():
        os.environ.setdefault("API_BASE_URL", "http://localhost:8000")
        import simulator  # backend/simulator.py -- same file used locally

        simulator.run_simulation()

    threading.Thread(target=_run, daemon=True, name="simulator").start()
