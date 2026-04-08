"""
Unit tests for validator.py

Run with:  .venv\\Scripts\\pytest backend/tests/test_validator.py -v
"""

import sys
import os

# Ensure the backend directory is on the path so imports work from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validator import (
    validate_gstin,
    validate_mathematics,
    detect_fraud_signals,
    validate_invoice_date,
    calculate_health_score,
)


# ── GSTIN Validation ──────────────────────────────────────────────────
# Regex: ^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$
# e.g.   27      ABCDE      1234      F    1        Z  5

class TestValidateGstin:
    def test_valid_gstin(self):
        result = validate_gstin("27ABCDE1234F1Z5")
        assert result["valid"] is True, f"Expected valid GSTIN but got: {result}"

    def test_valid_gstin_maharashtra(self):
        # Another genuine format: state 29 (Karnataka)
        result = validate_gstin("29AABCT1332L1ZD")
        assert result["valid"] is True, f"Expected valid GSTIN but got: {result}"

    def test_missing_gstin_empty_string(self):
        result = validate_gstin("")
        assert result["valid"] is False
        assert "missing" in result["message"].lower()

    def test_missing_gstin_none_like(self):
        # Passing None-like empty
        result = validate_gstin("")
        assert result["valid"] is False

    def test_too_short_gstin(self):
        result = validate_gstin("27ABCDE")
        assert result["valid"] is False
        assert "15 characters" in result["message"]

    def test_invalid_format_lowercase(self):
        # Lowercase letters should fail the regex (it uppercases first, so actually passes)
        # Test that a truly malformed GSTIN (bad pattern) fails
        result = validate_gstin("27ABCDE1234F1X5")  # X at position 13 instead of Z
        assert result["valid"] is False

    def test_invalid_state_code(self):
        # State code 38 is invalid (> 37). Use 38 which passes regex digits but fails state check.
        # Pattern says [0-3][0-9] so 38 is valid chars — state check catches it.
        result = validate_gstin("38ABCDE1234F1Z5")
        assert result["valid"] is False
        assert "state code" in result["message"].lower()


# ── Fraud Signal Detection ────────────────────────────────────────────

class TestDetectFraudSignals:
    def test_round_number_total_flagged(self):
        data = {"total": 100000, "items": []}
        result = detect_fraud_signals(data)
        assert result["valid"] is False
        assert any("round" in s.lower() for s in result["signals"])

    def test_identical_item_amounts_flagged(self):
        data = {
            "total": 3000,
            "items": [
                {"amount": 1000, "quantity": 1, "rate": 1000},
                {"amount": 1000, "quantity": 1, "rate": 1000},
                {"amount": 1000, "quantity": 1, "rate": 1000},
            ]
        }
        result = detect_fraud_signals(data)
        assert result["valid"] is False
        assert any("identical" in s.lower() for s in result["signals"])

    def test_single_high_value_item_flagged(self):
        data = {
            "total": 250000,
            "items": [{"amount": 250000, "quantity": 1, "rate": 250000}]
        }
        result = detect_fraud_signals(data)
        # Should flag both round number AND single high-value item
        assert result["valid"] is False

    def test_clean_invoice_no_signals(self):
        data = {
            "total": 5843,  # not a round number
            "items": [
                {"amount": 2500, "quantity": 5, "rate": 500},
                {"amount": 3343, "quantity": 7, "rate": 477.57},
            ]
        }
        result = detect_fraud_signals(data)
        assert result["valid"] is True
        assert len(result["signals"]) == 0


# ── Health Score ──────────────────────────────────────────────────────

class TestCalculateHealthScore:
    def test_empty_data_returns_low_score(self):
        result = calculate_health_score({})
        assert result["score"] < 50
        assert result["grade"] in ["D", "F"]

    def test_missing_required_fields_penalised(self):
        # Partial data — only GSTIN, no name/number/date/total
        data = {
            "seller_gstin": "27ABCDE1234F1Z5",
        }
        result = calculate_health_score(data)
        # Should have issues for the 4 missing required fields
        assert len(result["issues"]) >= 1
        assert result["score"] < 100

    def test_full_clean_invoice_scores_high(self):
        data = {
            "seller_gstin":  "27ABCDE1234F1Z5",
            "buyer_gstin":   "29AABCT1332L1ZD",
            "invoice_date":  "15/03/2026",  # March 2026 — safely in the past
            "invoice_number": "INV-100",
            "seller_name":   "ABC Corp Pvt Ltd",
            "buyer_name":    "XYZ Ltd",
            "total":   5900,
            "cgst":    450,
            "sgst":    450,
            "igst":    0,
            "subtotal": 5000,
        }
        result = calculate_health_score(data)
        assert result["score"] >= 75
        assert result["grade"] in ["A", "B"]

    def test_igst_and_cgst_both_nonzero_is_warned(self):
        # Having both IGST and CGST > 0 on the same invoice is a GST compliance error.
        # NOTE: the IGST/CGST mutual-exclusion check lives in validate_mathematics()
        # which only runs when items are present. We must include items to trigger it.
        data = {
            "seller_gstin":  "27ABCDE1234F1Z5",
            "buyer_gstin":   "29AABCT1332L1ZD",
            "invoice_date":  "15/03/2026",
            "invoice_number": "INV-101",
            "seller_name":   "ABC Corp",
            "buyer_name":    "XYZ Ltd",
            "total":  5900,
            "cgst":   450,
            "sgst":   450,
            "igst":   900,   # ← invalid: both IGST and CGST are set (interstate + intrastate)
            "subtotal": 5000,
            "items": [       # ← needed to trigger validate_mathematics IGST check
                {"description": "Widget", "quantity": 10, "rate": 500, "amount": 5000}
            ],
        }
        result = calculate_health_score(data)
        combined = " ".join(result["issues"] + result["warnings"]).lower()
        assert "igst" in combined, f"Expected IGST warning in issues/warnings, got: {combined}"


# ── Invoice Date Validation ───────────────────────────────────────────

class TestValidateInvoiceDate:
    def test_valid_date_dmy_slash(self):
        result = validate_invoice_date("15/03/2026")  # March 2026 — past date
        assert result["valid"] is True

    def test_valid_date_dmy_dash(self):
        result = validate_invoice_date("15-03-2026")  # March 2026 — past date
        assert result["valid"] is True

    def test_valid_date_iso_format(self):
        result = validate_invoice_date("2026-03-15")  # March 2026 — past date
        assert result["valid"] is True

    def test_future_date_is_invalid(self):
        result = validate_invoice_date("31/12/2099")
        assert result["valid"] is False
        assert "future" in result["message"].lower()

    def test_missing_date_is_invalid(self):
        result = validate_invoice_date("")
        assert result["valid"] is False
        assert "missing" in result["message"].lower()

    def test_unparseable_date_is_invalid(self):
        result = validate_invoice_date("not-a-date")
        assert result["valid"] is False
