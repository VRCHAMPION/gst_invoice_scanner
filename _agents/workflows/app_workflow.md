---
description: Comprehensive workflow for GST Invoice Scanner Enterprise SaaS
---

# GST Invoice Scanner: Enterprise Workflow

Follow these steps to initialize, run, and scale the application.

## 1. Environment Initialization
Ensure your `.env` file in `backend/` is configured:
- `DATABASE_URL`: Connection string for Neon PostgreSQL.
- `JWT_SECRET`: A secure string for authentication.
- `GROQ_API_KEY`: Required for LLM-based data extraction.

// turbo
## 2. Startup Protocol
1. **Database Migration**: Ensure the schema is active.
   ```powershell
   # Run the schema script if needed (manual via Neon console or psql)
   ```
2. **Launch Backend**:
   ```powershell
   cd backend
   python run.py
   ```
3. **Launch Frontend**:
   ```powershell
   cd frontend
   python -m http.server 5500
   ```

## 3. The Enterprise Lifecycle
### Phase A: Business Onboarding (Owner)
1. Navigate to `register.html`.
2. Select **"START A WORKSPACE"**.
3. Complete registration and sign-in.
4. On the **Onboarding Page**, enter your **Company Name** and **GSTIN**.
   - *Note: This Name is the unique key your employees will use to join.*

### Phase B: Team Expansion (Employee)
1. Navigate to `register.html`.
2. Select **"JOIN A WORKSPACE"**.
3. On the **Onboarding Page**, enter the **Exact Company Name** of your organization.
4. Your account is now linked to the corporate data silo.

### Phase C: Operational Flow
1. **Upload**: Go to `upload.html` and drop an invoice.
2. **Processing**:
   - The system uses **Neural OCR** (Tesseract) if available.
   - If Tesseract is missing, it **automatically falls back to Mock Data** for demo stability.
3. **Review**: Check `results.html` for health scores and extracted fields.
4. **Govern**: Owners visit `analytics.html` to monitor team spend and manage active seats.

## 4. Technical Architecture
- **Identity**: UUID v4 for all primary keys.
- **Security**: JWT-based RBAC (Owner vs. Employee).
- **Isolation**: Row-Level isolation via `company_id` filter on every API response.
