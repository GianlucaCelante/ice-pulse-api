# =====================================================
# test/repositories/test_reading_repository.py - CLEAN VERSION
# =====================================================
"""
Test per Reading Repository - versione pulita senza path hacks.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
from datetime import datetime, timezone

# Clean imports - no path manipulation needed
from src.models import BaseModel, Organization, Location, Sensor, Reading

def test_1_postgres_connection(postgresql_container):
    """Test basic PostgreSQL connection"""
    config = postgresql_container
    db_url = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    
    print(f"🔗 Connecting to: {db_url}")
    
    from sqlalchemy import create_engine, text
    engine = create_engine(db_url, echo=False)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        row = result.fetchone()
        assert row is not None, "Could not fetch PostgreSQL version"
        pg_version = row[0]
        print(f"✅ PostgreSQL connected: {pg_version[:50]}...")
    
    # Test table creation with ALL models imported
    print("📊 Creating tables...")
    BaseModel.metadata.create_all(engine)
    print("✅ Tables created successfully")
    
    # Verify tables were created
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), version()"))
        row = result.fetchone()
        assert row is not None, "Could not fetch database info"
        db_name, version = row
        print(f"✅ Using database: {db_name}")
        print(f"✅ PostgreSQL version: {version[:30]}...")
    
    # Cleanup
    print("🧹 Cleaning up database...")
    BaseModel.metadata.drop_all(engine)
    print("✅ Cleanup completed")
    
    print("✅ Test 1: PostgreSQL connection OK")


def test_2_organization_import():
    """Test Organization model import"""
    assert Organization is not None
    print(f"✅ Organization imported: {Organization}")
    print("✅ Test 2: Organization import OK")


def test_3_sensor_import():
    """Test Sensor model import"""
    assert Sensor is not None
    print(f"✅ Sensor imported: {Sensor}")
    print("✅ Test 3: Sensor import OK")


def test_4_sensor_creation_simple(test_db):
    """Test basic sensor creation"""
    # Create organization first
    org_data = {
        "name": "Test Organization",
        "slug": "test-org-sensor",
        "subscription_plan": "free",
        "max_sensors": 10,
        "timezone": "UTC"
    }
    org = Organization(**org_data)
    test_db.add(org)
    test_db.flush()  # Get the ID without committing
    
    # Create location
    location_data = {
        "organization_id": org.id,
        "name": "Test Freezer",
        "location_type": "freezer",
        "temperature_min": -20.0,
        "temperature_max": -15.0
    }
    location = Location(**location_data)
    test_db.add(location)
    test_db.flush()
    
    # Create sensor
    sensor_data = {
        "organization_id": org.id,
        "location_id": location.id,
        "device_id": "TEST_SENSOR_001",
        "name": "Test Temperature Sensor",
        "sensor_type": "temperature_humidity",
        "status": "offline",
        "battery_level": 100,
        "reading_interval_seconds": 300
    }
    sensor = Sensor(**sensor_data)
    test_db.add(sensor)
    test_db.commit()
    
    # Verify sensor was created
    assert sensor.id is not None
    assert sensor.device_id == "TEST_SENSOR_001"
    assert sensor.organization_id == org.id
    assert sensor.location_id == location.id
    
    print("✅ Test 4: Sensor creation OK")


def test_5_reading_import():
    """Test Reading model import"""
    assert Reading is not None
    print(f"✅ Reading imported: {Reading}")
    print("✅ Test 5: Reading import OK")


def test_6_reading_creation_simple(test_db):
    """Test basic reading creation"""
    from decimal import Decimal
    
    # Create organization
    org_data = {
        "name": "Test Organization Reading",
        "slug": "test-org-reading",
        "subscription_plan": "free",
        "max_sensors": 10,
        "timezone": "UTC"
    }
    org = Organization(**org_data)
    test_db.add(org)
    test_db.flush()
    
    # Create location
    location_data = {
        "organization_id": org.id,
        "name": "Test Reading Freezer",
        "location_type": "freezer",
        "temperature_min": Decimal('-20.0'),   # Use Decimal here too
        "temperature_max": Decimal('-15.0')
    }
    location = Location(**location_data)
    test_db.add(location)
    test_db.flush()
    
    # Create sensor
    sensor_data = {
        "organization_id": org.id,
        "location_id": location.id,
        "device_id": "TEST_READING_SENSOR_001",
        "name": "Test Reading Sensor",
        "sensor_type": "temperature_humidity",
        "status": "online",
        "battery_level": 95
    }
    sensor = Sensor(**sensor_data)
    test_db.add(sensor)
    test_db.flush()
    
    # Create reading - Use Decimal for input too
    reading_data = {
        "organization_id": org.id,
        "sensor_id": sensor.id,
        "timestamp": datetime.now(timezone.utc),
        "temperature": Decimal('-18.5'),       # Use Decimal for input
        "humidity": Decimal('65.2'),           # Use Decimal for input
        "battery_voltage": Decimal('3.7'),     # Use Decimal for input
        "data_quality_score": Decimal('0.95'), # Use Decimal for input
        "is_manual_entry": False,
        "temperature_deviation": False,
        "humidity_deviation": False,
        "deviation_detected": False,
        "haccp_compliance_status": "compliant"
    }
    reading = Reading(**reading_data)
    test_db.add(reading)
    test_db.commit()
    
    # Verify reading was created - Now the types match!
    assert reading.id is not None
    assert reading.temperature == Decimal('-18.500')  # PostgreSQL will store full precision
    assert reading.humidity == Decimal('65.20')       # PostgreSQL will store full precision
    assert reading.sensor_id == sensor.id
    assert reading.organization_id == org.id
    
    print("✅ Test 6: Reading creation OK")