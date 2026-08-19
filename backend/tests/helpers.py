"""Shared, side-effect-free helpers for tests.

Deliberately kept out of conftest.py: conftest.py has import-time side
effects (it patches app.database.engine/SessionLocal before importing
app.main). If a test module did `from tests.conftest import post_reading`,
Python would import conftest.py a second time under the module name
`tests.conftest` -- separate from the `conftest` module pytest already
auto-loaded -- re-running that patching code against a second, empty
in-memory SQLite database that never gets `create_all()` called on it.
`get_db()` would then silently start using that second, tableless engine,
and every request fails with "no such table: users" even though the
fixtures appear to run fine. This module has no import-time side effects,
so it's always safe to import directly from test files.
"""


def post_reading(client, headers, zone_id, *, vehicle_count, avg_speed_kmph, congestion_level):
    resp = client.post(
        "/traffic/data",
        json={
            "zone_id": zone_id,
            "vehicle_count": vehicle_count,
            "avg_speed_kmph": avg_speed_kmph,
            "congestion_level": congestion_level,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
