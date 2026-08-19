"""Milestone 1 -- User Management Module."""


def test_signup_and_login(client):
    resp = client.post(
        "/auth/signup",
        json={"name": "Alice", "email": "alice@test.com", "password": "AlicePass123!", "role": "user"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@test.com"
    assert body["role"] == "user"
    assert "password" not in body and "password_hash" not in body

    login = client.post("/auth/login", data={"username": "alice@test.com", "password": "AlicePass123!"})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["access_token"]


def test_signup_duplicate_email_rejected(client):
    payload = {"name": "Bob", "email": "bob@test.com", "password": "BobPass123!", "role": "user"}
    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/signup",
        json={"name": "Carol", "email": "carol@test.com", "password": "CarolPass123!", "role": "user"},
    )
    resp = client.post("/auth/login", data={"username": "carol@test.com", "password": "WrongPassword"})
    assert resp.status_code == 401


def test_login_unknown_email_rejected(client):
    resp = client.post("/auth/login", data={"username": "nobody@test.com", "password": "whatever"})
    assert resp.status_code == 401


def test_first_signup_can_become_admin(client):
    """The very first account in a fresh database is the one and only
    case where requesting role='admin' actually succeeds."""
    resp = client.post(
        "/auth/signup",
        json={"name": "First", "email": "first@test.com", "password": "FirstPass123!", "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "admin"


def test_second_signup_cannot_become_admin(client):
    """Once an admin already exists, requesting role='admin' again is
    silently downgraded -- the public signup form can never mint a second
    admin account."""
    client.post(
        "/auth/signup",
        json={"name": "First", "email": "first@test.com", "password": "FirstPass123!", "role": "admin"},
    )
    resp = client.post(
        "/auth/signup",
        json={"name": "Second", "email": "second@test.com", "password": "SecondPass123!", "role": "admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


def test_signup_invalid_role_defaults_to_user(client):
    resp = client.post(
        "/auth/signup",
        json={"name": "Dave", "email": "dave@test.com", "password": "DavePass123!", "role": "superuser"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "user"


def test_get_me_requires_token(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_get_me_returns_current_user(client, user_auth):
    resp = client.get("/auth/me", headers=user_auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == "user@test.com"


def test_invalid_token_rejected(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_update_profile_name(client, user_auth):
    resp = client.patch("/auth/me", json={"name": "New Name"}, headers=user_auth["headers"])
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


def test_update_profile_empty_name_rejected(client, user_auth):
    resp = client.patch("/auth/me", json={"name": "   "}, headers=user_auth["headers"])
    assert resp.status_code == 422


def test_change_password_requires_current_password(client, user_auth):
    resp = client.patch(
        "/auth/me", json={"new_password": "NewPassword123!"}, headers=user_auth["headers"]
    )
    assert resp.status_code == 400


def test_change_password_wrong_current_password_rejected(client, user_auth):
    resp = client.patch(
        "/auth/me",
        json={"current_password": "WrongOne", "new_password": "NewPassword123!"},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 401


def test_change_password_too_short_rejected(client, user_auth):
    resp = client.patch(
        "/auth/me",
        json={"current_password": "UserPass123!", "new_password": "short"},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 422


def test_change_password_success_and_relogin(client, user_auth):
    resp = client.patch(
        "/auth/me",
        json={"current_password": "UserPass123!", "new_password": "BrandNewPass123!"},
        headers=user_auth["headers"],
    )
    assert resp.status_code == 200

    old_login = client.post("/auth/login", data={"username": "user@test.com", "password": "UserPass123!"})
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login", data={"username": "user@test.com", "password": "BrandNewPass123!"}
    )
    assert new_login.status_code == 200
