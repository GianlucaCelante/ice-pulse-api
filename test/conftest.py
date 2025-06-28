# =====================================================
# test/conftest.py - Shared pytest configuration
# =====================================================
"""
Configurazione condivisa per tutti i test.

Questo file risolve automaticamente i problemi di import path
per tutti i test, evitando di dover ripetere il path fix in ogni file.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for all tests
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"🔧 Added to PYTHONPATH: {project_root}")

# Ensure src module is importable for all tests
try:
    import src
    print(f"✅ src module available at: {src.__file__}")
except ImportError as e:
    print(f"❌ src module import failed: {e}")
    print(f"   Current PYTHONPATH: {sys.path}")
    raise

# Optional: Import common fixtures here to make them available to all tests
import pytest
import subprocess
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import ALL models to ensure they're registered with SQLAlchemy
from src.models import *

# =====================================================
# POSTGRESQL SHARED FIXTURE
# =====================================================

def get_db_config():
    """Get PostgreSQL test database configuration"""
    return {
        'host': 'localhost',
        'port': 5433,
        'user': 'test_user',
        'password': 'test_password',
        'database': 'test_icepulse'
    }

@pytest.fixture(scope="session")
def postgresql_container():
    """Start PostgreSQL container for testing session - shared across all tests"""
    container_name = "ice-pulse-test-db"
    
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("Docker not available")
    
    # Check if container already exists and is running
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True
        )
        if container_name in result.stdout:
            print(f"🔄 Starting existing container {container_name}")
            yield get_db_config()
            return
    except subprocess.CalledProcessError:
        pass
    
    # Check if container exists but is stopped
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=True
        )
        if container_name in result.stdout:
            print(f"🔄 Starting existing container {container_name}")
            subprocess.run(["docker", "start", container_name], check=True)
        else:
            print(f"🐳 Creating new container {container_name}")
            # Create new container
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-e", "POSTGRES_USER=test_user",
                "-e", "POSTGRES_PASSWORD=test_password", 
                "-e", "POSTGRES_DB=test_icepulse",
                "-p", "5433:5432",
                "postgres:15-alpine"
            ], check=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start PostgreSQL container: {e}")
    
    print(f"{container_name}")
    
    # Wait for PostgreSQL to be ready
    import time
    import psycopg2
    from psycopg2 import OperationalError
    
    config = get_db_config()
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                user=config['user'],
                password=config['password'],
                database=config['database']
            )
            conn.close()
            print(f"✅ PostgreSQL ready at {config['host']}:{config['port']}")
            break
        except OperationalError:
            if attempt == max_attempts - 1:
                subprocess.run(["docker", "stop", container_name], check=False)
                subprocess.run(["docker", "rm", container_name], check=False)
                pytest.fail("PostgreSQL container failed to start")
            time.sleep(1)
    
    yield config
    
    # Cleanup handled by Docker container lifecycle
    print(f"🛑 Stopping container {container_name}")
    subprocess.run(["docker", "stop", container_name], check=False)

@pytest.fixture(scope="function") 
def test_db(postgresql_container):
    """Create clean test database session for each test function"""
    config = postgresql_container
    
    db_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    print(f"🔗 Connecting to: {db_url}")
    
    try:
        engine = create_engine(db_url, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            row = result.fetchone()
            if row is None:
                pytest.fail("Could not fetch PostgreSQL version")
            pg_version = row[0]
            print(f"✅ PostgreSQL connected: {pg_version[:50]}...")
        
        # Create all tables
        print("📊 Creating tables...")
        BaseModel.metadata.create_all(engine)
        print("✅ Tables created successfully")
        
        # Create session
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        
        # Verify database
        result = session.execute(text("SELECT current_database(), version()"))
        row = result.fetchone()
        if row is None:
            pytest.fail("Could not fetch database info")
        db_name, version = row
        print(f"✅ Using database: {db_name}")
        print(f"✅ PostgreSQL version: {version[:30]}...")
        
        yield session
        
        # Cleanup
        session.close()
        BaseModel.metadata.drop_all(engine)
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        pytest.fail(f"PostgreSQL setup failed: {e}")