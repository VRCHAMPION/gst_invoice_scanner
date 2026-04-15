"""
main.py - FastAPI app setup with middleware and routers
"""
import logging
import uuid
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from database import init_db, ping_db
from routers import auth, companies, invoices, analytics, vendors
from schemas import HealthResponse

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

APP_VERSION = "1.1.0"

app = FastAPI(
    title="GST Invoice Scanner API",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please slow down."},
    )

# CORS - allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gst-invoice-scanner.vercel.app",
        "https://gstinvoicescanner.netlify.app",
        "https://gstinvoicescanner.netlify.app/",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.on_event("startup")
def on_startup():
    init_db()
    log.info("app_started", version=APP_VERSION)


# Register routers
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(invoices.router)
app.include_router(analytics.router)
app.include_router(vendors.router)


@app.api_route("/health", methods=["GET", "HEAD"], response_model=HealthResponse, tags=["system"])
async def health_check():
    db_status = "connected" if ping_db() else "unreachable"
    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        db=db_status,
        version=APP_VERSION,
    )


@app.get("/", tags=["system"])
async def root():
    return {"message": "GST Invoice Scanner API", "version": APP_VERSION, "docs": "/docs"}


