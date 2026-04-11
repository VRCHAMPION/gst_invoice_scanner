"""
test_vendors.py - Tests for vendor management endpoints
"""
import pytest
from fastapi.testclient import TestClient

from models import Company, Vendor, Invoice


def test_get_vendors_empty(auth_client: TestClient):
    """Test getting vendors when none exist"""
    response = auth_client.get("/api/vendors")
    assert response.status_code == 200
    assert response.json() == []


def test_get_vendor_detail_not_found(auth_client: TestClient):
    """Test getting non-existent vendor"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = auth_client.get(f"/api/vendors/{fake_id}")
    assert response.status_code == 404


def test_get_vendor_detail_invalid_id(auth_client: TestClient):
    """Test getting vendor with invalid ID format"""
    response = auth_client.get("/api/vendors/invalid-id")
    assert response.status_code == 400
