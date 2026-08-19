import os

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
