# Pipeline — GST Invoice Scanner

## Overview

This pipeline converts raw invoice files into structured GST data through clearly defined stages.

The overall flow:

1. Ingest and validate file
2. Convert PDF pages to images (PyMuPDF)
3. Preprocess image (grayscale + binary threshold)
4. Extract text (Tesseract OCR)
5. Semantic extraction via LLM (Gemini 1.5 Flash)
6. Validate extracted data
7. Persist to database and return to client

---

## 1. Input Ingestion

### Supported Formats
- PDF, JPG, PNG

### Steps
- Validate MIME type and file extension (whitelist)
- Enforce 10 MB file size limit
- For PDFs: render up to 2 pages via PyMuPDF at 300 DPI
- For images: load directly into memory

### Output
PIL `Image` objects ready for preprocessing

---

## 2. Image Preprocessing

### Purpose
Improve image quality to increase Tesseract OCR accuracy.

### Implemented Steps
- Convert to grayscale (`ImageOps.grayscale`)
- Apply autocontrast to normalize brightness (`ImageOps.autocontrast`)
- Sharpen character edges (`ImageFilter.SHARPEN`)
- Apply binary threshold — pixels below 128 → black, above → white

### Library
- Pillow (PIL)

### Output
High-contrast grayscale image optimized for OCR

---

## 3. OCR (Optical Character Recognition)

### Engine
- Tesseract via `pytesseract`

### Output
Raw unstructured text blob

### Expected Performance
- 1–3 seconds per page
- Accuracy improved by preprocessing step above

---

## 4. Semantic Field Extraction (LLM)

### Purpose
Convert noisy OCR text into structured JSON with GST-specific fields.

### Implementation
- Provider: Google Gemini 1.5 Flash via `google-genai` SDK
- Prompt: hardcoded structural prompt with XML `<raw_text>` boundary tags
- Retry: exponential backoff — 3 attempts, delays 2s / 4s / 8s on 429/503

### Key Fields Extracted
- `seller_name`, `seller_gstin`
- `buyer_name`, `buyer_gstin`
- `invoice_number`, `invoice_date`
- `subtotal`, `cgst`, `sgst`, `igst`, `total`

### Security
XML boundary tags prevent prompt injection from malicious PDF content.

### Output
Structured JSON object

---

## 5. Validation and Cross-Verification

### Rules Applied
- GSTIN format: 15-char regex + state code range check (1–37)
- Invoice date: multi-format parsing, future date rejection, age warning (>90 days)
- Tax math: subtotal × rate ≈ tax; CGST must equal SGST for intrastate
- IGST/CGST mutual exclusion: interstate invoices should only have IGST
- Fraud signals: round totals, identical item amounts, single high-value items
- Required fields: seller name, buyer name, invoice number, date, total

### Output
Health score (0–100), grade (A–F), issues list, warnings list

---

## 6. Persistence

### Database
Neon Serverless PostgreSQL via SQLAlchemy ORM

### Job State
All job state is DB-backed — no in-memory dicts. Safe across multiple Gunicorn workers.

### Indexes
- `(company_id, status)` — for status filtering
- `(company_id, created_at)` — for analytics time-series queries

---

## 7. Output

### Formats
- JSON (API response)
- CSV (export via `POST /api/export`)

### Example JSON Response
```json
{
  "id": "uuid",
  "status": "completed",
  "invoice_number": "INV-1024",
  "invoice_date": "12-06-2025",
  "seller_gstin": "29ABCDE1234F1Z5",
  "buyer_gstin": "27PQRSX5678L1Z2",
  "subtotal": 10000.0,
  "cgst": 900.0,
  "sgst": 900.0,
  "igst": 0.0,
  "total": 11800.0,
  "health_score": {
    "score": 88,
    "grade": "B",
    "status": "Good",
    "issues": [],
    "warnings": [],
    "summary": "Invoice scored 88/100 — Good"
  }
}
```

---

## 8. Error Handling

| Stage | Issue | Handling |
|---|---|---|
| Input | Unsupported file type | HTTP 422 / 413 |
| Input | Corrupt PDF | `fitz.FileDataError` → `status=FAILED` in DB |
| Preprocessing | Image conversion error | Log + fall back to raw image |
| OCR | Empty text output | `status=FAILED` with descriptive error |
| LLM | Transient 429/503 | Exponential backoff retry (3 attempts) |
| LLM | No JSON in response | `status=FAILED` |
| Validation | Tax mismatch / bad GSTIN | Health score deduction + issue flag |

---

## 9. Performance

| Metric | Typical Range |
|---|---|
| Processing time (per invoice) | 3–10 seconds |
| OCR time (per page) | 1–3 seconds |
| LLM extraction | 1–4 seconds |
| Health score calculation | < 50ms |
