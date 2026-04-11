# GST Invoice Scanner

Extract structured data from Indian GST invoices using OCR and LLMs.

## What It Does

Processes invoices (PDF, JPG, PNG) and extracts key fields like GSTIN, amounts, tax breakdowns, etc. Uses Tesseract for OCR and Groq LLM for parsing the text into structured JSON.

## Why

Manual invoice data entry is tedious. This automates it. Works with varying invoice formats since it uses an LLM instead of rigid templates.

## Tech Stack

- **Backend**: FastAPI + Python
- **Database**: PostgreSQL (Supabase)
- **OCR**: Tesseract + PyMuPDF
- **AI**: Groq (Llama 3.3 70B)
- **Frontend**: Vanilla JS (no framework)
- **Auth**: JWT + Bcrypt

## Setup

```bash
git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
cd gst_invoice_scanner
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

You'll need Tesseract installed:
- Mac: `brew install tesseract`
- Ubuntu: `apt-get install tesseract-ocr`
- Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Configuration

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
JWT_SECRET=your_secret_key
DATABASE_URL=postgresql://user:pass@host/db
```

Get your Groq API key from: https://console.groq.com/keys

## Running

Backend:
```bash
cd backend
python run.py
```

Frontend:
```bash
cd frontend
python -m http.server 5500
```

Open http://localhost:5500/login.html

API docs: http://localhost:8000/docs

## How It Works

1. User uploads invoice
2. Backend returns job ID immediately
3. Background worker:
   - Converts PDF to image (if needed)
   - Runs OCR with Tesseract
   - Sends text to Groq LLM for parsing
   - Validates and saves structured data to DB
4. Frontend polls for results

## Features

- ✅ Multi-format support (PDF, JPG, PNG)
- ✅ Bulk upload (up to 20 files)
- ✅ Manual edit after OCR
- ✅ Duplicate detection
- ✅ Invoice approval workflow
- ✅ Vendor management
- ✅ Search & filters
- ✅ CSV export
- ✅ Health score validation

## Example Output

```json
{
  "seller_name": "ABC Tech Solutions",
  "seller_gstin": "27ABCDE1234F1Z5",
  "buyer_name": "XYZ Corp",
  "invoice_number": "INV-1045",
  "invoice_date": "15-10-2024",
  "subtotal": 5000.00,
  "cgst": 450.00,
  "sgst": 450.00,
  "total": 5900.00,
  "health_score": {
    "score": 88,
    "grade": "B",
    "status": "Good"
  }
}
```

## Deployment

- **Frontend**: Vercel / Netlify
- **Backend**: Render
- **Database**: Supabase PostgreSQL

See `VERCEL_DEPLOYMENT.md` for deployment instructions.

## License

MIT
