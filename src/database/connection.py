# src/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
import os
from typing import AsyncGenerator

# Database URL construction
def get_database_url() -> str:
    """Costruisce URL database da environment variables"""
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "icepulse")
    
    # Use asyncpg for production-like environments, psycopg2 otherwise
    env = os.getenv("ENVIRONMENT", "dev").lower()
    driver = "postgresql+asyncpg" if env in ("prod", "production") else "postgresql+psycopg2"
    
    return f"{driver}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Database engine
DATABASE_URL = get_database_url()

# Create async engine when using asyncpg driver
USE_ASYNC = DATABASE_URL.startswith("postgresql+asyncpg")

if USE_ASYNC:
    engine = create_async_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )

# Session factories
if USE_ASYNC:
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
else:
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

# Base class for models
Base = declarative_base()

# Dependency for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for FastAPI"""
    if USE_ASYNC:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        db = SessionLocal()
        try:
            yield db  # type: ignore[arg-type]
        finally:
            db.close()

# Health check function
def check_database_connection() -> bool:
    """Simple database connectivity test"""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False