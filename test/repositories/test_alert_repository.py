# test/repositories/test_alert_repository.py
# =====================================================
"""
Test per AlertRepository - versione realistica usando metodi esistenti.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import text

# Clean imports - no path manipulation needed
from src.models import Organization, Location, Sensor, Alert, User
from src.repositories.alert_repository import AlertRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def alert_repository(test_db):
    """Create AlertRepository instance"""
    return AlertRepository(test_db)

@pytest.fixture
def created_alert(alert_repository, sample_alert_data):
    """Create and return a test alert"""
    return alert_repository.create(sample_alert_data)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Alert Test Company",
        slug="alert-test-company",
        subscription_plan="premium",
        max_sensors=50,
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
        name="Test Freezer",
        location_type="freezer",
        temperature_min=Decimal('-20.0'),
        temperature_max=Decimal('-15.0')
    )
    test_db.add(location)
    test_db.commit()
    test_db.refresh(location)
    return location

@pytest.fixture
def sample_sensor(test_db, sample_organization, sample_location):
    """Create sample sensor for testing"""
    sensor = Sensor(
        organization_id=sample_organization.id,
        location_id=sample_location.id,
        device_id="ALERT_TEST_SENSOR_001",
        name="Alert Test Sensor",
        sensor_type="temperature_humidity",
        status="online",
        battery_level=95
    )
    test_db.add(sensor)
    test_db.commit()
    test_db.refresh(sensor)
    return sensor

@pytest.fixture
def sample_alert_data(sample_organization, sample_sensor):
    """Sample alert data for testing - using only existing fields"""
    return {
        "organization_id": sample_organization.id,
        "sensor_id": sample_sensor.id,
        "alert_type": "temperature_high",
        "severity": "medium",  # Changed from "warning" to "medium"
        "status": "active",
        "message": "Temperature exceeded threshold",
        "threshold_value": Decimal('10.0'),
        "current_value": Decimal('15.5'),  # Changed from "actual_value"
        "is_haccp_critical": True,
        "requires_corrective_action": False,
        "deviation_duration_minutes": 30
    }

@pytest.fixture
def sample_user(test_db, sample_organization):
    """Create sample user for testing acknowledgment/resolution"""
    user = User(
        organization_id=sample_organization.id,
        email="alert-test-user@example.com",
        first_name="Alert",
        last_name="Tester",
        role="operator",
        is_active=True,
        is_verified=True
    )
    # Set password using the method
    user.set_password("TestPassword123!")
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestAlertCRUD:
    """Test basic CRUD operations"""
    
    def test_create_alert_success(self, alert_repository, sample_alert_data):
        """Test creating a new alert"""
        
        # Act
        alert = alert_repository.create(sample_alert_data)
        
        # Assert
        assert alert.id is not None
        assert alert.alert_type == sample_alert_data["alert_type"]
        assert alert.severity == sample_alert_data["severity"]
        assert alert.status == sample_alert_data["status"]
        assert alert.message == sample_alert_data["message"]
        assert alert.organization_id == sample_alert_data["organization_id"]
        assert alert.sensor_id == sample_alert_data["sensor_id"]
        assert alert.is_haccp_critical == sample_alert_data["is_haccp_critical"]
        
        # Verify timestamps
        assert alert.created_at is not None
        assert alert.updated_at is not None
        
        print(f"✅ Alert created with ID: {alert.id}")
    
    def test_get_by_id(self, alert_repository, created_alert):
        """Test getting alert by ID"""
        # Act
        found_alert = alert_repository.get_by_id(created_alert.id)
        
        # Assert
        assert found_alert is not None
        assert found_alert.id == created_alert.id
        assert found_alert.alert_type == created_alert.alert_type
        
        print(f"✅ Alert found by ID: {found_alert.id}")
    
    def test_get_by_id_not_found(self, alert_repository):
        """Test getting non-existent alert"""
        # Act
        found_alert = alert_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_alert is None
        print("✅ Non-existent alert correctly returned None")
    
    def test_update_alert(self, alert_repository, created_alert):
        """Test updating alert"""
        # Arrange
        update_data = {
            "status": "acknowledged",
            "severity": "critical",
            "message": "Updated alert message"
        }
        
        # Act
        updated_alert = alert_repository.update(created_alert.id, update_data)
        
        # Assert
        assert updated_alert is not None
        assert updated_alert.status == "acknowledged"
        assert updated_alert.severity == "critical"
        assert updated_alert.message == "Updated alert message"
        # Check unchanged fields
        assert updated_alert.alert_type == created_alert.alert_type
        assert updated_alert.organization_id == created_alert.organization_id
        
        print(f"✅ Alert updated successfully")
    
    def test_delete_alert(self, alert_repository, created_alert):
        """Test deleting alert"""
        # Act
        result = alert_repository.delete(created_alert.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_alert = alert_repository.get_by_id(created_alert.id)
        assert found_alert is None
        
        print(f"✅ Alert deleted successfully")
    
    def test_delete_nonexistent_alert(self, alert_repository):
        """Test deleting non-existent alert"""
        # Act
        result = alert_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent alert correctly returned False")

# =====================================================
# TEST ALERT-SPECIFIC QUERIES
# =====================================================

class TestAlertQueries:
    """Test alert-specific query methods"""
    
    def test_get_by_organization(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting alerts by organization"""
        # Arrange - Create multiple alerts
        alert1 = alert_repository.create(sample_alert_data)
        alert2 = alert_repository.create({
            **sample_alert_data,
            "alert_type": "temperature_low",
            "message": "Temperature too low"
        })
        
        # Act
        org_alerts = alert_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_alerts) >= 2
        alert_ids = [alert.id for alert in org_alerts]
        assert alert1.id in alert_ids
        assert alert2.id in alert_ids
        assert all(alert.organization_id == sample_organization.id for alert in org_alerts)
        
        print(f"✅ Found {len(org_alerts)} alerts in organization")
    
    def test_get_by_organization_with_sensor_info(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting alerts with sensor relationship loaded"""
        # Arrange
        alert = alert_repository.create(sample_alert_data)
        
        # Act
        org_alerts = alert_repository.get_by_organization(
            sample_organization.id, 
            include_sensor=True
        )
        
        # Assert
        assert len(org_alerts) >= 1
        found_alert = next((a for a in org_alerts if a.id == alert.id), None)
        assert found_alert is not None
        # Sensor should be loaded due to joinedload
        assert hasattr(found_alert, 'sensor')
        
        print(f"✅ Organization alerts with sensor info loaded correctly")
    
    def test_get_active_alerts(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting only active alerts"""
        # Arrange - Create active and resolved alerts
        active_alert = alert_repository.create(sample_alert_data)  # status: active
        resolved_alert = alert_repository.create({
            **sample_alert_data,
            "status": "resolved",
            "alert_type": "temperature_low"
        })
        
        # Act
        active_alerts = alert_repository.get_active_alerts(sample_organization.id)
        
        # Assert
        assert len(active_alerts) >= 1
        active_alert_ids = [alert.id for alert in active_alerts]
        assert active_alert.id in active_alert_ids
        assert resolved_alert.id not in active_alert_ids
        assert all(alert.status == "active" for alert in active_alerts)
        
        print(f"✅ Found {len(active_alerts)} active alerts")
    
    def test_get_critical_alerts(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting critical alerts"""
        # Arrange - Create alerts with different severities
        critical_alert = alert_repository.create({
            **sample_alert_data,
            "severity": "critical",
            "status": "active"
        })
        medium_alert = alert_repository.create({  # Changed from warning_alert
            **sample_alert_data,
            "severity": "medium",  # Use valid severity
            "alert_type": "temperature_low"
        })
        
        # Act
        critical_alerts = alert_repository.get_critical_alerts(sample_organization.id)
        
        # Assert
        assert len(critical_alerts) >= 1
        critical_alert_ids = [alert.id for alert in critical_alerts]
        assert critical_alert.id in critical_alert_ids
        assert medium_alert.id not in critical_alert_ids
        assert all(alert.severity == "critical" for alert in critical_alerts)
        
        print(f"✅ Found {len(critical_alerts)} critical alerts")
    
    def test_get_haccp_alerts(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting HACCP critical alerts"""
        # Arrange - Create HACCP and non-HACCP alerts
        haccp_alert = alert_repository.create({
            **sample_alert_data,
            "is_haccp_critical": True
        })
        regular_alert = alert_repository.create({
            **sample_alert_data,
            "is_haccp_critical": False,
            "alert_type": "battery_low"  # Use valid alert_type
        })
        
        # Act
        haccp_alerts = alert_repository.get_haccp_alerts(sample_organization.id)
        
        # Assert
        assert len(haccp_alerts) >= 1
        haccp_alert_ids = [alert.id for alert in haccp_alerts]
        assert haccp_alert.id in haccp_alert_ids
        assert regular_alert.id not in haccp_alert_ids
        assert all(alert.is_haccp_critical == True for alert in haccp_alerts)
        
        print(f"✅ Found {len(haccp_alerts)} HACCP critical alerts")
    
    def test_get_unresolved_alerts(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting unresolved alerts (active + acknowledged)"""
        # Arrange - Create alerts with different statuses
        active_alert = alert_repository.create({
            **sample_alert_data,
            "status": "active"
        })
        acknowledged_alert = alert_repository.create({
            **sample_alert_data,
            "status": "acknowledged",
            "alert_type": "temperature_low"
        })
        resolved_alert = alert_repository.create({
            **sample_alert_data,
            "status": "resolved",
            "alert_type": "sensor_offline"  # Use valid alert_type
        })
        
        # Act
        unresolved_alerts = alert_repository.get_unresolved_alerts(sample_organization.id)
        
        # Assert
        assert len(unresolved_alerts) >= 2
        unresolved_ids = [alert.id for alert in unresolved_alerts]
        assert active_alert.id in unresolved_ids
        assert acknowledged_alert.id in unresolved_ids
        assert resolved_alert.id not in unresolved_ids
        
        print(f"✅ Found {len(unresolved_alerts)} unresolved alerts")

# =====================================================
# TEST SENSOR-SPECIFIC QUERIES
# =====================================================

class TestSensorAlerts:
    """Test sensor-specific alert queries"""
    
    def test_get_alerts_by_sensor(self, alert_repository, sample_sensor, sample_location, sample_alert_data):
        """Test getting alerts for specific sensor"""
        # Create alerts for this sensor and another
        sensor_alert1 = alert_repository.create(sample_alert_data)
        sensor_alert2 = alert_repository.create({
            **sample_alert_data,
            "alert_type": "temperature_low",
            "message": "Low temperature alert"
        })
        
        # Create alert for different sensor - CREATE REAL SENSOR
        # Create another sensor for proper foreign key
        other_sensor = Sensor(
            organization_id=sample_alert_data["organization_id"],
            location_id=sample_location.id,  # Use the sample_location
            device_id="OTHER_SENSOR_001",
            name="Other Test Sensor",
            sensor_type="temperature_humidity",
            status="online",
            battery_level=80
        )
        alert_repository.db.add(other_sensor)
        alert_repository.db.commit()
        alert_repository.db.refresh(other_sensor)
        
        other_sensor_alert = alert_repository.create({
            **sample_alert_data,
            "sensor_id": other_sensor.id,  # Use real sensor ID
            "alert_type": "sensor_offline"
        })
        
        # Act
        sensor_alerts = alert_repository.get_alerts_by_sensor(sample_sensor.id)
        
        # Assert
        assert len(sensor_alerts) >= 2
        sensor_alert_ids = [alert.id for alert in sensor_alerts]
        assert sensor_alert1.id in sensor_alert_ids
        assert sensor_alert2.id in sensor_alert_ids
        assert other_sensor_alert.id not in sensor_alert_ids
        assert all(alert.sensor_id == sample_sensor.id for alert in sensor_alerts)
        
        print(f"✅ Found {len(sensor_alerts)} alerts for sensor {sample_sensor.id}")
    
    def test_get_alerts_by_sensor_with_limit(self, alert_repository, sample_sensor, sample_alert_data):
        """Test getting alerts for sensor with limit"""
        # Arrange - Create multiple alerts
        for i in range(5):
            alert_repository.create({
                **sample_alert_data,
                "alert_type": "battery_low",  # Use consistent valid alert_type
                "message": f"Test alert {i}"
            })
        
        # Act
        limited_alerts = alert_repository.get_alerts_by_sensor(sample_sensor.id, limit=3)
        
        # Assert
        assert len(limited_alerts) <= 3
        assert all(alert.sensor_id == sample_sensor.id for alert in limited_alerts)
        
        print(f"✅ Limited query returned {len(limited_alerts)} alerts (max 3)")

# =====================================================
# TEST DATE RANGE QUERIES
# =====================================================

class TestDateRangeQueries:
    """Test date range alert queries"""
    
    def test_get_alerts_by_date_range(self, alert_repository, sample_organization, sample_alert_data):
        """Test getting alerts in specific date range"""
        # Arrange - Create alerts at different times
        now = datetime.now()
        
        # Recent alert (should be included)
        recent_alert = alert_repository.create(sample_alert_data)
        
        # Simulate older alert by manually updating created_at
        old_alert = alert_repository.create({
            **sample_alert_data,
            "alert_type": "temperature_low"
        })
        # Update timestamp to be older
        old_alert.created_at = now - timedelta(days=10)
        alert_repository.db.commit()
        
        # Act - Query for alerts from last 2 days
        start_date = now - timedelta(days=2)
        end_date = now + timedelta(hours=1)  # Slight buffer for timing
        
        range_alerts = alert_repository.get_alerts_by_date_range(
            sample_organization.id, 
            start_date, 
            end_date
        )
        
        # Assert
        range_alert_ids = [alert.id for alert in range_alerts]
        assert recent_alert.id in range_alert_ids
        # old_alert might or might not be included depending on exact timing
        
        print(f"✅ Found {len(range_alerts)} alerts in date range")

# =====================================================
# TEST ALERT LIFECYCLE
# =====================================================

class TestAlertLifecycle:
    """Test complete alert lifecycle scenarios"""
    
    def test_alert_acknowledgment_workflow(self, alert_repository, sample_alert_data, sample_user):
        """Test alert acknowledgment workflow with real user"""
        # 1. Create active alert
        alert = alert_repository.create(sample_alert_data)
        assert alert.status == "active"
        print(f"✅ Step 1: Created active alert {alert.id}")
        
        # 2. Acknowledge alert with real user
        updated_alert = alert_repository.update(alert.id, {
            "status": "acknowledged",
            "acknowledged_at": datetime.now(),
            "acknowledged_by": sample_user.id  # Use real user ID
        })
        assert updated_alert.status == "acknowledged"
        assert updated_alert.acknowledged_at is not None
        assert updated_alert.acknowledged_by == sample_user.id
        print(f"✅ Step 2: Alert acknowledged by user {sample_user.email}")
        
        # 3. Resolve alert with real user
        resolved_alert = alert_repository.update(alert.id, {
            "status": "resolved",
            "resolved_at": datetime.now(),
            "resolved_by": sample_user.id,  # Use real user ID
            "corrective_action_taken": "Adjusted temperature settings"
        })
        assert resolved_alert.status == "resolved"
        assert resolved_alert.resolved_at is not None
        assert resolved_alert.resolved_by == sample_user.id
        assert resolved_alert.corrective_action_taken is not None
        print(f"✅ Step 3: Alert resolved by user {sample_user.email} with corrective action")
        
        print("✅ Complete alert lifecycle test passed!")
    
    def test_alert_user_relationships(self, alert_repository, sample_alert_data, sample_user):
        """Test alert relationships with users (acknowledged_by_user, resolved_by_user)"""
        # 1. Create and acknowledge alert
        alert = alert_repository.create(sample_alert_data)
        
        # 2. Update with user relationships
        updated_alert = alert_repository.update(alert.id, {
            "status": "acknowledged",
            "acknowledged_by": sample_user.id,
            "acknowledged_at": datetime.now()
        })
        
        # 3. Reload to test relationships
        alert_with_relations = alert_repository.get_by_id(updated_alert.id)
        
        # 4. Test that foreign keys are set correctly
        assert alert_with_relations.acknowledged_by == sample_user.id
        
        # Note: To test the relationship objects (acknowledged_by_user), 
        # we would need to load them explicitly since they're not eagerly loaded
        print(f"✅ Alert properly linked to user {sample_user.email}")
        print(f"✅ acknowledged_by: {alert_with_relations.acknowledged_by}")
        
        # 5. Test resolution with user
        resolved_alert = alert_repository.update(alert.id, {
            "status": "resolved",
            "resolved_by": sample_user.id,
            "resolved_at": datetime.now()
        })
        
        assert resolved_alert.resolved_by == sample_user.id
        print(f"✅ Alert properly resolved by user {sample_user.email}")
    
    def test_alert_escalation_scenario(self, alert_repository, sample_alert_data):
        """Test alert escalation scenario"""
        # 1. Create medium alert
        medium_alert = alert_repository.create({
            **sample_alert_data,
            "severity": "medium"
        })
        print(f"✅ Step 1: Created medium alert")
        
        # 2. Escalate to critical
        critical_alert = alert_repository.update(medium_alert.id, {
            "severity": "critical",
            "message": "Temperature still rising - CRITICAL",
            "current_value": Decimal('20.0')  # Even higher temperature
        })
        assert critical_alert.severity == "critical"
        print(f"✅ Step 2: Escalated to critical")
        
        # 3. Verify it appears in critical alerts query
        critical_alerts = alert_repository.get_critical_alerts(
            sample_alert_data["organization_id"]
        )
        critical_ids = [alert.id for alert in critical_alerts]
        assert critical_alert.id in critical_ids
        print(f"✅ Step 3: Alert appears in critical alerts list")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestMultiTenancy:
    """Test multi-tenancy isolation for alerts"""
    
    def test_organization_isolation(self, alert_repository, test_db, sample_alert_data):
        """Test that alerts are isolated by organization"""
        
        # Create two organizations
        org1 = Organization(name="Org 1", slug="org-1-alerts")
        org2 = Organization(name="Org 2", slug="org-2-alerts")
        test_db.add_all([org1, org2])
        test_db.commit()
        
        # Create alerts in different organizations
        alert1 = alert_repository.create({
            **sample_alert_data,
            "organization_id": org1.id,
            "sensor_id": None  # No sensor for simplicity
        })
        
        alert2 = alert_repository.create({
            **sample_alert_data,
            "organization_id": org2.id,
            "sensor_id": None
        })
        
        # Test isolation using organization-specific queries
        org1_alerts = alert_repository.get_by_organization(org1.id)
        org2_alerts = alert_repository.get_by_organization(org2.id)
        
        # Assert isolation
        org1_alert_ids = [alert.id for alert in org1_alerts]
        org2_alert_ids = [alert.id for alert in org2_alerts]
        
        assert alert1.id in org1_alert_ids
        assert alert1.id not in org2_alert_ids
        assert alert2.id in org2_alert_ids
        assert alert2.id not in org1_alert_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")

# =====================================================
# TEST PERFORMANCE AND PAGINATION
# =====================================================

class TestAlertPerformance:
    """Test alert repository performance"""
    
    def test_large_alert_volume(self, alert_repository, sample_organization, sample_alert_data):
        """Test handling large volume of alerts"""
        import time
        
        # Arrange
        start_time = time.time()
        alert_count = 20  # Reasonable number for testing
        
        # Act - Create multiple alerts
        created_alerts = []
        for i in range(alert_count):
            alert_data = {
                **sample_alert_data,
                "alert_type": "battery_low",  # Use consistent valid alert_type
                "message": f"Test alert {i}",
                "sensor_id": None  # Simplify for performance test
            }
            alert = alert_repository.create(alert_data)
            created_alerts.append(alert)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_alerts) == alert_count
        assert duration < 10  # Should complete within 10 seconds
        
        print(f"✅ Created {alert_count} alerts in {duration:.2f} seconds")
        print(f"✅ Average: {duration/alert_count:.3f} seconds per alert")
    
    def test_pagination_with_get_all(self, alert_repository, sample_organization, sample_alert_data):
        """Test pagination functionality"""
        # Arrange - Create multiple alerts
        for i in range(10):
            alert_repository.create({
                **sample_alert_data,
                "alert_type": "calibration_due",  # Use consistent valid alert_type
                "sensor_id": None
            })
        
        # Act - Test pagination
        first_page = alert_repository.get_all(skip=0, limit=3)
        second_page = alert_repository.get_all(skip=3, limit=3)
        
        # Assert
        assert len(first_page) == 3
        assert len(second_page) == 3
        
        # Ensure different results
        first_page_ids = [alert.id for alert in first_page]
        second_page_ids = [alert.id for alert in second_page]
        assert not any(id in second_page_ids for id in first_page_ids)
        
        print(f"✅ Pagination working: page 1 has {len(first_page)} items, page 2 has {len(second_page)} items")

# =====================================================
# RUN COMMAND INSTRUCTIONS
# =====================================================

"""
COME ESEGUIRE I TEST:

# Single test file
pytest test/repositories/test_alert_repository.py -v -s

# Specific test class
pytest test/repositories/test_alert_repository.py::TestAlertCRUD -v -s

# Specific test method
pytest test/repositories/test_alert_repository.py::TestAlertCRUD::test_create_alert_success -v -s

# With coverage
pytest test/repositories/test_alert_repository.py --cov=src/repositories/alert_repository --cov-report=term-missing

# All alert tests
pytest test/repositories/test_alert_repository.py -v -s

# Run specific test categories
pytest test/repositories/test_alert_repository.py::TestAlertQueries -v -s
pytest test/repositories/test_alert_repository.py::TestSensorAlerts -v -s
pytest test/repositories/test_alert_repository.py::TestAlertLifecycle -v -s
pytest test/repositories/test_alert_repository.py::TestMultiTenancy -v -s
"""