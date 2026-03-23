# GST Invoice Scanner & Analyzer 🚀

![Banner](https://via.placeholder.com/1200x400?text=GST+Invoice+Scanner+MVP)

## Project Overview

The **GST Invoice Scanner** is an enterprise-grade web application tailored to automate the painstakingly manual and error-prone process of GST invoice data entry. In modern financial workflows, processing poorly formatted, blurry, and non-standardized invoices (PDFs and Images) creates a massive bottleneck. This application leverages a hybrid approach combining **Neural Optical Character Recognition (OCR)** via Tesseract and **Large Language Models (LLaMa-3)** to intelligently extract, standardize, and store structured financial data.

Evolving from a highly competitive hackathon concept, this project has been meticulously engineered into a **highly scalable, robust Minimum Viable Product (MVP)**. It handles real-world invoices under heavy load without blocking core server threads, offering an exceptionally resilient architecture.

## Key Features & Capabilities

### 1. Real-time Asynchronous Processing
Traditional synchronous applications freeze the frontend while waiting for lengthy OCR tasks to complete. We solve this by implementing an event-driven, asynchronous background worker system. Uploads are instantly assigned a `job_id` and pushed to a background queue. The server responds immediately, allowing the UI to remain highly responsive and informative while the heavy lifting happens behind the scenes.

### 2. Two-Tier AI Extraction Pipeline
We use a "Dumb Reader + Smart Organizer" paradigm:
- **Structural OCR (`pytesseract`):** Parses the physical image to extract raw, unstructured text strings, completely ignoring coordinate-based templates.
- **Cognitive NLP (Groq `llama-3.1`):** Acts as the brain, processing the chaotic OCR output. Using stringent prompt engineering, the LLM contextualizes the text (such as identifying various GSTIN formats or distinguishing Tax from Total) and returns exclusively formatted JSON data.

### 3. SaaS-Level UI/UX (Framework-Free)
To ensure lightning-fast load times and infinite customizability, the frontend is built entirely with Vanilla JavaScript and pure CSS. By utilizing modern CSS custom properties (CSS variables), CSS Grid/Flexbox, and subtle micro-animations, we achieve a visual fidelity and user experience that matches enterprise React or Angular applications, but with zero bundle bloat.

### 4. Robust Security & Authentication
- **Stateless JWT Authentication:** Secure, scalable JSON Web Tokens (JWT) handle session persistence.
- **Password Cryptography:** User credentials are salted and hashed using `bcrypt` preventing rainbow table attacks.
- **API Hardening:** Protected against abuse via SlowAPI rate-limiting and strictly defined CORS policies.

---

## Component Deep Dive

### 1. The Async Controller (`backend/main.py`)
Serving as the heart of the backend, the FastAPI server manages all incoming traffic. It orchestrates routing, enforces JWT-based security middleware, limits API abuse using SlowAPI, and establishes vital Database connections. 
**The Scalability Secret:** When a `.pdf` or `.png` is POSTed to `/scan`, the file is completely ingested into RAM (`await file.read()`). Instead of halting the event loop to read it, `main.py` dispatches a `fastapi.BackgroundTasks` job and instantly returns a `job_id`. This non-blocking I/O approach ensures the API can handle thousands of concurrent requests.

### 2. The AI Brain (`backend/parser.py`)
This vital module encapsulates the OCR and LLM pipeline.
**Reliability & Nuance:** 
- Instead of relying on OS-level PDF tools, we utilize `PyMuPDF` (`fitz`) to rapidly convert PDFs into PNG images natively in-memory.
- These in-memory PNG bytes are streamed to `pytesseract` to extract raw alphanumeric characters.
- To eliminate LLaMa-3 hallucinations, we encapsulate the messy text in a rigid prompt, instructing Groq to output unformatted JSON. A custom parsing regex then scrubs the output of any residual conversational text before hitting the database.

### 3. The Polling Engine (`frontend/js/upload.js`)
The drag-and-drop interface is powered by an intelligent polling loop.
**Real-world UX:** Rather than displaying an arbitrary progress bar, the frontend receives the backend `job_id` and utilizes `setInterval` to actively poll `/scan/status/{job_id}` every 2 seconds. The UI updates its state (`processing`, `completed`, or `failed`) in absolute real-time, redirecting to the results dashboard the exact millisecond the backend confirms the job is finished.

---

## Setup & Running Locally

### 1. Prerequisites
- **Python 3.10+**: Ensure `pip` and `venv` are available.
- **Tesseract-OCR:** Required for text extraction.
  - Windows: Download the latest executable from Mannheim University and add it to your System PATH variables.
  - Linux: `sudo apt-get update && sudo apt-get install tesseract-ocr libtesseract-dev`
  - macOS: `brew install tesseract`

### 2. Installation & Dependency Management
```bash
# Clone the repository
git clone https://github.com/yourusername/gst_invoice_scanner.git
cd gst_invoice_scanner

# Initialize a Virtual Environment to prevent dependency conflicts
python -m venv .venv

# On Windows use: 
.venv\Scripts\activate
# On Linux/macOS use: 
# source .venv/bin/activate  

# Install the necessary Python packages
pip install -r requirements.txt
# Ensure vision dependencies are fully installed
pip install pytesseract PyMuPDF Pillow
```

### 3. Environment Variables (.env)
Create a `.env` file in the `backend/` directory to manage secrets securely:
```env
# Get this free API key from console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# Used for signing JWTs. Generate a strong key via `openssl rand -hex 32`
SECRET_KEY=your_highly_secure_random_string

# JWT configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database URL (Defaulting to local SQLite, easy migration to PostgreSQL)
DATABASE_URL=sqlite:///./gst_scanner.db
```

### 4. Running the Application
```bash
# Navigate to backend
cd backend

# Run the Uvicorn server via the custom run script wrapper
python run.py
# The API and Interactive Swagger documentation will start on http://127.0.0.1:8000/docs
```

### 5. Accessing the UI
Since the frontend uses relative API paths and vanilla JS, simply open `frontend/login.html` directly in your web browser (via double-click or `file:///`), or for a better development experience, serve the `frontend/` directory using VSCode's Live Server extension.
