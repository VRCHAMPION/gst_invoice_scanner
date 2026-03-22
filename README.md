<div align="center">

# GST Invoice Scanner

**AI-powered invoice intelligence for Indian businesses**

A full-stack web application that scans GST invoices, validates compliance, calculates Input Tax Credit, and delivers supplier analytics — completely free.

[![Python](https://img.shields.io/badge/Python-3.14-3776ab?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/AI-Groq%20Llama--4--Scout-f55036?style=flat-square)](https://groq.com)
[![Neon](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00e599?style=flat-square)](https://neon.tech)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#)

[Live Demo](#) · [Report Bug](https://github.com/VRCHAMPION/gst_invoice_scanner/issues) · [Request Feature](https://github.com/VRCHAMPION/gst_invoice_scanner/issues)

</div>

---

## The Problem

Tools like ClearTax and Vyapar charge Indian businesses **₹5,000–₹20,000/year** for AI invoice scanning and ITC calculation. Small businesses and independent accountants often can't afford these tools — yet they deal with the same compliance burden.

This project delivers the same core intelligence **for free**, plus a unique **Invoice Health Score** that no competitor offers at any price tier.

| | ClearTax | Vyapar | **This App** |
|---|:---:|:---:|:---:|
| AI Invoice Scanning | ✅ Paid | ✅ Paid | **✅ Free** |
| Invoice Health Score | ❌ | ❌ | **✅ Free** |
| ITC Calculator | ✅ Paid | ✅ Paid | **✅ Free** |
| Supplier Spend Analytics | ✅ Paid | ✅ Paid | **✅ Free** |
| GST Deadline Tracker | ❌ | ❌ | **✅ Free** |
| JWT Authentication | ✅ | ✅ | **✅** |

---

## Screenshots

| Login | Upload |
|---|---|
| ![Login](screenshots/dashboard_login.png) | ![Upload](screenshots/dashboard_upload.png) |

| Results & Health Score | Analytics Dashboard |
|---|---|
| ![Results](screenshots/dashboard_results.png) | ![Analytics](screenshots/dashboard_analytics.png) |

| Transaction History |
|---|
| ![History](screenshots/dashboard_history.png) |

---

## Features

### 🤖 AI Invoice Scanning
Upload any GST invoice image (JPG/PNG). Groq's Llama-4-Scout Vision model extracts every field — seller name, buyer name, both GSTINs, all line items with quantities and rates, and the complete tax breakdown — in under 10 seconds.

### 🏥 Invoice Health Score *(unique feature)*
Every scanned invoice is automatically scored out of 100 with a grade from A to F. No competitor offers this for free. The engine checks:

- GSTIN format validity — 15-character structure, valid state code (01–37)
- Mathematical accuracy — line items, subtotal, and total all cross-verified
- CGST = SGST equality for intrastate transactions
- IGST/CGST conflict detection for interstate invoices
- HSN code presence on all line items
- Invoice date validity — not in future, not older than 1 year
- Fraud signal detection — suspiciously round totals, identical item amounts, high-value single items

### 💰 ITC Calculator
Automatically calculates your Input Tax Credit entitlement for the current month based on all scanned purchase invoices. Shows CGST, SGST, and IGST breakdown per supplier with month-over-month percentage change.

### 📊 Supplier Spend Analyzer
Tracks spending per supplier over time with bar charts, pie charts, and trend lines. Answers "which suppliers am I spending the most with?" and "how has my tax liability changed month-on-month?"

### 📅 GST Compliance Deadline Tracker
Live countdown timers for all monthly GST filing deadlines — GSTR-1 (11th), GSTR-3B (20th), and GSTR-2B (14th).

### 🔐 JWT Authentication
Production-grade security with JWT tokens, bcrypt password hashing, rate-limited API endpoints, and CORS whitelisting. All API routes require a valid Bearer token.

### 📥 Excel Export + WhatsApp Share
One-click export of any invoice to a formatted `.xlsx` file. Share invoice summaries directly via WhatsApp — useful for sending to your CA.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (ES6+), Chart.js |
| **Backend** | Python 3.14, FastAPI, Uvicorn |
| **AI / Vision** | Groq API — Llama-4-Scout-17b-16e |
| **Authentication** | JWT (python-jose), bcrypt (passlib) |
| **Database** | Neon PostgreSQL (psycopg2) |
| **Image Processing** | Pillow |
| **Excel Export** | openpyxl |
| **Rate Limiting** | slowapi |

---

## Architecture

```
User uploads invoice image
         ↓
   Frontend — Authorization: Bearer <jwt>
         ↓
   FastAPI — rate limit 10 req/min, max 10MB
         ↓
   auth.py — JWT validation
         ↓
   parser.py — Groq AI (Llama-4-Scout Vision)
         ↓
   validator.py — 7-check health score engine
         ↓
   database.py — Neon PostgreSQL
         ↓
   Response — extracted data + score + id
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/login` | ❌ | Get JWT token |
| `POST` | `/api/register` | ❌ | Create new user |
| `POST` | `/scan` | ✅ | Upload invoice → AI extract + health score |
| `POST` | `/export` | ✅ | Invoice JSON → Excel download |
| `GET` | `/invoices` | ✅ | All past scanned invoices |
| `GET` | `/analytics` | ✅ | Supplier spend + monthly trends |
| `GET` | `/itc-summary` | ✅ | ITC calculator data |
| `GET` | `/` | ❌ | Health check |

Interactive docs at `http://localhost:8000/docs`

---

## Health Score Breakdown

| Check | Deduction | What It Validates |
|---|---|---|
| Seller GSTIN invalid | −15 pts | 15-char format + valid state code |
| Buyer GSTIN invalid | −15 pts | 15-char format + valid state code |
| Math errors | −20 pts | Items × rate = amount, subtotal + tax = total |
| Invoice date invalid | −10 pts | Not in future, not older than 1 year |
| HSN codes missing | −10 pts | All line items have HSN/SAC codes |
| Fraud signals | −5 pts each | Round totals, identical amounts, high-value singles |
| Required fields missing | −5 pts each | Name, GSTIN, invoice no, date, total |

**Grades:** A (90–100) · B (75–89) · C (60–74) · D (40–59) · F (0–39)

---

## Getting Started

### Prerequisites
- Python 3.10+
- Free [Groq API key](https://console.groq.com) — no credit card needed
- Free [Neon PostgreSQL](https://neon.tech) database

### 1. Clone
```bash
git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
cd gst_invoice_scanner
```

### 2. Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Create environment file
Create `backend/.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=your_neon_connection_string_here
```

### 4. Set up the database
Run this in your Neon SQL Editor:
```sql
CREATE TABLE invoices (
    id             SERIAL PRIMARY KEY,
    seller_name    VARCHAR(255),
    seller_gstin   VARCHAR(20),
    buyer_name     VARCHAR(255),
    buyer_gstin    VARCHAR(20),
    invoice_number VARCHAR(100),
    invoice_date   VARCHAR(50),
    cgst           DECIMAL(10,2),
    sgst           DECIMAL(10,2),
    igst           DECIMAL(10,2),
    subtotal       DECIMAL(10,2),
    total          DECIMAL(10,2),
    items          JSONB,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `users` table is created automatically on first startup.

### 5. Run the backend
```bash
cd backend
python -m uvicorn main:app --reload
```

### 6. Open the frontend
Open `frontend/login.html` in your browser.

**Default credentials:** `admin` / `admin123`

---

## Security

- **JWT** — all protected routes require a valid Bearer token, expiring after 8 hours
- **bcrypt** — passwords hashed before storage; `bcrypt==4.0.1` pinned for passlib compatibility
- **Rate limiting** — `/scan` throttled to 10 requests/minute per IP via slowapi
- **CORS** — only whitelisted frontend origins accepted
- **File validation** — uploads over 10MB rejected; only JPG and PNG accepted

---

## Project Structure

```
gst_invoice_scanner/
├── backend/
│   ├── main.py           → FastAPI app + all endpoints
│   ├── auth.py           → JWT + login/register routes
│   ├── database.py       → All PostgreSQL queries
│   ├── parser.py         → Groq AI invoice reader
│   ├── validator.py      → Health score engine
│   ├── requirements.txt
│   └── .env              → Secret keys (not committed)
├── frontend/
│   ├── login.html
│   ├── register.html
│   ├── index.html
│   ├── results.html
│   ├── history.html
│   ├── analytics.html
│   ├── css/style.css
│   └── js/
│       ├── auth.js
│       ├── upload.js
│       ├── results.js
│       ├── history.js
│       └── analytics.js
├── screenshots/
├── ARCHITECTURE.md
├── PIPELINE.md
└── generate_test_data.py
```

---

## Acknowledgements

[Groq](https://groq.com) · [Neon](https://neon.tech) · [FastAPI](https://fastapi.tiangolo.com) · [Chart.js](https://chartjs.org) · [openpyxl](https://openpyxl.readthedocs.io)

---

<div align="center">
Built with curiosity and a lot of terminal time.
</div>