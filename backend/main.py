from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from parser import extract_invoice_data
from database import (
    save_invoice, get_all_invoices, get_analytics, get_itc_summary,
    init_users_table, seed_admin_user, create_user, get_user_by_username
)
from validator import calculate_health_score
from auth import (
    get_current_user, hash_password, verify_password,
    create_access_token, LoginRequest, RegisterRequest
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import openpyxl
import io

# ── App Setup ─────────────────────────────────────────────────────────
app = FastAPI(title="GST Invoice Scanner API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup Event ─────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_users_table()
    seed_admin_user()

# ── Rate Limit Error Handler ─────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

# ── Auth Routes (PUBLIC) ──────────────────────────────────────────────
@app.post("/api/login")
async def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user["username"], "name": user["name"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": user["username"], "name": user["name"]}
    }

@app.post("/api/register")
async def register(req: RegisterRequest):
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = hash_password(req.password)
    user_id = create_user(req.name, req.username, hashed)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Registration failed")
    
    token = create_access_token(data={"sub": req.username, "name": req.name})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"username": req.username, "name": req.name}
    }

# ── Protected Routes ──────────────────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/scan")
@limiter.limit("10/minute")
async def scan_invoice(
    request: Request,
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    allowed_types = [
        "image/jpeg", "image/png", "image/jpg", 
        "application/pdf", 
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only Images, PDF, and Word docs are allowed")
    
    contents = await file.read()
    
    # File size validation
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")
    
    data = extract_invoice_data(contents, file.content_type)
    invoice_id = save_invoice(data)
    data["id"] = invoice_id
    health = calculate_health_score(data)
    data["health_score"] = health
    return data

@app.post("/export")
async def export_invoice(data: dict, current_user: str = Depends(get_current_user)):
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
async def get_invoices(current_user: str = Depends(get_current_user)):
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
async def get_analytics_data(current_user: str = Depends(get_current_user)):
    data = get_analytics()
    return data

@app.get("/itc-summary")
async def get_itc_data(current_user: str = Depends(get_current_user)):
    data = get_itc_summary()
    return data

@app.get("/")
async def root():
    return {"message": "GST Invoice Scanner API is running!", "auth": "JWT Required"}