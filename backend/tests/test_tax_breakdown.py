"""
Tests for the CGST / SGST / IGST tax breakdown checks in validator.validate_mathematics.

Intrastate invoices carry CGST + SGST (equal halves of the GST rate).
Interstate invoices carry IGST only. The total must equal subtotal + taxes
within a 1 rupee rounding tolerance.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from validator import validate_mathematics


def _invoice(**taxes):
    data = {
        "items": [
            {"description": "Steel rods", "quantity": 10, "rate": 400, "amount": 4000},
            {"description": "Cement bags", "quantity": 20, "rate": 50, "amount": 1000},
        ],
        "subtotal": 5000,
        "cgst": 0,
        "sgst": 0,
        "igst": 0,
    }
    data.update(taxes)
    if "total" not in taxes:
        data["total"] = data["subtotal"] + data["cgst"] + data["sgst"] + data["igst"]
    return data


def test_intrastate_equal_cgst_sgst_is_valid():
    # 18% GST split as 9% CGST + 9% SGST
    result = validate_mathematics(_invoice(cgst=450, sgst=450))
    assert result["valid"], result["issues"]
    assert result["issues"] == []


def test_interstate_igst_only_is_valid():
    result = validate_mathematics(_invoice(igst=900))
    assert result["valid"], result["issues"]


def test_unequal_cgst_sgst_is_flagged():
    result = validate_mathematics(_invoice(cgst=450, sgst=300))
    assert not result["valid"]
    assert any("CGST" in i and "SGST" in i for i in result["issues"])


def test_cgst_sgst_rounding_within_one_rupee_is_allowed():
    # Odd paise split: 450.50 vs 449.50 is within the 1 rupee tolerance
    result = validate_mathematics(_invoice(cgst=450.5, sgst=449.5))
    assert result["valid"], result["issues"]


def test_igst_with_cgst_is_flagged():
    result = validate_mathematics(_invoice(cgst=450, sgst=450, igst=900))
    assert not result["valid"]
    assert any("IGST and CGST both present" in i for i in result["issues"])


def test_total_must_include_all_taxes():
    # Total leaves out SGST
    result = validate_mathematics(_invoice(cgst=450, sgst=450, total=5450))
    assert not result["valid"]
    assert any("Total mismatch" in i for i in result["issues"])


def test_missing_tax_fields_treated_as_zero():
    data = _invoice()
    data["cgst"] = None
    data["sgst"] = None
    data["igst"] = None
    data["total"] = 5000
    result = validate_mathematics(data)
    assert result["valid"], result["issues"]


def test_none_igst_with_cgst_sgst_is_valid():
    data = _invoice(cgst=450, sgst=450)
    data["igst"] = None
    result = validate_mathematics(data)
    assert result["valid"], result["issues"]
