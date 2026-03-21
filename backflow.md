Workflow for backend only 

User uploads invoice image
        ↓
main.py receives the request (/scan)
        ↓
parser.py sends image to Groq AI
        ↓
Groq reads invoice → returns JSON
        ↓
database.py saves JSON to Neon DB
        ↓
main.py returns data to frontend
        ↓
User clicks Export
        ↓
main.py generates Excel file (/export)
        ↓
User visits History page
        ↓
database.py fetches all past scans (/invoices)
```

## Files

| File | Purpose |
|---|---|
| `.env` | Stores all secret API keys |
| `database.py` | Connects to Neon DB, saves and fetches invoices |
| `parser.py` | Sends invoice image to Groq AI, returns extracted JSON |
| `main.py` | FastAPI server, exposes all API endpoints |
| `requirements.txt` | Lists all Python dependencies |

## API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/scan` | Upload invoice → AI extracts data → saves to DB |
| POST | `/export` | Takes invoice JSON → returns Excel file download |
| GET | `/invoices` | Returns all past scanned invoices |
| GET | `/` | Health check |

## Tech Stack

| Layer | Tool |
|---|---|
| Framework | FastAPI |
| AI | Groq (llama-4-scout-17b) |
| Database | Neon PostgreSQL |
| Excel Export | openpyxl |
| Image Processing | Pillow |