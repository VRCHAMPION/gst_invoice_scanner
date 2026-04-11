"""
Integration tests for company routes.
Run: pytest backend/tests/test_companies.py -v
"""


VALID_COMPANY = {"name": "Test Corp Pvt Ltd", "gstin": "27ABCDE1234F1Z5"}


class TestCreateCompany:
    def test_create_company_success(self, auth_client):
        resp = auth_client.post("/api/companies", json=VALID_COMPANY)
        assert resp.status_code == 200
        data = resp.json()
        assert data["gstin"] == "27ABCDE1234F1Z5"
        assert data["name"] == "Test Corp Pvt Ltd"

    def test_create_company_invalid_gstin_length(self, client):
        # Register a fresh user for this test
        client.post("/api/register", json={
            "name": "User2", "email": "user2@test.com", "password": "password123"
        })
        client.post("/api/login", json={"email": "user2@test.com", "password": "password123"})
        resp = client.post("/api/companies", json={"name": "Bad Corp", "gstin": "TOOSHORT"})
        assert resp.status_code == 422

    def test_create_company_unauthenticated(self, client):
        resp = client.post("/api/companies", json=VALID_COMPANY)
        assert resp.status_code == 401

    def test_get_companies_returns_list(self, auth_client):
        resp = auth_client.get("/api/companies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestJoinRequest:
    def test_join_request_flow(self, client):
        # Owner registers and creates company
        client.post("/api/register", json={
            "name": "Owner", "email": "owner_jr@test.com", "password": "password123"
        })
        client.post("/api/login", json={"email": "owner_jr@test.com", "password": "password123"})
        client.post("/api/companies", json={"name": "JR Corp", "gstin": "29AABCT1332L1ZD"})

        # Employee registers and sends join request
        client.post("/api/register", json={
            "name": "Employee", "email": "emp_jr@test.com", "password": "password123"
        })
        client.post("/api/login", json={"email": "emp_jr@test.com", "password": "password123"})
        resp = client.post("/api/join-request", json={"company_name": "JR Corp"})
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()

    def test_duplicate_pending_join_request_blocked(self, client):
        # Employee tries to send a second pending request
        resp = client.post("/api/join-request", json={"company_name": "JR Corp"})
        assert resp.status_code == 400
        assert "pending" in resp.json()["detail"].lower()
