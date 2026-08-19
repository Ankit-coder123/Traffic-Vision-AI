"""Milestone 3 -- Analytics Dashboard Module + AI-driven recommendations.

Where a computation is purely deterministic arithmetic over data we
control (summary, heatmap, road-performance, trends, road-conditions),
tests assert exact values. Where a computation runs through the trained
ML model (get_recommendations' "congestion" source), tests only assert
structural correctness and the parts of the logic that are NOT
model-dependent (severity ordering, dismiss/incident interaction) --
see test_prediction.py's docstring for why exact-label assertions on the
model are avoided.
"""
from tests.helpers import post_reading


def _make_zone(client, admin_auth, name, road_type="arterial", lat=1.0, lng=1.0):
    resp = client.post(
        "/traffic/zones",
        json={"name": name, "latitude": lat, "longitude": lng, "road_type": road_type},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 200
    return resp.json()


# ---------- Summary ----------

def test_summary_requires_auth(client):
    resp = client.get("/analytics/summary")
    assert resp.status_code == 401


def test_summary_empty_platform(client, user_auth):
    resp = client.get("/analytics/summary", headers=user_auth["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_zones"] == 0
    assert body["active_incidents"] == 0
    assert body["busiest_zone"] is None
    assert body["city_avg_speed_kmph"] is None


def test_summary_reflects_zones_incidents_and_busiest_zone(client, admin_auth, operator_auth):
    headers = admin_auth["headers"]
    zone_a = _make_zone(client, admin_auth, "Zone A")
    zone_b = _make_zone(client, admin_auth, "Zone B")

    post_reading(client, headers, zone_a["id"], vehicle_count=250, avg_speed_kmph=8, congestion_level="high")
    post_reading(client, headers, zone_b["id"], vehicle_count=20, avg_speed_kmph=55, congestion_level="low")

    client.post(
        "/incidents",
        json={"zone_id": zone_a["id"], "incident_type": "accident", "severity": "major"},
        headers=operator_auth["headers"],
    )

    resp = client.get("/analytics/summary", headers=headers)
    body = resp.json()
    assert body["total_zones"] == 2
    assert body["active_incidents"] == 1
    assert body["busiest_zone"] == "Zone A"
    assert body["congestion_distribution"]["high"] == 1
    assert body["congestion_distribution"]["low"] == 1
    assert body["city_avg_speed_kmph"] == round((8 + 55) / 2, 1)


# ---------- Heatmap ----------

def test_heatmap_uses_latest_reading_per_zone(client, admin_auth):
    headers = admin_auth["headers"]
    zone_a = _make_zone(client, admin_auth, "Zone A")
    post_reading(client, headers, zone_a["id"], vehicle_count=10, avg_speed_kmph=50, congestion_level="low")
    post_reading(client, headers, zone_a["id"], vehicle_count=99, avg_speed_kmph=15, congestion_level="high")

    resp = client.get("/analytics/heatmap", headers=headers)
    assert resp.status_code == 200
    point = resp.json()[0]
    assert point["congestion_level"] == "high"
    assert point["vehicle_count"] == 99


def test_heatmap_defaults_to_low_with_no_readings(client, zone, admin_auth):
    resp = client.get("/analytics/heatmap", headers=admin_auth["headers"])
    point = resp.json()[0]
    assert point["congestion_level"] == "low"
    assert point["vehicle_count"] is None


# ---------- Road performance ----------

def test_road_performance_groups_by_road_type(client, admin_auth):
    headers = admin_auth["headers"]
    highway = _make_zone(client, admin_auth, "Highway Zone", road_type="highway")
    local = _make_zone(client, admin_auth, "Local Zone", road_type="local")

    post_reading(client, headers, highway["id"], vehicle_count=200, avg_speed_kmph=80, congestion_level="low")
    post_reading(client, headers, local["id"], vehicle_count=30, avg_speed_kmph=25, congestion_level="medium")

    resp = client.get("/analytics/road-performance", headers=headers)
    assert resp.status_code == 200
    by_type = {r["road_type"]: r for r in resp.json()}

    assert by_type["highway"]["avg_speed_kmph"] == 80.0
    assert by_type["highway"]["reading_count"] == 1
    assert by_type["local"]["avg_speed_kmph"] == 25.0

    # Highway must be ordered before local (road hierarchy)
    road_types_in_order = [r["road_type"] for r in resp.json()]
    assert road_types_in_order.index("highway") < road_types_in_order.index("local")


def test_road_performance_zero_readings_road_type(client, zone, admin_auth):
    """A road type with zones but zero readings in the window still
    appears, with zeroed-out stats rather than being silently dropped."""
    resp = client.get("/analytics/road-performance", headers=admin_auth["headers"])
    body = resp.json()
    assert len(body) == 1
    assert body[0]["reading_count"] == 0
    assert body[0]["avg_speed_kmph"] == 0.0
    assert body[0]["worst_zone"] is None


# ---------- Trends ----------

def test_trends_bucket_and_average_readings(client, zone, admin_auth):
    headers = admin_auth["headers"]
    post_reading(client, headers, zone["id"], vehicle_count=100, avg_speed_kmph=40, congestion_level="low")
    post_reading(client, headers, zone["id"], vehicle_count=200, avg_speed_kmph=20, congestion_level="high")

    resp = client.get(f"/analytics/trends?zone_id={zone['id']}", headers=headers)
    assert resp.status_code == 200
    zone_trend = resp.json()[0]
    assert zone_trend["zone_id"] == zone["id"]
    # Both readings inserted seconds apart -> same hourly bucket
    assert len(zone_trend["points"]) == 1
    point = zone_trend["points"][0]
    assert point["avg_vehicle_count"] == 150.0
    assert point["avg_speed_kmph"] == 30.0
    assert point["congestion_score"] == 1.0  # avg of low(0) and high(2)


def test_trends_requires_auth(client):
    resp = client.get("/analytics/trends")
    assert resp.status_code == 401


# ---------- Recommendations ----------

def test_recommendations_requires_auth(client):
    resp = client.get("/analytics/recommendations")
    assert resp.status_code == 401


def test_recommendations_includes_active_incident(client, zone, operator_auth):
    client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "major"},
        headers=operator_auth["headers"],
    )
    resp = client.get("/analytics/recommendations", headers=operator_auth["headers"])
    assert resp.status_code == 200
    incident_recs = [r for r in resp.json() if r["source"] == "incident"]
    assert len(incident_recs) == 1
    assert incident_recs[0]["zone_id"] == zone["id"]
    assert incident_recs[0]["severity"] == "critical"  # major incident -> critical


def test_recommendations_minor_incident_is_warning_not_critical(client, zone, operator_auth):
    client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "hazard", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    resp = client.get("/analytics/recommendations", headers=operator_auth["headers"])
    incident_recs = [r for r in resp.json() if r["source"] == "incident"]
    assert incident_recs[0]["severity"] == "warning"


def test_recommendations_sorted_critical_first(client, admin_auth, operator_auth):
    zone_a = _make_zone(client, admin_auth, "Zone A")
    zone_b = _make_zone(client, admin_auth, "Zone B")

    client.post(
        "/incidents",
        json={"zone_id": zone_a["id"], "incident_type": "hazard", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    client.post(
        "/incidents",
        json={"zone_id": zone_b["id"], "incident_type": "accident", "severity": "major"},
        headers=operator_auth["headers"],
    )

    resp = client.get("/analytics/recommendations", headers=operator_auth["headers"])
    severities = [r["severity"] for r in resp.json()]
    assert severities.index("critical") < severities.index("warning")


def test_dismiss_requires_operator_or_admin(client, zone, user_auth):
    resp = client.post(f"/analytics/recommendations/{zone['id']}/dismiss", headers=user_auth["headers"])
    assert resp.status_code == 403


def test_dismiss_unknown_zone_404s(client, operator_auth):
    resp = client.post("/analytics/recommendations/9999/dismiss", headers=operator_auth["headers"])
    assert resp.status_code == 404


def test_dismiss_does_not_suppress_incident_recommendations(client, zone, operator_auth):
    """Dismissal only cools down the ML-driven 'congestion' alerts for a
    zone -- an active human-reported incident on that same zone must keep
    showing up regardless, per get_recommendations()/dismiss_congestion_alert()'s
    documented behavior."""
    client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "major"},
        headers=operator_auth["headers"],
    )

    dismiss_resp = client.post(
        f"/analytics/recommendations/{zone['id']}/dismiss", headers=operator_auth["headers"]
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["zone_id"] == zone["id"]

    resp = client.get("/analytics/recommendations", headers=operator_auth["headers"])
    incident_recs = [r for r in resp.json() if r["source"] == "incident"]
    assert len(incident_recs) == 1  # still present after dismissal


# ---------- Peak hours ----------

def test_peak_hours_404_with_no_data(client, zone, admin_auth):
    resp = client.get(f"/analytics/peak-hours?zone_id={zone['id']}", headers=admin_auth["headers"])
    assert resp.status_code == 404


def test_peak_hours_requires_auth(client):
    resp = client.get("/analytics/peak-hours")
    assert resp.status_code == 401


def test_peak_hours_with_data_returns_summary(client, zone, admin_auth):
    headers = admin_auth["headers"]
    for _ in range(3):
        post_reading(client, headers, zone["id"], vehicle_count=100, avg_speed_kmph=30, congestion_level="medium")

    resp = client.get(f"/analytics/peak-hours?zone_id={zone['id']}&days=7", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["zone_id"] == zone["id"]
    assert body["zone_name"] == "MG Road Junction"
    assert body["total_readings_analyzed"] == 3
    assert isinstance(body["summary"], str) and len(body["summary"]) > 0
    assert len(body["hourly_pattern"]) >= 1


def test_peak_hours_unknown_zone_404s(client, admin_auth):
    resp = client.get("/analytics/peak-hours?zone_id=9999", headers=admin_auth["headers"])
    assert resp.status_code == 404


# ---------- Road conditions ----------

def test_road_conditions_status_precedence(client, admin_auth, operator_auth):
    headers = admin_auth["headers"]

    closed_zone = _make_zone(client, admin_auth, "Closed Zone")
    impaired_zone = _make_zone(client, admin_auth, "Impaired Zone")
    congested_zone = _make_zone(client, admin_auth, "Congested Zone")
    normal_zone = _make_zone(client, admin_auth, "Normal Zone")

    client.post(
        "/incidents",
        json={"zone_id": closed_zone["id"], "incident_type": "road_closure", "severity": "major"},
        headers=operator_auth["headers"],
    )
    client.post(
        "/incidents",
        json={"zone_id": impaired_zone["id"], "incident_type": "accident", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    post_reading(client, headers, congested_zone["id"], vehicle_count=250, avg_speed_kmph=8, congestion_level="high")
    post_reading(client, headers, normal_zone["id"], vehicle_count=20, avg_speed_kmph=55, congestion_level="low")

    resp = client.get("/analytics/road-conditions", headers=headers)
    assert resp.status_code == 200
    status_by_zone = {r["zone_name"]: r["status"] for r in resp.json()}

    assert status_by_zone["Closed Zone"] == "closed"
    assert status_by_zone["Impaired Zone"] == "impaired"
    assert status_by_zone["Congested Zone"] == "congested"
    assert status_by_zone["Normal Zone"] == "normal"

    # Worst-first ordering
    ordered_statuses = [r["status"] for r in resp.json()]
    assert ordered_statuses == ["closed", "impaired", "congested", "normal"]


def test_road_conditions_requires_auth(client):
    resp = client.get("/analytics/road-conditions")
    assert resp.status_code == 401
