# GST Invoice Scanner & Analyzer 🚀

![Banner](https://via.placeholder.com/1200x400?text=GST+Invoice+Scanner+MVP)

## Project Overview
The **GST Invoice Scanner** is an enterprise-grade web application designed to automate the painful process of manual GST invoice data entry. It utilizes Neural OCR (Tesseract) and Large Language Models (LLaMa-3) to extract structured financial data from messy, unstructured invoices (PDFs and Images). 

This project evolved from a standard hackathon concept into a **highly scalable, robust Minimum Viable Product (MVP)** capable of parsing real-world invoices without blocking server threads.

## Key Features
- **Real-time Async Processing:** Uploads are pushed to a background worker instantly, preventing the server from hanging while the AI "reads" the document.
- **Two-Tier AI Extraction:** We use structural OCR (`pytesseract`) to grab raw text, and Groq's high-speed `llama-3.1` model to clean and parse that text into a strict JSON format.
- **SaaS-Level UI/UX:** Built entirely with Vanilla JS and CSS, achieving the visual fidelity of a high-end React application using custom properties, subtle micro-animations, and a responsive grid dashboard.
- **Secure Authentication:** JWT-based stateless authentication with `bcrypt` password hashing.

---

## What Does Every Component Do?

### 1. `backend/main.py` (The Async Controller)
This is the FastAPI server. It handles routing, JWT authentication, rate-limiting (SlowAPI), and Database connections. 
**How we achieved scalability:** When a user uploads an invoice to `/scan`, this file does *not* wait for the OCR to finish. Instead, `main.py` tosses the file into a `fastapi.BackgroundTasks` queue and immediately gives the user a `job_id`. 

### 2. `backend/parser.py` (The AI Brain)
This file holds the OCR pipeline. 
**How we achieved reliability:** We use `PyMuPDF` (fitz) to convert PDFs into PNG images natively (avoiding complex Poppler installations on Windows). We then pass those images to `pytesseract` to extract raw text characters. Finally, we inject that raw, messy text into a strictly formatted LLM prompt, forcing Groq to return clean, standardized JSON values containing the GSTIN, Total, and Tax amounts.

### 3. `frontend/js/upload.js` (The Polling Engine)
This handles the drag-and-drop interface. 
**How we achieved real-world UX:** Instead of a fake `setTimeout` progress bar, the frontend receives the `job_id` from the backend and begins *polling* `/scan/status/{job_id}` every 2 seconds. The UI updates dynamically based on the exact state of the background thread (`processing`, `failed`, or `completed`), resulting in an honest, reliable user journey.

---

## Setup & Running Locally

### 1. Prerequisites
- **Python 3.10+**
- **Tesseract-OCR:** Must be installed on your operating system.
  - Windows: Download the executable and add to System PATH.
  - Linux: `sudo apt-get install tesseract-ocr`

### 2. Installation
```bash
# Install Python dependencies
pip install -r requirements.txt
pip install pytesseract PyMuPDF Pillow
```

### 3. Environment Variables
Create a `.env` in the `backend/` directory:
```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=generate_a_secure_jwt_secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 4. Running the Server
```bash
cd backend
python run.py
# Server will start on http://127.0.0.1:8000
```

### 5. Accessing the UI
Simply open `frontend/login.html` in your web browser, or serve it via Live Server!
