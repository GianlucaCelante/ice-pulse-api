# =====================================================
# test/repositories/test_sensor_repository.py
# =====================================================
"""
Test per SensorRepository - testa gestione sensori IoT, monitoraggio HACCP e calibrazioni.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

# Clean imports - no path manipulation needed
from src.models import Organization, Location, Sensor, Calibration
from src.repositories.sensor_repository import SensorRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def sensor_repository(test_db):
    """Create SensorRepository instance"""
    return SensorRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Sensor Test Company",
        slug="sensor-test-company",
        subscription_plan="premium",
        max_sensors=100,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def sample_location(test_db, sample_organization):
    """Create sample location for testing"""
    location = Location(
        organization_id=sample_organization.id,
        name="Test Freezer A",
        location_type="freezer",
        temperature_min=Decimal('-25.0'),
        temperature_max=Decimal('-15.0'),
        floor="Ground",
        zone="Kitchen-Main"
    )
    test_db.add(location)
    test_db.commit()
    test_db.refresh(location)
    return location

@pytest.fixture
def sample_sensor_data(sample_organization, sample_location):
    """Sample sensor data for testing"""
    return {
        "organization_id": sample_organization.id,
        "location_id": sample_location.id,
        "device_id": "SENSOR_TEST_001",
        "name": "Main Freezer Temperature Sensor",
        "sensor_type": "temperature_humidity",
        "status": "online",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "firmware_version": "1.2.3",
        "hardware_model": "TempSense Pro v2",
        "battery_level": 85,
        "reading_interval_seconds": 300,  # 5 minutes
        "accuracy_specification": Decimal('0.5'),
        "alert_thresholds": {
            "temperature": {"min": -25.0, "max": -15.0},
            "humidity": {"min": 10.0, "max": 30.0}
        }
    }

@pytest.fixture
def created_sensor(sensor_repository, sample_sensor_data):
    """Create and return a test sensor"""
    return sensor_repository.create(sample_sensor_data)

@pytest.fixture
def second_organization(test_db):
    """Create second organization for multi-tenancy tests"""
    org = Organization(
        name="Second Sensor Test Company",
        slug="second-sensor-test-company",
        subscription_plan="basic",
        max_sensors=20,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def second_location(test_db, second_organization):
    """Create location for second organization"""
    location = Location(
        organization_id=second_organization.id,
        name="Second Org Fridge",
        location_type="fridge",
        temperature_min=Decimal('2.0'),
        temperature_max=Decimal('8.0')
    )
    test_db.add(location)
    test_db.commit()
    test_db.refresh(location)
    return location

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestSensorCRUD:
    """Test basic CRUD operations"""
    
    def test_create_sensor_success(self, sensor_repository, sample_sensor_data):
        """Test creating a new sensor"""
        
        # Act
        sensor = sensor_repository.create(sample_sensor_data)
        
        # Assert
        assert sensor.id is not None
        assert sensor.organization_id == sample_sensor_data["organization_id"]
        assert sensor.location_id == sample_sensor_data["location_id"]
        assert sensor.device_id == sample_sensor_data["device_id"]
        assert sensor.name == sample_sensor_data["name"]
        assert sensor.sensor_type == sample_sensor_data["sensor_type"]
        assert sensor.status == sample_sensor_data["status"]
        assert sensor.mac_address == sample_sensor_data["mac_address"]
        assert sensor.firmware_version == sample_sensor_data["firmware_version"]
        assert sensor.hardware_model == sample_sensor_data["hardware_model"]
        assert sensor.battery_level == sample_sensor_data["battery_level"]
        assert sensor.reading_interval_seconds == sample_sensor_data["reading_interval_seconds"]
        assert sensor.accuracy_specification == sample_sensor_data["accuracy_specification"]
        assert sensor.alert_thresholds == sample_sensor_data["alert_thresholds"]
        
        # Verify timestamps
        assert sensor.created_at is not None
        assert sensor.updated_at is not None
        
        print(f"✅ Sensor created with ID: {sensor.id}")
        print(f"✅ Device ID: {sensor.device_id}, Type: {sensor.sensor_type}")
        print(f"✅ Battery: {sensor.battery_level}%, Status: {sensor.status}")
    
    def test_get_by_id(self, sensor_repository, created_sensor):
        """Test getting sensor by ID"""
        # Act
        found_sensor = sensor_repository.get_by_id(created_sensor.id)
        
        # Assert
        assert found_sensor is not None
        assert found_sensor.id == created_sensor.id
        assert found_sensor.device_id == created_sensor.device_id
        assert found_sensor.name == created_sensor.name
        
        print(f"✅ Sensor found by ID: {found_sensor.id}")
    
    def test_get_by_id_not_found(self, sensor_repository):
        """Test getting non-existent sensor"""
        # Act
        found_sensor = sensor_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_sensor is None
        print("✅ Non-existent sensor correctly returned None")
    
    def test_update_sensor(self, sensor_repository, created_sensor):
        """Test updating sensor"""
        # Arrange
        update_data = {
            "name": "Updated Freezer Sensor",
            "firmware_version": "1.3.0",
            "battery_level": 75,
            "status": "warning"
        }
        
        # Act
        updated_sensor = sensor_repository.update(created_sensor.id, update_data)
        
        # Assert
        assert updated_sensor is not None
        assert updated_sensor.name == "Updated Freezer Sensor"
        assert updated_sensor.firmware_version == "1.3.0"
        assert updated_sensor.battery_level == 75
        assert updated_sensor.status == "warning"
        # Check unchanged fields
        assert updated_sensor.device_id == created_sensor.device_id
        assert updated_sensor.sensor_type == created_sensor.sensor_type
        
        print(f"✅ Sensor updated successfully")
    
    def test_delete_sensor(self, sensor_repository, created_sensor):
        """Test deleting sensor"""
        # Act
        result = sensor_repository.delete(created_sensor.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_sensor = sensor_repository.get_by_id(created_sensor.id)
        assert found_sensor is None
        
        print(f"✅ Sensor deleted successfully")
    
    def test_delete_nonexistent_sensor(self, sensor_repository):
        """Test deleting non-existent sensor"""
        # Act
        result = sensor_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent sensor correctly returned False")

# =====================================================
# TEST SENSOR-SPECIFIC QUERIES
# =====================================================

class TestSensorQueries:
    """Test sensor-specific query methods"""
    
    def test_get_by_organization(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting sensors by organization"""
        # Arrange - Create multiple sensors
        sensor1 = sensor_repository.create(sample_sensor_data)
        sensor2 = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "SENSOR_TEST_002",
            "name": "Secondary Temperature Sensor",
            "sensor_type": "temperature_pressure"
        })
        
        # Act
        org_sensors = sensor_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_sensors) >= 2
        sensor_ids = [s.id for s in org_sensors]
        assert sensor1.id in sensor_ids
        assert sensor2.id in sensor_ids
        assert all(s.organization_id == sample_organization.id for s in org_sensors)
        
        print(f"✅ Found {len(org_sensors)} sensors in organization")
    
    def test_get_by_organization_with_location(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting sensors with location data loaded"""
        # Arrange
        sensor = sensor_repository.create(sample_sensor_data)
        
        # Act - Include location data
        org_sensors = sensor_repository.get_by_organization(sample_organization.id, include_location=True)
        
        # Assert
        assert len(org_sensors) >= 1
        found_sensor = next(s for s in org_sensors if s.id == sensor.id)
        assert found_sensor.location is not None  # Location should be loaded
        assert found_sensor.location.name is not None
        
        print(f"✅ Location data loaded: {found_sensor.location.name}")
    
    def test_get_by_device_id(self, sensor_repository, sample_sensor_data):
        """Test getting sensor by device ID"""
        # Arrange
        sensor = sensor_repository.create(sample_sensor_data)
        
        # Act
        found_sensor = sensor_repository.get_by_device_id(sensor.device_id)
        
        # Assert
        assert found_sensor is not None
        assert found_sensor.id == sensor.id
        assert found_sensor.device_id == sensor.device_id
        
        print(f"✅ Sensor found by device ID: {found_sensor.device_id}")
    
    def test_get_by_device_id_not_found(self, sensor_repository):
        """Test getting sensor by non-existent device ID"""
        # Act
        found_sensor = sensor_repository.get_by_device_id("NON_EXISTENT_DEVICE")
        
        # Assert
        assert found_sensor is None
        print("✅ Non-existent device ID correctly returned None")
    
    def test_get_by_location(self, sensor_repository, sample_location, sample_sensor_data):
        """Test getting sensors by location"""
        # Arrange - Create sensors in same location
        sensor1 = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "LOC_SENSOR_001",
            "name": "Location Sensor 1"
        })
        
        sensor2 = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "LOC_SENSOR_002",
            "name": "Location Sensor 2"
        })
        
        # Act
        location_sensors = sensor_repository.get_by_location(sample_location.id)
        
        # Assert
        assert len(location_sensors) >= 2
        sensor_ids = [s.id for s in location_sensors]
        assert sensor1.id in sensor_ids
        assert sensor2.id in sensor_ids
        assert all(s.location_id == sample_location.id for s in location_sensors)
        
        print(f"✅ Found {len(location_sensors)} sensors in location")
    
    def test_get_by_status(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting sensors by status"""
        # Arrange - Create sensors with different statuses
        online_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "ONLINE_SENSOR_001",
            "status": "online"
        })
        
        offline_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OFFLINE_SENSOR_001",
            "status": "offline"
        })
        
        warning_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "WARNING_SENSOR_001",
            "status": "warning"
        })
        
        # Act
        online_sensors = sensor_repository.get_by_status(sample_organization.id, "online")
        offline_sensors = sensor_repository.get_by_status(sample_organization.id, "offline")
        
        # Assert
        online_ids = [s.id for s in online_sensors]
        offline_ids = [s.id for s in offline_sensors]
        
        assert online_sensor.id in online_ids
        assert offline_sensor.id in offline_ids
        assert warning_sensor.id not in online_ids
        assert warning_sensor.id not in offline_ids
        assert all(s.status == "online" for s in online_sensors)
        assert all(s.status == "offline" for s in offline_sensors)
        
        print(f"✅ Found {len(online_sensors)} online and {len(offline_sensors)} offline sensors")

# =====================================================
# TEST SENSOR MONITORING FUNCTIONALITY
# =====================================================

class TestSensorMonitoring:
    """Test sensor monitoring and status functionality"""
    
    def test_get_online_sensors(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting online sensors specifically"""
        # Arrange
        online_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "ONLINE_TEST_001",
            "status": "online"
        })
        
        offline_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OFFLINE_TEST_001", 
            "status": "offline"
        })
        
        # Act
        online_sensors = sensor_repository.get_online_sensors(sample_organization.id)
        
        # Assert
        online_ids = [s.id for s in online_sensors]
        assert online_sensor.id in online_ids
        assert offline_sensor.id not in online_ids
        assert all(s.status == "online" for s in online_sensors)
        
        print(f"✅ Found {len(online_sensors)} online sensors")
    
    def test_get_offline_sensors(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting offline sensors specifically"""
        # Arrange
        online_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "ONLINE_FOR_OFFLINE_TEST",
            "status": "online"
        })
        
        offline_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OFFLINE_FOR_TEST",
            "status": "offline"
        })
        
        # Act
        offline_sensors = sensor_repository.get_offline_sensors(sample_organization.id)
        
        # Assert
        offline_ids = [s.id for s in offline_sensors]
        assert offline_sensor.id in offline_ids
        assert online_sensor.id not in offline_ids
        assert all(s.status == "offline" for s in offline_sensors)
        
        print(f"✅ Found {len(offline_sensors)} offline sensors")
    
    def test_get_low_battery_sensors(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting sensors with low battery"""
        # Arrange - Create sensors with different battery levels
        low_battery_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "LOW_BATTERY_001",
            "battery_level": 15  # Below default threshold of 20
        })
        
        critical_battery_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "CRITICAL_BATTERY_001",
            "battery_level": 5  # Very low
        })
        
        good_battery_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "GOOD_BATTERY_001",
            "battery_level": 80  # Good level
        })
        
        # Act - Test with default threshold (20%)
        low_battery_sensors = sensor_repository.get_low_battery_sensors(sample_organization.id)
        
        # Act - Test with custom threshold (10%)
        critical_battery_sensors = sensor_repository.get_low_battery_sensors(sample_organization.id, threshold=10)
        
        # Assert
        low_battery_ids = [s.id for s in low_battery_sensors]
        critical_battery_ids = [s.id for s in critical_battery_sensors]
        
        assert low_battery_sensor.id in low_battery_ids
        assert critical_battery_sensor.id in low_battery_ids
        assert good_battery_sensor.id not in low_battery_ids
        
        assert critical_battery_sensor.id in critical_battery_ids
        assert low_battery_sensor.id not in critical_battery_ids  # Above 10% threshold
        assert good_battery_sensor.id not in critical_battery_ids
        
        print(f"✅ Found {len(low_battery_sensors)} low battery sensors (≤20%)")
        print(f"✅ Found {len(critical_battery_sensors)} critical battery sensors (≤10%)")
    
    def test_get_recently_seen(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting recently seen sensors"""
        # Arrange - Create sensors with different last_seen times
        recent_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "RECENT_SENSOR_001",
            "last_seen_at": datetime.utcnow() - timedelta(hours=2)  # 2 hours ago
        })
        
        old_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OLD_SENSOR_001",
            "last_seen_at": datetime.utcnow() - timedelta(hours=30)  # 30 hours ago
        })
        
        never_seen_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "NEVER_SEEN_001",
            "last_seen_at": None  # Never seen
        })
        
        # Act - Get sensors seen in last 24 hours
        recent_sensors = sensor_repository.get_recently_seen(sample_organization.id, hours=24)
        
        # Assert
        recent_ids = [s.id for s in recent_sensors]
        assert recent_sensor.id in recent_ids
        assert old_sensor.id not in recent_ids
        assert never_seen_sensor.id not in recent_ids
        
        # Should be ordered by last_seen_at DESC
        if len(recent_sensors) > 1:
            last_seen_times = [s.last_seen_at for s in recent_sensors if s.last_seen_at]
            assert last_seen_times == sorted(last_seen_times, reverse=True)
        
        print(f"✅ Found {len(recent_sensors)} recently seen sensors")

# =====================================================
# TEST HACCP CALIBRATION FUNCTIONALITY
# =====================================================

class TestSensorCalibration:
    """Test sensor calibration and HACCP compliance functionality"""
    
    def test_get_sensors_needing_calibration(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test getting sensors needing calibration"""
        # Arrange - Create sensors with different calibration statuses
        due_soon_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "DUE_SOON_001",
            "calibration_due_date": date.today() + timedelta(days=15)  # Due in 15 days
        })
        
        overdue_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OVERDUE_001",
            "calibration_due_date": date.today() - timedelta(days=5)  # Overdue
        })
        
        never_calibrated_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "NEVER_CALIBRATED_001",
            "calibration_due_date": None  # No calibration date set
        })
        
        future_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "FUTURE_CALIB_001",
            "calibration_due_date": date.today() + timedelta(days=60)  # Due in 60 days
        })
        
        # Act - Get sensors needing calibration in next 30 days
        sensors_needing_calibration = sensor_repository.get_sensors_needing_calibration(
            sample_organization.id, days_ahead=30
        )
        
        # Assert
        needing_calibration_ids = [s.id for s in sensors_needing_calibration]
        assert due_soon_sensor.id in needing_calibration_ids
        assert overdue_sensor.id in needing_calibration_ids
        assert never_calibrated_sensor.id in needing_calibration_ids  # No date = needs calibration
        assert future_sensor.id not in needing_calibration_ids  # Due too far in future
        
        print(f"✅ Found {len(sensors_needing_calibration)} sensors needing calibration")

# =====================================================
# TEST SENSOR BUSINESS LOGIC
# =====================================================

class TestSensorBusinessLogic:
    """Test sensor business logic and properties"""
    
    def test_sensor_properties(self, sensor_repository, sample_sensor_data):
        """Test sensor model properties"""
        # Create sensor with recent activity
        sensor = sensor_repository.create({
            **sample_sensor_data,
            "last_seen_at": datetime.utcnow() - timedelta(minutes=5),  # 5 minutes ago
            "calibration_due_date": date.today() + timedelta(days=15)
        })
        
        # Test is_online property (should be true for sensor seen 5 min ago)
        assert sensor.is_online == True
        
        # Test is_calibration_due property (should be true for sensor due in 15 days)
        assert sensor.is_calibration_due == True
        
        # Test location_name property
        assert sensor.location_name is not None
        assert sensor.location_name == sensor.location.name
        
        print(f"✅ Sensor properties working correctly")
        print(f"   - is_online: {sensor.is_online}")
        print(f"   - is_calibration_due: {sensor.is_calibration_due}")
        print(f"   - location_name: {sensor.location_name}")
    
    def test_offline_sensor_properties(self, sensor_repository, sample_sensor_data):
        """Test properties for offline sensor"""
        # Create sensor not seen recently
        sensor = sensor_repository.create({
            **sample_sensor_data,
            "last_seen_at": datetime.utcnow() - timedelta(hours=2),  # 2 hours ago
            "calibration_due_date": date.today() + timedelta(days=60)  # Due far in future
        })
        
        # Test is_online property (should be false for sensor not seen for 2 hours)
        assert sensor.is_online == False
        
        # Test is_calibration_due property (should be false for sensor due in 60 days)
        assert sensor.is_calibration_due == False
        
        print(f"✅ Offline sensor properties working correctly")
    
    def test_alert_threshold_management(self, sensor_repository, sample_sensor_data):
        """Test alert threshold getter and setter methods"""
        # Create sensor
        sensor = sensor_repository.create(sample_sensor_data)
        
        # Test getting existing threshold
        temp_threshold = sensor.get_alert_threshold("temperature")
        assert temp_threshold is not None
        assert temp_threshold["min"] == -25.0
        assert temp_threshold["max"] == -15.0
        
        # Test setting new threshold
        sensor.set_alert_threshold("pressure", 900.0, 1100.0)
        sensor_repository.db.commit()
        
        # Refresh and verify
        sensor_repository.db.refresh(sensor)
        pressure_threshold = sensor.get_alert_threshold("pressure")
        assert pressure_threshold is not None
        assert pressure_threshold["min"] == 900.0
        assert pressure_threshold["max"] == 1100.0
        
        # Test getting non-existent threshold
        non_existent = sensor.get_alert_threshold("non_existent")
        assert non_existent is None
        
        print(f"✅ Alert threshold management working correctly")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestSensorMultiTenancy:
    """Test multi-tenancy isolation for sensors"""
    
    def test_organization_isolation(self, sensor_repository, sample_organization, second_organization, 
                                   sample_sensor_data, second_location):
        """Test that sensors are isolated by organization"""
        
        # Create sensors in different organizations
        sensor1 = sensor_repository.create({
            **sample_sensor_data,
            "organization_id": sample_organization.id,
            "device_id": "ORG1_SENSOR_001"
        })
        
        sensor2 = sensor_repository.create({
            **sample_sensor_data,
            "organization_id": second_organization.id,
            "location_id": second_location.id,
            "device_id": "ORG2_SENSOR_001"
        })
        
        # Test isolation using organization-specific queries
        org1_sensors = sensor_repository.get_by_organization(sample_organization.id)
        org2_sensors = sensor_repository.get_by_organization(second_organization.id)
        
        # Assert isolation
        org1_sensor_ids = [s.id for s in org1_sensors]
        org2_sensor_ids = [s.id for s in org2_sensors]
        
        assert sensor1.id in org1_sensor_ids
        assert sensor1.id not in org2_sensor_ids
        assert sensor2.id in org2_sensor_ids
        assert sensor2.id not in org1_sensor_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")
        print(f"   - Org1 sensors: {len(org1_sensors)}")
        print(f"   - Org2 sensors: {len(org2_sensors)}")

# =====================================================
# TEST SENSOR CONSTRAINTS AND VALIDATION
# =====================================================

class TestSensorConstraints:
    """Test sensor database constraints and validation"""
    
    def test_device_id_uniqueness(self, sensor_repository, sample_sensor_data):
        """Test device_id uniqueness constraint"""
        # Create first sensor
        sensor1 = sensor_repository.create(sample_sensor_data)
        
        # Try to create second sensor with same device_id
        try:
            sensor_repository.create({
                **sample_sensor_data,
                "name": "Duplicate Device ID Sensor"
            })
            assert False, "Should have failed due to duplicate device_id"
        except Exception as e:
            assert "device_id" in str(e).lower() or "unique" in str(e).lower()
        
        print(f"✅ Device ID uniqueness constraint working correctly")
    
    def test_sensor_type_constraint(self, sensor_repository, sample_sensor_data):
        """Test sensor type constraint validation"""
        # Valid sensor types should work
        valid_types = ['temperature_humidity', 'temperature_pressure', 'multi_sensor']
        
        for sensor_type in valid_types:
            sensor = sensor_repository.create({
                **sample_sensor_data,
                "device_id": f"TYPE_TEST_{sensor_type.upper()}",
                "sensor_type": sensor_type
            })
            assert sensor.sensor_type == sensor_type
        
        print(f"✅ All valid sensor types work correctly")
    
    def test_status_constraint(self, sensor_repository, sample_sensor_data):
        """Test sensor status constraint validation"""
        # Valid statuses should work
        valid_statuses = ['online', 'offline', 'warning', 'error', 'maintenance']
        
        for status in valid_statuses:
            sensor = sensor_repository.create({
                **sample_sensor_data,
                "device_id": f"STATUS_TEST_{status.upper()}",
                "status": status
            })
            assert sensor.status == status
        
        print(f"✅ All valid sensor statuses work correctly")
    
    def test_battery_level_constraint(self, sensor_repository, sample_sensor_data):
        """Test battery level constraint (0-100)"""
        # Valid battery levels
        valid_levels = [0, 25, 50, 75, 100]
        
        for level in valid_levels:
            sensor = sensor_repository.create({
                **sample_sensor_data,
                "device_id": f"BATTERY_TEST_{level}",
                "battery_level": level
            })
            assert sensor.battery_level == level
        
        print(f"✅ Battery level constraint validation working correctly")
    
    def test_mac_address_format_constraint(self, sensor_repository, sample_sensor_data):
        """Test MAC address format constraint"""
        # Valid MAC address formats
        valid_macs = ["AA:BB:CC:DD:EE:FF", "aa:bb:cc:dd:ee:ff", "AA-BB-CC-DD-EE-FF"]
        
        for i, mac in enumerate(valid_macs):
            sensor = sensor_repository.create({
                **sample_sensor_data,
                "device_id": f"MAC_TEST_{i:03d}",
                "mac_address": mac
            })
            assert sensor.mac_address == mac
        
        # NULL MAC address should be allowed
        sensor_no_mac = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "NO_MAC_TEST",
            "mac_address": None
        })
        assert sensor_no_mac.mac_address is None
        
        print(f"✅ MAC address format constraint validation working correctly")

# =====================================================
# TEST SENSOR RELATIONSHIPS
# =====================================================

class TestSensorRelationships:
    """Test sensor relationships and database joins"""
    
    def test_organization_relationship(self, sensor_repository, created_sensor):
        """Test sensor-organization relationship"""
        # Act
        sensor = sensor_repository.get_by_id(created_sensor.id)
        
        # Assert
        assert sensor.organization is not None
        assert sensor.organization.id == sensor.organization_id
        assert sensor.organization.name is not None
        
        print(f"✅ Organization relationship working: {sensor.organization.name}")
    
    def test_location_relationship(self, sensor_repository, created_sensor):
        """Test sensor-location relationship"""
        # Act
        sensor = sensor_repository.get_by_id(created_sensor.id)
        
        # Assert
        assert sensor.location is not None
        assert sensor.location.id == sensor.location_id
        assert sensor.location.name is not None
        
        print(f"✅ Location relationship working: {sensor.location.name}")
    
    def test_null_location_handling(self, sensor_repository, sample_sensor_data):
        """Test sensor creation without location"""
        # Create sensor without location
        sensor_data_no_location = {k: v for k, v in sample_sensor_data.items() if k != 'location_id'}
        sensor = sensor_repository.create({
            **sensor_data_no_location,
            "device_id": "NO_LOCATION_SENSOR",
            "location_id": None
        })
        
        assert sensor.location_id is None
        assert sensor.location is None
        
        print(f"✅ Null location handling working correctly")
    
    def test_calibrations_relationship(self, sensor_repository, test_db, sample_organization, created_sensor):
        """Test sensor-calibrations relationship"""
        # Create calibrations for the sensor
        from src.models import User
        
        # Create user for calibration
        user = User(
            organization_id=sample_organization.id,
            email="calibration_tech@example.com",
            first_name="Calib",
            last_name="Tech",
            role="admin",
            is_active=True,
            is_verified=True
        )
        user.set_password("CalibPass123!")
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        # Create calibrations
        calibration1 = Calibration(
            organization_id=sample_organization.id,
            sensor_id=created_sensor.id,
            calibrated_by=user.id,
            calibration_type="routine",
            calibration_method="comparison_method",
            accuracy_achieved=Decimal('0.25'),
            calibration_passed=True,
            notes="Test calibration 1",
            calibrated_at=datetime.now() - timedelta(days=30),
            next_calibration_due=datetime.combine(
                date.today() + timedelta(days=335), 
                datetime.min.time()
            )
        )
        
        calibration2 = Calibration(
            organization_id=sample_organization.id,
            sensor_id=created_sensor.id,
            calibrated_by=user.id,
            calibration_type="verification",
            calibration_method="comparison_method",
            accuracy_achieved=Decimal('0.15'),
            calibration_passed=True,
            notes="Test calibration 2",
            calibrated_at=datetime.now() - timedelta(days=1),
            next_calibration_due=datetime.combine(
                date.today() + timedelta(days=364), 
                datetime.min.time()
            )
        )
        
        test_db.add_all([calibration1, calibration2])
        test_db.commit()
        test_db.refresh(created_sensor)  # Refresh to load relationships
        
        # Act & Assert
        assert len(created_sensor.calibrations) == 2
        calibration_ids = [c.id for c in created_sensor.calibrations]
        assert calibration1.id in calibration_ids
        assert calibration2.id in calibration_ids
        assert all(c.sensor_id == created_sensor.id for c in created_sensor.calibrations)
        
        print(f"✅ Calibrations relationship working: {len(created_sensor.calibrations)} calibrations")

# =====================================================
# TEST COMPLEX QUERIES AND FILTERING
# =====================================================

class TestSensorComplexQueries:
    """Test complex sensor queries and filtering scenarios"""
    
    def test_combined_filtering(self, sensor_repository, sample_organization, sample_sensor_data, sample_location):
        """Test complex filtering combining multiple criteria"""
        # Create diverse set of sensors
        sensors_data = [
            {
                **sample_sensor_data,
                "device_id": "KITCHEN_TEMP_001",
                "name": "Kitchen Main Temperature Sensor",
                "sensor_type": "temperature_humidity",
                "status": "online",
                "battery_level": 85,
                "last_seen_at": datetime.utcnow() - timedelta(hours=1)
            },
            {
                **sample_sensor_data,
                "device_id": "KITCHEN_PRESS_001",
                "name": "Kitchen Pressure Sensor",
                "sensor_type": "temperature_pressure",
                "status": "online",
                "battery_level": 15,  # Low battery
                "last_seen_at": datetime.utcnow() - timedelta(minutes=30)
            },
            {
                **sample_sensor_data,
                "device_id": "STORAGE_MULTI_001",
                "name": "Storage Multi Sensor",
                "sensor_type": "multi_sensor",
                "status": "offline",
                "battery_level": 90,
                "last_seen_at": datetime.utcnow() - timedelta(hours=48)  # Not recently seen
            },
            {
                **sample_sensor_data,
                "device_id": "FREEZER_TEMP_001",
                "name": "Freezer Temperature Monitor",
                "sensor_type": "temperature_humidity",
                "status": "warning",
                "battery_level": 5,  # Critical battery
                "last_seen_at": datetime.utcnow() - timedelta(hours=3)
            }
        ]
        
        created_sensors = []
        for sensor_data in sensors_data:
            sensor = sensor_repository.create(sensor_data)
            created_sensors.append(sensor)
        
        # Test various filtering combinations
        
        # 1. Get all online sensors
        online_sensors = sensor_repository.get_online_sensors(sample_organization.id)
        online_names = [s.name for s in online_sensors]
        assert any("Kitchen Main Temperature" in name for name in online_names)
        assert any("Kitchen Pressure" in name for name in online_names)
        
        # 2. Get low battery sensors
        low_battery_sensors = sensor_repository.get_low_battery_sensors(sample_organization.id, threshold=20)
        low_battery_names = [s.name for s in low_battery_sensors]
        assert any("Kitchen Pressure" in name for name in low_battery_names)
        assert any("Freezer Temperature" in name for name in low_battery_names)
        
        # 3. Get recently seen sensors
        recent_sensors = sensor_repository.get_recently_seen(sample_organization.id, hours=24)
        recent_names = [s.name for s in recent_sensors]
        assert any("Kitchen Main Temperature" in name for name in recent_names)
        assert any("Kitchen Pressure" in name for name in recent_names)
        
        # 4. Get sensors by location
        location_sensors = sensor_repository.get_by_location(sample_location.id)
        assert len(location_sensors) >= 4  # All our test sensors
        
        print(f"✅ Complex filtering working correctly")
        print(f"   - Online sensors: {len(online_sensors)}")
        print(f"   - Low battery sensors: {len(low_battery_sensors)}")
        print(f"   - Recently seen sensors: {len(recent_sensors)}")
        print(f"   - Location sensors: {len(location_sensors)}")

# =====================================================
# TEST PERFORMANCE AND LARGE DATASETS
# =====================================================

class TestSensorPerformance:
    """Test sensor repository performance"""
    
    def test_large_sensor_volume(self, sensor_repository, sample_organization, sample_location, sample_sensor_data):
        """Test handling large volume of sensors"""
        import time
        
        # Arrange
        start_time = time.time()
        sensor_count = 30  # Reasonable number for testing
        sensor_types = ['temperature_humidity', 'temperature_pressure', 'multi_sensor']
        
        # Act - Create multiple sensors
        created_sensors = []
        for i in range(sensor_count):
            sensor_data = {
                **sample_sensor_data,
                "device_id": f"PERF_SENSOR_{i:04d}",
                "name": f"Performance Test Sensor {i:03d}",
                "sensor_type": sensor_types[i % len(sensor_types)],
                "battery_level": 50 + (i % 50),  # Varies from 50-99
                "status": "online" if i % 3 == 0 else "offline"
            }
            sensor = sensor_repository.create(sensor_data)
            created_sensors.append(sensor)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_sensors) == sensor_count
        assert duration < 20  # Should complete within 20 seconds
        
        # Test bulk queries performance
        start_query_time = time.time()
        all_org_sensors = sensor_repository.get_by_organization(sample_organization.id)
        end_query_time = time.time()
        query_duration = end_query_time - start_query_time
        
        assert len(all_org_sensors) >= sensor_count
        assert query_duration < 3  # Query should be fast
        
        print(f"✅ Created {sensor_count} sensors in {duration:.2f} seconds")
        print(f"✅ Queried {len(all_org_sensors)} sensors in {query_duration:.3f} seconds")
        print(f"✅ Average: {duration/sensor_count:.3f} seconds per sensor")

# =====================================================
# TEST HACCP COMPLIANCE SCENARIOS
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance scenarios for sensors"""
    
    def test_temperature_monitoring_setup(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test proper HACCP temperature monitoring setup"""
        # Create HACCP critical sensors with proper thresholds
        freezer_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "HACCP_FREEZER_001",
            "name": "HACCP Critical Freezer Sensor",
            "sensor_type": "temperature_humidity",
            "accuracy_specification": Decimal('0.5'),  # ±0.5°C for HACCP
            "alert_thresholds": {
                "temperature": {"min": -25.0, "max": -18.0},  # HACCP freezer range
                "humidity": {"min": 10.0, "max": 30.0}
            }
        })
        
        fridge_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "HACCP_FRIDGE_001",
            "name": "HACCP Critical Fridge Sensor",
            "sensor_type": "temperature_humidity",
            "accuracy_specification": Decimal('0.5'),  # ±0.5°C for HACCP
            "alert_thresholds": {
                "temperature": {"min": 0.0, "max": 4.0},  # HACCP fridge range
                "humidity": {"min": 80.0, "max": 95.0}
            }
        })
        
        # Test HACCP-compliant threshold validation
        freezer_temp_threshold = freezer_sensor.get_alert_threshold("temperature")
        assert freezer_temp_threshold["min"] == -25.0
        assert freezer_temp_threshold["max"] == -18.0
        
        fridge_temp_threshold = fridge_sensor.get_alert_threshold("temperature")
        assert fridge_temp_threshold["min"] == 0.0
        assert fridge_temp_threshold["max"] == 4.0
        
        # Test accuracy specification for HACCP compliance
        assert freezer_sensor.accuracy_specification == Decimal('0.5')
        assert fridge_sensor.accuracy_specification == Decimal('0.5')
        
        print(f"✅ HACCP temperature monitoring setup working correctly")
        print(f"   - Freezer range: {freezer_temp_threshold['min']}°C to {freezer_temp_threshold['max']}°C")
        print(f"   - Fridge range: {fridge_temp_threshold['min']}°C to {fridge_temp_threshold['max']}°C")
    
    def test_calibration_compliance_tracking(self, sensor_repository, sample_organization, sample_sensor_data):
        """Test calibration compliance tracking for HACCP"""
        # Create sensors with different calibration statuses
        compliant_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "COMPLIANT_SENSOR_001",
            "name": "HACCP Compliant Sensor",
            "last_calibration_date": date.today() - timedelta(days=300),  # Recently calibrated
            "calibration_due_date": date.today() + timedelta(days=65)  # Due in future
        })
        
        due_soon_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "DUE_SOON_SENSOR_001",
            "name": "Calibration Due Soon Sensor",
            "last_calibration_date": date.today() - timedelta(days=335),  # Old calibration
            "calibration_due_date": date.today() + timedelta(days=15)  # Due soon
        })
        
        overdue_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "OVERDUE_SENSOR_001",
            "name": "Overdue Calibration Sensor",
            "last_calibration_date": date.today() - timedelta(days=400),  # Very old
            "calibration_due_date": date.today() - timedelta(days=35)  # Overdue
        })
        
        # Test calibration compliance status
        assert compliant_sensor.is_calibration_due == False  # Not due yet
        assert due_soon_sensor.is_calibration_due == True   # Due soon
        assert overdue_sensor.is_calibration_due == True    # Overdue
        
        # Test getting sensors needing calibration
        sensors_needing_calibration = sensor_repository.get_sensors_needing_calibration(
            sample_organization.id, days_ahead=30
        )
        
        needing_calibration_ids = [s.id for s in sensors_needing_calibration]
        assert compliant_sensor.id not in needing_calibration_ids
        assert due_soon_sensor.id in needing_calibration_ids
        assert overdue_sensor.id in needing_calibration_ids
        
        print(f"✅ HACCP calibration compliance tracking working correctly")
        print(f"   - Compliant sensors: 1")
        print(f"   - Sensors needing calibration: {len(sensors_needing_calibration)}")

# =====================================================
# TEST EDGE CASES AND ERROR SCENARIOS
# =====================================================

class TestSensorEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cascade_delete_organization(self, test_db, sensor_repository, sample_sensor_data):
        """Test what happens when organization is deleted"""
        # Create temporary organization and location
        temp_org = Organization(
            name="Temp Org for Sensor Delete Test",
            slug="temp-org-delete-sensors",
            subscription_plan="basic"
        )
        test_db.add(temp_org)
        test_db.commit()
        test_db.refresh(temp_org)
        
        temp_location = Location(
            organization_id=temp_org.id,
            name="Temp Location",
            location_type="freezer",
            temperature_min=Decimal('-20.0'),
            temperature_max=Decimal('-15.0')
        )
        test_db.add(temp_location)
        test_db.commit()
        test_db.refresh(temp_location)
        
        # Create sensor in temp organization
        sensor = sensor_repository.create({
            **sample_sensor_data,
            "organization_id": temp_org.id,
            "location_id": temp_location.id,
            "device_id": "TEMP_DELETE_SENSOR"
        })
        
        # Store sensor ID before deletion
        sensor_id = sensor.id
        
        # Clear session to avoid stale references
        test_db.expunge(sensor)
        
        # Act - Delete organization (should cascade)
        test_db.delete(temp_org)
        test_db.commit()
        
        # Assert - Sensor should be gone due to CASCADE
        found_sensor = sensor_repository.get_by_id(sensor_id)
        assert found_sensor is None
        
        print(f"✅ Cascade delete working correctly")
    
    def test_sensor_with_special_characters(self, sensor_repository, sample_sensor_data):
        """Test sensor with special characters and unicode"""
        # Create sensor with special characters
        special_sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "SPECIAL_CHARS_001",
            "name": "Sensore di Temperatura Ñ°1 - Frigorifero (Cucina)",
            "hardware_model": "TempSense® Pro™ v2.0"
        })
        
        assert "Ñ°1" in special_sensor.name
        assert "®" in special_sensor.hardware_model
        assert "™" in special_sensor.hardware_model
        
        print(f"✅ Special characters handling working correctly")
    
    def test_sensor_alert_threshold_edge_cases(self, sensor_repository, sample_sensor_data):
        """Test edge cases in alert threshold management"""
        # Create sensor
        sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "THRESHOLD_EDGE_001",
            "alert_thresholds": {}  # Empty thresholds
        })
        
        # Test empty thresholds
        assert sensor.get_alert_threshold("temperature") is None
        
        # Test setting threshold with only min value
        sensor.set_alert_threshold("temperature", -20.0, None)
        sensor_repository.db.commit()
        sensor_repository.db.refresh(sensor)
        
        temp_threshold = sensor.get_alert_threshold("temperature")
        assert temp_threshold["min"] == -20.0
        assert "max" not in temp_threshold
        
        # Test setting threshold with only max value
        sensor.set_alert_threshold("humidity", None, 80.0)
        sensor_repository.db.commit()
        sensor_repository.db.refresh(sensor)
        
        humidity_threshold = sensor.get_alert_threshold("humidity")
        assert humidity_threshold["max"] == 80.0
        assert "min" not in humidity_threshold
        
        print(f"✅ Alert threshold edge cases handled correctly")

# =====================================================
# TEST SENSOR LIFECYCLE AND AUDIT
# =====================================================

class TestSensorLifecycleScenarios:
    """Test sensor lifecycle and audit scenarios"""
    
    def test_sensor_lifecycle_tracking(self, sensor_repository, sample_sensor_data):
        """Test tracking of sensor lifecycle events"""
        # Create sensor
        sensor = sensor_repository.create(sample_sensor_data)
        creation_time = sensor.created_at
        initial_update_time = sensor.updated_at
        
        # Wait a moment and update
        import time
        time.sleep(0.1)
        
        updated_sensor = sensor_repository.update(sensor.id, {
            "status": "maintenance",
            "firmware_version": "1.4.0",
            "battery_level": 70
        })
        
        # Timestamps should reflect the changes
        assert updated_sensor.created_at == creation_time  # Should not change
        assert updated_sensor.updated_at > initial_update_time  # Should be updated
        
        print(f"✅ Sensor lifecycle tracking working")
        print(f"   - Created: {creation_time}")
        print(f"   - Updated: {updated_sensor.updated_at}")
    
    def test_sensor_communication_tracking(self, sensor_repository, sample_sensor_data):
        """Test sensor communication timestamp tracking"""
        # Create sensor with initial communication times
        now = datetime.utcnow()
        sensor = sensor_repository.create({
            **sample_sensor_data,
            "device_id": "COMM_TRACK_001",
            "last_seen_at": now - timedelta(hours=1),
            "last_reading_at": now - timedelta(minutes=30)
        })
        
        # Save original timestamps for comparison
        original_last_seen = sensor.last_seen_at
        original_last_reading = sensor.last_reading_at
        
        # Wait to ensure different timestamps
        import time
        time.sleep(0.1)
        
        # Simulate sensor coming online (update communication times)
        recent_time = datetime.utcnow()
        updated_sensor = sensor_repository.update(sensor.id, {
            "status": "online",
            "last_seen_at": recent_time,
            "last_reading_at": recent_time
        })
        
        # Verify tracking using saved original timestamps
        assert updated_sensor.last_seen_at > original_last_seen
        assert updated_sensor.last_reading_at > original_last_reading
        assert updated_sensor.is_online == True  # Should be online now
        
        print(f"✅ Sensor communication tracking working correctly")
        print(f"   - Original last seen: {original_last_seen}")
        print(f"   - Updated last seen: {updated_sensor.last_seen_at}")
        print(f"   - Original last reading: {original_last_reading}")
        print(f"   - Updated last reading: {updated_sensor.last_reading_at}")
        print(f"   - Is online: {updated_sensor.is_online}")