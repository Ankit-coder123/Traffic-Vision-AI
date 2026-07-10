from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, traffic

# Creates tables in trafficvision.db if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TrafficVision AI",
    description="Smart Traffic Prediction & Congestion Management System API",
    version="0.1.0",
)

# Allow the React frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(traffic.router)


@app.get("/")
def root():
    return {"message": "TrafficVision AI backend is running"}
