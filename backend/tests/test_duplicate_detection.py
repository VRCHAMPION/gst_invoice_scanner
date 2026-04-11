"""
Unit tests for duplicate invoice detection logic.
"""
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest


def test_duplicate_invoice_detection():
    """Test that duplicate invoices are detected correctly."""
    from models import Invoice, Company, User
    from services.invoice_service import process_invoice_background
    
    # Create mock database session
    mock_db = Mock()
    
    # Create mock company
    mock_company = Mock(spec=Company)
    mock_company.id = uuid.uuid4()
    mock_company.gstin = "27ABCDE1234F1Z5"
    
    # Create mock user
    mock_user = Mock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_user.name = "Test User"
    
    # Create mock invoice record (the one being processed)
    mock_invoice = Mock(spec=Invoice)
    mock_invoice.id = uuid.uuid4()
    mock_invoice.job_id = "test-job-123"
    mock_invoice.company_id = mock_company.id
    
    # Create mock existing invoice (duplicate)
    mock_existing_invoice = Mock(spec=Invoice)
    mock_existing_invoice.id = uuid.uuid4()
    mock_existing_invoice.invoice_number = "INV-001"
    mock_existing_invoice.created_at = datetime(2026, 1, 1, 10, 0, 0)
    mock_existing_invoice.uploaded_by = mock_user.id
    
    # Setup mock query chain for finding the invoice being processed
    mock_db.query.return_value.filter.return_value.first.return_value = mock_invoice
    
    # Setup mock query chain for finding company
    invoice_query_count = [0]  # Use list to allow modification in nested function
    
    def query_side_effect(model):
        mock_query = Mock()
        if model == Company:
            mock_query.filter.return_value.first.return_value = mock_company
        elif model == Invoice:
            invoice_query_count[0] += 1
            if invoice_query_count[0] == 1:
                # First call: finding the invoice being processed
                mock_query.filter.return_value.first.return_value = mock_invoice
            elif invoice_query_count[0] == 2:
                # Second call: checking for duplicates
                mock_query.filter.return_value.first.return_value = mock_existing_invoice
            else:
                mock_query.filter.return_value.first.return_value = None
        elif model == User:
            mock_query.filter.return_value.first.return_value = mock_user
        return mock_query
    
    mock_db.query.side_effect = query_side_effect
    
    # Mock extract_invoice_data to return duplicate invoice data
    mock_data = {
        "status": "completed",
        "seller_name": "Acme Corp",
        "seller_gstin": "27ABCDE1234F1Z5",
        "buyer_name": "Test Buyer",
        "buyer_gstin": "29AABCT1332L1ZD",
        "invoice_number": "INV-001",
        "invoice_date": "01/01/2026",
        "subtotal": 1000.0,
        "cgst": 90.0,
        "sgst": 90.0,
        "igst": None,
        "total": 1180.0,
    }
    
    with patch("services.invoice_service.extract_invoice_data", return_value=mock_data):
        with patch("database.SessionLocal", return_value=mock_db):
            with patch("services.invoice_service._create_or_update_vendor"):
                # Call the background processing function
                process_invoice_background(
                    job_id="test-job-123",
                    file_bytes=b"fake pdf content",
                    content_type="application/pdf",
                    user_id=mock_user.id,
                    company_id=mock_company.id,
                )
    
    # Verify that the invoice was marked as FAILED
    assert mock_invoice.status == "FAILED"
    
    # Verify that is_duplicate was set to the existing invoice ID
    assert mock_invoice.is_duplicate == str(mock_existing_invoice.id)
    
    # Verify error message contains expected text
    assert "Duplicate invoice" in mock_invoice.error_message
    assert "INV-001" in mock_invoice.error_message
    assert "was already uploaded" in mock_invoice.error_message
    assert "Test User" in mock_invoice.error_message
    
    # Verify database commit was called
    mock_db.commit.assert_called()


def test_first_invoice_accepted():
    """Test that the first invoice with a number is accepted."""
    from models import Invoice, Company
    from services.invoice_service import process_invoice_background
    
    # Create mock database session
    mock_db = Mock()
    
    # Create mock company
    mock_company = Mock(spec=Company)
    mock_company.id = uuid.uuid4()
    mock_company.gstin = "27ABCDE1234F1Z5"
    
    # Create mock invoice record (the one being processed)
    mock_invoice = Mock(spec=Invoice)
    mock_invoice.id = uuid.uuid4()
    mock_invoice.job_id = "test-job-456"
    mock_invoice.company_id = mock_company.id
    
    # Setup mock query chain - no existing invoice found
    invoice_query_count = [0]  # Use list to allow modification in nested function
    
    def query_side_effect(model):
        mock_query = Mock()
        if model == Company:
            mock_query.filter.return_value.first.return_value = mock_company
        elif model == Invoice:
            invoice_query_count[0] += 1
            if invoice_query_count[0] == 1:
                # First call: finding the invoice being processed
                mock_query.filter.return_value.first.return_value = mock_invoice
            else:
                # Second call: checking for duplicates - none found
                mock_query.filter.return_value.first.return_value = None
        return mock_query
    
    mock_db.query.side_effect = query_side_effect
    
    # Mock extract_invoice_data to return invoice data
    mock_data = {
        "status": "completed",
        "seller_name": "Acme Corp",
        "seller_gstin": "27ABCDE1234F1Z5",
        "buyer_name": "Test Buyer",
        "buyer_gstin": "29AABCT1332L1ZD",
        "invoice_number": "INV-NEW-001",
        "invoice_date": "01/01/2026",
        "subtotal": 1000.0,
        "cgst": 90.0,
        "sgst": 90.0,
        "igst": None,
        "total": 1180.0,
    }
    
    with patch("services.invoice_service.extract_invoice_data", return_value=mock_data):
        with patch("database.SessionLocal", return_value=mock_db):
            with patch("services.invoice_service._create_or_update_vendor"):
                # Call the background processing function
                process_invoice_background(
                    job_id="test-job-456",
                    file_bytes=b"fake pdf content",
                    content_type="application/pdf",
                    user_id=uuid.uuid4(),
                    company_id=mock_company.id,
                )
    
    # Verify that the invoice was marked as PENDING_REVIEW (not FAILED)
    assert mock_invoice.status == "PENDING_REVIEW"
    
    # Verify that invoice data was set
    assert mock_invoice.invoice_number == "INV-NEW-001"
    assert mock_invoice.seller_name == "Acme Corp"
    assert mock_invoice.total == 1180.0
    
    # Verify database commit and refresh were called
    mock_db.commit.assert_called()
    mock_db.refresh.assert_called_with(mock_invoice)


def test_same_invoice_number_different_company():
    """Test that same invoice number is allowed for different companies."""
    from models import Invoice, Company
    from services.invoice_service import process_invoice_background
    
    # Create mock database session
    mock_db = Mock()
    
    # Create mock company
    mock_company = Mock(spec=Company)
    mock_company.id = uuid.uuid4()
    mock_company.gstin = "27ABCDE1234F1Z5"
    
    # Create mock invoice record (the one being processed)
    mock_invoice = Mock(spec=Invoice)
    mock_invoice.id = uuid.uuid4()
    mock_invoice.job_id = "test-job-789"
    mock_invoice.company_id = mock_company.id
    
    # Setup mock query chain - no existing invoice found for THIS company
    invoice_query_count = [0]  # Use list to allow modification in nested function
    
    def query_side_effect(model):
        mock_query = Mock()
        if model == Company:
            mock_query.filter.return_value.first.return_value = mock_company
        elif model == Invoice:
            invoice_query_count[0] += 1
            if invoice_query_count[0] == 1:
                # First call: finding the invoice being processed
                mock_query.filter.return_value.first.return_value = mock_invoice
            else:
                # Second call: checking for duplicates - none found for this company
                mock_query.filter.return_value.first.return_value = None
        return mock_query
    
    mock_db.query.side_effect = query_side_effect
    
    # Mock extract_invoice_data to return invoice data
    mock_data = {
        "status": "completed",
        "seller_name": "Acme Corp",
        "seller_gstin": "27ABCDE1234F1Z5",
        "buyer_name": "Test Buyer",
        "buyer_gstin": "29AABCT1332L1ZD",
        "invoice_number": "INV-SHARED-001",
        "invoice_date": "01/01/2026",
        "subtotal": 1000.0,
        "cgst": 90.0,
        "sgst": 90.0,
        "igst": None,
        "total": 1180.0,
    }
    
    with patch("services.invoice_service.extract_invoice_data", return_value=mock_data):
        with patch("database.SessionLocal", return_value=mock_db):
            with patch("services.invoice_service._create_or_update_vendor"):
                # Call the background processing function
                process_invoice_background(
                    job_id="test-job-789",
                    file_bytes=b"fake pdf content",
                    content_type="application/pdf",
                    user_id=uuid.uuid4(),
                    company_id=mock_company.id,
                )
    
    # Verify that the invoice was accepted (not marked as duplicate)
    assert mock_invoice.status == "PENDING_REVIEW"
    assert mock_invoice.invoice_number == "INV-SHARED-001"
    
    # Verify database commit was called
    mock_db.commit.assert_called()
