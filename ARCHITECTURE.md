# GST Invoice Scanner: System Architecture

The following diagram illustrates the flow of data from the initial invoice upload to the final analytics dashboard.

```mermaid
graph TD
    subgraph "Frontend Layer (Client-Side)"
        UI["User Interface (HTML/CSS)"]
        JS["Dashboard Logic (upload.js)"]
        UI -->|Upload Invoice| JS
    end

    subgraph "Logic Layer (FastAPI)"
        API["API Gateway (main.py)"]
        JS -->|POST /scan (File)| API
        
        Parser["Groq Vision Parser (parser.py)"]
        API -->|Image Bytes| Parser
        Parser -->|Structured JSON| API
        
        Validator["GST Validator (validator.py)"]
        API -->|Verify Logic| Validator
        Validator -->|Health Score & Grade| API
    end

    subgraph "Data & Analytics"
        DB[("Neon PostgreSQL")]
        API -->|save_invoice| DB
        
        Analytics["Analytics Engine (database.py)"]
        DB -->|Query Results| Analytics
        Analytics -->|JSON Summaries| API
    end

    subgraph "Output & Export"
        Results["Results UI (results.html)"]
        History["Archive (history.html)"]
        BI["Analytics Hub (analytics.html)"]
        
        API -->|Display| Results
        API -->|Fetch| History
        API -->|Aggregated Data| BI
        
        Excel["Excel Export"]
        WA["WhatsApp Share"]
        Results --> Excel
        Results --> WA
    end

    style UI fill:#00ff88,stroke:#000,stroke-width:2px,color:#000
    style API fill:#080808,stroke:#00ff88,stroke-width:2px,color:#fff
    style DB fill:#1c1c24,stroke:#00c3ff,stroke-width:2px,color:#fff
    style Parser fill:#ff6b00,stroke:#000,stroke-width:1px,color:#fff
```
