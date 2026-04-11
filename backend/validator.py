from datetime import datetime, date
import re

# GSTIN regex: 2-digit state code + 5 alpha + 4 digit + 1 alpha + 1 alphanum + Z + 1 alphanum
GSTIN_REGEX = re.compile(r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$')


def validate_gstin(gstin: str) -> dict:
    # TODO: add checksum digit validation
    if not gstin:
        return {"valid": False, "message": "gstin is missing"}

    if len(gstin) != 15:
        return {"valid": False, "message": "gstin must be 15 characters long"}

    if not GSTIN_REGEX.match(gstin.upper()):
        return {"valid": False, "message": "invalid gstin format"}

    state_code = int(gstin[:2])
    if state_code < 1 or state_code > 37:
        return {"valid": False, "message": f"Invalid state code: {gstin[:2]}"}

    return {"valid": True, "message": "gstin is valid"}


def validate_mathematics(data: dict) -> dict:
    issues = []

    items = data.get("items")
    subtotal = data.get("subtotal")
    cgst = data.get("cgst")
    sgst = data.get("sgst")
    igst = data.get("igst")
    total = data.get("total")

    if not items:
        issues.append("No items found in invoice")
        return {"valid": True, "issues": issues}

    calculated_subtotal = 0
    for item in items:
        qty = item.get("quantity") or 0
        rate = item.get("rate") or 0
        amount = item.get("amount") or 0
        expected = round(qty * rate, 2)
        if amount and expected and abs(expected - amount) > 1:
            issues.append(
                f"Item '{item.get('description', 'Unknown')}': "
                f"qty({qty}) × rate({rate}) = {expected} but amount shows {amount}"
            )
        calculated_subtotal += amount

    if subtotal and calculated_subtotal:
        if abs(calculated_subtotal - subtotal) > 1:
            issues.append(
                f"Subtotal mismatch: items sum to ₹{calculated_subtotal} "
                f"but subtotal shows ₹{subtotal}"
            )

    cgst_val = cgst or 0
    sgst_val = sgst or 0
    igst_val = igst or 0

    expected_total = round((subtotal or 0) + cgst_val + sgst_val + igst_val, 2)
    if total and abs(expected_total - total) > 1:
        issues.append(
            f"Total mismatch: subtotal({subtotal}) + taxes({cgst_val + sgst_val + igst_val}) "
            f"= {expected_total} but total shows {total}"
        )

    # CGST and SGST should be equal for intrastate transactions
    if cgst_val and sgst_val and abs(cgst_val - sgst_val) > 1:
        issues.append(
            f"CGST (₹{cgst_val}) ≠ SGST (₹{sgst_val}) — "
            f"for intrastate transactions they must be equal"
        )

    if igst_val and igst_val > 0:
        if cgst_val and cgst_val > 0:
            issues.append(
                "IGST and CGST both present — "
                "interstate invoices should only have IGST"
            )

    return {"valid": len(issues) == 0, "issues": issues}


def validate_invoice_date(invoice_date: str) -> dict:
    if not invoice_date:
        return {"valid": False, "message": "Invoice date is missing"}

    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y",
    ]

    parsed_date = None
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(invoice_date.strip(), fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        return {"valid": False, "message": f"Could not parse invoice date: '{invoice_date}'"}

    today = date.today()
    if parsed_date > today:
        return {"valid": False, "message": f"Invoice date {invoice_date} is in the future"}

    days_old = (today - parsed_date).days
    if days_old > 365:
        return {"valid": False, "message": f"Invoice is {days_old} days old — verify before processing"}
    if days_old > 90:
        return {
            "valid": True,
            "message": f"Invoice is {days_old} days old — confirm this is intentional",
            "warning": True,
        }

    return {"valid": True, "message": "Invoice date is valid"}


def validate_hsn_codes(data: dict) -> dict:
    items = data.get("items") or []
    missing_hsn = []

    for item in items:
        description = item.get("description", "Unknown item")
        hsn = item.get("hsn") or item.get("hsn_code") or None
        if not hsn:
            missing_hsn.append(description)

    if missing_hsn:
        return {"valid": False, "message": f"HSN code missing for: {', '.join(missing_hsn)}"}

    return {"valid": True, "message": "All items have HSN codes"}


def detect_fraud_signals(data: dict) -> dict:
    signals = []
    items = data.get("items") or []
    total = data.get("total") or 0

    if total and total > 0 and total % 1000 == 0:
        signals.append(f"Total amount ₹{total} is a perfectly round number — verify")

    amounts = [item.get("amount") for item in items if item.get("amount")]
    if len(amounts) > 1 and len(set(amounts)) == 1:
        signals.append("All items have identical amounts — unusual pattern")

    if len(items) == 1 and total and total > 100000:
        signals.append(f"Single item invoice worth ₹{total} — verify authenticity")

    for item in items:
        qty = item.get("quantity") or 0
        if qty <= 0:
            signals.append(
                f"Item '{item.get('description', 'Unknown')}' has invalid quantity: {qty}"
            )

    return {"valid": len(signals) == 0, "signals": signals}


def calculate_health_score(data: dict) -> dict:
    score = 100
    all_issues = []
    all_warnings = []

    seller_gstin_result = validate_gstin(data.get("seller_gstin", ""))
    if not seller_gstin_result["valid"]:
        score -= 15
        all_issues.append(f"Seller GSTIN: {seller_gstin_result['message']}")

    buyer_gstin_result = validate_gstin(data.get("buyer_gstin", ""))
    if not buyer_gstin_result["valid"]:
        score -= 15
        all_issues.append(f"Buyer GSTIN: {buyer_gstin_result['message']}")

    math_result = validate_mathematics(data)
    if not math_result["valid"]:
        score -= 20
        all_issues.extend(math_result["issues"])

    date_result = validate_invoice_date(data.get("invoice_date", ""))
    if not date_result["valid"]:
        score -= 10
        all_issues.append(f"Invoice Date: {date_result['message']}")
    elif date_result.get("warning"):
        all_warnings.append(f"Invoice Date: {date_result['message']}")

    hsn_result = validate_hsn_codes(data)
    if not hsn_result["valid"]:
        score -= 10
        all_warnings.append(hsn_result["message"])

    fraud_result = detect_fraud_signals(data)
    if not fraud_result["valid"]:
        score -= len(fraud_result["signals"]) * 5
        all_warnings.extend(fraud_result["signals"])

    required_fields = {
        "seller_name": "Seller name",
        "buyer_name": "Buyer name",
        "invoice_number": "Invoice number",
        "invoice_date": "Invoice date",
        "total": "Total amount",
    }
    for field, label in required_fields.items():
        if not data.get(field):
            score -= 5
            all_issues.append(f"{label} is missing")

    score = max(0, score)

    if score >= 90:
        grade, status = "A", "Excellent"
    elif score >= 75:
        grade, status = "B", "Good"
    elif score >= 60:
        grade, status = "C", "Average"
    elif score >= 40:
        grade, status = "D", "Poor"
    else:
        grade, status = "F", "Critical"

    return {
        "score": score,
        "grade": grade,
        "status": status,
        "issues": all_issues,
        "warnings": all_warnings,
        "passed_checks": [],
        "summary": f"Invoice scored {score}/100 — {status}",
    }
