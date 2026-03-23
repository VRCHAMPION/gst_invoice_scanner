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

* Works with non-standard invoice formats
* Asynchronous processing to avoid blocking requests
* OCR-based text extraction using Tesseract
* Semantic parsing using LLaMA-3 via Groq API
* JWT-based authentication
* Rate limiting for API protection
* In-memory file handling (no disk writes)
* Excel export for processed data

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

* Backend: FastAPI
* OCR: Tesseract (pytesseract)
* AI Processing: LLaMA-3 (Groq API)
* PDF Handling: PyMuPDF
* Database: SQLite with SQLAlchemy
* Authentication: JWT (python-jose), bcrypt
* Frontend: HTML, CSS, JavaScript

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
│   ├── main.py
│   ├── parser.py
│   └── database.py
├── frontend/
├── test_invoices/
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
pip install -r requirements.txt
pip install pytesseract PyMuPDF Pillow
```

---

## Configuration

Create a `.env` file inside the `backend/` directory:

```
GROQ_API_KEY=your_api_key
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./gst_scanner.db
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
