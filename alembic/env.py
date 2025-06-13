# alembic/env.py - DEBUG VERSION per trovare il problema
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# CRITICAL: target_metadata MUST be None for manual migrations
target_metadata = None

# Configurazione Alembic
config = context.config

# Setup logging se alembic.ini presente
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def get_database_url():
    """Costruisce URL database da environment variables"""
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "icepulse")
    
    # Usa psycopg2 per Alembic (sincrono), non asyncpg
    return f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # NO autogenerate options here
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override della connection string da environment
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # NO autogenerate options here either
        )

        with context.begin_transaction():
            context.run_migrations()

# Esecuzione migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()