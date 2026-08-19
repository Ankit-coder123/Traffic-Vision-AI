"""
Performance benchmark script for TrafficVision AI.

Measures real numbers against a RUNNING backend (local uvicorn or the
Docker deployment) -- nothing here is estimated or hardcoded. This exists
to answer the PDF's "Performance Metrics" and "Example Quantitative Goals"
sections (API response time, dashboard/heatmap generation speed, database
query behavior under concurrency) with actual measurements rather than
guesses.

Usage:
    # against local manual dev setup
    python scripts/benchmark.py

    # against Docker
    BASE_URL=http://localhost:8000 python scripts/benchmark.py

    # with different credentials than the simulator's default seed admin
    ADMIN_EMAIL=you@example.com ADMIN_PASSWORD=yourpass python scripts/benchmark.py

Requires the backend (and its database) to actually be running with some
data in it -- run the simulator for a few minutes first, or the "requests
per zone" numbers below will be based on very little traffic_data.
"""

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@trafficvision.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Endpoints exercised for the single-request latency benchmark, chosen to
# cover each "Performance Metrics" category from the project brief:
#   - Analytics Performance: summary, heatmap, trends, road-performance
#   - Traffic Prediction Performance: predict/congestion
ENDPOINTS = [
    ("GET", "/analytics/summary", None),
    ("GET", "/analytics/heatmap", None),
    ("GET", "/analytics/trends?hours=24", None),
    ("GET", "/analytics/road-performance", None),
    ("GET", "/analytics/recommendations", None),
    ("GET", "/traffic/zones", None),
    (
        "POST",
        "/predict/congestion",
        {
            "vehicle_count": 180,
            "avg_speed_kmph": 22.0,
            "road_occupancy_pct": 65.0,
            "weather_condition": "Clear",
        },
    ),
]

RUNS_PER_ENDPOINT = 20        # single-request latency sample size
CONCURRENCY_LEVELS = [1, 5, 10, 20]   # simultaneous requests, for the throughput test
CONCURRENCY_ENDPOINT = ("GET", "/analytics/summary")  # what the concurrency test hammers


def get_two_zone_ids(token: str):
    """Route optimization needs two real zone IDs to test against -- fetch
    whatever's actually in this deployment rather than hardcoding IDs that
    would only happen to match one specific database."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/traffic/zones", headers=headers, timeout=10)
    resp.raise_for_status()
    zones = resp.json()
    if len(zones) < 2:
        return None
    return zones[0]["id"], zones[1]["id"]


def login() -> str:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def timed_request(method: str, path: str, token: str, json_body=None) -> float:
    headers = {"Authorization": f"Bearer {token}"}
    start = time.perf_counter()
    if method == "GET":
        r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=15)
    else:
        r = requests.post(f"{BASE_URL}{path}", headers=headers, json=json_body, timeout=15)
    elapsed_ms = (time.perf_counter() - start) * 1000
    r.raise_for_status()
    return elapsed_ms


def percentile(values, p):
    values = sorted(values)
    idx = int(len(values) * p) - 1
    return values[max(0, min(idx, len(values) - 1))]


def run_latency_benchmark(token: str):
    print(f"\n{'Endpoint':<32} {'min':>7} {'p50':>7} {'p95':>7} {'max':>7}   (ms, n={RUNS_PER_ENDPOINT})")
    print("-" * 72)
    results = {}
    for method, path, body in ENDPOINTS:
        samples = []
        for _ in range(RUNS_PER_ENDPOINT):
            try:
                samples.append(timed_request(method, path, token, body))
            except requests.RequestException as e:
                print(f"  ! {path} failed: {e}")
                break
        if samples:
            results[path] = samples
            print(
                f"{path:<32} {min(samples):>6.1f}  {statistics.median(samples):>6.1f}  "
                f"{percentile(samples, 0.95):>6.1f}  {max(samples):>6.1f}"
            )
    return results


def run_concurrency_benchmark(token: str):
    method, path = CONCURRENCY_ENDPOINT
    print(f"\nConcurrency test: {method} {path}")
    print(f"{'Concurrent requests':<22} {'total time':>12} {'req/sec':>10} {'failures':>10}")
    print("-" * 58)
    for level in CONCURRENCY_LEVELS:
        failures = 0
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=level) as pool:
            futures = [pool.submit(timed_request, method, path, token) for _ in range(level)]
            for f in as_completed(futures):
                try:
                    f.result()
                except requests.RequestException:
                    failures += 1
        total_s = time.perf_counter() - start
        throughput = level / total_s if total_s > 0 else float("inf")
        print(f"{level:<22} {total_s * 1000:>10.1f}ms {throughput:>9.1f}   {failures:>10}")


def main():
    print(f"Benchmarking {BASE_URL}")
    try:
        token = login()
    except requests.RequestException as e:
        print(f"Could not log in as {ADMIN_EMAIL}: {e}")
        print("Is the backend running? Does this admin account exist?")
        return

    # /routes/optimize needs real zone IDs and calls the external OSRM
    # service -- added dynamically so a fresh deployment with no zones yet
    # doesn't crash the whole benchmark, and NOTE: this endpoint depends on
    # router.project-osrm.org being reachable from wherever you run this.
    # It was NOT reachable when this script was developed (network egress
    # restrictions in that dev environment) -- run this yourself on your
    # own machine/Docker host to get a real number for this one.
    zone_pair = get_two_zone_ids(token)
    if zone_pair:
        origin_id, dest_id = zone_pair
        ENDPOINTS.append((
            "POST",
            "/routes/optimize",
            {"origin_zone_id": origin_id, "destination_zone_id": dest_id},
        ))
    else:
        print("Skipping /routes/optimize -- need at least 2 zones in the DB (run the simulator first).")

    run_latency_benchmark(token)
    run_concurrency_benchmark(token)


if __name__ == "__main__":
    main()
