# src/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

# Database URL construction
def get_database_url() -> str:
    """Costruisce URL database da environment variables"""
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "icepulse")
    
    # Use asyncpg for production, psycopg2 for development
    driver = "postgresql+asyncpg" if os.getenv("ENVIRONMENT") == "production" else "postgresql+psycopg2"
    
    return f"{driver}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Database engine
DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    # Connection pool settings
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=os.getenv("DB_ECHO", "false").lower() == "true"  # SQL logging for debug
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
def get_db() -> Generator:
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Context manager for manual DB operations
class DatabaseSession:
    """Context manager for database sessions"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.db.rollback()
        else:
            self.db.commit()
        self.db.close()

# Health check function
def check_database_connection() -> bool:
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute()
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False