"""Milestone 1 -- Traffic Monitoring Module."""
from tests.helpers import post_reading


def test_create_zone_requires_admin(client, operator_auth):
    resp = client.post(
        "/traffic/zones",
        json={"name": "Should Fail", "latitude": 1.0, "longitude": 1.0},
        headers=operator_auth["headers"],
    )
    assert resp.status_code == 403


def test_create_zone_rejects_regular_user(client, user_auth):
    resp = client.post(
        "/traffic/zones",
        json={"name": "Should Fail", "latitude": 1.0, "longitude": 1.0},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 403


def test_create_zone_as_admin_succeeds(client, admin_auth):
    resp = client.post(
        "/traffic/zones",
        json={"name": "Outer Ring Road", "latitude": 12.93, "longitude": 77.62, "road_type": "highway"},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Outer Ring Road"
    assert body["road_type"] == "highway"
    assert "id" in body


def test_create_zone_defaults_road_type_to_arterial(client, admin_auth):
    resp = client.post(
        "/traffic/zones",
        json={"name": "No Road Type Given", "latitude": 1.0, "longitude": 1.0},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["road_type"] == "arterial"


def test_list_zones_requires_auth(client):
    resp = client.get("/traffic/zones")
    assert resp.status_code == 401


def test_list_zones_any_authenticated_role(client, zone, user_auth):
    resp = client.get("/traffic/zones", headers=user_auth["headers"])
    assert resp.status_code == 200
    names = [z["name"] for z in resp.json()]
    assert "MG Road Junction" in names


def test_ingest_traffic_data_any_authenticated_role(client, zone, user_auth):
    reading = post_reading(
        client, user_auth["headers"], zone["id"],
        vehicle_count=120, avg_speed_kmph=35.5, congestion_level="medium",
    )
    assert reading["zone_id"] == zone["id"]
    assert reading["congestion_level"] == "medium"


def test_ingest_traffic_data_requires_auth(client, zone):
    resp = client.post(
        "/traffic/data",
        json={"zone_id": zone["id"], "vehicle_count": 10, "avg_speed_kmph": 40, "congestion_level": "low"},
    )
    assert resp.status_code == 401


def test_get_live_traffic_returns_most_recent_reading_per_zone(client, zone, admin_auth):
    headers = admin_auth["headers"]
    post_reading(client, headers, zone["id"], vehicle_count=50, avg_speed_kmph=50, congestion_level="low")
    post_reading(client, headers, zone["id"], vehicle_count=200, avg_speed_kmph=10, congestion_level="high")

    resp = client.get("/traffic/live", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1  # one zone -> one "latest" entry
    assert body[0]["congestion_level"] == "high"
    assert body[0]["vehicle_count"] == 200


def test_get_live_traffic_empty_when_no_readings(client, zone, admin_auth):
    resp = client.get("/traffic/live", headers=admin_auth["headers"])
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_zone_history_ordered_most_recent_first(client, zone, admin_auth):
    headers = admin_auth["headers"]
    post_reading(client, headers, zone["id"], vehicle_count=10, avg_speed_kmph=60, congestion_level="low")
    post_reading(client, headers, zone["id"], vehicle_count=20, avg_speed_kmph=55, congestion_level="low")
    post_reading(client, headers, zone["id"], vehicle_count=30, avg_speed_kmph=50, congestion_level="medium")

    resp = client.get(f"/traffic/history/{zone['id']}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    # Most recently inserted reading (vehicle_count=30) should come first
    assert body[0]["vehicle_count"] == 30
    assert body[-1]["vehicle_count"] == 10


def test_get_zone_history_limited_to_50(client, zone, admin_auth):
    headers = admin_auth["headers"]
    for i in range(55):
        post_reading(client, headers, zone["id"], vehicle_count=i, avg_speed_kmph=40, congestion_level="low")

    resp = client.get(f"/traffic/history/{zone['id']}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 50
