# =====================================================
# test/repositories/test_location_repository.py
# =====================================================
"""
Test per LocationRepository - testa tutte le funzionalità HACCP location management.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from decimal import Decimal
from sqlalchemy import text

# Clean imports - no path manipulation needed
from src.models import Organization, Location, Sensor, User
from src.repositories.location_repository import LocationRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def location_repository(test_db):
    """Create LocationRepository instance"""
    return LocationRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Location Test Company",
        slug="location-test-company",
        subscription_plan="premium",
        max_sensors=100,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def sample_location_data(sample_organization):
    """Sample location data for testing"""
    return {
        "organization_id": sample_organization.id,
        "name": "Main Freezer Unit A",
        "description": "Primary freezer for storing frozen foods and ice cream",
        "location_type": "freezer",
        "temperature_min": Decimal('-25.0'),
        "temperature_max": Decimal('-15.0'),
        "humidity_min": Decimal('10.0'),
        "humidity_max": Decimal('30.0'),
        "floor": "Ground",
        "zone": "Kitchen-North"
        # Note: deliberately omitting coordinates to test NULL handling
    }

@pytest.fixture
def sample_location_data_with_coords(sample_organization):
    """Sample location data with coordinates for testing"""
    return {
        "organization_id": sample_organization.id,
        "name": "Main Freezer Unit A",
        "description": "Primary freezer for storing frozen foods and ice cream",
        "location_type": "freezer",
        "temperature_min": Decimal('-25.0'),
        "temperature_max": Decimal('-15.0'),
        "humidity_min": Decimal('10.0'),
        "humidity_max": Decimal('30.0'),
        "floor": "Ground",
        "zone": "Kitchen-North",
        "coordinates": {"lat": 45.6684, "lng": 11.9564}  # Treviso coordinates
    }

@pytest.fixture
def created_location(location_repository, sample_location_data):
    """Create and return a test location"""
    return location_repository.create(sample_location_data)

@pytest.fixture
def second_organization(test_db):
    """Create second organization for multi-tenancy tests"""
    org = Organization(
        name="Second Location Test Company",
        slug="second-location-test-company",
        subscription_plan="basic",
        max_sensors=20,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestLocationCRUD:
    """Test basic CRUD operations"""
    
    def test_create_location_success(self, location_repository, sample_location_data):
        """Test creating a new location"""
        
        # Act
        location = location_repository.create(sample_location_data)
        
        # Assert
        assert location.id is not None
        assert location.name == sample_location_data["name"]
        assert location.description == sample_location_data["description"]
        assert location.location_type == sample_location_data["location_type"]
        assert location.temperature_min == sample_location_data["temperature_min"]
        assert location.temperature_max == sample_location_data["temperature_max"]
        assert location.humidity_min == sample_location_data["humidity_min"]
        assert location.humidity_max == sample_location_data["humidity_max"]
        assert location.floor == sample_location_data["floor"]
        assert location.zone == sample_location_data["zone"]
        assert location.coordinates is None  # No coordinates in default fixture
        assert location.organization_id == sample_location_data["organization_id"]
        
        # Verify timestamps
        assert location.created_at is not None
        assert location.updated_at is not None
        
        print(f"✅ Location created with ID: {location.id}")
        print(f"✅ Name: {location.name}, Type: {location.location_type}")
        print(f"✅ Temperature range: {location.temperature_min}°C to {location.temperature_max}°C")
        print(f"✅ Coordinates: {location.coordinates} (None as expected)")
    
    def test_get_by_id(self, location_repository, created_location):
        """Test getting location by ID"""
        # Act
        found_location = location_repository.get_by_id(created_location.id)
        
        # Assert
        assert found_location is not None
        assert found_location.id == created_location.id
        assert found_location.name == created_location.name
        assert found_location.location_type == created_location.location_type
        
        print(f"✅ Location found by ID: {found_location.id}")
    
    def test_get_by_id_not_found(self, location_repository):
        """Test getting non-existent location"""
        # Act
        found_location = location_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_location is None
        print("✅ Non-existent location correctly returned None")
    
    def test_update_location(self, location_repository, created_location):
        """Test updating location"""
        # Arrange
        update_data = {
            "name": "Updated Freezer Unit A",
            "description": "Updated description for main freezer",
            "temperature_min": Decimal('-30.0'),
            "temperature_max": Decimal('-10.0'),
            "zone": "Kitchen-South"
        }
        
        # Act
        updated_location = location_repository.update(created_location.id, update_data)
        
        # Assert
        assert updated_location is not None
        assert updated_location.name == "Updated Freezer Unit A"
        assert updated_location.description == "Updated description for main freezer"
        assert updated_location.temperature_min == Decimal('-30.0')
        assert updated_location.temperature_max == Decimal('-10.0')
        assert updated_location.zone == "Kitchen-South"
        # Check unchanged fields
        assert updated_location.location_type == created_location.location_type
        assert updated_location.organization_id == created_location.organization_id
        
        print(f"✅ Location updated successfully")
    
    def test_delete_location(self, location_repository, created_location):
        """Test deleting location"""
        # Act
        result = location_repository.delete(created_location.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_location = location_repository.get_by_id(created_location.id)
        assert found_location is None
        
        print(f"✅ Location deleted successfully")
    
    def test_delete_nonexistent_location(self, location_repository):
        """Test deleting non-existent location"""
        # Act
        result = location_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent location correctly returned False")

# =====================================================
# TEST LOCATION-SPECIFIC QUERIES
# =====================================================

class TestLocationQueries:
    """Test location-specific query methods"""
    
    def test_get_by_organization(self, location_repository, sample_organization, sample_location_data):
        """Test getting locations by organization"""
        # Arrange - Create multiple locations
        loc1 = location_repository.create(sample_location_data)
        loc2 = location_repository.create({
            **sample_location_data,
            "name": "Secondary Fridge",
            "location_type": "fridge",
            "temperature_min": Decimal('2.0'),
            "temperature_max": Decimal('8.0')
        })
        
        # Act
        org_locations = location_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_locations) >= 2
        location_ids = [loc.id for loc in org_locations]
        assert loc1.id in location_ids
        assert loc2.id in location_ids
        assert all(loc.organization_id == sample_organization.id for loc in org_locations)
        
        print(f"✅ Found {len(org_locations)} locations in organization")
    
    def test_get_by_type(self, location_repository, sample_organization, sample_location_data):
        """Test getting locations by type"""
        # Arrange - Create locations of different types
        freezer = location_repository.create({
            **sample_location_data,
            "name": "Freezer A",
            "location_type": "freezer"
        })
        
        fridge = location_repository.create({
            **sample_location_data,
            "name": "Fridge B",
            "location_type": "fridge",
            "temperature_min": Decimal('2.0'),
            "temperature_max": Decimal('8.0')
        })
        
        cold_room = location_repository.create({
            **sample_location_data,
            "name": "Cold Room C",
            "location_type": "cold_room",
            "temperature_min": Decimal('0.0'),
            "temperature_max": Decimal('4.0')
        })
        
        # Act
        freezers = location_repository.get_by_type(sample_organization.id, "freezer")
        fridges = location_repository.get_by_type(sample_organization.id, "fridge")
        
        # Assert
        freezer_ids = [loc.id for loc in freezers]
        fridge_ids = [loc.id for loc in fridges]
        
        assert freezer.id in freezer_ids
        assert fridge.id in fridge_ids
        assert cold_room.id not in freezer_ids
        assert cold_room.id not in fridge_ids
        assert all(loc.location_type == "freezer" for loc in freezers)
        assert all(loc.location_type == "fridge" for loc in fridges)
        
        print(f"✅ Found {len(freezers)} freezers and {len(fridges)} fridges")
    
    def test_get_freezers(self, location_repository, sample_organization, sample_location_data):
        """Test getting freezer locations specifically"""
        # Arrange
        freezer1 = location_repository.create({
            **sample_location_data,
            "name": "Freezer Unit 1",
            "location_type": "freezer"
        })
        
        freezer2 = location_repository.create({
            **sample_location_data,
            "name": "Freezer Unit 2", 
            "location_type": "freezer",
            "temperature_min": Decimal('-30.0'),
            "temperature_max": Decimal('-20.0')
        })
        
        # Create non-freezer location
        fridge = location_repository.create({
            **sample_location_data,
            "name": "Fridge Unit",
            "location_type": "fridge",
            "temperature_min": Decimal('2.0'),
            "temperature_max": Decimal('8.0')
        })
        
        # Act
        freezers = location_repository.get_freezers(sample_organization.id)
        
        # Assert
        freezer_ids = [f.id for f in freezers]
        assert freezer1.id in freezer_ids
        assert freezer2.id in freezer_ids
        assert fridge.id not in freezer_ids
        assert all(f.location_type == "freezer" for f in freezers)
        
        print(f"✅ Found {len(freezers)} freezer locations")
    
    def test_get_fridges(self, location_repository, sample_organization, sample_location_data):
        """Test getting fridge locations specifically"""
        # Arrange
        fridge1 = location_repository.create({
            **sample_location_data,
            "name": "Fridge Unit 1",
            "location_type": "fridge",
            "temperature_min": Decimal('1.0'),
            "temperature_max": Decimal('6.0')
        })
        
        fridge2 = location_repository.create({
            **sample_location_data,
            "name": "Fridge Unit 2",
            "location_type": "fridge", 
            "temperature_min": Decimal('3.0'),
            "temperature_max": Decimal('9.0')
        })
        
        # Create non-fridge location
        freezer = location_repository.create({
            **sample_location_data,
            "name": "Freezer Unit",
            "location_type": "freezer"
        })
        
        # Act
        fridges = location_repository.get_fridges(sample_organization.id)
        
        # Assert
        fridge_ids = [f.id for f in fridges]
        assert fridge1.id in fridge_ids
        assert fridge2.id in fridge_ids
        assert freezer.id not in fridge_ids
        assert all(f.location_type == "fridge" for f in fridges)
        
        print(f"✅ Found {len(fridges)} fridge locations")
    
    def test_search_by_name(self, location_repository, sample_organization, sample_location_data):
        """Test searching locations by name"""
        # Arrange - Create locations with different names
        kitchen_freezer = location_repository.create({
            **sample_location_data,
            "name": "Kitchen Main Freezer",
            "location_type": "freezer"
        })
        
        storage_freezer = location_repository.create({
            **sample_location_data,
            "name": "Storage Room Freezer",
            "location_type": "freezer",
            "zone": "Storage"
        })
        
        kitchen_fridge = location_repository.create({
            **sample_location_data,
            "name": "Kitchen Prep Fridge", 
            "location_type": "fridge",
            "temperature_min": Decimal('2.0'),
            "temperature_max": Decimal('8.0')
        })
        
        # Act - Search for "Kitchen"
        kitchen_results = location_repository.search_by_name(sample_organization.id, "Kitchen")
        freezer_results = location_repository.search_by_name(sample_organization.id, "Freezer")
        
        # Assert
        kitchen_ids = [loc.id for loc in kitchen_results]
        freezer_ids = [loc.id for loc in freezer_results]
        
        assert kitchen_freezer.id in kitchen_ids
        assert kitchen_fridge.id in kitchen_ids
        assert storage_freezer.id not in kitchen_ids
        
        assert kitchen_freezer.id in freezer_ids
        assert storage_freezer.id in freezer_ids
        assert kitchen_fridge.id not in freezer_ids
        
        print(f"✅ Search 'Kitchen': {len(kitchen_results)} results")
        print(f"✅ Search 'Freezer': {len(freezer_results)} results")

# =====================================================
# TEST SENSOR RELATIONSHIP QUERIES
# =====================================================

class TestLocationSensorRelationships:
    """Test location-sensor relationship queries"""
    
    def test_get_with_sensor_count(self, location_repository, test_db, sample_organization, sample_location_data):
        """Test getting locations with sensor count"""
        # Arrange - Create locations
        location_with_sensors = location_repository.create({
            **sample_location_data,
            "name": "Location with Sensors"
        })
        
        location_without_sensors = location_repository.create({
            **sample_location_data,
            "name": "Location without Sensors",
            "zone": "Different Zone"
        })
        
        # Create sensors for first location
        sensor1 = Sensor(
            organization_id=sample_organization.id,
            location_id=location_with_sensors.id,
            device_id="SENSOR_WITH_LOC_001",
            name="Temperature Sensor 1",
            sensor_type="temperature_humidity",
            status="online"
        )
        
        sensor2 = Sensor(
            organization_id=sample_organization.id,
            location_id=location_with_sensors.id,
            device_id="SENSOR_WITH_LOC_002", 
            name="Temperature Sensor 2",
            sensor_type="temperature_humidity",
            status="online"
        )
        
        test_db.add_all([sensor1, sensor2])
        test_db.commit()
        
        # Act
        locations_with_counts = location_repository.get_with_sensor_count(sample_organization.id)
        
        # Assert
        locations_dict = {item["location"].id: item["sensor_count"] for item in locations_with_counts}
        
        assert location_with_sensors.id in locations_dict
        assert location_without_sensors.id in locations_dict
        assert locations_dict[location_with_sensors.id] == 2
        assert locations_dict[location_without_sensors.id] == 0
        
        print(f"✅ Location with sensors has {locations_dict[location_with_sensors.id]} sensors")
        print(f"✅ Location without sensors has {locations_dict[location_without_sensors.id]} sensors")

# =====================================================
# TEST LOCATION BUSINESS LOGIC
# =====================================================

class TestLocationBusinessLogic:
    """Test location business logic and properties"""
    
    def test_location_properties(self, location_repository, sample_location_data):
        """Test location model properties"""
        # Create location
        location = location_repository.create(sample_location_data)
        
        # Test sensor_count property (initially 0)
        assert location.sensor_count == 0
        
        # Test temperature validation
        assert location.is_temperature_valid(-20.0) == True  # Within range
        assert location.is_temperature_valid(-30.0) == False  # Below min
        assert location.is_temperature_valid(-10.0) == False  # Above max
        
        # Test humidity validation
        assert location.is_humidity_valid(20.0) == True   # Within range
        assert location.is_humidity_valid(5.0) == False   # Below min
        assert location.is_humidity_valid(35.0) == False  # Above max
        
        # Test temperature range getter
        temp_range = location.get_temperature_range()
        assert temp_range["min"] == -25.0
        assert temp_range["max"] == -15.0
        
        print(f"✅ Location business logic working correctly")
        print(f"   - sensor_count: {location.sensor_count}")
        print(f"   - temperature_range: {temp_range}")
    
    def test_location_with_sensors(self, location_repository, test_db, sample_organization, sample_location_data):
        """Test location properties when it has sensors"""
        # Create location
        location = location_repository.create(sample_location_data)
        
        # Add sensors to location
        sensor1 = Sensor(
            organization_id=sample_organization.id,
            location_id=location.id,
            device_id="LOC_LOGIC_SENSOR_001",
            name="Logic Test Sensor 1",
            sensor_type="temperature_humidity",
            status="online"
        )
        
        sensor2 = Sensor(
            organization_id=sample_organization.id,
            location_id=location.id,
            device_id="LOC_LOGIC_SENSOR_002",
            name="Logic Test Sensor 2",
            sensor_type="temperature_humidity",
            status="offline"
        )
        
        test_db.add_all([sensor1, sensor2])
        test_db.commit()
        test_db.refresh(location)  # Refresh to load relationships
        
        # Test sensor count with actual sensors
        assert location.sensor_count == 2
        
        print(f"✅ Location with sensors: sensor_count = {location.sensor_count}")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestLocationMultiTenancy:
    """Test multi-tenancy isolation for locations"""
    
    def test_organization_isolation(self, location_repository, sample_organization, second_organization, sample_location_data):
        """Test that locations are isolated by organization"""
        
        # Create locations in different organizations
        loc1 = location_repository.create({
            **sample_location_data,
            "organization_id": sample_organization.id,
            "name": "Org1 Location"
        })
        
        loc2 = location_repository.create({
            **sample_location_data,
            "organization_id": second_organization.id,
            "name": "Org2 Location"
        })
        
        # Test isolation using organization-specific queries
        org1_locations = location_repository.get_by_organization(sample_organization.id)
        org2_locations = location_repository.get_by_organization(second_organization.id)
        
        # Assert isolation
        org1_location_ids = [loc.id for loc in org1_locations]
        org2_location_ids = [loc.id for loc in org2_locations]
        
        assert loc1.id in org1_location_ids
        assert loc1.id not in org2_location_ids
        assert loc2.id in org2_location_ids
        assert loc2.id not in org1_location_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")
        print(f"   - Org1 locations: {len(org1_locations)}")
        print(f"   - Org2 locations: {len(org2_locations)}")

# =====================================================
# TEST LOCATION CONSTRAINTS AND VALIDATION
# =====================================================

class TestLocationConstraints:
    """Test location database constraints and validation"""
    
    def test_location_type_constraint(self, location_repository, sample_location_data):
        """Test location type constraint validation"""
        # Valid location types should work
        valid_types = ['freezer', 'fridge', 'cold_room', 'outdoor', 'kitchen', 'storage']
        
        for location_type in valid_types:
            location = location_repository.create({
                **sample_location_data,
                "name": f"Test {location_type}",
                "location_type": location_type
            })
            assert location.location_type == location_type
        
        print(f"✅ All valid location types work correctly")
    
    def test_coordinates_validation(self, location_repository, sample_location_data_with_coords):
        """Test coordinates JSON validation"""
        # Valid coordinates - MUST have both 'lat' and 'lng' keys per DB constraint
        valid_coords = {"lat": 45.6684, "lng": 11.9564}
        location = location_repository.create({
            **sample_location_data_with_coords,
            "name": "Valid Coordinates Location",
            "coordinates": valid_coords
        })
        assert location.coordinates == valid_coords
        
        # Test without coordinates field (omit coordinates completely)
        location_data_no_coords = {k: v for k, v in sample_location_data_with_coords.items() if k != 'coordinates'}
        location_no_coords = location_repository.create({
            **location_data_no_coords,
            "name": "No Coordinates Location"
        })
        assert location_no_coords.coordinates is None
        
        # Test invalid coordinates (missing 'lng') should fail
        try:
            invalid_coords = {"lat": 45.6684}  # Missing 'lng'
            location_repository.create({
                **sample_location_data_with_coords,
                "name": "Invalid Coordinates Location",
                "coordinates": invalid_coords
            })
            assert False, "Should have failed due to missing 'lng' key"
        except Exception as e:
            # Expected to fail due to DB constraint
            assert "chk_coordinates_structure" in str(e) or "constraint" in str(e).lower()
        
        print(f"✅ Coordinates validation working correctly")
    
    def test_temperature_range_logic(self, location_repository, sample_location_data):
        """Test temperature range logical constraints"""
        # Valid range
        location = location_repository.create({
            **sample_location_data,
            "name": "Valid Temp Range",
            "temperature_min": Decimal('-20.0'),
            "temperature_max": Decimal('-10.0')
        })
        assert location.temperature_min < location.temperature_max
        
        # Only min or max (should be allowed)
        location_min_only = location_repository.create({
            **sample_location_data,
            "name": "Min Only Location",
            "temperature_min": Decimal('-25.0'),
            "temperature_max": None
        })
        assert location_min_only.temperature_min == Decimal('-25.0')
        assert location_min_only.temperature_max is None
        
        print(f"✅ Temperature range logic working correctly")

# =====================================================
# TEST EDGE CASES AND ERROR SCENARIOS
# =====================================================

class TestLocationEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cascade_delete_organization(self, test_db, location_repository, sample_location_data):
        """Test what happens when organization is deleted"""
        # Create temporary organization
        temp_org = Organization(
            name="Temp Org for Delete Test",
            slug="temp-org-delete-locations",
            subscription_plan="basic"
        )
        test_db.add(temp_org)
        test_db.commit()
        test_db.refresh(temp_org)
        
        # Create location in temp organization
        location = location_repository.create({
            **sample_location_data,
            "organization_id": temp_org.id,
            "name": "Location to be deleted"
        })
        
        # Act - Delete organization (should cascade)
        test_db.delete(temp_org)
        test_db.commit()
        
        # Assert - Location should be gone due to CASCADE
        found_location = location_repository.get_by_id(location.id)
        assert found_location is None
        
        print(f"✅ Cascade delete working correctly")
    
    def test_location_with_special_characters(self, location_repository, sample_location_data):
        """Test location with special characters and unicode"""
        # Create location with special characters
        special_location = location_repository.create({
            **sample_location_data,
            "name": "Freezer Ñ°1 - Main (Kitchen)",
            "description": "Frigo principale con caratteri speciali: àèìòù",
            "zone": "Cucina-Nord/Est"
        })
        
        assert "Ñ°1" in special_location.name
        assert "àèìòù" in special_location.description
        assert "Nord/Est" in special_location.zone
        
        print(f"✅ Special characters handling working correctly")
    
    def test_extreme_coordinate_values(self, location_repository, sample_location_data):
        """Test extreme but valid coordinate values"""
        # Test extreme valid coordinates
        extreme_coords = {"lat": -89.9999, "lng": 179.9999}
        extreme_location = location_repository.create({
            **sample_location_data,
            "name": "Extreme Coordinates Location",
            "coordinates": extreme_coords
        })
        
        assert extreme_location.coordinates["lat"] == -89.9999
        assert extreme_location.coordinates["lng"] == 179.9999
        
        print(f"✅ Extreme coordinates handling working correctly")

# =====================================================
# TEST PERFORMANCE AND LARGE DATASETS
# =====================================================

class TestLocationPerformance:
    """Test location repository performance"""
    
    def test_large_location_volume(self, location_repository, sample_organization, sample_location_data):
        """Test handling large volume of locations"""
        import time
        
        # Arrange
        start_time = time.time()
        location_count = 20  # Reasonable number for testing
        
        # Act - Create multiple locations
        created_locations = []
        location_types = ['freezer', 'fridge', 'cold_room', 'storage', 'kitchen']
        
        for i in range(location_count):
            loc_data = {
                **sample_location_data,
                "name": f"Performance Test Location {i:03d}",
                "location_type": location_types[i % len(location_types)],
                "zone": f"Zone-{i // 5}",
                "coordinates": {"lat": 45.6684 + (i * 0.001), "lng": 11.9564 + (i * 0.001)}
            }
            location = location_repository.create(loc_data)
            created_locations.append(location)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_locations) == location_count
        assert duration < 10  # Should complete within 10 seconds
        
        # Test bulk queries performance
        start_query_time = time.time()
        all_org_locations = location_repository.get_by_organization(sample_organization.id)
        end_query_time = time.time()
        query_duration = end_query_time - start_query_time
        
        assert len(all_org_locations) >= location_count
        assert query_duration < 2  # Query should be fast
        
        print(f"✅ Created {location_count} locations in {duration:.2f} seconds")
        print(f"✅ Queried {len(all_org_locations)} locations in {query_duration:.3f} seconds")
        print(f"✅ Average: {duration/location_count:.3f} seconds per location")

# =====================================================
# TEST HACCP COMPLIANCE SCENARIOS
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance scenarios for locations"""
    
    def test_temperature_monitoring_setup(self, location_repository, sample_organization, sample_location_data):
        """Test proper HACCP temperature monitoring setup"""
        # Create different types of HACCP critical locations
        freezer = location_repository.create({
            **sample_location_data,
            "name": "HACCP Critical Freezer",
            "location_type": "freezer",
            "temperature_min": Decimal('-25.0'),
            "temperature_max": Decimal('-18.0'),  # HACCP freezer requirements
            "description": "Critical freezer for frozen food storage - HACCP monitored"
        })
        
        fridge = location_repository.create({
            **sample_location_data,
            "name": "HACCP Critical Fridge",
            "location_type": "fridge", 
            "temperature_min": Decimal('0.0'),
            "temperature_max": Decimal('4.0'),  # HACCP fridge requirements
            "description": "Critical fridge for fresh food storage - HACCP monitored"
        })
        
        cold_room = location_repository.create({
            **sample_location_data,
            "name": "HACCP Cold Room",
            "location_type": "cold_room",
            "temperature_min": Decimal('-2.0'),
            "temperature_max": Decimal('2.0'),  # HACCP cold room requirements
            "description": "Critical cold room for meat storage - HACCP monitored"
        })
        
        # Test that temperature validation works for HACCP compliance
        assert freezer.is_temperature_valid(-20.0) == True   # Compliant
        assert freezer.is_temperature_valid(-15.0) == False  # Too warm
        
        assert fridge.is_temperature_valid(2.0) == True     # Compliant
        assert fridge.is_temperature_valid(6.0) == False    # Too warm
        
        assert cold_room.is_temperature_valid(0.0) == True  # Compliant
        assert cold_room.is_temperature_valid(3.0) == False # Too warm
        
        print(f"✅ HACCP temperature monitoring setup working correctly")
        print(f"   - Freezer range: {freezer.temperature_min}°C to {freezer.temperature_max}°C")
        print(f"   - Fridge range: {fridge.temperature_min}°C to {fridge.temperature_max}°C")
        print(f"   - Cold room range: {cold_room.temperature_min}°C to {cold_room.temperature_max}°C")
    
    def test_location_compliance_categorization(self, location_repository, sample_organization, sample_location_data):
        """Test categorizing locations by HACCP compliance criticality"""
        # Create locations with different criticality levels
        critical_freezer = location_repository.create({
            **sample_location_data,
            "name": "Critical Storage Freezer",
            "location_type": "freezer",
            "temperature_min": Decimal('-25.0'),
            "temperature_max": Decimal('-18.0'),
            "zone": "Critical-Storage"
        })
        
        standard_fridge = location_repository.create({
            **sample_location_data,
            "name": "Standard Kitchen Fridge",
            "location_type": "fridge",
            "temperature_min": Decimal('2.0'),
            "temperature_max": Decimal('8.0'),
            "zone": "Kitchen-Standard"
        })
        
        non_critical_storage = location_repository.create({
            **sample_location_data,
            "name": "Dry Storage Room",
            "location_type": "storage",
            "temperature_min": None,  # No temperature requirements
            "temperature_max": None,
            "zone": "Non-Critical"
        })
        
        # Get all locations and categorize by criticality
        all_locations = location_repository.get_by_organization(sample_organization.id)
        
        critical_locations = [loc for loc in all_locations 
                            if loc.temperature_min is not None and loc.temperature_max is not None]
        non_critical_locations = [loc for loc in all_locations 
                                if loc.temperature_min is None and loc.temperature_max is None]
        
        # Assert categorization
        critical_ids = [loc.id for loc in critical_locations]
        non_critical_ids = [loc.id for loc in non_critical_locations]
        
        assert critical_freezer.id in critical_ids
        assert standard_fridge.id in critical_ids
        assert non_critical_storage.id in non_critical_ids
        
        print(f"✅ HACCP compliance categorization working correctly")
        print(f"   - Critical locations: {len(critical_locations)}")
        print(f"   - Non-critical locations: {len(non_critical_locations)}")

# =====================================================
# TEST LOCATION RELATIONSHIPS AND JOINS
# =====================================================

class TestLocationRelationships:
    """Test location relationships and database joins"""
    
    def test_organization_relationship(self, location_repository, created_location):
        """Test location-organization relationship"""
        # Act
        location = location_repository.get_by_id(created_location.id)
        
        # Assert
        assert location.organization is not None
        assert location.organization.id == location.organization_id
        assert location.organization.name is not None
        
        print(f"✅ Organization relationship working: {location.organization.name}")
    
    def test_sensors_relationship(self, location_repository, test_db, sample_organization, created_location):
        """Test location-sensors relationship"""
        # Create sensors for the location
        sensor1 = Sensor(
            organization_id=sample_organization.id,
            location_id=created_location.id,
            device_id="RELATIONSHIP_TEST_001",
            name="Relationship Test Sensor 1",
            sensor_type="temperature_humidity",
            status="online"
        )
        
        sensor2 = Sensor(
            organization_id=sample_organization.id,
            location_id=created_location.id,
            device_id="RELATIONSHIP_TEST_002",
            name="Relationship Test Sensor 2", 
            sensor_type="temperature_humidity",
            status="offline"
        )
        
        test_db.add_all([sensor1, sensor2])
        test_db.commit()
        test_db.refresh(created_location)  # Refresh to load relationships
        
        # Act & Assert
        assert len(created_location.sensors) == 2
        sensor_ids = [s.id for s in created_location.sensors]
        assert sensor1.id in sensor_ids
        assert sensor2.id in sensor_ids
        assert all(s.location_id == created_location.id for s in created_location.sensors)
        
        print(f"✅ Sensors relationship working: {len(created_location.sensors)} sensors")
    
    def test_cascade_delete_sensors(self, location_repository, test_db, sample_organization, sample_location_data):
        """Test that deleting location cascades to sensors"""
        # Create location
        location = location_repository.create({
            **sample_location_data,
            "name": "Location for Cascade Test"
        })
        
        # Create sensors
        sensor1 = Sensor(
            organization_id=sample_organization.id,
            location_id=location.id,
            device_id="CASCADE_TEST_001",
            name="Cascade Test Sensor 1",
            sensor_type="temperature_humidity",
            status="online"
        )
        
        sensor2 = Sensor(
            organization_id=sample_organization.id,
            location_id=location.id,
            device_id="CASCADE_TEST_002",
            name="Cascade Test Sensor 2",
            sensor_type="temperature_humidity", 
            status="online"
        )
        
        test_db.add_all([sensor1, sensor2])
        test_db.commit()
        
        sensor1_id = sensor1.id
        sensor2_id = sensor2.id
        
        # Delete location
        location_repository.delete(location.id)
        
        # Assert sensors are deleted too (cascade)
        remaining_sensor1 = test_db.query(Sensor).filter(Sensor.id == sensor1_id).first()
        remaining_sensor2 = test_db.query(Sensor).filter(Sensor.id == sensor2_id).first()
        
        assert remaining_sensor1 is None
        assert remaining_sensor2 is None
        
        print(f"✅ Cascade delete to sensors working correctly")

# =====================================================
# TEST COMPLEX QUERIES AND FILTERING
# =====================================================

class TestLocationComplexQueries:
    """Test complex location queries and filtering scenarios"""
    
    def test_combined_filtering(self, location_repository, sample_organization, sample_location_data):
        """Test complex filtering combining multiple criteria"""
        # Create diverse set of locations
        locations_data = [
            {
                **sample_location_data,
                "name": "Kitchen Main Freezer",
                "location_type": "freezer",
                "zone": "Kitchen-Main",
                "floor": "Ground"
            },
            {
                **sample_location_data,
                "name": "Kitchen Secondary Fridge",
                "location_type": "fridge",
                "zone": "Kitchen-Main",
                "floor": "Ground",
                "temperature_min": Decimal('2.0'),
                "temperature_max": Decimal('8.0')
            },
            {
                **sample_location_data,
                "name": "Basement Storage Freezer",
                "location_type": "freezer",
                "zone": "Storage-Cold",
                "floor": "Basement"
            },
            {
                **sample_location_data,
                "name": "First Floor Cold Room",
                "location_type": "cold_room",
                "zone": "Processing",
                "floor": "First",
                "temperature_min": Decimal('-5.0'),
                "temperature_max": Decimal('0.0')
            }
        ]
        
        created_locations = []
        for loc_data in locations_data:
            location = location_repository.create(loc_data)
            created_locations.append(location)
        
        # Test various filtering combinations
        
        # 1. Get all kitchen locations
        kitchen_search = location_repository.search_by_name(sample_organization.id, "Kitchen")
        kitchen_names = [loc.name for loc in kitchen_search]
        assert any("Kitchen Main Freezer" in name for name in kitchen_names)
        assert any("Kitchen Secondary Fridge" in name for name in kitchen_names)
        
        # 2. Get all freezers
        freezers = location_repository.get_freezers(sample_organization.id)
        freezer_names = [loc.name for loc in freezers]
        assert any("Kitchen Main Freezer" in name for name in freezer_names)
        assert any("Basement Storage Freezer" in name for name in freezer_names)
        
        # 3. Get all locations by type
        fridges = location_repository.get_by_type(sample_organization.id, "fridge")
        cold_rooms = location_repository.get_by_type(sample_organization.id, "cold_room")
        
        assert len(fridges) >= 1
        assert len(cold_rooms) >= 1
        
        print(f"✅ Complex filtering working correctly")
        print(f"   - Kitchen locations: {len(kitchen_search)}")
        print(f"   - Freezers: {len(freezers)}")
        print(f"   - Fridges: {len(fridges)}")
        print(f"   - Cold rooms: {len(cold_rooms)}")
    
    def test_sensor_count_accuracy(self, location_repository, test_db, sample_organization, sample_location_data):
        """Test accuracy of sensor count queries"""
        # Create locations with known sensor counts
        loc_0_sensors = location_repository.create({
            **sample_location_data,
            "name": "Location with 0 sensors"
        })
        
        loc_3_sensors = location_repository.create({
            **sample_location_data,
            "name": "Location with 3 sensors",
            "zone": "Zone-3"
        })
        
        # Add exactly 3 sensors to second location
        for i in range(3):
            sensor = Sensor(
                organization_id=sample_organization.id,
                location_id=loc_3_sensors.id,
                device_id=f"COUNT_TEST_SENSOR_{i:03d}",
                name=f"Count Test Sensor {i}",
                sensor_type="temperature_humidity",
                status="online"
            )
            test_db.add(sensor)
        
        test_db.commit()
        
        # Test sensor count query
        locations_with_counts = location_repository.get_with_sensor_count(sample_organization.id)
        counts_dict = {item["location"].id: item["sensor_count"] for item in locations_with_counts}
        
        assert counts_dict[loc_0_sensors.id] == 0
        assert counts_dict[loc_3_sensors.id] == 3
        
        print(f"✅ Sensor count accuracy verified")
        print(f"   - Location 1: {counts_dict[loc_0_sensors.id]} sensors")
        print(f"   - Location 2: {counts_dict[loc_3_sensors.id]} sensors")

# =====================================================
# TEST DATA INTEGRITY AND CONSISTENCY
# =====================================================

class TestLocationDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_unique_name_per_organization(self, location_repository, sample_organization, second_organization, sample_location_data):
        """Test that location names can be duplicate across organizations but are tracked properly"""
        # Same name in different organizations should be allowed
        loc1 = location_repository.create({
            **sample_location_data,
            "organization_id": sample_organization.id,
            "name": "Main Freezer"
        })
        
        loc2 = location_repository.create({
            **sample_location_data,
            "organization_id": second_organization.id,
            "name": "Main Freezer"  # Same name, different org
        })
        
        # Both should exist and be isolated
        org1_locations = location_repository.get_by_organization(sample_organization.id)
        org2_locations = location_repository.get_by_organization(second_organization.id)
        
        org1_names = [loc.name for loc in org1_locations]
        org2_names = [loc.name for loc in org2_locations]
        
        assert "Main Freezer" in org1_names
        assert "Main Freezer" in org2_names
        assert loc1.id != loc2.id
        
        print(f"✅ Name isolation across organizations working correctly")
    
    def test_coordinate_precision(self, location_repository, sample_location_data):
        """Test coordinate precision and storage"""
        # Test high precision coordinates
        precise_coords = {"lat": 45.668412345, "lng": 11.956453789}
        location = location_repository.create({
            **sample_location_data,
            "name": "High Precision Location",
            "coordinates": precise_coords
        })
        
        # Coordinates should be stored and retrieved accurately
        assert abs(location.coordinates["lat"] - precise_coords["lat"]) < 0.000001
        assert abs(location.coordinates["lng"] - precise_coords["lng"]) < 0.000001
        
        print(f"✅ Coordinate precision maintained")
        print(f"   - Stored: {location.coordinates}")
        print(f"   - Original: {precise_coords}")
    
    def test_decimal_precision(self, location_repository, sample_location_data):
        """Test decimal precision for temperature values"""
        # Test decimal temperatures within DECIMAL(5,2) precision limits
        # DECIMAL(5,2) = 5 total digits, 2 after decimal: -999.99 to 999.99
        precise_location = location_repository.create({
            **sample_location_data,
            "name": "Precise Temperature Location",
            "temperature_min": Decimal('-23.12'),  # Within DECIMAL(5,2) precision
            "temperature_max": Decimal('-17.87'),  # Within DECIMAL(5,2) precision  
            "humidity_min": Decimal('12.50'),      # Within DECIMAL(5,2) precision
            "humidity_max": Decimal('27.50')       # Within DECIMAL(5,2) precision
        })
        
        # Precision should be maintained for DECIMAL(5,2)
        assert precise_location.temperature_min == Decimal('-23.12')
        assert precise_location.temperature_max == Decimal('-17.87')
        assert precise_location.humidity_min == Decimal('12.50')
        assert precise_location.humidity_max == Decimal('27.50')
        
        print(f"✅ Decimal precision maintained for temperatures")
        print(f"   - DECIMAL(5,2) format: max 999.99, min -999.99")
        print(f"   - Temp min: {precise_location.temperature_min}")
        print(f"   - Temp max: {precise_location.temperature_max}")
    
    def test_decimal_precision_limits(self, location_repository, sample_location_data):
        """Test decimal precision limits and rounding"""
        # Test that values get rounded to 2 decimal places as per DECIMAL(5,2)
        location_with_rounding = location_repository.create({
            **sample_location_data,
            "name": "Rounding Test Location",
            "temperature_min": Decimal('-23.126'),  # Should round to -23.13
            "temperature_max": Decimal('-17.874'),  # Should round to -17.87
        })
        
        # Values should be rounded to 2 decimal places
        assert location_with_rounding.temperature_min == Decimal('-23.13')  # Rounded up
        assert location_with_rounding.temperature_max == Decimal('-17.87')  # Rounded down
        
        print(f"✅ Decimal rounding working correctly for DECIMAL(5,2)")
        print(f"   - -23.126 → {location_with_rounding.temperature_min}")
        print(f"   - -17.874 → {location_with_rounding.temperature_max}")

# =====================================================
# TEST LOCATION AUDIT AND LOGGING
# =====================================================

class TestLocationAuditScenarios:
    """Test location audit and logging scenarios"""
    
    def test_location_lifecycle_tracking(self, location_repository, sample_location_data):
        """Test tracking of location lifecycle events"""
        # Create location
        location = location_repository.create(sample_location_data)
        creation_time = location.created_at
        initial_update_time = location.updated_at
        
        # Wait a moment and update
        import time
        time.sleep(0.1)
        
        updated_location = location_repository.update(location.id, {
            "name": "Updated Location Name",
            "description": "Updated description"
        })
        
        # Timestamps should reflect the changes
        assert updated_location.created_at == creation_time  # Should not change
        assert updated_location.updated_at > initial_update_time  # Should be updated
        
        print(f"✅ Location lifecycle tracking working")
        print(f"   - Created: {creation_time}")
        print(f"   - Updated: {updated_location.updated_at}")
    
    def test_location_change_detection(self, location_repository, sample_location_data):
        """Test detection of significant location changes"""
        # Create location
        location = location_repository.create(sample_location_data)
        original_temp_min = location.temperature_min
        original_temp_max = location.temperature_max
        
        # Make significant temperature threshold changes
        updated_location = location_repository.update(location.id, {
            "temperature_min": Decimal('-30.0'),  # Significant change
            "temperature_max": Decimal('-10.0'),  # Significant change
            "description": "HACCP thresholds updated due to new requirements"
        })
        
        # Changes should be reflected
        assert updated_location.temperature_min != original_temp_min
        assert updated_location.temperature_max != original_temp_max
        assert "HACCP thresholds updated" in updated_location.description
        
        # Temperature validation should work with new ranges
        assert updated_location.is_temperature_valid(-25.0) == True   # Within new range
        assert updated_location.is_temperature_valid(-35.0) == False  # Below new min
        assert updated_location.is_temperature_valid(-5.0) == False   # Above new max
        
        print(f"✅ Location change detection working")
        print(f"   - Old range: {original_temp_min}°C to {original_temp_max}°C")
        print(f"   - New range: {updated_location.temperature_min}°C to {updated_location.temperature_max}°C")