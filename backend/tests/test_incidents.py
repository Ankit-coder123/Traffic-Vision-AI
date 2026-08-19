"""Milestone 3 -- Alert & Notification Module (incident reporting half)."""


def test_report_incident_requires_operator_or_admin(client, zone, user_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "major"},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 403


def test_report_incident_as_operator_succeeds(client, zone, operator_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "major", "description": "Multi-vehicle collision"},
        headers=operator_auth["headers"],
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["zone_name"] == "MG Road Junction"
    assert body["is_resolved"] is False


def test_report_incident_as_admin_succeeds(client, zone, admin_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "road_closure", "severity": "moderate"},
        headers=admin_auth["headers"],
    )
    assert resp.status_code == 201


def test_report_incident_unknown_zone_404s(client, operator_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": 9999, "incident_type": "accident", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    assert resp.status_code == 404


def test_report_incident_invalid_type_rejected(client, zone, operator_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "not_a_real_type", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    assert resp.status_code == 422


def test_report_incident_invalid_severity_rejected(client, zone, operator_auth):
    resp = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "catastrophic"},
        headers=operator_auth["headers"],
    )
    assert resp.status_code == 422


def test_list_incidents_any_authenticated_role(client, zone, operator_auth, user_auth):
    client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "hazard", "severity": "minor"},
        headers=operator_auth["headers"],
    )
    resp = client.get("/incidents", headers=user_auth["headers"])
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_incidents_requires_auth(client):
    resp = client.get("/incidents")
    assert resp.status_code == 401


def test_list_incidents_active_only_filters_resolved(client, zone, operator_auth):
    incident = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "construction", "severity": "minor"},
        headers=operator_auth["headers"],
    ).json()

    client.patch(
        f"/incidents/{incident['id']}/resolve", json={"is_resolved": True}, headers=operator_auth["headers"]
    )

    active = client.get("/incidents?active_only=true", headers=operator_auth["headers"])
    assert active.json() == []

    everything = client.get("/incidents?active_only=false", headers=operator_auth["headers"])
    assert len(everything.json()) == 1
    assert everything.json()[0]["is_resolved"] is True


def test_resolve_incident_requires_operator_or_admin(client, zone, operator_auth, user_auth):
    incident = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "minor"},
        headers=operator_auth["headers"],
    ).json()

    resp = client.patch(
        f"/incidents/{incident['id']}/resolve", json={"is_resolved": True}, headers=user_auth["headers"]
    )
    assert resp.status_code == 403


def test_resolve_unknown_incident_404s(client, operator_auth):
    resp = client.patch(
        "/incidents/9999/resolve", json={"is_resolved": True}, headers=operator_auth["headers"]
    )
    assert resp.status_code == 404


def test_resolve_then_unresolve_incident(client, zone, operator_auth):
    incident = client.post(
        "/incidents",
        json={"zone_id": zone["id"], "incident_type": "accident", "severity": "minor"},
        headers=operator_auth["headers"],
    ).json()

    resolved = client.patch(
        f"/incidents/{incident['id']}/resolve", json={"is_resolved": True}, headers=operator_auth["headers"]
    )
    assert resolved.json()["is_resolved"] is True

    reopened = client.patch(
        f"/incidents/{incident['id']}/resolve", json={"is_resolved": False}, headers=operator_auth["headers"]
    )
    assert reopened.json()["is_resolved"] is False
