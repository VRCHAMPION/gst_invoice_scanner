from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from parser import extract_invoice_data
from database import save_invoice, get_all_invoices, get_analytics, get_itc_summary
from validator import calculate_health_score
import openpyxl
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/scan")
async def scan_invoice(file: UploadFile = File(...)):
    allowed_types = [
        "image/jpeg", "image/png", "image/jpg", 
        "application/pdf", 
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only Images, PDF, and Word docs are allowed")
    contents = await file.read()
    data = extract_invoice_data(contents, file.content_type)
    invoice_id = save_invoice(data)
    data["id"] = invoice_id
    health = calculate_health_score(data)
    data["health_score"] = health
    return data

@app.post("/export")
async def export_invoice(data: dict):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "GST Invoice"
    ws.append(["INVOICE DETAILS"])
    ws.append(["Seller Name", data.get("seller_name", "")])
    ws.append(["Seller GSTIN", data.get("seller_gstin", "")])
    ws.append(["Buyer Name", data.get("buyer_name", "")])
    ws.append(["Buyer GSTIN", data.get("buyer_gstin", "")])
    ws.append(["Invoice Number", data.get("invoice_number", "")])
    ws.append(["Invoice Date", data.get("invoice_date", "")])
    ws.append([])
    ws.append(["ITEMS"])
    ws.append(["Description", "Quantity", "Rate", "Amount"])
    items = data.get("items", [])
    for item in items:
        ws.append([
            item.get("description", ""),
            item.get("quantity", 0),
            item.get("rate", 0),
            item.get("amount", 0)
        ])
    ws.append([])
    ws.append(["TAX SUMMARY"])
    ws.append(["Subtotal", data.get("subtotal", 0)])
    ws.append(["CGST", data.get("cgst", 0)])
    ws.append(["SGST", data.get("sgst", 0)])
    ws.append(["IGST", data.get("igst", 0)])
    ws.append(["TOTAL", data.get("total", 0)])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=invoice.xlsx"}
    )

@app.get("/invoices")
async def get_invoices():
    rows = get_all_invoices()
    invoices = []
    for row in rows:
        invoices.append({
            "id": row[0],
            "seller_name": row[1],
            "buyer_name": row[2],
            "invoice_number": row[3],
            "invoice_date": row[4],
            "total": row[5],
            "created_at": str(row[6])
        })
    return invoices

@app.get("/analytics")
async def get_analytics_data():
    data = get_analytics()
    return data

@app.get("/itc-summary")
async def get_itc_data():
    data = get_itc_summary()
    return data

@app.get("/")
async def root():
    return {"message": "GST Invoice Scanner API is running!"}