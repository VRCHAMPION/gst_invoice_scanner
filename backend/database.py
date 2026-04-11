import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")
DATABASE_URL = DATABASE_URL.strip()

# Supabase / Neon prefer sslmode=require
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_timeout": 30,
    "pool_size": 5,
    "max_overflow": 10,
}

# Supabase transaction-mode pooler (port 6543) needs prepared-statement cache disabled
if "6543" in DATABASE_URL:
    engine_kwargs["execution_options"] = {"prepared_statement_cache_size": 0}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Migration helpers ─────────────────────────────────────────────────

def init_db():
    from models import Base as ModelsBase  # noqa: F401 — registers all models
    ModelsBase.metadata.create_all(bind=engine)


def ping_db() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def seed_admin_user_orm():
    """Create a default admin user if one doesn't already exist."""
    from models import User
    from auth import hash_password

    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@gstscanner.internal").strip()
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "change-me-immediately").strip()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin = User(
                email=admin_email,
                name="Admin User",
                password_hash=hash_password(admin_password),
                role="owner",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
