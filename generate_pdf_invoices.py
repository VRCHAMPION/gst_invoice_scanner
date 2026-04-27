"""
generate_pdf_invoices.py
Generates 20 professional PDF GST invoices with the exact same data as the old PNGs.
Uses reportlab for high-quality, OCR-friendly PDF output.
"""
import os
import glob
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# ── Exact same data as the PNG invoices (from invoice_relationships_report.md) ──
COMPANIES = {
    "TechCorp India":    {"gstin": "27AADCB2230M1Z2", "address": "Mumbai, Maharashtra - 400001"},
    "Global Solutions":  {"gstin": "29ABCDE1234F2Z5", "address": "Bangalore, Karnataka - 560001"},
    "Innovatex Pvt Ltd": {"gstin": "07AACCI1234G1Z2", "address": "New Delhi, Delhi - 110001"},
    "Smart Systems":     {"gstin": "33AABCS1429B1Z4", "address": "Chennai, Tamil Nadu - 600001"},
    "NextGen Tech":      {"gstin": "19AAAAA0000A1Z5", "address": "Kolkata, West Bengal - 700001"},
}

# Exact totals from the report — back-calculate subtotal (total / 1.18)
INVOICE_DATA = [
    (1,  "TechCorp India",    "NextGen Tech",       44962.72, "15-03-2024"),
    (2,  "Global Solutions",  "TechCorp India",     44614.62, "03-03-2024"),
    (3,  "TechCorp India",    "Smart Systems",       9275.98, "22-03-2024"),
    (4,  "Smart Systems",     "TechCorp India",     29654.58, "08-03-2024"),
    (5,  "Global Solutions",  "Smart Systems",      55266.48, "17-03-2024"),
    (6,  "TechCorp India",    "Global Solutions",   49643.78, "05-03-2024"),
    (7,  "Innovatex Pvt Ltd", "TechCorp India",     40418.54, "03-04-2024"),
    (8,  "TechCorp India",    "Global Solutions",    8730.82, "11-03-2024"),
    (9,  "Global Solutions",  "TechCorp India",     10868.98, "27-03-2024"),
    (10, "NextGen Tech",      "Innovatex Pvt Ltd",  55661.78, "19-03-2024"),
    (11, "Smart Systems",     "Innovatex Pvt Ltd",  12688.54, "24-03-2024"),
    (12, "NextGen Tech",      "Global Solutions",   32365.04, "14-03-2024"),
    (13, "Global Solutions",  "TechCorp India",     52958.40, "02-03-2024"),
    (14, "Innovatex Pvt Ltd", "Global Solutions",    7552.00, "28-03-2024"),
    (15, "Smart Systems",     "TechCorp India",     19198.60, "10-03-2024"),
    (16, "Global Solutions",  "Innovatex Pvt Ltd",  58863.12, "07-03-2024"),
    (17, "Innovatex Pvt Ltd", "TechCorp India",     56327.30, "21-03-2024"),
    (18, "Global Solutions",  "NextGen Tech",       50875.70, "13-03-2024"),
    (19, "TechCorp India",    "Innovatex Pvt Ltd",  48594.76, "26-03-2024"),
    (20, "Smart Systems",     "TechCorp India",     22279.58, "16-03-2024"),
]

TEST_DIR = "test_invoices"
os.makedirs(TEST_DIR, exist_ok=True)

styles = getSampleStyleSheet()

def make_style(name, parent="Normal", **kwargs):
    return ParagraphStyle(name, parent=styles[parent], **kwargs)

title_style   = make_style("InvTitle",  fontSize=22, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=colors.HexColor("#1a1a2e"), spaceAfter=2)
sub_style     = make_style("InvSub",    fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor("#555555"), spaceAfter=8)
label_style   = make_style("Label",     fontSize=8,  fontName="Helvetica-Bold", textColor=colors.HexColor("#888888"))
value_style   = make_style("Value",     fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#1a1a2e"))
small_style   = make_style("Small",     fontSize=9,  textColor=colors.HexColor("#444444"))
header_style  = make_style("Header",    fontSize=9,  fontName="Helvetica-Bold", textColor=colors.white)
cell_style    = make_style("Cell",      fontSize=10, textColor=colors.HexColor("#222222"))
right_style   = make_style("Right",     fontSize=10, alignment=TA_RIGHT, textColor=colors.HexColor("#222222"))
total_style   = make_style("Total",     fontSize=13, fontName="Helvetica-Bold", alignment=TA_RIGHT, textColor=colors.HexColor("#1a1a2e"))

def build_invoice_pdf(num, seller_name, buyer_name, total, date_str):
    seller  = COMPANIES[seller_name]
    buyer   = COMPANIES[buyer_name]
    inv_no  = f"INV-{1000 + num}"

    # Back-calculate taxes (18% GST split equally as CGST+SGST)
    subtotal = round(total / 1.18, 2)
    cgst     = round(subtotal * 0.09, 2)
    sgst     = round(subtotal * 0.09, 2)
    # Adjust for rounding
    actual_total = round(subtotal + cgst + sgst, 2)

    filename = os.path.join(TEST_DIR, f"invoice_{num}.pdf")
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm,   bottomMargin=12*mm,
    )

    story = []

    # ── Header banner ──
    story.append(Paragraph("TAX INVOICE", title_style))
    story.append(Paragraph("GOODS AND SERVICES TAX INVOICE", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e"), spaceAfter=10))

    # ── Invoice meta + party details ──
    meta_data = [
        [
            Paragraph(f"<b>Invoice No:</b> {inv_no}", small_style),
            Paragraph(f"<b>Invoice Date:</b> {date_str}", small_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[90*mm, 90*mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f4f6fb")),
        ("BOX",        (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6*mm))

    # ── Seller / Buyer block ──
    party_data = [
        [Paragraph("SELLER DETAILS", label_style), Paragraph("BUYER DETAILS", label_style)],
        [Paragraph(seller_name.upper(), value_style), Paragraph(buyer_name.upper(), value_style)],
        [Paragraph(f"GSTIN: {seller['gstin']}", small_style), Paragraph(f"GSTIN: {buyer['gstin']}", small_style)],
        [Paragraph(seller["address"], small_style), Paragraph(buyer["address"], small_style)],
    ]
    party_table = Table(party_data, colWidths=[90*mm, 90*mm])
    party_table.setStyle(TableStyle([
        ("BOX",       (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("LINEAFTER", (0,0), (0,-1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8ecf5")),
    ]))
    story.append(party_table)
    story.append(Spacer(1, 6*mm))

    # ── Line items table ──
    item_header = [
        Paragraph("DESCRIPTION", header_style),
        Paragraph("HSN", header_style),
        Paragraph("QTY", header_style),
        Paragraph("RATE (Rs.)", header_style),
        Paragraph("AMOUNT (Rs.)", header_style),
    ]
    item_row = [
        Paragraph("Software Services", cell_style),
        Paragraph("998314", cell_style),
        Paragraph("1", cell_style),
        Paragraph(f"{subtotal:,.2f}", right_style),
        Paragraph(f"{subtotal:,.2f}", right_style),
    ]
    items_table = Table([item_header, item_row], colWidths=[70*mm, 20*mm, 15*mm, 35*mm, 40*mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("LINEBELOW",     (0,0), (-1,0), 1, colors.HexColor("#1a1a2e")),
        ("GRID",          (0,1), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ALIGN",         (2,0), (-1,-1), "RIGHT"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4*mm))

    # ── Tax summary ──
    tax_data = [
        ["", Paragraph("Taxable Value (Subtotal):", right_style), Paragraph(f"Rs. {subtotal:,.2f}", right_style)],
        ["", Paragraph("CGST @ 9%:", right_style),                Paragraph(f"Rs. {cgst:,.2f}",     right_style)],
        ["", Paragraph("SGST @ 9%:", right_style),                Paragraph(f"Rs. {sgst:,.2f}",     right_style)],
        ["", Paragraph("IGST @ 0%:", right_style),                Paragraph("Rs. 0.00",              right_style)],
        ["", Paragraph("<b>GRAND TOTAL:</b>",    total_style),     Paragraph(f"<b>Rs. {actual_total:,.2f}</b>", total_style)],
    ]
    tax_table = Table(tax_data, colWidths=[60*mm, 70*mm, 50*mm])
    tax_table.setStyle(TableStyle([
        ("LINEABOVE",     (1,4), (-1,4), 1.5, colors.HexColor("#1a1a2e")),
        ("BACKGROUND",    (1,4), (-1,4), colors.HexColor("#f4f6fb")),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(tax_table)
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=6))
    story.append(Paragraph("This is a computer-generated invoice. No signature required.", sub_style))

    doc.build(story)
    return filename, actual_total


# ── Generate all 20 PDFs ──
print("Generating 20 PDF invoices...\n")
pdf_relationships = []

for num, seller, buyer, total, date in INVOICE_DATA:
    filename, actual_total = build_invoice_pdf(num, seller, buyer, total, date)
    pdf_relationships.append((num, seller, buyer, actual_total))
    print(f"  ✓ invoice_{num}.pdf  |  {seller} → {buyer}  |  Rs. {actual_total:,.2f}")

# ── Delete all PNG files ──
print("\nDeleting old PNG files...")
deleted = 0
for png_file in glob.glob(os.path.join(TEST_DIR, "*.png")):
    os.remove(png_file)
    deleted += 1
print(f"  Deleted {deleted} PNG files.")

# ── Update the report ──
with open("invoice_relationships_report.md", "w") as f:
    f.write("# Invoice Test Data Report\n\n")
    f.write("## The 5 Unique Companies & GSTINs\n")
    for name, info in COMPANIES.items():
        f.write(f"- **{name}** | GSTIN: `{info['gstin']}`\n")
    f.write("\n## Who Sent Invoices To Whom (20 Invoices)\n")
    f.write("| File Name | Seller (Sender) | Buyer (Receiver) | Total Amount |\n")
    f.write("|-----------|-----------------|------------------|--------------|\n")
    for num, seller, buyer, total in pdf_relationships:
        f.write(f"| invoice_{num}.pdf | {seller} | {buyer} | Rs. {total} |\n")

print("\n✅ Done! 20 PDF invoices generated in test_invoices/")
print("   Report updated: invoice_relationships_report.md")
