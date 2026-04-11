# GST Invoice Scanner

A system for extracting structured GST data from unstructured invoices using OCR and large language models.

---

## Overview

GST Invoice Scanner is designed to process real-world invoices that do not follow fixed templates. Instead of relying on coordinate-based extraction, it uses a two-step pipeline:

1. Optical Character Recognition (OCR) to extract raw text
2. A language model to interpret and structure that text

This approach allows the system to handle varying invoice formats and still produce consistent, structured output.

---

## Problem

Businesses often receive invoices in multiple formats, making automated data extraction difficult. Traditional systems depend on fixed layouts, which break when formats change.

This project addresses that by focusing on semantic understanding rather than positional rules.

---

## Approach

The system follows an asynchronous processing model:

* The user uploads an invoice (PDF, JPG, PNG)
* The backend assigns a job ID and processes the file in the background
* OCR extracts raw text from the document
* A language model converts the text into structured JSON
* The frontend polls for results and displays the extracted data

---

## Features

* **Enterprise Document Parsing:** Works gracefully with non-standard invoice formats natively.
* **Asynchronous Resiliency:** Background processing with built-in PyMuPDF C-level failure trapping.
* **OCR Text Extraction:** Tesseract handles the dense visual layer.
* **Semantic Extraction:** Powered by Google Gemini 2.5 Flash for JSON-structured deterministic outputs.
* **Financial Determinism:** SQLAlchemy aggregations executing heavily optimized Postgres queries.
* **Military-Grade Security:** Deep HttpOnly/SameSite Cookie pivot prevents XSS token theft.
* **Cross-Validation:** Programmatic verification of CGST/SGST/IGST mapping and 15-character GSTIN logic.

---

## Example Output

```json
{
  "seller_name": "ABC Tech Solutions",
  "seller_gstin": "27ABCDE1234F1Z5",
  "buyer_name": "XYZ Corp Pvt Ltd",
  "buyer_gstin": "27XYZAB5678C1Z2",
  "invoice_number": "INV-1045",
  "invoice_date": "2023-10-15",
  "subtotal": 5000.00,
  "cgst": 450.00,
  "sgst": 450.00,
  "igst": 0.00,
  "total": 5900.00
}
```

---

## Tech Stack

* **Backend:** FastAPI (Python)
* **Database:** Neon Serverless PostgreSQL with SQLAlchemy ORM
* **Auth:** HttpOnly JWT Cookies (python-jose) + Bcrypt
* **OCR Foundation:** Tesseract (pytesseract) + PyMuPDF
* **AI Parsing:** Google Gemini 2.5 Flash
* **Frontend:** Dynamic HTML/Vanilla JS with apiFetch Credential Interceptors

---

## Architecture Summary

* Client uploads invoice
* Backend returns a job ID immediately
* Background worker processes the file
* OCR extracts text
* LLM structures the data
* Result is stored and returned to the client

---

## Project Structure

```
gst_invoice_scanner/
├── backend/
│   ├── main.py              # App factory — middleware + router registration
│   ├── auth.py              # JWT, bcrypt, RBAC dependency
│   ├── schemas.py           # All Pydantic request + response models
│   ├── models.py            # SQLAlchemy ORM models
│   ├── database.py          # Engine, session, ping_db
│   ├── validator.py         # GSTIN, math, fraud, health score
│   ├── parser.py            # OCR + Gemini pipeline
│   ├── run.py               # Dev entry point
│   ├── routers/
│   │   ├── auth.py          # /api/login, /api/register, /api/logout, /api/me
│   │   ├── companies.py     # /api/companies, /api/join-request, /api/users
│   │   ├── invoices.py      # /api/scan, /api/scan/status, /api/invoices, /api/export
│   │   └── analytics.py     # /api/analytics, /api/itc-summary
│   ├── services/
│   │   └── invoice_service.py  # Background processing logic
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_companies.py
│       ├── test_invoices.py
│       └── test_validator.py
├── frontend/
│   ├── js/
│   │   ├── config.js        # API base URL, apiFetch wrapper
│   │   ├── utils.js         # Shared: formatCurrency, formatDate, animateCounter
│   │   ├── auth.js          # Auth state management
│   │   ├── upload.js        # File upload + polling (2-min timeout)
│   │   ├── results.js       # Scan result display + CSV export
│   │   └── analytics.js     # Charts + ITC summary
├── .github/workflows/ci.yml # CI: ruff lint + pytest
├── Dockerfile               # Production container with HEALTHCHECK
├── render.yaml              # Render deployment config
├── ARCHITECTURE.md
├── PIPELINE.md
└── README.md
```

---

## Setup

### Prerequisites

* Python 3.10+
* Tesseract OCR installed on your system

### Installation

```
git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
cd gst_invoice_scanner
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
```

---

## Configuration

Create a `.env` file inside the `backend/` directory:

```env
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET=your_jwt_secret_key
DATABASE_URL=postgresql://user:pass@ep-shiny...
```

---

## Running the Application

Start the backend:

```
cd backend
python run.py
```

API documentation will be available at:
http://127.0.0.1:8000/docs

> **Tip:** The `/docs` endpoint provides a full interactive API reference (Swagger UI) — use it to explore and test all endpoints directly from your browser.

Start the frontend:

```
cd frontend
python -m http.server 5500
```

Open in browser:
http://localhost:5500/login.html

---

## Limitations

* Accuracy depends on OCR quality
* Performance varies with invoice complexity
* Requires proper Tesseract installation

---

## Future Work

* Improve extraction accuracy with fine-tuned models
* Add batch processing support
* Introduce analytics and reporting features
* Explore fraud or anomaly detection

---

## License

MIT License
