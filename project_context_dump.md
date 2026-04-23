# GST Invoice Scanner — Full Project Context Dump

> Generated: 2026-04-23. Share this document with any AI assistant to provide complete project context.

---

## 1. Project Architecture & Directory Structure

```
gst_invoice_scanner/
├── backend/
│   ├── .env                        # Local secrets (git-ignored)
│   ├── .env.example                # Template for secrets
│   ├── auth.py                     # Supabase JWT verification + get_current_user dependency
│   ├── database.py                 # SQLAlchemy engine + session + init_db()
│   ├── main.py                     # FastAPI app, CORS, rate limiting, router registration
│   ├── models.py                   # SQLAlchemy ORM models (User, Company, Invoice, JoinRequest, Vendor)
│   ├── parser.py                   # Gemini/Groq OCR parsing logic
│   ├── requirements.txt
│   ├── schemas.py                  # Pydantic request/response schemas
│   ├── validator.py                # Invoice health score calculator
│   ├── routers/
│   │   ├── auth.py                 # GET /api/me, POST /api/logout
│   │   ├── companies.py            # Workspace CRUD + join request flow
│   │   ├── invoices.py             # Upload, scan, approve, reject, export
│   │   ├── analytics.py            # GET /api/analytics, /api/itc-summary
│   │   └── vendors.py              # Vendor list + detail
│   └── services/
│       └── invoice_service.py      # Background processing, webhook trigger
│
├── frontend/
│   ├── index.html                  # Public landing page
│   ├── login.html                  # Email/password + Google OAuth login
│   ├── register.html               # Registration with role selection (owner/employee)
│   ├── auth-callback.html          # OAuth callback handler & post-login redirect logic
│   ├── onboarding.html             # Create workspace OR join workspace form
│   ├── upload.html                 # Main dashboard: upload & scan invoices
│   ├── results.html                # Invoice detail + approve/reject/edit
│   ├── history.html                # Invoice list with filters & search
│   ├── analytics.html              # Charts & ITC summary
│   ├── vendors.html                # Vendor directory
│   └── js/
│       ├── env.js                  # LOCAL ONLY, git-ignored. Sets window.ENV_SUPABASE_ANON_KEY
│       ├── config.js               # CONFIG object: API_BASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY
│       │                           # Also defines: window.apiFetch, window.getToken, window.setToken,
│       │                           # window.getApiUrl, window._handleSessionExpired
│       ├── auth.js                 # Supabase client init, checkAuth(), login(), register(),
│       │                           # loginWithGoogle(), logout(), getCurrentUser()
│       ├── utils.js                # formatCurrency(), formatDate(), animateCounter()
│       ├── page-register.js        # Role toggle UI + form submit → calls register()
│       ├── page-login.js           # Form submit → calls login()
│       ├── page-onboarding.js      # Shows owner/employee view, polling, form submissions
│       ├── page-upload.js          # File drop + scan trigger
│       ├── upload.js               # Full upload page logic
│       ├── results.js              # Invoice detail page logic
│       ├── history.js              # Invoice list + filters
│       ├── analytics.js            # Charts
│       ├── vendors.js              # Vendor page
│       └── companies.js            # Company settings panel
│
├── .gitignore                      # Includes: backend/.env, frontend/js/env.js
├── render.yaml                     # Render.com deployment config for backend
├── netlify.toml                    # Netlify config for frontend
├── vercel.json                     # Vercel config with CSP headers
└── Dockerfile
```

---

## 2. Database Schema & Models

### SQLAlchemy ORM (`backend/models.py`)

```python
class User(Base):
    __tablename__ = "users"
    id           = Column(UUID, primary_key=True)   # Matches Supabase Auth user UUID (sub)
    email        = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)   # "SUPABASE_AUTH" placeholder for OAuth users
    name         = Column(String)
    role         = Column(String, nullable=False)   # CHECK: 'owner' | 'employee'
    company_id   = Column(UUID, ForeignKey("companies.id"), nullable=True)  # NULL until onboarding
    created_at   = Column(DateTime)

class Company(Base):
    __tablename__ = "companies"
    id         = Column(UUID, primary_key=True)
    name       = Column(String, unique=True, nullable=False)
    gstin      = Column(String, unique=True, nullable=False)
    owner_id   = Column(UUID, ForeignKey("users.id"), nullable=True)
    webhook_url = Column(String, nullable=True)
    created_at = Column(DateTime)

class JoinRequest(Base):
    __tablename__ = "join_requests"
    id         = Column(UUID, primary_key=True)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID, ForeignKey("companies.id"), nullable=False)
    status     = Column(String, default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime)

class Invoice(Base):
    __tablename__ = "invoices"
    id               = Column(UUID, primary_key=True)
    job_id           = Column(String, unique=True)   # Background task identifier
    company_id       = Column(UUID, ForeignKey("companies.id"), nullable=False)
    uploaded_by      = Column(UUID, ForeignKey("users.id"), nullable=False)
    invoice_number   = Column(String)
    invoice_date     = Column(String)
    seller_name      = Column(String)
    seller_gstin     = Column(String)
    buyer_name       = Column(String)
    buyer_gstin      = Column(String)
    subtotal/cgst/sgst/igst/total = Column(Float)
    status           = Column(String)  # PROCESSING | PENDING_REVIEW | APPROVED | REJECTED | FAILED
    approval_status  = Column(String)  # null | approved | rejected
    approved_by      = Column(UUID, ForeignKey("users.id"), nullable=True)
    is_duplicate     = Column(String)  # null | original_invoice_id
    manually_verified = Column(String) # null | "true"
    raw_json         = Column(JSON)
    created_at/updated_at = Column(DateTime)

class Vendor(Base):
    __tablename__ = "vendors"
    id             = Column(UUID, primary_key=True)
    company_id     = Column(UUID, ForeignKey("companies.id"), nullable=False)
    gstin          = Column(String, nullable=False)
    name           = Column(String, nullable=False)
    total_invoices = Column(Float, default=0)
    total_amount   = Column(Float, default=0.0)
    # UNIQUE index on (company_id, gstin)
```

### Key Relationships
- `User.company_id → Company.id` (nullable — NULL means not yet onboarded)
- `Company.owner_id → User.id`
- `JoinRequest.user_id → User.id`, `JoinRequest.company_id → Company.id`
- `Invoice.company_id → Company.id`, `Invoice.uploaded_by → User.id`
- `Vendor.company_id → Company.id`

---

## 3. Backend API

### Authentication Middleware (`backend/auth.py`)

```python
load_dotenv()
SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")   # Loaded from env only
ALGORITHM  = "HS256"

def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience="authenticated")
    return payload

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # 1. Extract Bearer token from Authorization header (fallback: cookie)
    # 2. Decode and verify Supabase JWT using SUPABASE_JWT_SECRET + HS256 + audience="authenticated"
    # 3. Extract sub (UUID) and email from payload
    # 4. Look up user in local DB by id
    # 5. If not found → JUST-IN-TIME SYNC: create User row with id=sub, role="owner",
    #    password_hash="SUPABASE_AUTH", name from user_metadata.full_name
    # 6. Return User object

class RoleChecker:
    # Dependency factory: Depends(RoleChecker(["owner"])) enforces role-based access
```

### All API Routes

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/health` | Public | Health check |
| GET | `/api/me` | ✅ | Returns current user profile |
| POST | `/api/logout` | ✅ | Clears access_token cookie |
| POST | `/api/companies` | ✅ | Create workspace (owner only) |
| GET | `/api/companies` | ✅ | Get user's company |
| PATCH | `/api/companies/me` | Owner | Update webhook URL |
| POST | `/api/join-request` | ✅ | Employee sends join request |
| GET | `/api/join-requests` | Owner | List pending join requests |
| POST | `/api/join-requests/{id}/approve` | Owner | Approve employee |
| POST | `/api/join-requests/{id}/reject` | Owner | Reject employee |
| GET | `/api/join-request/status` | ✅ | Check own join request status |
| POST | `/api/invite-user` | Owner | Pre-register employee by email |
| GET | `/api/users` | ✅ | List users in same company |
| POST | `/api/users/{id}/remove` | Owner | Remove employee from workspace |
| POST | `/api/scan` | ✅ | Upload invoice file → background OCR |
| GET | `/api/scan/status/{job_id}` | ✅ | Poll scan status |
| GET | `/api/invoices` | ✅ | Paginated invoice list (filters: q, status, date, vendor, amount) |
| GET | `/api/invoices/{id}` | ✅ | Single invoice detail |
| PATCH | `/api/invoices/{id}` | ✅ | Update extracted fields |
| POST | `/api/invoices/{id}/approve` | ✅ | Approve invoice |
| POST | `/api/invoices/{id}/reject` | ✅ | Reject invoice |
| POST | `/api/invoices/{id}/retry` | ✅ | Delete FAILED invoice so user can re-upload |
| POST | `/api/invoices/check-duplicate` | ✅ | Check if invoice already exists |
| POST | `/api/invoices/manual` | ✅ | Create invoice from manual data |
| POST | `/api/export` | ✅ | Export invoice data as CSV |
| GET | `/api/analytics` | ✅ | Aggregated analytics data |
| GET | `/api/itc-summary` | ✅ | ITC summary by tax type |
| GET | `/api/vendors` | ✅ | Vendor list |
| GET | `/api/vendors/{id}` | ✅ | Vendor detail |
| GET | `/api/vendors/{id}/invoices` | ✅ | Invoices for a vendor |

### Key Backend Logic: Workspace Creation (`routers/companies.py`)

```python
@router.post("/companies")
async def create_company(req, current_user, db):
    # Guard: user must not already have a company
    company = Company(name=req.name, gstin=req.gstin, owner_id=current_user.id)
    db.add(company); db.flush()
    current_user.company_id = company.id
    current_user.role = "owner"
    db.commit()
    return company

@router.post("/join-request")
async def request_join_company(req, current_user, db):
    # Finds company by exact name, creates JoinRequest with status="pending"
    # Blocks: duplicate pending requests, already-accepted members

@router.post("/join-requests/{id}/approve")
async def approve_join_request(request_id, current_user, db):
    # Sets employee.company_id = current_user.company_id
    # Sets employee.role = "employee"
    # Sets jr.status = "accepted"
```

---

## 4. Frontend Architecture & State Management

### Script Loading Order (every HTML page)
```html
<script src="js/env.js">           <!-- Sets window.ENV_SUPABASE_ANON_KEY (git-ignored) -->
<script src="js/config.js">        <!-- Defines CONFIG, window.apiFetch, window.getToken, etc. -->
<script src="js/utils.js">         <!-- formatCurrency, formatDate, animateCounter -->
<script src="https://cdn.../supabase-js@2"> <!-- Supabase SDK -->
<script src="js/auth.js">          <!-- Supabase client init, checkAuth(), login(), register(), etc. -->
<script src="js/page-*.js">        <!-- Page-specific logic -->
```

### `frontend/js/config.js` — Global Configuration & API Client

```javascript
const CONFIG = {
    API_BASE_URL: (hostname === 'localhost') ? 'http://localhost:8000'
                                             : 'https://gst-invoice-scanner-api-vrc-3o7k.onrender.com',
    SUPABASE_URL: 'https://qcttkeoxdwkmdjjlsjdx.supabase.co',
    SUPABASE_ANON_KEY: window.ENV_SUPABASE_ANON_KEY || 'REPLACE_WITH_SUPABASE_ANON_KEY'
    //                 ↑ Injected by env.js locally, or by CI/CD in production
};

window.getApiUrl  = (endpoint) => `${CONFIG.API_BASE_URL}${endpoint}`;
window.getToken   = () => sessionStorage.getItem('authToken');
window.setToken   = (token) => sessionStorage.setItem('authToken', token);
window.clearToken = () => sessionStorage.removeItem('authToken');

window.apiFetch = async (url, options = {}) => {
    // Automatically attaches: Authorization: Bearer <token> header
    // Intercepts 401 responses → shows session expired modal → redirects to login.html
};
```

### `frontend/js/auth.js` — Supabase Client & Auth Functions

```javascript
// Initialized ONCE here. All other files use functions exported from this file.
const _supabase = supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);

async function checkAuth() {
    const { data: { session } } = await _supabase.auth.getSession();
    const user = session?.user;
    // Page classification: isLoginPage, isRegisterPage, isLandingPage, isOnboardingPage, isCallbackPage
    // If authenticated: stores token, fetches /api/me → sessionStorage('currentUser')
    // If not authenticated + protected page → redirect to login.html
    // If authenticated + no company_id → redirect to onboarding.html
}
checkAuth(); // Runs immediately on every page load

_supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN')  window.setToken(session.access_token);
    if (event === 'SIGNED_OUT') { sessionStorage.clear(); redirect to login.html }
});

async function login(email, password)    // signInWithPassword → /api/me → sessionStorage
async function register(name, email, password, role) // signUp with emailRedirectTo=/auth-callback.html
async function loginWithGoogle()         // signInWithOAuth({ provider: 'google', redirectTo: /auth-callback.html })
async function logout()                  // signOut → clear sessionStorage → login.html
function getCurrentUser()                // JSON.parse(sessionStorage.getItem('currentUser'))
```

### `frontend/js/page-register.js` — Registration Form

```javascript
// Role toggle: switches between "owner" and "employee" buttons, updates hidden input #role
// On submit:
//   1. Validates passwords match
//   2. Calls register(name, email, pass, role)   [from auth.js]
//   3. Stores sessionStorage.setItem('intendedRole', role)  ← KEY: used by onboarding page
//   4. If email confirmation required → user sees "Check your email" message
//   5. If instant session (e.g. email confirm disabled) → redirect to upload.html
//      (auth.js checkAuth will catch company_id=null and redirect to onboarding.html)
```

### `frontend/auth-callback.html` — OAuth Redirect Handler

```javascript
// Purpose: Landing page after Google OAuth or email confirmation link click
const _supabase = supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);

async function handleCallback() {
    const { data: { session } } = await _supabase.auth.getSession();
    
    if (!session) {
        // If access_token is in URL hash, wait for onAuthStateChange instead
        if (window.location.hash.includes('access_token')) return;
        redirect to login.html;
        return;
    }
    
    window.setToken(session.access_token);
    const resp = await window.apiFetch('/api/me');  // ← triggers JIT user creation in backend
    
    if (resp.ok) {
        const userData = await resp.json();
        sessionStorage.setItem('currentUser', JSON.stringify(userData));
        const onboardingComplete = session.user.user_metadata?.onboarding_complete || userData.company_id;
        redirect to: onboardingComplete ? 'upload.html' : 'onboarding.html';
    } else {
        redirect to login.html;
    }
}

_supabase.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') handleCallback();
});
handleCallback(); // Also runs immediately
```

### `frontend/js/page-onboarding.js` — Workspace Setup

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const user = getCurrentUser();
    // Determine which view to show:
    const intendedRole = sessionStorage.getItem('intendedRole') || user.role || 'owner';
    // 'owner' → show #ownerView (Create workspace form)
    // 'employee' → call checkPendingStatus() → show join form or pending screen

    // Toggle links allow switching between Create/Join views regardless of intendedRole
    document.getElementById('switchToJoin')?.addEventListener('click', ...)
    document.getElementById('switchToCreate')?.addEventListener('click', ...)
});

async function checkPendingStatus() {
    // GET /api/join-request/status
    // 'approved' → GET /api/companies → store in sessionStorage → redirect upload.html
    // 'pending'  → show pending screen + startPolling() every 10s
    // else       → show #employeeView (join form)
}

// Create Workspace Form submit:
//   POST /api/companies { name, gstin }
//   → store company in sessionStorage → redirect upload.html

// Join Workspace Form submit:
//   POST /api/join-request { company_name }
//   → show pending screen → startPolling()
```

### sessionStorage Keys Used

| Key | Set By | Used By | Value |
|-----|--------|---------|-------|
| `authToken` | `auth.js setToken()` | `config.js apiFetch()` | Supabase JWT access token |
| `currentUser` | `auth.js`, `auth-callback.html` | All pages | `UserOut` JSON from `/api/me` |
| `currentCompany` | `page-onboarding.js` | Various pages | `CompanyOut` JSON from `/api/companies` |
| `intendedRole` | `page-register.js` | `page-onboarding.js` | `'owner'` or `'employee'` |

---

## 5. Configuration & Dependencies

### Backend `requirements.txt`

```
fastapi==0.135.1
uvicorn[standard]==0.42.0
sqlalchemy==2.0.48
psycopg2-binary==2.9.11
pydantic[email]==2.12.5
python-dotenv==1.2.2
python-multipart==0.0.22
slowapi==0.1.9
python-jose[cryptography]==3.5.0  # JWT verification
passlib[bcrypt]==1.7.4
google-genai==1.68.0              # Gemini OCR
groq==0.13.1                      # Groq LLM fallback
pytesseract==0.3.13
pymupdf==1.27.2.2
pillow==12.1.1
structlog==25.5.0
```

### Required Environment Variables

**Backend (`.env` / Render Dashboard):**

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (Supabase pooled, port 6543) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_JWT_SECRET` | From Supabase Dashboard → Settings → API → JWT Secret. Used to verify tokens server-side |
| `GROQ_API_KEY` | Groq API key for LLM-based OCR parsing |
| `GEMINI_API_KEY` | Google Gemini API key |

**Frontend (local `js/env.js`, git-ignored):**
```javascript
window.ENV_SUPABASE_ANON_KEY = 'your-actual-anon-key-here';
```

**Frontend (production — Vercel/Netlify):**
- Set `SUPABASE_ANON_KEY` as an environment variable on the platform.
- Build command replaces the placeholder in `config.js`:
  ```bash
  sed -i "s/REPLACE_WITH_SUPABASE_ANON_KEY/$SUPABASE_ANON_KEY/g" frontend/js/config.js
  ```

### Supabase Dashboard Configuration Required

1. **Authentication → URL Configuration:**
   - Site URL: `https://your-app.netlify.app`
   - Redirect URLs: `https://your-app.netlify.app/auth-callback.html`, `http://127.0.0.1:*/auth-callback.html`

2. **Authentication → Providers → Google:**
   - Enable Google provider
   - Paste Client ID and Client Secret from Google Cloud Console
   - Register Supabase callback URL in Google Cloud: `https://<project>.supabase.co/auth/v1/callback`

3. **Authentication → Email Templates:**
   - Confirmation URL template should use `{{ .ConfirmationURL }}`
   - `emailRedirectTo` in `auth.js signUp()` points to `/auth-callback.html`

---

## 6. Key Architectural Decisions

1. **Supabase-First Auth**: All authentication (sign up, sign in, OAuth, JWT issuance) is handled by Supabase. The backend is a pure resource server that validates JWTs — it does NOT issue its own tokens.

2. **Just-In-Time User Sync**: When a user logs in for the first time (especially via Google), the backend's `get_current_user()` dependency automatically creates a local `users` row using the `sub` field (UUID) from the Supabase JWT as the primary key. This ensures FK relationships work without a separate registration endpoint.

3. **`password_hash` placeholder**: The `users` table has a `password_hash NOT NULL` constraint in the DB schema but the ORM column is `nullable=True`. For all Supabase-authenticated users, this is set to the string `"SUPABASE_AUTH"` or `"SUPABASE_INVITE"` as a placeholder.

4. **`intendedRole` in sessionStorage**: Since Google OAuth bypasses the register form (which has the role toggle), the `intendedRole` key is used to tell the onboarding page which view to show. If missing, defaults to `'owner'`. Toggle links on the onboarding page allow switching between views at any time.

5. **Two-step onboarding**: A user with `company_id = NULL` is considered "not onboarded." `checkAuth()` in `auth.js` enforces a redirect to `onboarding.html` for all protected pages until they create or join a workspace.
