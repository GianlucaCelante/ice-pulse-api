# alembic/env.py - Environment setup per migrations Ice Pulse
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from pathlib import Path

# Aggiungi src path per import models
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Import dei models per auto-generation
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# Configurazione Alembic
config = context.config

# Setup logging se alembic.ini presente
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata per auto-generation
target_metadata = Base.metadata

# Configurazione database da environment variables
def get_database_url():
    """Costruisce URL database da environment variables"""
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "icepulse")
    
    return f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Configurazioni specifiche Ice Pulse
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
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
            # Configurazioni specifiche Ice Pulse
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,
            # Include schemi per RLS
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()

# Esecuzione migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()