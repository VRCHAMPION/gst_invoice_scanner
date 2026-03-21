# GST Invoice Scanner: End-to-End Pipeline

This document outlines the high-precision data pipeline of the GST Invoice Scanner, from the initial upload to the final business intelligence analytics.

## 1. Input Layer (Frontend)
- **User Interface**: A "Dark Industrial Brutalist" dashboard built with HTML5/CSS3.
- **Payload Capture**: `index.html` leverages a custom drag-and-drop zone.
- **Validation**: `upload.js` performs client-side MIME-type checks (JPG/PNG) and size limits (10MB).
- **Asynchronous Hand-off**: The file is sent via `multipart/form-data` to the FastAPI backend.

## 2. Extraction Engine (LLM-Vision)
- **API Arrival**: `main.py` receives the byte stream at the `POST /scan` endpoint.
- **Conversion**: PIL (Pillow) processes the bytes into a standard RGB format.
- **Structured Extraction**: The image is sent to the **Groq (meta-llama/llama-3.2-90b-vision-preview)** model.
- **Prompt Engineering**: The model extracts 15+ fields including `seller_gstin`, `subtotal`, `cgst`, `sgst`, and `igst` into a strict JSON schema.

## 3. Persistent Storage (PostgreSQL)
- **Database**: Hosted on **Neon PostgreSQL**.
- **Normalization**: Data is mapped to the `invoices` table using `psycopg2`.
- **JSONB Usage**: Line items are stored as JSONB for flexible retrieval while keeping financial sums in flat columns for indexing.
- **Automatic Metadata**: Each record is timestamped for historical tracking.

## 4. Intelligence & Validation Layer
- **Health Scoring**: `validator.py` executes a series of 10+ mathematical and legal checks:
  - **GSTIN Regex**: Validates checksums and state codes.
  - **Math Integrity**: Verifies if `Items Sum == Subtotal` and `Subtotal + Taxes == Total`.
  - **Tax Consistency**: Ensures `CGST == SGST` for intrastate transactions.
  - **Fraud Detection**: Flags suspicious patterns like "Perfect Round Totals" or "Same-amount Multi-items".
- **Dynamic Scoring**: A final health score (0-100) and grade (A-F) are generated.

## 5. Analytics & Business Intelligence
- **Aggregation**: `database.py` performs complex queries for `GET /analytics`:
  - **Spend Concentration**: Identifies top suppliers by volume and value.
  - **Monthly Trends**: Aggregates tax and spend data over time.
- **ITC Calculator**: `GET /itc-summary` calculates Input Tax Credit entitlement based on scanned purchase invoices.
- **Compliance Tracking**: Real-time GSTR deadline countdowns integrated into the dashboard.

## 6. Visualization (Output)
- **Results Hub**: `results.html` renders the health dial and tax breakdown.
- **Transactional Archive**: `history.html` allows searching and sorting through the entire database.
- **Data Export**: Users can generate **Excel** files or share results directly via **WhatsApp**.
