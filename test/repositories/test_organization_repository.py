# =====================================================
# test/repositories/test_organization_repository.py - CLEAN VERSION
# =====================================================
"""
Test per OrganizationRepository - versione pulita senza path hacks.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from decimal import Decimal

# Clean imports - no path manipulation needed
from src.models import Organization
from src.repositories.organization_repository import OrganizationRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def organization_repository(test_db):
    """Create OrganizationRepository instance"""
    return OrganizationRepository(test_db)

@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing"""
    return {
        "name": "Test Company",
        "slug": "test-company",
        "subscription_plan": "free",
        "max_sensors": 10,
        "timezone": "UTC",
        "retention_months": 24,
        "auto_archive_enabled": True
    }

@pytest.fixture
def created_organization(organization_repository, sample_organization_data):
    """Create and return a test organization"""
    return organization_repository.create(sample_organization_data)

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestOrganizationCRUD:
    """Test basic CRUD operations"""
    
    def test_create_organization_success(self, organization_repository, sample_organization_data):
        """Test creating a new organization"""
        # Act
        org = organization_repository.create(sample_organization_data)
        
        # Assert
        assert org.id is not None
        assert org.name == sample_organization_data["name"]
        assert org.slug == sample_organization_data["slug"]
        assert org.subscription_plan == sample_organization_data["subscription_plan"]
        assert org.max_sensors == sample_organization_data["max_sensors"]
        assert org.timezone == sample_organization_data["timezone"]
        
        # Verify timestamps
        assert org.created_at is not None
        assert org.updated_at is not None
        
        print(f"✅ Organization created with ID: {org.id}")
    
    def test_get_by_id(self, organization_repository, created_organization):
        """Test getting organization by ID"""
        # Act
        found_org = organization_repository.get_by_id(created_organization.id)
        
        # Assert
        assert found_org is not None
        assert found_org.id == created_organization.id
        assert found_org.name == created_organization.name
        assert found_org.slug == created_organization.slug
        
        print(f"✅ Organization found by ID: {found_org.id}")
    
    def test_get_by_id_not_found(self, organization_repository):
        """Test getting non-existent organization"""
        # Act
        found_org = organization_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_org is None
        print("✅ Non-existent organization correctly returned None")
    
    def test_update_organization(self, organization_repository, created_organization):
        """Test updating organization"""
        # Arrange
        update_data = {
            "name": "Updated Company Name",
            "max_sensors": 100,
            "subscription_plan": "enterprise"
        }
        
        # Act
        updated_org = organization_repository.update(created_organization.id, update_data)
        
        # Assert
        assert updated_org is not None
        assert updated_org.name == "Updated Company Name"
        assert updated_org.max_sensors == 100
        assert updated_org.subscription_plan == "enterprise"
        # Check unchanged fields
        assert updated_org.slug == created_organization.slug
        assert updated_org.timezone == created_organization.timezone
        
        print(f"✅ Organization updated successfully")
    
    def test_update_nonexistent_organization(self, organization_repository):
        """Test updating non-existent organization"""
        # Act
        result = organization_repository.update(uuid.uuid4(), {"name": "Test"})
        
        # Assert
        assert result is None
        print("✅ Update of non-existent organization correctly returned None")
    
    def test_delete_organization(self, organization_repository, created_organization):
        """Test deleting organization"""
        # Act
        result = organization_repository.delete(created_organization.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_org = organization_repository.get_by_id(created_organization.id)
        assert found_org is None
        
        print(f"✅ Organization deleted successfully")
    
    def test_delete_nonexistent_organization(self, organization_repository):
        """Test deleting non-existent organization"""
        # Act
        result = organization_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent organization correctly returned False")
    
    def test_exists(self, organization_repository, created_organization):
        """Test exists method"""
        # Test existing
        assert organization_repository.exists(created_organization.id) == True
        
        # Test non-existing
        assert organization_repository.exists(uuid.uuid4()) == False
        
        print("✅ Exists method working correctly")
    
    def test_count(self, organization_repository, sample_organization_data):
        """Test count method"""
        # Initial count
        initial_count = organization_repository.count()
        
        # Create organizations
        organization_repository.create(sample_organization_data)
        organization_repository.create({
            **sample_organization_data, 
            "slug": "test-company-2", 
            "name": "Test Company 2"
        })
        
        # Check count
        new_count = organization_repository.count()
        assert new_count == initial_count + 2
        
        print(f"✅ Count increased from {initial_count} to {new_count}")

# =====================================================
# TEST ORGANIZATION-SPECIFIC QUERIES
# =====================================================

class TestOrganizationQueries:
    """Test organization-specific query methods"""
    
    def test_get_by_slug(self, organization_repository, created_organization):
        """Test getting organization by slug"""
        # Act
        found_org = organization_repository.get_by_slug("test-company")
        
        # Assert
        assert found_org is not None
        assert found_org.id == created_organization.id
        assert found_org.slug == "test-company"
        
        print(f"✅ Organization found by slug: {found_org.slug}")
    
    def test_get_by_slug_not_found(self, organization_repository):
        """Test getting organization by non-existent slug"""
        # Act
        found_org = organization_repository.get_by_slug("non-existent-slug")
        
        # Assert
        assert found_org is None
        print("✅ Non-existent slug correctly returned None")
    
    def test_get_by_subscription_plan(self, organization_repository, sample_organization_data):
        """Test getting organizations by subscription plan"""
        # Arrange - Create multiple organizations
        org1 = organization_repository.create(sample_organization_data)
        org2 = organization_repository.create({
            **sample_organization_data,
            "slug": "premium-org",
            "name": "Premium Org",
            "subscription_plan": "premium"
        })
        
        # Act
        free_orgs = organization_repository.get_by_subscription_plan("free")
        premium_orgs = organization_repository.get_by_subscription_plan("premium")
        
        # Assert
        assert len(free_orgs) >= 1
        assert len(premium_orgs) >= 1
        assert org1.id in [org.id for org in free_orgs]
        assert org2.id in [org.id for org in premium_orgs]
        
        print(f"✅ Found {len(free_orgs)} free orgs and {len(premium_orgs)} premium orgs")

# =====================================================
# VALIDATION TESTS
# =====================================================

class TestOrganizationValidation:
    """Test organization validation and constraints"""
    
    def test_create_duplicate_slug_should_fail(self, organization_repository, sample_organization_data):
        """Test that creating organization with duplicate slug fails"""
        # Arrange
        organization_repository.create(sample_organization_data)
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise IntegrityError
            organization_repository.create({
                **sample_organization_data, 
                "name": "Different Name"
            })
        
        print("✅ Duplicate slug correctly rejected")
    
    def test_update_with_invalid_field(self, organization_repository, created_organization):
        """Test updating with invalid field should be ignored"""
        # Act
        updated_org = organization_repository.update(created_organization.id, {
            "name": "Updated Name",
            "invalid_field": "should be ignored"
        })
        
        # Assert
        assert updated_org.name == "Updated Name"
        assert not hasattr(updated_org, "invalid_field")
        
        print("✅ Invalid field correctly ignored during update")
    
    def test_get_all_with_pagination(self, organization_repository, sample_organization_data):
        """Test get_all with pagination"""
        # Arrange - Create multiple organizations
        for i in range(5):
            organization_repository.create({
                **sample_organization_data,
                "slug": f"test-org-{i}",
                "name": f"Test Org {i}"
            })
        
        # Act
        first_page = organization_repository.get_all(skip=0, limit=2)
        second_page = organization_repository.get_all(skip=2, limit=2)
        
        # Assert
        assert len(first_page) == 2
        assert len(second_page) == 2
        
        # Ensure different results
        first_page_ids = [org.id for org in first_page]
        second_page_ids = [org.id for org in second_page]
        assert not any(id in second_page_ids for id in first_page_ids)
        
        print(f"✅ Pagination working: page 1 has {len(first_page)} items, page 2 has {len(second_page)} items")

# =====================================================
# INTEGRATION TESTS
# =====================================================

class TestOrganizationIntegration:
    """Integration tests with complete business logic"""
    
    def test_organization_lifecycle(self, organization_repository, sample_organization_data):
        """Test complete organization lifecycle"""
        # 1. Create
        org = organization_repository.create(sample_organization_data)
        assert org.name == "Test Company"
        print(f"✅ Step 1: Created organization {org.id}")
        
        # 2. Read
        found_org = organization_repository.get_by_slug("test-company")
        assert found_org.id == org.id
        print(f"✅ Step 2: Found organization by slug")
        
        # 3. Update
        updated_org = organization_repository.update(org.id, {
            "subscription_plan": "enterprise",
            "max_sensors": 200
        })
        assert updated_org.subscription_plan == "enterprise"
        print(f"✅ Step 3: Updated organization to enterprise plan")
        
        # 4. Verify update persisted
        reloaded_org = organization_repository.get_by_id(org.id)
        assert reloaded_org.subscription_plan == "enterprise"
        assert reloaded_org.max_sensors == 200
        print(f"✅ Step 4: Update persisted correctly")
        
        # 5. Delete
        delete_result = organization_repository.delete(org.id)
        assert delete_result == True
        print(f"✅ Step 5: Deleted organization")
        
        # 6. Verify deletion
        deleted_org = organization_repository.get_by_id(org.id)
        assert deleted_org is None
        print(f"✅ Step 6: Deletion verified - organization no longer exists")
        
        print("✅ Complete organization lifecycle test passed!")

# =====================================================
# RUN COMMAND INSTRUCTIONS
# =====================================================

"""
COME ESEGUIRE I TEST:

# Single test file
pytest test/repositories/test_organization_repository.py -v -s

# Specific test class
pytest test/repositories/test_organization_repository.py::TestOrganizationCRUD -v -s

# Specific test method  
pytest test/repositories/test_organization_repository.py::TestOrganizationCRUD::test_create_organization_success -v -s

# With coverage
pytest test/repositories/test_organization_repository.py --cov=src/repositories/organization_repository --cov-report=term-missing

# All organization tests
pytest test/repositories/test_organization_repository.py -v -s
"""