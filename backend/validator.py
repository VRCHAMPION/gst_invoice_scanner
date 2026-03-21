from datetime import datetime, date
import re

def validate_gstin(gstin: str) -> dict:
    if not gstin:
        return{"valid" : False, "message": "gstin is missing"}

    if len(gstin) != 15:
        return{"valid" : False, "message": "gstin must be 15 characters long"}
    pattern = r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'
    if not re.match(pattern, gstin.upper()):
        return{"valid" : False, "message": "invalid gstin format"}
    
    state_code = int(gstin[:2])
    if state_code < 1 or state_code > 37:
        return {"valid": False, "message": f"Invalid state code: {gstin[:2]}"}

    return {"valid" : True, "message": "gstin is valid"}

def validate_mathematics(data: dict) -> dict:
    issues=[]

    items = data.get("items")
    subtotal = data.get("subtotal")
    cgst = data.get("cgst")
    sgst = data.get("sgst")
    igst = data.get("igst")
    total = data.get("total")

    if not items:
        issues.append("No items found in invoice")
        return {"issues": issues}

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

    # Check 3 — total = subtotal + cgst + sgst + igst
    expected_total = round((subtotal or 0) + cgst + sgst + igst, 2)
    if total and abs(expected_total - total) > 1:
        issues.append(
            f"Total mismatch: subtotal({subtotal}) + taxes({cgst + sgst + igst}) "
            f"= {expected_total} but total shows {total}"
        )

    # Check 4 — CGST should equal SGST for intrastate
    if cgst and sgst and abs(cgst - sgst) > 1:
        issues.append(
            f"CGST (₹{cgst}) ≠ SGST (₹{sgst}) — "
            f"for intrastate transactions they must be equal"
        )

    # Check 5 — if IGST is present, CGST and SGST should be 0
    if igst and igst > 0:
        if cgst and cgst > 0:
            issues.append(
                "IGST and CGST both present — "
                "interstate invoices should only have IGST"
            )

    return {"valid": len(issues) == 0, "issues": issues}


def validate_invoice_date(invoice_date: str) -> dict:
    if not invoice_date:
        return {"valid": False, "message": "Invoice date is missing"}

    # Try multiple date formats
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
        "%d %B %Y", "%d %b %Y", "%B %d, %Y"
    ]

    parsed_date = None
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(invoice_date.strip(), fmt).date()
            break
        except ValueError:
            continue

    if not parsed_date:
        return {
            "valid": False,
            "message": f"Could not parse invoice date: '{invoice_date}'"
        }

    today = date.today()

    # Check if date is in the future
    if parsed_date > today:
        return {
            "valid": False,
            "message": f"Invoice date {invoice_date} is in the future"
        }

    # Check if date is more than 1 year old
    days_old = (today - parsed_date).days
    if days_old > 365:
        return {
            "valid": False,
            "message": f"Invoice is {days_old} days old — verify before processing"
        }

    # Check if date is more than 3 months old — warning
    if days_old > 90:
        return {
            "valid": True,
            "message": f"Invoice is {days_old} days old — confirm this is intentional",
            "warning": True
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
        return {
            "valid": False,
            "message": f"HSN code missing for: {', '.join(missing_hsn)}"
        }

    return {"valid": True, "message": "All items have HSN codes"}


def detect_fraud_signals(data: dict) -> dict:
    signals = []
    items = data.get("items") or []
    total = data.get("total") or 0

    # Check 1 — suspiciously round total
    if total and total > 0:
        if total % 1000 == 0:
            signals.append(
                f"Total amount ₹{total} is a perfectly round number — verify"
            )

    # Check 2 — all items have same amount
    amounts = [item.get("amount") for item in items if item.get("amount")]
    if len(amounts) > 1 and len(set(amounts)) == 1:
        signals.append(
            "All items have identical amounts — unusual pattern"
        )

    # Check 3 — single item invoice with very high value
    if len(items) == 1 and total and total > 100000:
        signals.append(
            f"Single item invoice worth ₹{total} — verify authenticity"
        )

    # Check 4 — quantity is 0 or negative
    for item in items:
        qty = item.get("quantity") or 0
        if qty <= 0:
            signals.append(
                f"Item '{item.get('description', 'Unknown')}' "
                f"has invalid quantity: {qty}"
            )

    return {
        "valid": len(signals) == 0,
        "signals": signals
    }


def calculate_health_score(data: dict) -> dict:
    score = 100
    all_issues = []
    all_warnings = []

    # --- Check 1: Seller GSTIN (-15 if invalid) ---
    seller_gstin_result = validate_gstin(data.get("seller_gstin", ""))
    if not seller_gstin_result["valid"]:
        score -= 15
        all_issues.append(f"Seller GSTIN: {seller_gstin_result['message']}")

    # --- Check 2: Buyer GSTIN (-15 if invalid) ---
    buyer_gstin_result = validate_gstin(data.get("buyer_gstin", ""))
    if not buyer_gstin_result["valid"]:
        score -= 15
        all_issues.append(f"Buyer GSTIN: {buyer_gstin_result['message']}")

    # --- Check 3: Mathematics (-20 if wrong) ---
    math_result = validate_mathematics(data)
    if not math_result["valid"]:
        score -= 20
        all_issues.extend(math_result["issues"])

    # --- Check 4: Invoice Date (-10 if invalid) ---
    date_result = validate_invoice_date(data.get("invoice_date", ""))
    if not date_result["valid"]:
        score -= 10
        all_issues.append(f"Invoice Date: {date_result['message']}")
    elif date_result.get("warning"):
        all_warnings.append(f"Invoice Date: {date_result['message']}")

    # --- Check 5: HSN Codes (-10 if missing) ---
    hsn_result = validate_hsn_codes(data)
    if not hsn_result["valid"]:
        score -= 10
        all_warnings.append(hsn_result["message"])

    # --- Check 6: Fraud Signals (-5 per signal) ---
    fraud_result = detect_fraud_signals(data)
    if not fraud_result["valid"]:
        score -= len(fraud_result["signals"]) * 5
        all_warnings.extend(fraud_result["signals"])

    # --- Check 7: Required fields missing (-5 each) ---
    required_fields = {
        "seller_name": "Seller name",
        "buyer_name": "Buyer name",
        "invoice_number": "Invoice number",
        "invoice_date": "Invoice date",
        "total": "Total amount"
    }
    for field, label in required_fields.items():
        if not data.get(field):
            score -= 5
            all_issues.append(f"{label} is missing")

    # Ensure score doesn't go below 0
    score = max(0, score)

    # Determine grade
    if score >= 90:
        grade = "A"
        status = "Excellent"
    elif score >= 75:
        grade = "B"
        status = "Good"
    elif score >= 60:
        grade = "C"
        status = "Average"
    elif score >= 40:
        grade = "D"
        status = "Poor"
    else:
        grade = "F"
        status = "Critical"

    return {
        "score": score,
        "grade": grade,
        "status": status,
        "issues": all_issues,
        "warnings": all_warnings,
        "passed_checks": [],
        "summary": f"Invoice scored {score}/100 — {status}"
    }
    