# Complete Project Explanation 📖

This document provides a deep, component-by-component explanation of the **GST Invoice Scanner**, detailing how every moving part connects to create the final production-grade MVP.

---

## 1. The Core Application Flow

Before diving into individual files, it is crucial to understand the lifecycle of an invoice moving through this system:
1. **Upload:** A user drags & drops a PDF or JPEG into the Dashboard UI.
2. **Dispatch:** The frontend sends the raw file bytes to the FastAPI backend.
3. **Queueing:** The backend immediately assigns the file a unique `job_id`, tosses it to a background worker, and returns the `job_id` to the user so the browser isn't frozen waiting for processing.
4. **Extraction (OCR):** The background worker physically "reads" the document pixels using Tesseract and converts them into chaotic, raw text strings.
5. **Structuring (LLM):** The chaotic text is handed to Groq's LLaMa-3 model, which uses natural language understanding to pluck out specific fields (GSTIN, Totals, Taxes) and formats them into a strict JSON payload.
6. **Storage:** The JSON payload is saved to the SQL database.
7. **Retrieval:** The frontend, which has been polling the server every 2 seconds for a status update, receives the "Completed" signal, fetches the final JSON from the server, and redirects the user to the Results dashboard.

---

## 2. The Frontend Layer 🎨

The frontend is built with pure Vanilla JavaScript, HTML5, and standard CSS. This ensures lightning-fast load times with absolutely zero complex framework overhead (like React or Angular).

- **`frontend/upload.html` & `js/upload.js`:** The entry point for processing. It contains the drag-and-drop zone. Under the hood, `upload.js` intercepts the file, posts it to the `/scan` API, and begins a `setInterval` loop to constantly ask the backend, *"Is job 123 done yet?"*
- **`frontend/results.html`:** The display interface that renders the final, parsed JSON data. It computes warnings (e.g., if mathematical totals mismatch) and allows exporting data to Excel via the backend API.
- **`frontend/history.html` & `analytics.html`:** These act as the application's memory. They fetch data via authenticated `GET` requests from the database to populate metric tables and historical ledgers.

---

## 3. The Backend Application ⚙️

The core server is orchestrated by **FastAPI (Python)**, chosen for its exceptional asynchronous performance and automated OpenAPI swagger documentation.

- **`backend/main.py`:** The traffic controller. It defines the API routes (`/scan`, `/login`, `/history`). Crucially, it handles the **FastAPI BackgroundTasks**, ensuring that heavy CPU operations (OCR parsing) are shunted to secondary threads so the main server can keep responding to other users rapidly.
- **`backend/auth.py`:** The security module. It uses `bcrypt` via the `passlib` library to salt and hash user passwords irreversibly. It issues **JSON Web Tokens (JWTs)** upon successful login, which the frontend must attach to every subsequent API request as a Bearer Token. Fast, stateless, and scalable.
- **`backend/database.py`:** The persistence layer. We use **SQLAlchemy**, a powerful Object Relational Mapper (ORM), to interface with a local SQLite database file (`gst_scanner.db`). Because we use SQLAlchemy, upgrading to an enterprise PostgreSQL database requires changing only one line of code in `.env`.

---

## 4. The Artificial Intelligence Engine 🧠

This is the most critical and complex part of the system, housed entirely within `backend/parser.py`.

### A. Rendering Documents to Images (PyMuPDF)
Tesseract-OCR cannot directly read PDFs; it requires images. Therefore, if a user uploads a `.pdf`, `PyMuPDF` (`fitz`) intercepts it. It essentially takes a virtual screenshot of the first two pages of the PDF and converts them into `.png` image bytes directly in RAM (avoiding slow hard-drive read/writes).

### B. Optical Character Recognition (Tesseract)
The image bytes are fed into Python's `pytesseract` library. This is a local machine-learning engine that looks at pixels and attempts to identify letters and numbers. It produces a massive, unstructured string of text.

### C. Large Language Model Structuring (Groq / LLaMa)
If we stopped at Tesseract, the user would just get a wall of confusing text. To extract structured data (like `{"total": 500}`), we send the raw OCR text to the **Groq API** running `llama-3.1-8b-instant`. 

We utilize **Prompt Engineering** to place incredibly strict bounding rules on the model:
> *"You are a strict JSON data extractor... Return ONLY a valid JSON object with EXACTLY these keys."*

The model identifies context (e.g., it knows that the string "GSTIN: 27A BC DE1234F1Z5" corresponds to the `seller_gstin` key) and structures the data flawlessly.

### D. Sanity Cleaning Regex
Because Language Models occasionally hallucinate and wrap their answers in Markdown formatting (e.g., ` ```json { ... } ``` `), `parser.py` implements a strict string-slicing logic that searches exclusively for the first `{` and the last `}`, guaranteeing the application never crashes attempting to parse a corrupted JSON string.

---

## Conclusion
By combining the raw processing speed of FastAPI background tasks, the zero-cost text extraction of native Tesseract, and the cognitive reasoning power of LLaMa-3, the GST Invoice Scanner achieves production-level capabilities in an extremely lightweight codebase.
