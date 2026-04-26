import os
import random
import shutil
from PIL import Image, ImageDraw, ImageFont

# Define the 5 unique companies
COMPANIES = [
    {"name": "TechCorp India", "gstin": "27AADCB2230M1Z2", "address": "Mumbai, Maharashtra"},
    {"name": "Global Solutions", "gstin": "29ABCDE1234F2Z5", "address": "Bangalore, Karnataka"},
    {"name": "Innovatex Pvt Ltd", "gstin": "07AACCI1234G1Z2", "address": "New Delhi, Delhi"},
    {"name": "Smart Systems", "gstin": "33AABCS1429B1Z4", "address": "Chennai, Tamil Nadu"},
    {"name": "NextGen Tech", "gstin": "19AAAAA0000A1Z5", "address": "Kolkata, West Bengal"}
]

# Clean up old invoices
TEST_DIR = "test_invoices"
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR)

# Generate 20 relationships
relationships = []
invoices = []

print("Generating 20 new test invoices...")

for i in range(1, 21):
    # Pick random sender and receiver (must be different)
    seller = random.choice(COMPANIES)
    buyer = random.choice([c for c in COMPANIES if c != seller])
    
    invoice_no = f"INV-{1000 + i}"
    date = f"{random.randint(1,28):02d}-03-2024"
    amount = random.randint(1000, 50000)
    cgst = amount * 0.09
    sgst = amount * 0.09
    total = amount + cgst + sgst
    
    # Store relationship
    relationships.append({
        "file": f"invoice_{i}.png",
        "seller": seller["name"],
        "seller_gstin": seller["gstin"],
        "buyer": buyer["name"],
        "buyer_gstin": buyer["gstin"],
        "amount": round(total, 2)
    })
    
    # Draw image using PIL
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    try:
        # Try to use a default font if available, else default
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_bold = ImageFont.truetype("arialbd.ttf", 20)
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font_title = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font = ImageFont.load_default()
        
    y = 40
    d.text((300, y), "TAX INVOICE", fill=(0,0,0), font=font_title)
    
    y += 80
    d.text((50, y), "SELLER DETAILS:", fill=(0,0,0), font=font_bold)
    d.text((500, y), f"Invoice No: {invoice_no}", fill=(0,0,0), font=font_bold)
    
    y += 30
    d.text((50, y), f"Name: {seller['name']}", fill=(0,0,0), font=font)
    d.text((500, y), f"Date: {date}", fill=(0,0,0), font=font)
    
    y += 30
    d.text((50, y), f"GSTIN: {seller['gstin']}", fill=(0,0,0), font=font)
    
    y += 30
    d.text((50, y), f"Address: {seller['address']}", fill=(0,0,0), font=font)
    
    y += 80
    d.text((50, y), "BUYER DETAILS:", fill=(0,0,0), font=font_bold)
    
    y += 30
    d.text((50, y), f"Name: {buyer['name']}", fill=(0,0,0), font=font)
    
    y += 30
    d.text((50, y), f"GSTIN: {buyer['gstin']}", fill=(0,0,0), font=font)
    
    y += 30
    d.text((50, y), f"Address: {buyer['address']}", fill=(0,0,0), font=font)
    
    y += 80
    d.text((50, y), "--------------------------------------------------------------------------------", fill=(0,0,0), font=font)
    y += 20
    d.text((50, y), "Item Description                     Qty      Rate        Amount", fill=(0,0,0), font=font_bold)
    y += 30
    d.text((50, y), f"Software Services                    1        {amount}       {amount}", fill=(0,0,0), font=font)
    y += 30
    d.text((50, y), "--------------------------------------------------------------------------------", fill=(0,0,0), font=font)
    
    y += 30
    d.text((450, y), f"Subtotal: Rs. {amount:.2f}", fill=(0,0,0), font=font)
    y += 30
    d.text((450, y), f"CGST (9%): Rs. {cgst:.2f}", fill=(0,0,0), font=font)
    y += 30
    d.text((450, y), f"SGST (9%): Rs. {sgst:.2f}", fill=(0,0,0), font=font)
    y += 40
    d.text((450, y), f"TOTAL: Rs. {total:.2f}", fill=(0,0,0), font=font_bold)
    
    filename = os.path.join(TEST_DIR, f"invoice_{i}.png")
    img.save(filename)

# Clear DB Invoices
print("Connecting to DB to clear old invoices...")
import sys
sys.path.append('backend')
from database import SessionLocal
from models import Invoice

db = SessionLocal()
try:
    deleted = db.query(Invoice).delete()
    db.commit()
    print(f"Deleted {deleted} old invoices from the database.")
except Exception as e:
    print(f"Failed to delete DB invoices: {e}")
finally:
    db.close()

# Write the report
with open("invoice_relationships_report.md", "w") as f:
    f.write("# Invoice Test Data Report\n\n")
    
    f.write("## The 5 Unique Companies & GSTINs\n")
    for c in COMPANIES:
        f.write(f"- **{c['name']}** | GSTIN: `{c['gstin']}`\n")
        
    f.write("\n## Who Sent Invoices To Whom (20 Invoices)\n")
    f.write("| File Name | Seller (Sender) | Buyer (Receiver) | Total Amount |\n")
    f.write("|-----------|-----------------|------------------|--------------|\n")
    for r in relationships:
        f.write(f"| {r['file']} | {r['seller']} | {r['buyer']} | Rs. {r['amount']} |\n")

print("Done! Report saved to invoice_relationships_report.md")
