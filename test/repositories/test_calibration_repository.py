# =====================================================
# test/repositories/test_calibration_repository.py
# =====================================================
"""
Test per CalibrationRepository - versione corretta con fix per tutti gli errori.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text

# Clean imports - no path manipulation needed
from src.models import Organization, Location, Sensor, Calibration, User
from src.repositories.calibration_repository import CalibrationRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def calibration_repository(test_db):
    """Create CalibrationRepository instance"""
    return CalibrationRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Calibration Test Company",
        slug="calibration-test-company",
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
        name="Calibration Test Freezer",
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
        device_id="CALIBRATION_TEST_SENSOR_001",
        name="Calibration Test Sensor",
        sensor_type="temperature_humidity",
        status="online",
        battery_level=95
    )
    test_db.add(sensor)
    test_db.commit()
    test_db.refresh(sensor)
    return sensor

@pytest.fixture
def sample_technician(test_db, sample_organization):
    """Create sample technician user for testing"""
    user = User(
        organization_id=sample_organization.id,
        email="technician@example.com",
        first_name="Tech",
        last_name="Nician",
        role="admin",  # Assuming technicians have admin role
        is_active=True,
        is_verified=True
    )
    user.set_password("TechPassword123!")
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def sample_calibration_data(sample_organization, sample_sensor, sample_technician):
    """Sample calibration data for testing - usando dati validi"""
    calibrated_at = datetime.now()
    # IMPORTANTE: next_calibration_due ora è datetime, non date
    next_calibration_due = datetime.combine(
        date.today() + timedelta(days=365), 
        datetime.min.time()
    )
    
    return {
        "organization_id": sample_organization.id,
        "sensor_id": sample_sensor.id,
        "calibrated_by": sample_technician.id,
        "calibration_type": "routine",
        "calibration_method": "comparison_method",
        "accuracy_achieved": Decimal('0.125'),  # ±0.125°C
        "calibration_passed": True,
        "notes": "Standard routine calibration completed successfully",
        "technician_name": "John Tech",
        "technician_certificate": "CERT-2024-001",
        "reference_equipment_model": "Fluke 1524",
        "reference_equipment_serial": "SN-123456",
        "reference_equipment_cert_date": date.today() - timedelta(days=30),
        "scheduled_date": calibrated_at - timedelta(days=1),
        "calibrated_at": calibrated_at,
        "next_calibration_due": next_calibration_due  # Ora è datetime
    }

@pytest.fixture
def created_calibration(calibration_repository, sample_calibration_data):
    """Create and return a test calibration"""
    return calibration_repository.create(sample_calibration_data)

# Fixture per multi-tenancy testing
@pytest.fixture  
def second_organization(test_db):
    """Create second organization for multi-tenancy tests"""
    org = Organization(
        name="Second Test Company",
        slug="second-test-company",
        subscription_plan="basic",
        max_sensors=10,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def second_sensor(test_db, second_organization):
    """Create sensor for second organization"""
    # Create location first
    location = Location(
        organization_id=second_organization.id,
        name="Second Org Freezer",
        location_type="freezer",
        temperature_min=Decimal('-18.0'),
        temperature_max=Decimal('-12.0')
    )
    test_db.add(location)
    test_db.commit()
    
    sensor = Sensor(
        organization_id=second_organization.id,
        location_id=location.id,
        device_id="SECOND_ORG_SENSOR_001",
        name="Second Org Test Sensor",
        sensor_type="temperature_humidity",
        status="online",
        battery_level=85
    )
    test_db.add(sensor)
    test_db.commit()
    test_db.refresh(sensor)
    return sensor

@pytest.fixture
def second_technician(test_db, second_organization):
    """Create technician for second organization"""
    user = User(
        organization_id=second_organization.id,
        email="tech2@example.com",
        first_name="Tech2",
        last_name="Nician2",
        role="admin",
        is_active=True,
        is_verified=True
    )
    user.set_password("TechPassword123!")
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestCalibrationCRUD:
    """Test basic CRUD operations"""
    
    def test_create_calibration_success(self, calibration_repository, sample_calibration_data):
        """Test creating a new calibration"""
        
        # Act
        calibration = calibration_repository.create(sample_calibration_data)
        
        # Assert
        assert calibration.id is not None
        assert calibration.calibration_type == sample_calibration_data["calibration_type"]
        assert calibration.calibration_method == sample_calibration_data["calibration_method"]
        assert calibration.accuracy_achieved == sample_calibration_data["accuracy_achieved"]
        assert calibration.calibration_passed == sample_calibration_data["calibration_passed"]
        assert calibration.organization_id == sample_calibration_data["organization_id"]
        assert calibration.sensor_id == sample_calibration_data["sensor_id"]
        assert calibration.calibrated_by == sample_calibration_data["calibrated_by"]
        assert calibration.technician_name == sample_calibration_data["technician_name"]
        assert calibration.next_calibration_due == sample_calibration_data["next_calibration_due"]
        
        # Verify timestamps
        assert calibration.created_at is not None
        assert calibration.updated_at is not None
        
        print(f"✅ Calibration created with ID: {calibration.id}")
        print(f"✅ Type: {calibration.calibration_type}, Passed: {calibration.calibration_passed}")
    
    def test_get_by_id(self, calibration_repository, created_calibration):
        """Test getting calibration by ID"""
        # Act
        found_calibration = calibration_repository.get_by_id(created_calibration.id)
        
        # Assert
        assert found_calibration is not None
        assert found_calibration.id == created_calibration.id
        assert found_calibration.calibration_type == created_calibration.calibration_type
        
        print(f"✅ Calibration found by ID: {found_calibration.id}")
    
    def test_get_by_id_not_found(self, calibration_repository):
        """Test getting non-existent calibration"""
        # Act
        found_calibration = calibration_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_calibration is None
        print("✅ Non-existent calibration correctly returned None")
    
    def test_update_calibration(self, calibration_repository, created_calibration):
        """Test updating calibration"""
        # Arrange
        update_data = {
            "calibration_passed": False,
            "notes": "Calibration failed - sensor drift detected",
            "accuracy_achieved": Decimal('1.500')  # Poor accuracy
        }
        
        # Act
        updated_calibration = calibration_repository.update(created_calibration.id, update_data)
        
        # Assert
        assert updated_calibration is not None
        assert updated_calibration.calibration_passed == False
        assert updated_calibration.notes == "Calibration failed - sensor drift detected"
        assert updated_calibration.accuracy_achieved == Decimal('1.500')
        # Check unchanged fields
        assert updated_calibration.calibration_type == created_calibration.calibration_type
        assert updated_calibration.sensor_id == created_calibration.sensor_id
        
        print(f"✅ Calibration updated successfully")
    
    def test_delete_calibration(self, calibration_repository, created_calibration):
        """Test deleting calibration"""
        # Act
        result = calibration_repository.delete(created_calibration.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_calibration = calibration_repository.get_by_id(created_calibration.id)
        assert found_calibration is None
        
        print(f"✅ Calibration deleted successfully")
    
    def test_delete_nonexistent_calibration(self, calibration_repository):
        """Test deleting non-existent calibration"""
        # Act
        result = calibration_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent calibration correctly returned False")

# =====================================================
# TEST CALIBRATION-SPECIFIC QUERIES
# =====================================================

class TestCalibrationQueries:
    """Test calibration-specific query methods"""
    
    def test_get_by_organization(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test getting calibrations by organization"""
        # Arrange - Create multiple calibrations
        cal1 = calibration_repository.create(sample_calibration_data)
        cal2 = calibration_repository.create({
            **sample_calibration_data,
            "calibration_type": "corrective",
            "notes": "Corrective calibration after drift detection"
        })
        
        # Act
        org_calibrations = calibration_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_calibrations) >= 2
        cal_ids = [cal.id for cal in org_calibrations]
        assert cal1.id in cal_ids
        assert cal2.id in cal_ids
        assert all(cal.organization_id == sample_organization.id for cal in org_calibrations)
        
        print(f"✅ Found {len(org_calibrations)} calibrations in organization")
    
    def test_get_by_sensor(self, calibration_repository, sample_sensor, sample_calibration_data):
        """Test getting calibrations for specific sensor"""
        # Arrange - Create calibrations for this sensor
        cal1 = calibration_repository.create(sample_calibration_data)
        cal2 = calibration_repository.create({
            **sample_calibration_data,
            "calibration_type": "verification",
            "calibrated_at": datetime.now() - timedelta(hours=1),  # Slightly different time
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=366), 
                datetime.min.time()
            )
        })
        
        # Act
        sensor_calibrations = calibration_repository.get_by_sensor(sample_sensor.id)
        
        # Assert
        assert len(sensor_calibrations) >= 2
        sensor_cal_ids = [cal.id for cal in sensor_calibrations]
        assert cal1.id in sensor_cal_ids
        assert cal2.id in sensor_cal_ids
        assert all(cal.sensor_id == sample_sensor.id for cal in sensor_calibrations)
        
        print(f"✅ Found {len(sensor_calibrations)} calibrations for sensor {sample_sensor.id}")
    
    def test_get_latest_calibration(self, calibration_repository, sample_sensor, sample_calibration_data):
        """Test getting latest calibration for sensor"""
        # Arrange - Create calibrations at different times con datetime
        old_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=60),
            "calibration_type": "routine",
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=305), 
                datetime.min.time()
            )
        })
        
        latest_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=1),
            "calibration_type": "verification",
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=364), 
                datetime.min.time()
            )
        })
        
        # Act
        result = calibration_repository.get_latest_calibration(sample_sensor.id)
        
        # Assert
        assert result is not None
        assert result.id == latest_cal.id
        assert result.calibration_type == "verification"
        
        print(f"✅ Latest calibration correctly identified: {result.calibration_type}")

# =====================================================
# TEST DATE RANGE QUERIES
# =====================================================

class TestCalibrationDateQueries:
    """Test date range calibration queries"""
    
    def test_get_passed_calibrations(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test getting passed calibrations in date range"""
        # Arrange - Create passed and failed calibrations con datetime
        passed_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": True,
            "calibrated_at": datetime.now() - timedelta(days=10),
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=355), 
                datetime.min.time()
            )
        })
        
        failed_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": False,
            "calibrated_at": datetime.now() - timedelta(days=5),
            "calibration_type": "corrective",
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=360), 
                datetime.min.time()
            )
        })
        
        # Act
        start_date = date.today() - timedelta(days=15)
        end_date = date.today()
        passed_calibrations = calibration_repository.get_passed_calibrations(
            sample_organization.id, start_date, end_date
        )
        
        # Assert
        passed_ids = [cal.id for cal in passed_calibrations]
        assert passed_cal.id in passed_ids
        assert failed_cal.id not in passed_ids
        assert all(cal.calibration_passed == True for cal in passed_calibrations)
        
        print(f"✅ Found {len(passed_calibrations)} passed calibrations in date range")
    
    def test_get_failed_calibrations(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test getting failed calibrations in date range"""
        # Arrange - Create passed and failed calibrations con datetime
        passed_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": True,
            "calibrated_at": datetime.now() - timedelta(days=10),
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=355), 
                datetime.min.time()
            )
        })
        
        failed_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": False,
            "calibrated_at": datetime.now() - timedelta(days=5),
            "calibration_type": "corrective",
            "notes": "Sensor requires replacement",
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=360), 
                datetime.min.time()
            )
        })
        
        # Act
        start_date = date.today() - timedelta(days=15)
        end_date = date.today()
        failed_calibrations = calibration_repository.get_failed_calibrations(
            sample_organization.id, start_date, end_date
        )
        
        # Assert
        failed_ids = [cal.id for cal in failed_calibrations]
        assert failed_cal.id in failed_ids
        assert passed_cal.id not in failed_ids
        assert all(cal.calibration_passed == False for cal in failed_calibrations)
        
        print(f"✅ Found {len(failed_calibrations)} failed calibrations in date range")

# =====================================================
# TEST SCHEDULING QUERIES
# =====================================================

class TestCalibrationScheduling:
    """Test calibration scheduling query methods"""
    
    def test_get_calibrations_due_soon(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test getting calibrations due soon"""
        # Arrange - Create calibrations with different due dates usando datetime
        due_soon_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=350),  # Old calibration
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=15), 
                datetime.min.time()
            ),  # Due in 15 days
            "calibration_type": "routine"
        })
        
        due_later_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=300),  # Old calibration  
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=60), 
                datetime.min.time()
            ),  # Due in 60 days
            "calibration_type": "verification"
        })
        
        # Act - Look for calibrations due in next 30 days
        due_soon = calibration_repository.get_calibrations_due_soon(
            sample_organization.id, days_ahead=30
        )
        
        # Assert
        due_soon_ids = [cal.id for cal in due_soon]
        assert due_soon_cal.id in due_soon_ids
        assert due_later_cal.id not in due_soon_ids
        
        print(f"✅ Found {len(due_soon)} calibrations due in next 30 days")
    
    def test_get_overdue_calibrations(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test getting overdue calibrations"""
        # Arrange - Create overdue and current calibrations usando datetime
        overdue_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=375),  # Old calibration
            "next_calibration_due": datetime.combine(
                date.today() - timedelta(days=10), 
                datetime.min.time()
            ),  # Overdue by 10 days
            "calibration_type": "routine"
        })
        
        current_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_at": datetime.now() - timedelta(days=335),  # Old calibration
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=30), 
                datetime.min.time()
            ),  # Due in future
            "calibration_type": "verification"
        })
        
        # Act
        overdue_calibrations = calibration_repository.get_overdue_calibrations(
            sample_organization.id
        )
        
        # Assert
        overdue_ids = [cal.id for cal in overdue_calibrations]
        assert overdue_cal.id in overdue_ids
        assert current_cal.id not in overdue_ids
        
        print(f"✅ Found {len(overdue_calibrations)} overdue calibrations")

# =====================================================
# TEST TECHNICIAN QUERIES
# =====================================================

class TestTechnicianQueries:
    """Test technician-specific calibration queries"""
    
    def test_get_by_technician(self, calibration_repository, sample_technician, sample_calibration_data, test_db, sample_organization, sample_location):
        """Test getting calibrations by technician in date range"""
        # Create additional sensor for other technician
        other_sensor = Sensor(
            organization_id=sample_organization.id,
            location_id=sample_location.id,
            device_id="OTHER_TECHNICIAN_SENSOR",
            name="Other Tech Sensor",
            sensor_type="temperature_humidity",
            status="online",
            battery_level=75
        )
        test_db.add(other_sensor)
        test_db.commit()
        test_db.refresh(other_sensor)
        
        # Create other technician
        other_technician = User(
            organization_id=sample_organization.id,
            email="other_tech@example.com",
            first_name="Other",
            last_name="Tech",
            role="admin",
            is_active=True,
            is_verified=True
        )
        other_technician.set_password("OtherTechPass123!")
        test_db.add(other_technician)
        test_db.commit()
        test_db.refresh(other_technician)
        
        # Arrange - Create calibrations for this technician and others con datetime
        tech_cal1 = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_by": sample_technician.id,
            "calibrated_at": datetime.now() - timedelta(days=5),
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=360), 
                datetime.min.time()
            )
        })
        
        tech_cal2 = calibration_repository.create({
            **sample_calibration_data,
            "calibrated_by": sample_technician.id,
            "calibrated_at": datetime.now() - timedelta(days=2),
            "calibration_type": "corrective",
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=363), 
                datetime.min.time()
            )
        })
        
        # Create calibration by different technician (should not appear)
        other_tech_cal = calibration_repository.create({
            **sample_calibration_data,
            "sensor_id": other_sensor.id,
            "calibrated_by": other_technician.id,
            "calibrated_at": datetime.now() - timedelta(days=3),
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=362), 
                datetime.min.time()
            )
        })
        
        # Act
        start_date = date.today() - timedelta(days=10)
        end_date = date.today()
        tech_calibrations = calibration_repository.get_by_technician(
            sample_technician.id, start_date, end_date
        )
        
        # Assert
        tech_cal_ids = [cal.id for cal in tech_calibrations]
        assert tech_cal1.id in tech_cal_ids
        assert tech_cal2.id in tech_cal_ids
        assert other_tech_cal.id not in tech_cal_ids
        assert all(cal.calibrated_by == sample_technician.id for cal in tech_calibrations)
        
        print(f"✅ Found {len(tech_calibrations)} calibrations by technician {sample_technician.email}")

# =====================================================
# TEST CALIBRATION BUSINESS LOGIC
# =====================================================

class TestCalibrationBusinessLogic:
    """Test calibration business logic and properties"""
    
    def test_calibration_properties(self, calibration_repository, sample_calibration_data):
        """Test calibration model properties"""
        # Create calibration
        calibration = calibration_repository.create(sample_calibration_data)
        
        # Test is_passed property
        assert calibration.is_passed == True
        
        # Test days_until_due property - ora gestisce datetime vs date
        # Il model ora dovrebbe avere una property che converte correttamente
        days_until = calibration.days_until_due
        # Confrontiamo con la data di next_calibration_due convertita a date
        expected_days = (calibration.next_calibration_due.date() - date.today()).days
        assert days_until == expected_days
        
        print(f"✅ Calibration properties working correctly")
        print(f"   - is_passed: {calibration.is_passed}")
        print(f"   - days_until_due: {calibration.days_until_due}")
        print(f"   - next_calibration_due: {calibration.next_calibration_due}")
        print(f"   - next_calibration_due type: {type(calibration.next_calibration_due)}")
    
    def test_mark_as_passed(self, calibration_repository, sample_calibration_data):
        """Test marking calibration as passed"""
        # Create failed calibration
        failed_cal_data = {
            **sample_calibration_data,
            "calibration_passed": False,
            "accuracy_achieved": Decimal('2.000'),
            "notes": "Initial calibration failed"
        }
        calibration = calibration_repository.create(failed_cal_data)
        
        # Mark as passed
        calibration.mark_as_passed(
            accuracy=Decimal('0.250'),
            notes="Recalibration successful after sensor adjustment"
        )
        calibration_repository.db.commit()
        
        # Verify changes
        updated_cal = calibration_repository.get_by_id(calibration.id)
        assert updated_cal.calibration_passed == True
        assert updated_cal.accuracy_achieved == Decimal('0.250')
        assert "Recalibration successful" in updated_cal.notes
        
        print(f"✅ Mark as passed functionality working correctly")
    
    def test_mark_as_failed(self, calibration_repository, sample_calibration_data):
        """Test marking calibration as failed"""
        # Create passed calibration
        calibration = calibration_repository.create(sample_calibration_data)
        
        # Mark as failed
        calibration.mark_as_failed("Sensor drift exceeds acceptable limits")
        calibration_repository.db.commit()
        
        # Verify changes
        updated_cal = calibration_repository.get_by_id(calibration.id)
        assert updated_cal.calibration_passed == False
        assert "Sensor drift exceeds" in updated_cal.notes
        
        print(f"✅ Mark as failed functionality working correctly")

# =====================================================
# TEST CALIBRATION LIFECYCLE
# =====================================================

class TestCalibrationLifecycle:
    """Test complete calibration lifecycle scenarios"""
    
    def test_calibration_workflow(self, calibration_repository, sample_calibration_data, sample_technician):
        """Test complete calibration workflow"""
        # 1. Schedule calibration
        scheduled_cal_data = {
            **sample_calibration_data,
            "scheduled_date": datetime.now() + timedelta(days=7),
            "calibrated_at": datetime.now() - timedelta(days=1)  # Performed recently
        }
        
        print(f"✅ Step 1: Calibration scheduled for {scheduled_cal_data['scheduled_date']}")
        
        # 2. Perform calibration
        performed_cal_data = {
            **sample_calibration_data,
            "calibrated_at": datetime.now(),
            "calibration_passed": True,
            "accuracy_achieved": Decimal('0.150'),
            "notes": "Calibration completed successfully within specifications"
        }
        calibration = calibration_repository.create(performed_cal_data)
        print(f"✅ Step 2: Calibration performed by {sample_technician.email}")
        
        # 3. Verify calibration was recorded correctly
        assert calibration.calibration_passed == True
        assert calibration.calibrated_by == sample_technician.id
        print(f"✅ Step 3: Calibration recorded with accuracy ±{calibration.accuracy_achieved}°C")
        
        # 4. Check next calibration is scheduled
        assert calibration.next_calibration_due > datetime.now()  # Confronta datetime con datetime
        print(f"✅ Step 4: Next calibration due on {calibration.next_calibration_due.date()}")
        
        print("✅ Complete calibration workflow test passed!")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestMultiTenancy:
    """Test multi-tenancy isolation for calibrations"""
    
    def test_organization_isolation(self, calibration_repository, test_db, sample_calibration_data, 
                                   second_organization, second_sensor, second_technician):
        """Test that calibrations are isolated by organization"""
        
        # Create calibrations in different organizations
        cal1 = calibration_repository.create({
            **sample_calibration_data,
            "organization_id": sample_calibration_data["organization_id"],  # First org
            "sensor_id": sample_calibration_data["sensor_id"],             # First org sensor
            "calibrated_by": sample_calibration_data["calibrated_by"]      # First org technician
        })
        
        cal2 = calibration_repository.create({
            **sample_calibration_data,
            "organization_id": second_organization.id,
            "sensor_id": second_sensor.id,
            "calibrated_by": second_technician.id,
            "calibrated_at": datetime.now() - timedelta(hours=1),  # Slightly different time
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=366), 
                datetime.min.time()
            )
        })
        
        # Test isolation using organization-specific queries
        org1_calibrations = calibration_repository.get_by_organization(sample_calibration_data["organization_id"])
        org2_calibrations = calibration_repository.get_by_organization(second_organization.id)
        
        # Assert isolation
        org1_cal_ids = [cal.id for cal in org1_calibrations]
        org2_cal_ids = [cal.id for cal in org2_calibrations]
        
        assert cal1.id in org1_cal_ids
        assert cal1.id not in org2_cal_ids
        assert cal2.id in org2_cal_ids
        assert cal2.id not in org1_cal_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")
        print(f"   - Org1 calibrations: {len(org1_calibrations)}")
        print(f"   - Org2 calibrations: {len(org2_calibrations)}")

# =====================================================
# TEST PERFORMANCE AND PAGINATION
# =====================================================

class TestCalibrationPerformance:
    """Test calibration repository performance"""
    
    def test_large_calibration_volume(self, calibration_repository, test_db, sample_organization, sample_location, sample_technician):
        """Test handling large volume of calibrations"""
        import time
        
        # Create multiple sensors for performance test
        sensors = []
        for i in range(5):
            sensor = Sensor(
                organization_id=sample_organization.id,
                location_id=sample_location.id,
                device_id=f"PERF_TEST_SENSOR_{i:03d}",
                name=f"Performance Test Sensor {i}",
                sensor_type="temperature_humidity",
                status="online",
                battery_level=80 + i
            )
            test_db.add(sensor)
            sensors.append(sensor)
        
        test_db.commit()
        for sensor in sensors:
            test_db.refresh(sensor)
        
        # Arrange
        start_time = time.time()
        calibration_count = 15  # Reasonable number for testing
        
        # Act - Create multiple calibrations
        created_calibrations = []
        for i in range(calibration_count):
            sensor = sensors[i % len(sensors)]  # Rotate through sensors
            cal_data = {
                "organization_id": sample_organization.id,
                "sensor_id": sensor.id,
                "calibrated_by": sample_technician.id,
                "calibration_type": "routine",
                "calibration_method": "comparison_method",
                "accuracy_achieved": Decimal('0.125'),
                "calibration_passed": True,
                "notes": f"Calibration batch test {i}",
                "technician_name": "Batch Test Tech",
                "calibrated_at": datetime.now() - timedelta(days=i),
                "next_calibration_due": datetime.combine(
                    date.today() + timedelta(days=365 - i), 
                    datetime.min.time()
                )
            }
            calibration = calibration_repository.create(cal_data)
            created_calibrations.append(calibration)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_calibrations) == calibration_count
        assert duration < 15  # Should complete within 15 seconds
        
        print(f"✅ Created {calibration_count} calibrations in {duration:.2f} seconds")
        print(f"✅ Average: {duration/calibration_count:.3f} seconds per calibration")

# =====================================================
# TEST HACCP COMPLIANCE SCENARIOS
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance scenarios"""
    
    def test_calibration_compliance_tracking(self, calibration_repository, sample_organization, sample_calibration_data):
        """Test calibration compliance tracking for HACCP"""
        # Arrange - Create calibrations with different compliance status within the target date range
        yesterday = datetime.now() - timedelta(days=1)
        
        compliant_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": True,
            "accuracy_achieved": Decimal('0.125'),  # Within spec
            "calibration_type": "routine",
            "calibrated_at": yesterday.replace(hour=10, minute=0, second=0, microsecond=0),  # Yesterday 10:00 AM
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=365), 
                datetime.min.time()
            )
        })
        
        non_compliant_cal = calibration_repository.create({
            **sample_calibration_data,
            "calibration_passed": False,
            "accuracy_achieved": Decimal('2.500'),  # Out of spec
            "calibration_type": "corrective",
            "notes": "HACCP non-compliance: accuracy exceeds ±0.5°C requirement",
            "calibrated_at": yesterday.replace(hour=14, minute=0, second=0, microsecond=0),  # Yesterday 2:00 PM
            "next_calibration_due": datetime.combine(
                date.today() + timedelta(days=366), 
                datetime.min.time()
            )
        })
        
        # Act - Get passed and failed calibrations (search within yesterday's range)
        start_date = date.today() - timedelta(days=1)  # Yesterday
        end_date = date.today()  # Today (inclusive up to start of today)
        
        passed_cals = calibration_repository.get_passed_calibrations(
            sample_organization.id, start_date, end_date
        )
        failed_cals = calibration_repository.get_failed_calibrations(
            sample_organization.id, start_date, end_date
        )
        
        # Debug info
        print(f"🔍 Debug info:")
        print(f"   - Search range: {start_date} to {end_date}")
        print(f"   - Compliant cal time: {compliant_cal.calibrated_at}")
        print(f"   - Non-compliant cal time: {non_compliant_cal.calibrated_at}")
        print(f"   - Found passed: {len(passed_cals)}")
        print(f"   - Found failed: {len(failed_cals)}")
        
        # Assert
        passed_ids = [cal.id for cal in passed_cals]
        failed_ids = [cal.id for cal in failed_cals]
        
        assert compliant_cal.id in passed_ids, f"Compliant calibration {compliant_cal.id} not found in passed list"
        assert non_compliant_cal.id in failed_ids, f"Non-compliant calibration {non_compliant_cal.id} not found in failed list"
        assert compliant_cal.id not in failed_ids, f"Compliant calibration incorrectly found in failed list"
        assert non_compliant_cal.id not in passed_ids, f"Non-compliant calibration incorrectly found in passed list"
        
        print(f"✅ HACCP compliance tracking working correctly")
        print(f"   - Compliant calibrations: {len(passed_cals)}")
        print(f"   - Non-compliant calibrations: {len(failed_cals)}")

# =====================================================
# TEST RELAZIONI E CONSTRAINTS
# =====================================================

class TestCalibrationRelationships:
    """Test calibration relationships and database constraints"""
    
    def test_sensor_relationship(self, calibration_repository, created_calibration):
        """Test calibration-sensor relationship"""
        # Act
        calibration = calibration_repository.get_by_id(created_calibration.id)
        
        # Assert
        assert calibration.sensor is not None
        assert calibration.sensor.id == calibration.sensor_id
        assert calibration.sensor.device_id is not None
        
        print(f"✅ Sensor relationship working: {calibration.sensor.device_id}")
    
    def test_organization_relationship(self, calibration_repository, created_calibration):
        """Test calibration-organization relationship"""
        # Act
        calibration = calibration_repository.get_by_id(created_calibration.id)
        
        # Assert
        assert calibration.organization is not None
        assert calibration.organization.id == calibration.organization_id
        assert calibration.organization.name is not None
        
        print(f"✅ Organization relationship working: {calibration.organization.name}")
    
    def test_technician_relationship(self, calibration_repository, created_calibration):
        """Test calibration-technician relationship"""
        # Act
        calibration = calibration_repository.get_by_id(created_calibration.id)
        
        # Assert
        assert calibration.technician is not None
        assert calibration.technician.id == calibration.calibrated_by
        assert calibration.technician.email is not None
        
        print(f"✅ Technician relationship working: {calibration.technician.email}")
    
    def test_date_constraint_validation(self, calibration_repository, sample_calibration_data):
        """Test that next_calibration_due must be in future"""
        # Arrange - Try to create calibration with past due date (datetime)
        invalid_data = {
            **sample_calibration_data,
            "next_calibration_due": datetime.combine(
                date.today() - timedelta(days=1), 
                datetime.min.time()
            )  # Past datetime
        }
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            calibration_repository.create(invalid_data)
        
        # Should fail due to constraint
        assert "chk_next_calibration_future" in str(exc_info.value) or "constraint" in str(exc_info.value).lower()
        
        print(f"✅ Date constraint validation working correctly")
    
    def test_accuracy_constraint_validation(self, calibration_repository, sample_calibration_data):
        """Test that accuracy_achieved must be positive"""
        # Arrange - Try to create calibration with negative accuracy
        invalid_data = {
            **sample_calibration_data,
            "accuracy_achieved": Decimal('-0.5')  # Negative accuracy
        }
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            calibration_repository.create(invalid_data)
        
        # Should fail due to constraint
        assert "chk_accuracy_positive" in str(exc_info.value) or "constraint" in str(exc_info.value).lower()
        
        print(f"✅ Accuracy constraint validation working correctly")

# =====================================================
# TEST EDGE CASES
# =====================================================

class TestCalibrationEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cascade_delete_organization(self, test_db, calibration_repository, sample_calibration_data):
        """Test what happens when organization is deleted"""
        # Create temporary organization and entities
        temp_org = Organization(
            name="Temp Org for Delete Test",
            slug="temp-org-delete",
            subscription_plan="basic"
        )
        test_db.add(temp_org)
        test_db.commit()
        test_db.refresh(temp_org)
        
        # Create location
        temp_location = Location(
            organization_id=temp_org.id,
            name="Temp Location",
            location_type="freezer",
            temperature_min=Decimal('-20.0'),
            temperature_max=Decimal('-15.0')
        )
        test_db.add(temp_location)
        test_db.commit()
        
        # Create sensor
        temp_sensor = Sensor(
            organization_id=temp_org.id,
            location_id=temp_location.id,
            device_id="TEMP_DELETE_SENSOR",
            name="Temp Delete Sensor",
            sensor_type="temperature_humidity",
            status="online"
        )
        test_db.add(temp_sensor)
        test_db.commit()
        test_db.refresh(temp_sensor)
        
        # Create calibration
        cal_data = {
            **sample_calibration_data,
            "organization_id": temp_org.id,
            "sensor_id": temp_sensor.id,
            "calibrated_by": None  # No technician to avoid FK issues
        }
        
        calibration = calibration_repository.create(cal_data)
        
        # Act - Delete organization (should cascade)
        test_db.delete(temp_org)
        test_db.commit()
        
        # Assert - Calibration should be gone due to CASCADE
        found_calibration = calibration_repository.get_by_id(calibration.id)
        assert found_calibration is None
        
        print(f"✅ Cascade delete working correctly")
    
    def test_null_technician_handling(self, calibration_repository, sample_calibration_data):
        """Test calibration creation without technician"""
        # Arrange
        cal_data = {
            **sample_calibration_data,
            "calibrated_by": None,  # No technician
            "technician_name": "External Technician",
            "technician_certificate": "EXT-CERT-001"
        }
        
        # Act
        calibration = calibration_repository.create(cal_data)
        
        # Assert
        assert calibration.calibrated_by is None
        assert calibration.technician is None
        assert calibration.technician_name == "External Technician"
        
        print(f"✅ Null technician handling working correctly")