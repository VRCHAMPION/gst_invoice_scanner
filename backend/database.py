import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use PostgreSQL connection string for Neon
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Neon (Postgres) prefers sslmode=require for security
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

# Detect if using Neon's pooled connection string (routes via PgBouncer over port 443).
# The pooled string contains "-pooler." in the hostname.
# PgBouncer in transaction mode doesn't support named prepared statements,
# so we must disable SQLAlchemy's prepared statement cache when using it.
IS_POOLED = "-pooler." in DATABASE_URL if DATABASE_URL else False

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,   # re-test dead connections (crucial for Neon's auto-suspend)
    "pool_timeout": 30,
}

if IS_POOLED:
    # Pooled (PgBouncer) mode: route over port 443, safe on restrictive college WiFi.
    # Must disable prepared statements — PgBouncer transaction mode doesn't support them.
    connect_args["options"] = "-c statement_timeout=30000"
    engine_kwargs.update({
        "pool_size": 2,         # 2 × 4 workers = 8 connections (safe on free tier)
        "max_overflow": 0,      # no overflow — stay within Neon's 10-connection limit
        "connect_args": connect_args,
        "execution_options": {"prepared_statement_cache_size": 0},  # disable for PgBouncer
    })
else:
    # Direct connection (port 5432) — standard mode for home/server networks.
    engine_kwargs.update({
        "pool_size": 2,         # conservative — Neon free tier has 10-connection limit
        "max_overflow": 1,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Migration Helpers ─────────────────────────────────────────────────
def init_db():
    from models import Base
    # Create all tables in Neon
    Base.metadata.create_all(bind=engine)

def seed_admin_user_orm():
    from models import User
    from auth import hash_password
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin = User(
                password_hash=hash_password(os.getenv("DEFAULT_ADMIN_PASSWORD", "super-secure-randomization-temp")),
                name="Admin User",
                role="owner"
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()