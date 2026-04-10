import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use PostgreSQL connection string for Database (e.g., Supabase)
DATABASE_URL = os.getenv("DATABASE_URL").strip() if os.getenv("DATABASE_URL") else None

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

# Supabase (Postgres) prefers sslmode=require for security
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"

# Standard connection kwargs
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_timeout": 30,
    "pool_size": 5,
    "max_overflow": 10,
}

# If using Supabase connection pooling (Transaction mode, typically port 6543),
# you might need to disable prepared statements if you encounter issues.
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

# ── Migration Helpers ─────────────────────────────────────────────────
def init_db():
    from models import Base
    # Create all tables in DB
    Base.metadata.create_all(bind=engine)

def seed_admin_user_orm():
    from models import User
    from auth import hash_password
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            admin = User(
                password_hash=hash_password(os.getenv("DEFAULT_ADMIN_PASSWORD", "super-secure-randomization-temp").strip()),
                name="Admin User",
                role="owner"
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()