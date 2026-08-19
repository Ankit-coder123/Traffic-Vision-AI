"""Milestone 2 -- Traffic Prediction Module.

These tests call through to the real trained RandomForest model
(app/congestion_model.joblib) rather than mocking it -- the point of the
prediction endpoint IS the model, so a mock would only be testing the
FastAPI plumbing around it. Assertions are deliberately kept to
"is this a well-formed prediction" (valid class, confidence in range,
probabilities sum to ~1) rather than "predicts exactly X for this input,"
since asserting an exact class would make the suite brittle to any future
retrain -- that kind of accuracy/regression check belongs in the ml/
training pipeline's own evaluation step, not here.
"""
VALID_CONGESTION_LABELS = {"low", "medium", "high"}


def test_predict_congestion_requires_auth(client):
    resp = client.post(
        "/predict/congestion",
        json={"vehicle_count": 100, "avg_speed_kmph": 40, "road_occupancy_pct": 50},
    )
    assert resp.status_code == 401


def test_predict_congestion_returns_well_formed_response(client, user_auth):
    resp = client.post(
        "/predict/congestion",
        json={
            "vehicle_count": 150,
            "avg_speed_kmph": 25,
            "road_occupancy_pct": 70,
            "weather_condition": "Clear",
        },
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["predicted_congestion"] in VALID_CONGESTION_LABELS
    assert 0.0 <= body["confidence"] <= 1.0

    probs = body["probabilities"]
    assert set(probs.keys()) == VALID_CONGESTION_LABELS
    assert abs(sum(probs.values()) - 1.0) < 1e-6
    # The predicted label should be the highest-probability class
    assert body["predicted_congestion"] == max(probs, key=probs.get)


def test_predict_congestion_light_traffic_input(client, user_auth):
    """Free-flowing conditions (few vehicles, high speed, low occupancy)
    should not be classified as the most severe class -- a sanity check on
    the model's directionality without pinning an exact label."""
    resp = client.post(
        "/predict/congestion",
        json={
            "vehicle_count": 5,
            "avg_speed_kmph": 80,
            "road_occupancy_pct": 5,
            "weather_condition": "Clear",
            "hour": 3,       # 3am, not rush hour
            "is_weekend": True,
        },
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["predicted_congestion"] != "high"


def test_predict_congestion_heavy_traffic_input(client, user_auth):
    """Gridlock-style conditions (near-capacity occupancy, crawling speed)
    should not be classified as the least severe class."""
    resp = client.post(
        "/predict/congestion",
        json={
            "vehicle_count": 280,
            "avg_speed_kmph": 4,
            "road_occupancy_pct": 98,
            "weather_condition": "Rain",
            "hour": 18,      # evening rush hour
            "is_weekend": False,
        },
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["predicted_congestion"] != "low"


def test_predict_congestion_is_logged_to_reports(client, user_auth):
    client.post(
        "/predict/congestion",
        json={"vehicle_count": 100, "avg_speed_kmph": 30, "road_occupancy_pct": 60},
        headers=user_auth["headers"],
    )
    resp = client.get("/predict/reports", headers=user_auth["headers"])
    assert resp.status_code == 200
    reports = resp.json()
    assert len(reports) == 1
    assert reports[0]["vehicle_count"] == 100
    assert reports[0]["predicted_congestion"] in VALID_CONGESTION_LABELS


def test_prediction_reports_most_recent_first(client, user_auth):
    for count in (50, 100, 150):
        client.post(
            "/predict/congestion",
            json={"vehicle_count": count, "avg_speed_kmph": 30, "road_occupancy_pct": 50},
            headers=user_auth["headers"],
        )
    resp = client.get("/predict/reports", headers=user_auth["headers"])
    reports = resp.json()
    assert len(reports) == 3
    assert reports[0]["vehicle_count"] == 150  # most recently created


def test_prediction_reports_respects_limit(client, user_auth):
    for count in range(5):
        client.post(
            "/predict/congestion",
            json={"vehicle_count": count, "avg_speed_kmph": 30, "road_occupancy_pct": 50},
            headers=user_auth["headers"],
        )
    resp = client.get("/predict/reports?limit=2", headers=user_auth["headers"])
    assert len(resp.json()) == 2


def test_prediction_reports_requires_auth(client):
    resp = client.get("/predict/reports")
    assert resp.status_code == 401
