# System Architecture (The Async MVP) 🏗️

This document outlines the high-level architecture of the GST Invoice Scanner following the asynchronous production upgrade.

## The Bottleneck Problem We Solved
Originally, the application utilized a **Synchronous Blocking Architecture**. When User A uploaded a 5MB PDF, FastAPI would freeze the main event loop while it waited for the LLM to read the document. If User B tried to log in at the exact same time, User B's request would hang completely until User A's invoice was finished. This is unacceptable for a production environment.

## The New Asynchronous Blueprint

```mermaid
sequenceDiagram
    participant User as Frontend (upload.js)
    participant API as FastAPI (main.py)
    participant Worker as BackgroundTask
    participant OCR as Tesseract Engine
    participant LLM as Groq LLM
    participant DB as Database (SQLite/PG)

    User->>API: POST /api/scan (File)
    API->>Worker: Dispatch Background Task
    API-->>User: Return {"job_id": "123", "status": "processing"}
    
    loop Every 2 Seconds
        User->>API: GET /api/scan/status/123
        API-->>User: {"status": "processing"}
    end

    Note over Worker: OCR & LLM processing happens here quietly

    Worker->>OCR: Extract raw text from Image/PDF
    OCR-->>Worker: Return messy text chunk
    
    Worker->>LLM: Prompt + Messy Text
    LLM-->>Worker: Clean structured JSON
    
    Worker->>DB: Save to Database
    DB-->>Worker: Success ID

    Note over Worker: Job Status updated to 'Completed' in memory

    User->>API: GET /api/scan/status/123
    API-->>User: {"status": "completed", "data": {...}}
    User->>User: Redirect to results.html!
```

## Explanation of Key Architectural Choices

### 1. In-Memory Job Tracking (Hackathon Speed)
For tracking the background tasks, we currently use a Python dictionary `scan_jobs = {}` living inside the FastAPI memory. 
**Why?** It requires zero external infrastructure (like Dockerizing Redis). It is blazingly fast and perfect for a hackathon. 
**Tradeoff:** If the FastAPI server crashes or restarts, all currently processing jobs are permanently lost. For enterprise production, `scan_jobs` must be replaced by **Celery & Redis**.

### 2. File Handling
Files are parsed into RAM (`await file.read()`) and passed directly as bytes into the background thread. We do not save physical PDFs temporarily to the hard drive. 
**Why?** It drastically reduces Disk I/O bottlenecks and eliminates the need to write cleanup scripts for orphaned files in a `/tmp/` directory.

### 3. Database Layer Independence
The system is built on **SQLAlchemy ORM**. Currently utilizing SQLite, the application is strictly designed to migrate to **PostgreSQL** (e.g. Supabase or Neon DB) by changing precisely one single string in the `.env` file (`DATABASE_URL`). The object mapping remains unchanged, allowing for instant scalability when SQLite's write-locks become a bottleneck.
