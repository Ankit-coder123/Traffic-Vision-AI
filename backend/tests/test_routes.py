"""Milestone 2 -- Route Analysis Module.

/routes/optimize calls the public OSRM demo server over the network.
That's outside what a unit/integration test suite should depend on (flaky,
slow, no uptime guarantee -- router.project-osrm.org is explicitly
documented as such in routes.py itself), so `requests.get` is monkeypatched
here to return a canned-but-realistic OSRM response shape instead of
hitting the network.
"""
import pytest
from app.routers import routes as routes_module


class _FakeOSRMResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise routes_module.requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _osrm_success_payload():
    # Two alternative routes, geometry as a short straight line -- shape
    # matches what OSRM actually returns (GeoJSON [lng, lat] coordinate
    # pairs), just with made-up numbers.
    return {
        "code": "Ok",
        "routes": [
            {
                "duration": 600,   # 10 min, no congestion applied yet
                "distance": 5000,  # 5 km
                "geometry": {"coordinates": [[77.5946, 12.9716], [77.62, 12.93]]},
            },
            {
                "duration": 900,   # 15 min -- slower alternative
                "distance": 7000,
                "geometry": {"coordinates": [[77.5946, 12.9716], [77.60, 12.95], [77.62, 12.93]]},
            },
        ],
    }


@pytest.fixture()
def mock_osrm_success(monkeypatch):
    monkeypatch.setattr(
        routes_module.requests, "get", lambda *a, **k: _FakeOSRMResponse(_osrm_success_payload())
    )


@pytest.fixture()
def mock_osrm_failure(monkeypatch):
    def _raise(*a, **k):
        raise routes_module.requests.exceptions.RequestException("simulated network failure")

    monkeypatch.setattr(routes_module.requests, "get", _raise)


def _second_zone(client, admin_auth):
    resp = client.post(
        "/traffic/zones",
        json={"name": "Airport Road", "latitude": 13.19, "longitude": 77.71, "road_type": "highway"},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 200
    return resp.json()


def test_optimize_route_requires_auth(client, zone):
    resp = client.post(
        "/routes/optimize", json={"origin_zone_id": zone["id"], "destination_zone_id": zone["id"]}
    )
    assert resp.status_code == 401


def test_optimize_route_requires_origin_or_destination(client, zone, user_auth, mock_osrm_success):
    resp = client.post(
        "/routes/optimize", json={"destination_zone_id": zone["id"]}, headers=user_auth["headers"]
    )
    assert resp.status_code == 422


def test_optimize_route_unknown_zone_404(client, user_auth, mock_osrm_success):
    resp = client.post(
        "/routes/optimize",
        json={"origin_zone_id": 9999, "destination_zone_id": 9999},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 404


def test_optimize_route_returns_ranked_routes(client, admin_auth, user_auth, mock_osrm_success):
    origin = client.post(
        "/traffic/zones",
        json={"name": "Origin Zone", "latitude": 12.9716, "longitude": 77.5946},
        headers=admin_auth["headers"],
    ).json()
    destination = _second_zone(client, admin_auth)

    resp = client.post(
        "/routes/optimize",
        json={"origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["routes"]) == 2
    # Faster (lower estimated_duration_min) route should be marked recommended
    recommended = [r for r in body["routes"] if r["is_recommended"]]
    assert len(recommended) == 1
    fastest = min(body["routes"], key=lambda r: r["estimated_duration_min"])
    assert recommended[0]["distance_km"] == fastest["distance_km"]


def test_optimize_route_flags_active_incident_on_destination(
    client, admin_auth, operator_auth, user_auth, mock_osrm_success
):
    origin = client.post(
        "/traffic/zones",
        json={"name": "Origin Zone", "latitude": 12.9716, "longitude": 77.5946},
        headers=admin_auth["headers"],
    ).json()
    destination = _second_zone(client, admin_auth)

    client.post(
        "/incidents",
        json={"zone_id": destination["id"], "incident_type": "accident", "severity": "major"},
        headers=operator_auth["headers"],
    )

    resp = client.post(
        "/routes/optimize",
        json={"origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["incident_warnings"]) == 1
    assert "accident" in body["incident_warnings"][0].lower()


def test_optimize_route_osrm_failure_returns_502(client, zone, user_auth, mock_osrm_failure):
    resp = client.post(
        "/routes/optimize",
        json={"origin_zone_id": zone["id"], "origin_lat": 1.0, "origin_lng": 1.0,
              "destination_lat": 2.0, "destination_lng": 2.0},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 502


def test_optimize_route_accepts_raw_coordinates(client, user_auth, mock_osrm_success):
    resp = client.post(
        "/routes/optimize",
        json={"origin_lat": 12.9, "origin_lng": 77.5, "destination_lat": 13.0, "destination_lng": 77.6},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200


# ---------- Saved Routes ----------

def test_save_route_and_list(client, admin_auth, user_auth):
    destination = _second_zone(client, admin_auth)
    origin = client.get("/traffic/zones", headers=user_auth["headers"]).json()[0]

    save_resp = client.post(
        "/routes/saved",
        json={"label": "Home to Office", "origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    )
    assert save_resp.status_code == 201
    assert save_resp.json()["label"] == "Home to Office"

    list_resp = client.get("/routes/saved", headers=user_auth["headers"])
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_saved_routes_are_private_per_user(client, admin_auth, user_auth, operator_auth):
    destination = _second_zone(client, admin_auth)
    origin = client.get("/traffic/zones", headers=user_auth["headers"]).json()[0]

    client.post(
        "/routes/saved",
        json={"label": "User's Route", "origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    )

    operator_list = client.get("/routes/saved", headers=operator_auth["headers"])
    assert operator_list.status_code == 200
    assert operator_list.json() == []  # operator sees none of the user's saved routes


def test_delete_saved_route(client, admin_auth, user_auth):
    destination = _second_zone(client, admin_auth)
    origin = client.get("/traffic/zones", headers=user_auth["headers"]).json()[0]

    saved = client.post(
        "/routes/saved",
        json={"label": "Temp Route", "origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    ).json()

    delete_resp = client.delete(f"/routes/saved/{saved['id']}", headers=user_auth["headers"])
    assert delete_resp.status_code == 204

    list_resp = client.get("/routes/saved", headers=user_auth["headers"])
    assert list_resp.json() == []


def test_delete_someone_elses_saved_route_404s(client, admin_auth, user_auth, operator_auth):
    destination = _second_zone(client, admin_auth)
    origin = client.get("/traffic/zones", headers=user_auth["headers"]).json()[0]

    saved = client.post(
        "/routes/saved",
        json={"label": "User's Route", "origin_zone_id": origin["id"], "destination_zone_id": destination["id"]},
        headers=user_auth["headers"],
    ).json()

    # operator tries to delete user's saved route
    resp = client.delete(f"/routes/saved/{saved['id']}", headers=operator_auth["headers"])
    assert resp.status_code == 404
