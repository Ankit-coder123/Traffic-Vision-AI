"""
TrafficVision AI - Traffic Data Simulator
-------------------------------------------
Since we don't have real road sensors, this script simulates live traffic
feeds by generating realistic vehicle-count / speed / congestion readings
for each traffic zone, on a repeating interval.

Run this in a SEPARATE terminal while your FastAPI server is running:
    python simulator.py

It talks to the API over HTTP, exactly like a real sensor gateway would.
"""

import os
import random
import time
from datetime import datetime

import requests

# In docker-compose this is set to http://backend:8000 (the service name
# doubles as the DNS hostname on the compose network). Defaults to
# localhost for running the simulator directly on your machine.
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Change these to a real admin account you create via /auth/signup
ADMIN_EMAIL = os.getenv("SIMULATOR_ADMIN_EMAIL", "admin@trafficvision.ai")
ADMIN_PASSWORD = os.getenv("SIMULATOR_ADMIN_PASSWORD", "admin123")

# Seed zones - realistic Indian city road names as an example
# All zones are real locations within Bangalore, India -- scoped to a single
# city so route optimization produces meaningful in-city distances/times,
# and the live dashboard/heatmap reads as one coherent traffic network
# rather than disconnected points scattered across the country.
CITY_NAME = "Bangalore"

SEED_ZONES = [
    # Central
    {"name": "MG Road Junction", "latitude": 12.9756, "longitude": 77.6068, "road_type": "arterial"},
    {"name": "Indiranagar 100 Feet Road", "latitude": 12.9719, "longitude": 77.6412, "road_type": "arterial"},
    {"name": "Domlur Flyover", "latitude": 12.9611, "longitude": 77.6387, "road_type": "arterial"},
    # East
    {"name": "Outer Ring Road - Marathahalli", "latitude": 12.9569, "longitude": 77.7011, "road_type": "highway"},
    {"name": "Whitefield Main Road", "latitude": 12.9698, "longitude": 77.7500, "road_type": "arterial"},
    {"name": "KR Puram Bridge", "latitude": 13.0027, "longitude": 77.6958, "road_type": "highway"},
    {"name": "Bellandur Junction", "latitude": 12.9257, "longitude": 77.6784, "road_type": "arterial"},
    {"name": "Sarjapur Road Junction", "latitude": 12.9020, "longitude": 77.6870, "road_type": "arterial"},
    # South
    {"name": "Silk Board Junction", "latitude": 12.9172, "longitude": 77.6228, "road_type": "highway"},
    {"name": "Electronic City Toll", "latitude": 12.8452, "longitude": 77.6602, "road_type": "highway"},
    {"name": "Koramangala Sony Signal", "latitude": 12.9352, "longitude": 77.6245, "road_type": "arterial"},
    {"name": "HSR Layout Sector 7", "latitude": 12.9116, "longitude": 77.6389, "road_type": "local"},
    {"name": "BTM Layout Junction", "latitude": 12.9166, "longitude": 77.6101, "road_type": "arterial"},
    {"name": "Jayanagar 4th Block", "latitude": 12.9308, "longitude": 77.5838, "road_type": "local"},
    {"name": "Banashankari Bus Stand", "latitude": 12.9250, "longitude": 77.5665, "road_type": "arterial"},
    {"name": "Bannerghatta Road Junction", "latitude": 12.8988, "longitude": 77.5987, "road_type": "highway"},
    # North / West
    {"name": "Hebbal Flyover", "latitude": 13.0358, "longitude": 77.5970, "road_type": "highway"},
    {"name": "Yeshwanthpur Junction", "latitude": 13.0284, "longitude": 77.5540, "road_type": "local"},
    {"name": "Rajajinagar", "latitude": 12.9910, "longitude": 77.5550, "road_type": "arterial"},
    {"name": "Peenya Industrial Area", "latitude": 13.0280, "longitude": 77.5200, "road_type": "highway"},
    {"name": "Nagawara Junction", "latitude": 13.0428, "longitude": 77.6208, "road_type": "arterial"},
    {"name": "Vijayanagar", "latitude": 12.9719, "longitude": 77.5330, "road_type": "local"},
]


def wait_for_backend(timeout_seconds: int = 60) -> None:
    """Only matters in docker-compose: the backend container can take a few
    seconds to finish connecting to Postgres and creating tables after it
    starts, so a simulator container starting at the same time needs to
    poll rather than assume the API is immediately reachable."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            if requests.get(f"{API_BASE_URL}/", timeout=3).status_code == 200:
                return
        except requests.exceptions.RequestException:
            pass
        print(f"Waiting for backend at {API_BASE_URL} ...")
        time.sleep(2)
    raise RuntimeError(f"Backend at {API_BASE_URL} did not become ready in {timeout_seconds}s")


def get_token() -> str:
    """Log in as admin and get a JWT. Creates the admin account on first run."""
    login_resp = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if login_resp.status_code == 200:
        return login_resp.json()["access_token"]

    # Account doesn't exist yet -> create it
    signup_resp = requests.post(
        f"{API_BASE_URL}/auth/signup",
        json={
            "name": "Admin",
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "role": "admin",
        },
    )
    signup_resp.raise_for_status()
    print("Created admin account:", ADMIN_EMAIL)

    login_resp = requests.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    login_resp.raise_for_status()
    return login_resp.json()["access_token"]


def ensure_zones_exist(token: str) -> list:
    headers = {"Authorization": f"Bearer {token}"}
    existing = requests.get(f"{API_BASE_URL}/traffic/zones", headers=headers).json()

    if existing:
        return existing

    created = []
    for zone in SEED_ZONES:
        resp = requests.post(f"{API_BASE_URL}/traffic/zones", json=zone, headers=headers)
        resp.raise_for_status()
        created.append(resp.json())
        print(f"Created zone: {zone['name']}")
    return created


def generate_reading(road_type: str) -> dict:
    """
    Produces a semi-realistic reading. Highways support more vehicles at
    higher speed before congestion kicks in; local roads congest faster.
    """
    hour = datetime.now().hour
    is_peak = hour in (8, 9, 10, 17, 18, 19, 20)  # rough morning/evening rush hours

    base_capacity = {"highway": 300, "arterial": 180, "local": 90}.get(road_type, 150)
    vehicle_count = int(base_capacity * (random.uniform(0.7, 1.3) if is_peak else random.uniform(0.2, 0.7)))

    # More vehicles -> lower average speed
    congestion_ratio = vehicle_count / base_capacity
    max_speed = {"highway": 100, "arterial": 60, "local": 40}.get(road_type, 50)
    avg_speed = max(5, max_speed * (1 - min(congestion_ratio, 1) * 0.85) + random.uniform(-5, 5))

    if congestion_ratio < 0.5:
        level = "low"
    elif congestion_ratio < 0.85:
        level = "medium"
    elif congestion_ratio < 1.15:
        level = "high"
    else:
        level = "severe"

    return {
        "vehicle_count": vehicle_count,
        "avg_speed_kmph": round(avg_speed, 1),
        "congestion_level": level,
    }


def run_simulation(interval_seconds: int = 5):
    wait_for_backend()
    token = get_token()
    zones = ensure_zones_exist(token)
    headers = {"Authorization": f"Bearer {token}"}

    print(f"\nSimulating live traffic for {len(zones)} zones every {interval_seconds}s. Ctrl+C to stop.\n")

    try:
        while True:
            for zone in zones:
                reading = generate_reading(zone["road_type"])
                payload = {**reading, "zone_id": zone["id"]}
                resp = requests.post(f"{API_BASE_URL}/traffic/data", json=payload, headers=headers)
                resp.raise_for_status()
                print(f"{zone['name']:35s} | {reading['congestion_level']:7s} | "
                      f"{reading['vehicle_count']:4d} vehicles | {reading['avg_speed_kmph']:5.1f} km/h")
            print("-" * 80)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")


if __name__ == "__main__":
    run_simulation()
