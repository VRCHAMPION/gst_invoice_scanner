# GST Invoice Scanner

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/github/license/VRCHAMPION/gst_invoice_scanner?style=for-the-badge" />
  <img src="https://img.shields.io/github/stars/VRCHAMPION/gst_invoice_scanner?style=for-the-badge&color=yellow" />
  <img src="https://img.shields.io/github/issues/VRCHAMPION/gst_invoice_scanner?style=for-the-badge&color=red" />
  <img src="https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge" />
</p>

<p align="center"><i>Extract structured GST data from unstructured, varying invoice formats using Asynchronous OCR and Large Language Models.</i></p>

<p align="center">
  <img src="https://via.placeholder.com/900x450?text=GST+Scanner+Dashboard+UI" alt="GST Scanner Dashboard UI Placeholder" width="100%"/>
</p>

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture & Processing Flow](#architecture--processing-flow)
- [Project Structure](#project-structure)
- [Sample Output](#sample-output)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Configuration](#configuration)
- [Acknowledgments](#acknowledgments)
- [Contributing](#contributing)
- [License](#license)

---

## About

**GST Invoice Scanner** is a Python-based tool designed specifically to scan unpredictable, non-standard Indian GST invoices (in PDF, JPG, or PNG formats). It skips fragile, coordinate-based templates and instead leverages a robust two-step approach: grabbing raw text via `Tesseract OCR` and structuring it semantically using the `Groq LLaMa-3` API. 

This hybrid approach provides high extraction accuracy for unstructured fields like GSTIN, invoice numbers, tax breakdowns (CGST, SGST, IGST), and total amounts across varied templates.

---

## Features

- **Asynchronous Execution Engine:** Heavy OCR processing is pushed to background workers instantly, ensuring the API handles continuous traffic without freezing.
- **Two-Tier AI Extraction:** Replaces rigid templates with a hybrid pipeline of Optical Character Recognition and NLP Semantic Parsing.
- **Stateless Authentication:** Secured routes using JSON Web Tokens (JWT) and bcrypt password hashing.
- **API Hardening:** App-level rate limiting using SlowAPI middleware.
- **Zero-Storage Parsing:** Incoming PDFs are mapped directly to RAM bytes via PyMuPDF (`fitz`), avoiding slow and vulnerable hard-drive write operations.
- **Data Export:** Built-in capability to generate formatted Excel reports of scanned batches using `openpyxl`.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Application Language | Python 3.10+ |
| Backend API | FastAPI |
| Asynchronous Workers | FastAPI BackgroundTasks |
| Neural OCR Engine | Tesseract (pytesseract) |
| NLP Intelligence | Groq API (llama-3.1-8b-instant) |
| Non-destructive Vision | PyMuPDF (fitz) |
| Database & ORM | SQLite, SQLAlchemy |
| Frontend Interface | Vanilla JavaScript, HTML5, CSS3 Grid |
| Application Security | Passlib (Bcrypt), python-jose (JWT), SlowAPI |

---

## Architecture & Processing Flow

The system runs on an event-driven loop to avoid traditional processing bottlenecks:
1. **Upload:** Client POSTs document bytes to the FastAPI ingestion route.
2. **Dispatch:** The server assigns a unique Job ID, placing the file straight into a non-blocking background queue and returning the ID.
3. **Polling Retrieval:** The Vanilla JS frontend establishes a 2-second polling loop against the server verifying the Job ID's status.
4. **Cognitive Extraction:** The worker thread uses PyMuPDF and Tesseract to generate a raw text string, then prompts the LLaMa-3 model to parse JSON keys precisely.
5. **Persistence:** Extracted data is committed safely via Python ORM, and the frontend renders the resulting payload.

---

## Project Structure

```text
gst_invoice_scanner/
├── backend/            # FastAPI layer, Database logic, ORM models, and Auth
│   ├── main.py
│   ├── parser.py       # Core OCR + LLaMa-3 extraction logic
│   └── database.py
├── frontend/           # Vanilla JS, HTML, and CSS application UI
├── test_invoices/      # Generated syntactically valid test PDFs and tracking images
├── ARCHITECTURE.md     # Detailed async architectural design breakdown
├── PIPELINE.md         # Deep dive into the Tesseract to LLM conversion pipeline
└── README.md
```

---

## Sample Output

The backend structures chaotic OCR text into a rigidly defined JSON response similar to below:

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
  "total": 5900.00,
  "items": [
    {
      "description": "Software Implementation Services",
      "quantity": 1,
      "rate": 5000.00,
      "amount": 5000.00
    }
  ]
}
```

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Tesseract-OCR:** The OS-level binary must be installed on your machine.
  - Windows: Download the executable installer and map to your environment variables.
  - Linux: `sudo apt-get install tesseract-ocr`

### Installation
1. Clone the repository and initialize a virtual environment:
   ```bash
   git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
   cd gst_invoice_scanner
   python -m venv .venv
   source .venv/bin/activate  # (On Windows: .venv\Scripts\activate)
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytesseract PyMuPDF Pillow
   ```

---

## Configuration

A `.env` file is required in the `backend/` directory for secrets management. Add the following keys:
```env
# Acquire an API Key from console.groq.com
GROQ_API_KEY=your_production_key_here

# JWT Signing Secret (Create via openssl rand -hex 32)
SECRET_KEY=your_secure_random_string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ORM Target (Change to PostgreSQL for cluster deployments later)
DATABASE_URL=sqlite:///./gst_scanner.db
```

---

## Usage

1. Start the FastAPI backend server:
   ```bash
   cd backend
   python run.py
   ```
   > The API Documentation swagger instance is now live at `http://127.0.0.1:8000/docs`.

2. To access the user interface, launch the frontend via Live Server (or a local Python HTTP instance):
   ```bash
   cd frontend
   python -m http.server 5500
   ```
   > Now open `http://localhost:5500/login.html` to begin automated scanning.

---

## Acknowledgments
Powered by [Groq](https://groq.com/) for rapid LLM inference, [Tesseract](https://github.com/tesseract-ocr/tesseract) for local character extraction, and [PyMuPDF](https://pymupdf.readthedocs.io/) for lightweight in-RAM PDF rasterization.

---

## Contributing
Contributions are what make the open source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License
Distributed under the MIT License. See `LICENSE` for more information.
