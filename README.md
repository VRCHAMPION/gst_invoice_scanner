# 🚀 GST Invoice Scanner

### AI-Powered GST Data Extraction from Any Invoice Format

> Turn messy, unstructured invoices into clean, structured GST data — instantly.

---

## 🔥 Overview

GST Invoice Scanner is an **AI-powered document intelligence platform** that extracts structured GST data from **non-standard, real-world invoices** (PDF, JPG, PNG).

Instead of relying on fragile templates, it uses a **hybrid AI pipeline (OCR + LLM)** to understand invoices the way humans do — making it robust across different formats and layouts.

---

## ⚡ Why This Matters

Businesses deal with hundreds of invoice formats. Traditional systems fail because they depend on fixed layouts.

This system solves that by:

* ✅ Understanding *any* invoice structure
* ✅ Extracting GST data automatically
* ✅ Eliminating manual data entry

---

## 🧠 How It Works

1. **Upload Invoice**
   User uploads PDF/image via UI

2. **Async Processing**
   File is sent to a background worker (non-blocking)

3. **OCR Extraction**
   Tesseract converts image → raw text

4. **AI Structuring**
   LLaMA-3 parses raw text → structured JSON

5. **Result Delivery**
   Clean GST data is returned and displayed

---

## 🧩 Example Output

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

## 🚀 Key Features

### ⚡ Intelligent AI Extraction

* Works on **unstructured invoices**
* No templates required
* Handles real-world variability

### 🔄 Asynchronous Processing

* Non-blocking architecture
* Handles multiple uploads efficiently

### 🔐 Secure & Scalable Backend

* JWT-based authentication
* Rate limiting (SlowAPI)
* ORM-backed database

### 💾 Zero-Disk Processing

* Files processed directly in memory
* Faster + more secure

### 📊 Data Export

* Export structured GST data to Excel

---

## 🏗️ Architecture

* **Frontend** → Vanilla JS (Upload + Dashboard)
* **Backend** → FastAPI (API + Workers)
* **OCR Layer** → Tesseract
* **AI Layer** → LLaMA-3 (via Groq API)
* **Database** → SQLite + SQLAlchemy

---

## 📁 Project Structure

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

## ⚙️ Getting Started

### 1. Clone Repository

```
git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
cd gst_invoice_scanner
```

### 2. Setup Environment

```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
pip install pytesseract PyMuPDF Pillow
```

### 4. Configure Environment Variables

Create `.env` inside `/backend`:

```
GROQ_API_KEY=your_api_key
SECRET_KEY=your_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./gst_scanner.db
```

---

## ▶️ Run the Project

### Start Backend

```
cd backend
python run.py
```

API Docs:
👉 http://127.0.0.1:8000/docs

### Start Frontend

```
cd frontend
python -m http.server 5500
```

👉 http://localhost:5500/login.html

---

## 📊 Performance (Expected)

* ⚡ ~2–3 seconds per invoice
* 🎯 High accuracy on unstructured formats
* 📄 Supports PDF, JPG, PNG

---

## 💡 Use Cases

* GST filing automation
* Accounting workflows
* Invoice digitization
* SME financial operations

---

## 🚀 Future Improvements

* 🔍 Fraud / duplicate invoice detection
* 📊 Monthly GST analytics dashboard
* 📱 WhatsApp export integration
* ☁️ Cloud deployment

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a branch
3. Submit a PR

---

## 📜 License

MIT License

---

## 🙌 Acknowledgments

* Groq (LLaMA-3 inference)
* Tesseract OCR
* PyMuPDF

---

## ⭐ Final Note

This project demonstrates how **AI + async systems** can transform messy real-world documents into structured, actionable data.

If you found this useful, consider ⭐ starring the repo!
