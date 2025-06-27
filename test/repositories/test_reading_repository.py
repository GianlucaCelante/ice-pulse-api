# =====================================================
# tests/repositories/test_reading_simple.py
# =====================================================
"""
Test semplificato per Reading - solo per isolare il problema
"""

import sys
import os
from pathlib import Path

# BRUTAL FIX: Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import psycopg2
from psycopg2 import OperationalError

from datetime import datetime, date, timedelta
import uuid
import subprocess
import time
from decimal import Decimal

# Test solo i modelli base - IMPORT SOLO QUELLO CHE SERVE
from src.models.base import BaseModel

# Per ora facciamo test senza Organization che ha problemi con relationships

# Test PostgreSQL setup base
@pytest.fixture(scope="session")
def postgresql_container():
    """Start PostgreSQL container for testing session"""
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
            print(f"✅ Container {container_name} already running")
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
            print(f"🚀 Creating new container {container_name}")
            # Create new container
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-e", "POSTGRES_PASSWORD=test_password",
                "-e", "POSTGRES_USER=test_user", 
                "-e", "POSTGRES_DB=test_icepulse",
                "-p", "5433:5432",
                "postgres:15-alpine"
            ], check=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start PostgreSQL container: {e}")
    
    # Wait for PostgreSQL to be ready
    wait_for_postgres()
    
    db_config = get_db_config()
    print(f"✅ PostgreSQL ready at {db_config['host']}:{db_config['port']}")
    
    yield db_config
    
    # Cleanup - stop container but keep it for next run
    print(f"🛑 Stopping container {container_name}")
    subprocess.run(["docker", "stop", container_name], check=False)

def get_db_config():
    """Get database connection config"""
    return {
        "host": "localhost",
        "port": 5433,
        "user": "test_user",
        "password": "test_password",
        "database": "test_icepulse"
    }

def wait_for_postgres(max_retries=30):
    """Wait for PostgreSQL to be ready"""
    config = get_db_config()
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"], 
                database=config["database"]
            )
            conn.close()
            return
        except OperationalError:
            if i == max_retries - 1:
                pytest.fail("PostgreSQL container failed to start in time")
            time.sleep(1)
            print(f"⏳ Waiting for PostgreSQL... ({i+1}/{max_retries})")

@pytest.fixture(scope="function")
def test_db(postgresql_container):
    """Create test database session with clean state"""
    config = postgresql_container
    
    # Create engine with PostgreSQL
    db_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    
    print(f"🔗 Connecting to: {db_url}")
    
    try:
        engine = create_engine(db_url, echo=False)
        
        # Test connection immediately
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            row = result.fetchone()
            if row is None:
                pytest.fail("Could not fetch PostgreSQL version from database connection")
            pg_version = row[0]
            print(f"✅ PostgreSQL connected: {pg_version[:50]}...")
        
        # Create all tables
        print("📊 Creating tables...")
        BaseModel.metadata.create_all(engine)
        print("✅ Tables created successfully")
        
        # Create session
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        
        # Verify we're using PostgreSQL
        result = session.execute(text("SELECT current_database(), version()"))
        row = result.fetchone()
        if row is None:
            pytest.fail("Could not fetch database name and version from database connection")
        db_name, version = row
        print(f"✅ Using database: {db_name}")
        print(f"✅ PostgreSQL version: {version[:30]}...")
        
        yield session
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        pytest.fail(f"PostgreSQL setup failed: {e}")
    
    # Cleanup - close session and drop all tables for clean state
    print("🧹 Cleaning up database...")
    session.close()
    BaseModel.metadata.drop_all(engine)
    engine.dispose()
    print("✅ Cleanup completed")

# =====================================================
# TEST STEP BY STEP
# =====================================================

def test_1_postgres_connection(test_db):
    """Test 1: PostgreSQL connection works"""
    result = test_db.execute(text("SELECT 1 as test"))
    row = result.fetchone()
    assert row[0] == 1
    print("✅ Test 1: PostgreSQL connection OK")

def test_2_organization_import():
    """Test 2: Can we import Organization model?"""
    try:
        from src.models.organization import Organization
        print(f"✅ Organization imported: {Organization}")
        print("✅ Test 2: Organization import OK")
        return Organization
    except Exception as e:
        print(f"❌ Organization import failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_3_sensor_import():
    """Test 3: Can we import Sensor model?"""
    try:
        from src.models.sensor import Sensor
        print(f"✅ Sensor imported: {Sensor}")
        print("✅ Test 3: Sensor import OK")
        return Sensor
    except Exception as e:
        print(f"❌ Sensor import failed: {e}")
        raise

def test_4_sensor_creation_simple(test_db):
    """Test 4: Create a simple Organization first"""
    try:
        # Creiamo solo Organization senza relationships problematiche
        # Usiamo SQL diretto per evitare i problemi SQLAlchemy
        
        test_db.execute(text("""
            INSERT INTO organizations (id, name, slug) 
            VALUES (gen_random_uuid(), 'Test Company', 'test-company')
        """))
        test_db.commit()
        
        # Ora prendiamo l'organization ID
        result = test_db.execute(text("""
            SELECT id FROM organizations WHERE slug = 'test-company'
        """))
        org_row = result.fetchone()
        org_id = org_row[0]
        
        print(f"✅ Organization created via SQL: {org_id}")
        
        # Ora tentiamo di creare un sensor
        from src.models.sensor import Sensor
        
        sensor = Sensor(
            organization_id=org_id,
            device_id="TEMP001",
            name="Test Sensor",
            location_id=None  # EXPLICIT NULL per evitare FK error
        )
        print(f"✅ Sensor created: {type(sensor)}")
        
        test_db.add(sensor)
        test_db.commit()
        test_db.refresh(sensor)
        
        assert sensor.id is not None
        assert sensor.device_id == "TEMP001"
        print("✅ Test 4: Sensor model OK")
        
        return sensor
        
    except Exception as e:
        print(f"❌ Sensor creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_5_reading_import():
    """Test 5: Can we import Reading model?"""
    try:
        from src.models.reading import Reading
        print(f"✅ Reading imported: {Reading}")
        print("✅ Test 5: Reading import OK")
        return Reading
    except Exception as e:
        print(f"❌ Reading import failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_6_reading_creation_simple(test_db):
    """Test 6: Reading model creation"""
    try:
        # Create organization via SQL
        test_db.execute(text("""
            INSERT INTO organizations (id, name, slug) 
            VALUES (gen_random_uuid(), 'Test Company 2', 'test-company-2')
        """))
        test_db.commit()
        
        result = test_db.execute(text("""
            SELECT id FROM organizations WHERE slug = 'test-company-2'
        """))
        org_row = result.fetchone()
        org_id = org_row[0]
        
        # Create sensor via SQL to avoid FK issues
        test_db.execute(text("""
            INSERT INTO sensors (id, organization_id, device_id, name, location_id) 
            VALUES (gen_random_uuid(), :org_id, 'TEMP002', 'Test Sensor 2', NULL)
        """), {"org_id": org_id})
        test_db.commit()
        
        result = test_db.execute(text("""
            SELECT id FROM sensors WHERE device_id = 'TEMP002'
        """))
        sensor_row = result.fetchone()
        sensor_id = sensor_row[0]
        
        print(f"✅ Sensor created via SQL: {sensor_id}")
        
        # Now create Reading
        from src.models.reading import Reading
        
        reading = Reading(
            organization_id=org_id,
            sensor_id=sensor_id,
            timestamp=datetime.now(),
            temperature=4.5
        )
        print(f"✅ Reading created: {type(reading)}")
        
        test_db.add(reading)
        test_db.commit()
        test_db.refresh(reading)
        
        assert reading.id is not None
        assert reading.temperature == Decimal('4.500')
        print("✅ Test 6: Reading model OK")
        
        return reading
        
    except Exception as e:
        print(f"❌ Reading creation failed: {e}")
        import traceback
        traceback.print_exc()
        raise

"""
COME ESEGUIRE I TEST:

# Test uno alla volta per isolare il problema
pytest test/repositories/test_reading_repository.py::test_1_postgres_connection -v -s
pytest test/repositories/test_reading_repository.py::test_2_organization_creation -v -s
pytest test/repositories/test_reading_repository.py::test_3_sensor_import -v -s
pytest test/repositories/test_reading_repository.py::test_4_sensor_creation -v -s
pytest test/repositories/test_reading_repository.py::test_5_reading_import -v -s
pytest test/repositories/test_reading_repository.py::test_6_reading_creation -v -s

# Oppure tutti insieme
pytest test/repositories/test_reading_repository.py -v -s
"""