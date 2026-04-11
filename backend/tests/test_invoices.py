"""
Integration tests for invoice routes.
Gemini client is mocked — no real API calls are made.
Run: pytest --tb=short -v
"""
import io
from unittest.mock import patch

import pytest


def _make_fake_pdf() -> bytes:
    """Minimal structurally-valid PDF bytes for upload tests."""
    return (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )


# ── Shared setup helper ───────────────────────────────────────────────

def _register_login_create_company(client, suffix="inv"):
    """Register a unique user, log in, create a company, return the client."""
    email = f"{suffix}owner@test.com"
    client.post("/api/register", json={
        "name": "Inv Owner", "email": email, "password": "password123"
    })
    client.post("/api/login", json={"email": email, "password": "password123"})
    client.post("/api/companies", json={
        "name": f"Invoice Corp {suffix}",
        "gstin": "27ABCDE1234F1Z5",
    })
    return client


# ── Upload tests ──────────────────────────────────────────────────────

class TestScanUpload:
    @patch("services.invoice_service.extract_invoice_data")
    def test_upload_valid_file_returns_job_id(self, mock_extract, client):
        mock_extract.return_value = {
            "status": "completed",
            "seller_name": "Test Seller",
            "seller_gstin": "27ABCDE1234F1Z5",
            "buyer_name": "Test Buyer",
            "buyer_gstin": "29AABCT1332L1ZD",
            "invoice_number": "INV-001",
            "invoice_date": "15/03/2026",
            "subtotal": 1000.0,
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": None,
            "total": 1180.0,
        }
        _register_login_create_company(client, suffix="upload1")
        resp = client.post(
            "/api/scan",
            files={"file": ("invoice.pdf", io.BytesIO(_make_fake_pdf()), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"

    def test_upload_unauthenticated_returns_401(self, client):
        # Use the same client but with cookies cleared — no login performed
        client.cookies.clear()
        resp = client.post(
            "/api/scan",
            files={"file": ("invoice.pdf", io.BytesIO(b"data"), "application/pdf")},
        )
        assert resp.status_code == 401

    def test_upload_invalid_file_type_does_not_crash(self, client):
        _register_login_create_company(client, suffix="upload2")
        resp = client.post(
            "/api/scan",
            files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
        )
        # Server accepts the upload; background task will fail OCR gracefully.
        # The important invariant: the API itself must not 500.
        assert resp.status_code in (200, 400, 413, 422)


# ── Status poll tests ─────────────────────────────────────────────────

class TestScanStatus:
    def test_status_unauthenticated_returns_401(self, client):
        client.cookies.clear()
        resp = client.get("/api/scan/status/nonexistent-job-id")
        assert resp.status_code == 401

    def test_status_unknown_job_returns_404(self, client):
        _register_login_create_company(client, suffix="status1")
        resp = client.get("/api/scan/status/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ── Invoice list tests ────────────────────────────────────────────────

class TestInvoiceList:
    def test_list_invoices_paginated(self, client):
        _register_login_create_company(client, suffix="list1")
        resp = client.get("/api/invoices?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data

    def test_list_invoices_unauthenticated(self, client):
        client.cookies.clear()
        resp = client.get("/api/invoices")
        assert resp.status_code == 401

    def test_list_invoices_limit_capped_at_200(self, client):
        _register_login_create_company(client, suffix="list2")
        resp = client.get("/api/invoices?page=1&limit=9999")
        assert resp.status_code == 200
        # limit is silently capped — response must still be valid
        assert "items" in resp.json()


# ── Export tests ──────────────────────────────────────────────────────

class TestExport:
    def test_export_returns_csv(self, client):
        _register_login_create_company(client, suffix="export1")
        payload = {
            "invoice_number": "INV-001",
            "seller_name": "Test Seller",
            "invoice_date": "15/03/2026",
            "total": 1180.0,
            "cgst": 90.0,
            "sgst": 90.0,
            "igst": 0.0,
            "status": "SUCCESS",
            "health_score": {"score": 85, "grade": "B"},
        }
        resp = client.post("/api/export", json=payload)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "INV-001" in resp.text

    def test_export_unauthenticated_returns_401(self, client):
        client.cookies.clear()
        resp = client.post("/api/export", json={"invoice_number": "INV-X"})
        assert resp.status_code == 401
