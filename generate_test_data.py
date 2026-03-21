import os
from PIL import Image, ImageDraw, ImageFont
import random
from datetime import datetime, timedelta

# Create directory if not exists
os.makedirs('test_invoices', exist_ok=True)

def generate_invoice(invoice_id, status="valid"):
    # Image size
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fallback to default
    try:
        font_header = ImageFont.truetype("arial.ttf", 30)
        font_body = ImageFont.truetype("arial.ttf", 18)
        font_mono = ImageFont.truetype("cour.ttf", 18)
    except:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_mono = ImageFont.load_default()

    # Base data
    seller_name = f"SELLER_{invoice_id} LIMITED"
    seller_gstin = "27ABCDE1234F1Z5" # Valid Maharashtra GSTIN
    buyer_name = "URMI TECHNOLOGIES PVT LTD"
    buyer_gstin = "27AAACU1234A1Z1"
    invoice_no = f"INV/2026/{invoice_id:04d}"
    invoice_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%d/%m/%Y")
    
    items = [
        {"desc": "CONSULTING SERVICES", "qty": 1, "rate": 10000},
        {"desc": "CLOUD INFRASTRUCTURE", "qty": 2, "rate": 5000}
    ]
    
    # Inject Issues
    if status == "invalid_gstin":
        seller_gstin = "12345ABCDE" # Invalid format
    elif status == "math_mismatch":
        items[0]["rate"] = 15000 # Will cause mismatch if we keep original total
    elif status == "tax_mismatch":
        pass # Handle in calculation
    elif status == "future_date":
        invoice_date = (datetime.now() + timedelta(days=10)).strftime("%d/%m/%Y")
    
    # Calculations
    subtotal = sum(item["qty"] * item["rate"] for item in items)
    cgst = subtotal * 0.09
    sgst = subtotal * 0.09
    igst = 0
    total = subtotal + cgst + sgst
    
    if status == "math_mismatch":
        total = subtotal + 500 # Intentionally wrong
    elif status == "tax_mismatch":
        sgst = cgst + 100 # Intentionally unequal
    elif status == "igst_cgst_both":
        igst = subtotal * 0.18
        cgst = subtotal * 0.09 # Both present
        total = subtotal + igst + cgst
    
    # DRAWING
    draw.rectangle([20, 20, 780, 980], outline="black", width=2)
    draw.text((300, 40), "TAX INVOICE", fill="black", font=font_header)
    
    # Header Info
    draw.text((40, 100), f"Seller: {seller_name}", fill="black", font=font_body)
    draw.text((40, 130), f"GSTIN: {seller_gstin}", fill="black", font=font_mono)
    
    draw.text((400, 100), f"Buyer: {buyer_name}", fill="black", font=font_body)
    draw.text((400, 130), f"GSTIN: {buyer_gstin}", fill="black", font=font_mono)
    
    draw.line([20, 180, 780, 180], fill="black", width=1)
    
    draw.text((40, 200), f"Invoice No: {invoice_no}", fill="black", font=font_body)
    draw.text((400, 200), f"Date: {invoice_date}", fill="black", font=font_body)
    
    draw.line([20, 250, 780, 250], fill="black", width=1)
    
    # Items Table Header
    draw.text((40, 270), "Description", fill="black", font=font_body)
    draw.text((350, 270), "Qty", fill="black", font=font_body)
    draw.text((450, 270), "Rate", fill="black", font=font_body)
    draw.text((600, 270), "Amount", fill="black", font=font_body)
    
    draw.line([20, 300, 780, 300], fill="black", width=1)
    
    y = 320
    for item in items:
        draw.text((40, y), item["desc"], fill="black", font=font_body)
        draw.text((350, y), str(item["qty"]), fill="black", font=font_body)
        draw.text((450, y), f"{item['rate']:.2f}", fill="black", font=font_body)
        draw.text((600, y), f"{(item['qty'] * item['rate']):.2f}", fill="black", font=font_body)
        y += 40
        
    draw.line([20, 600, 780, 600], fill="black", width=1)
    
    # Totals
    ty = 630
    draw.text((450, ty), "Subtotal:", fill="black", font=font_body)
    draw.text((600, ty), f"₹{subtotal:.2f}", fill="black", font=font_mono)
    
    ty += 30
    draw.text((450, ty), "CGST (9%):", fill="black", font=font_body)
    draw.text((600, ty), f"₹{cgst:.2f}", fill="black", font=font_mono)
    
    ty += 30
    draw.text((450, ty), "SGST (9%):", fill="black", font=font_body)
    draw.text((600, ty), f"₹{sgst:.2f}", fill="black", font=font_mono)
    
    if igst > 0:
        ty += 30
        draw.text((450, ty), "IGST (18%):", fill="black", font=font_body)
        draw.text((600, ty), f"₹{igst:.2f}", fill="black", font=font_mono)
        
    ty += 50
    draw.rectangle([440, ty-5, 760, ty+40], outline="black", width=1)
    draw.text((450, ty+5), "GRAND TOTAL:", fill="black", font=font_header)
    draw.text((650, ty+5), f"₹{total:.2f}", fill="black", font=font_mono)

    # Save
    filename = f"test_invoices/invoice_{invoice_id}_{status}.png"
    image.save(filename)
    return filename

# Generate 20 Invoices
statuses = ["valid"] * 10 + ["invalid_gstin"] * 2 + ["math_mismatch"] * 2 + ["tax_mismatch"] * 2 + ["igst_cgst_both"] * 2 + ["future_date"] * 2
random.shuffle(statuses)

for i, status in enumerate(statuses):
    fn = generate_invoice(i + 1, status)
    print(f"Generated: {fn}")

print("Successfully generated 20 test invoices in test_invoices/ directory.")
