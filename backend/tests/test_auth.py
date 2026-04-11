"""
Integration tests for auth routes.
Run: pytest backend/tests/test_auth.py -v
"""


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/register", json={
            "name": "Alice",
            "email": "alice_unique@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["email"] == "alice_unique@example.com"
        assert data["user"]["role"] == "owner"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

    def test_register_duplicate_email(self, client):
        payload = {"name": "Bob", "email": "bob_dup@example.com", "password": "password123"}
        r1 = client.post("/api/register", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/api/register", json=payload)
        assert r2.status_code == 400
        assert "already registered" in r2.json()["detail"].lower()

    def test_register_password_too_short(self, client):
        resp = client.post("/api/register", json={
            "name": "Charlie",
            "email": "charlie@example.com",
            "password": "short",
        })
        assert resp.status_code == 422  # Pydantic validation error

    def test_register_invalid_email(self, client):
        resp = client.post("/api/register", json={
            "name": "Dave",
            "email": "not-an-email",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_name_too_short(self, client):
        resp = client.post("/api/register", json={
            "name": "X",
            "email": "x@example.com",
            "password": "password123",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        creds = registered_user["credentials"]
        resp = client.post("/api/login", json={
            "email": creds["email"],
            "password": creds["password"],
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == creds["email"]
        # Cookie should be set
        assert "access_token" in resp.cookies

    def test_login_wrong_password(self, client, registered_user):
        creds = registered_user["credentials"]
        resp = client.post("/api/login", json={
            "email": creds["email"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/api/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401


class TestLogout:
    def test_logout_clears_cookie(self, auth_client):
        resp = auth_client.post("/api/logout")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully"


class TestMe:
    def test_me_returns_current_user(self, auth_client, registered_user):
        resp = auth_client.get("/api/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == registered_user["credentials"]["email"]

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/me")
        assert resp.status_code == 401
