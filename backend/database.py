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

engine = create_engine(DATABASE_URL)
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