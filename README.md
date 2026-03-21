# GST Invoice Scanner

A professional, high-precision financial data terminal for scanning, validating, and analyzing GST purchase invoices. Built with a Dark Industrial Brutalist aesthetic, this tool leverages LLM-based vision models for data extraction and provides deep tax intelligence.

## Pipeline Architecture

The system follows a 6-stage data pipeline:
1. **Frontend**: Drag-and-drop interface for image capture.
2. **Extraction**: Groq (Llama-3-Vision) structured JSON parsing.
3. **Storage**: Neon PostgreSQL persistence.
4. **Validation**: 10+ mathematical and legal GST compliance checks.
5. **Analytics**: Real-time ITC calculation and spend trends.
6. **Export**: Data export to Excel and WhatsApp sharing.

## Key Features

- **AI-Powered OCR**: Extraction of GSTINs, invoice numbers, dates, and line items with high accuracy.
- **Intelligent Health Scoring**: Automated validation of tax logic (CGST/SGST/IGST) and mathematical consistency.
- **Transaction Archive**: Searchable and sortable database of all scanned invoices.
- **Business Intelligence**: Visual dashboards for monthly spend and supplier concentration.
- **ITC entitlement Tracker**: Accurate calculation of Input Tax Credit based on purchase records.
- **Compliance Calendar**: Countdown timers for GSTR-1, GSTR-3B, and GSTR-2B deadlines.

## Technology Stack

- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6+), Chart.js
- **Backend**: FastAPI (Python), Uvicorn
- **AI/ML**: Groq Cloud (Llama-3-Vision)
- **Database**: PostgreSQL (Neon)
- **Data Processing**: Pillow, Pydantic, Psycopg2

## Setup and Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/VRCHAMPION/gst_invoice_scanner.git
   cd gst_invoice_scanner
   ```

2. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the `backend/` directory with the following:
   ```env
   GROQ_API_KEY=your_key_here
   DATABASE_URL=your_postgresql_url_here
   ```

4. **Run the Backend**:
   ```bash
   cd backend
   python -m uvicorn main:app --reload
   ```

5. **Access the Frontend**:
   Open `frontend/login.html` in your browser.
   - **Default Login**: admin / admin123

## Dashboard Gallery

### Secure Access Terminal
![Login Page](screenshots/dashboard_login.png)

### Invoice Processing Hub
![Upload Dashboard](screenshots/dashboard_upload.png)

### Data Extraction and Health Score
![Scan Results](screenshots/dashboard_results.png)

### Transaction Archive
![History Page](screenshots/dashboard_history.png)

### Business Intelligence Dashboard
![Analytics Page](screenshots/dashboard_analytics.png)
