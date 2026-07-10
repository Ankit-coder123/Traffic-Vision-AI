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

import random
import time
from datetime import datetime

import requests

API_BASE_URL = "http://localhost:8000"

# Change these to a real admin account you create via /auth/signup
ADMIN_EMAIL = "admin@trafficvision.ai"
ADMIN_PASSWORD = "admin123"

# Seed zones - realistic Indian city road names as an example
SEED_ZONES = [
    {"name": "MG Road Junction", "latitude": 12.9756, "longitude": 77.6068, "road_type": "arterial"},
    {"name": "Outer Ring Road - Marathahalli", "latitude": 12.9569, "longitude": 77.7011, "road_type": "highway"},
    {"name": "Cantonment Station Road", "latitude": 25.3176, "longitude": 82.9739, "road_type": "local"},
    {"name": "Andheri Kurla Road", "latitude": 19.1136, "longitude": 72.8697, "road_type": "arterial"},
    {"name": "NH-44 Toll Plaza", "latitude": 28.4595, "longitude": 77.0266, "road_type": "highway"},
]


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
