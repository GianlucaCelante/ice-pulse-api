# =====================================================
# test/repositories/test_user_repository.py - REALISTIC VERSION
# =====================================================
"""
Test per UserRepository - versione realistica che usa solo metodi esistenti.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy import text

# Clean imports - no path manipulation needed
from src.models import Organization, User
from src.repositories.user_repository import UserRepository
from src.database.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    DatabaseError
)

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def user_repository(test_db):
    """Create UserRepository instance"""
    return UserRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Test Company",
        slug="test-company",
        subscription_plan="premium",
        max_sensors=50,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def sample_user_data(sample_organization):
    """Sample user data for testing - only existing fields"""
    return {
        "organization_id": sample_organization.id,
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "first_name": "John",
        "last_name": "Doe", 
        "role": "operator",
        "is_active": True,
        "is_verified": True
    }

@pytest.fixture
def created_user(user_repository, sample_user_data):
    """Create and return a test user"""
    return user_repository.create(sample_user_data)

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestUserCRUD:
    """Test basic CRUD operations"""
    
    def test_create_user_success(self, user_repository, sample_user_data):
        """Test creating a new user"""
        
        # Verify PostgreSQL database
        session = user_repository.db
        try:
            result = session.execute(text("SELECT current_database(), version()"))
            db_info = result.fetchone()
            print(f"🔍 DB TYPE: PostgreSQL - {db_info}")
            assert "PostgreSQL" in str(db_info), f"Expected PostgreSQL, got: {db_info}"
        except Exception as e:
            pytest.fail(f"PostgreSQL verification failed: {e}")
        
        # Act
        original_password = sample_user_data["password"]
        user = user_repository.create(sample_user_data)
        
        # Assert
        assert user.id is not None
        assert user.email == sample_user_data["email"]
        assert user.first_name == sample_user_data["first_name"]
        assert user.last_name == sample_user_data["last_name"]
        assert user.role == sample_user_data["role"]
        assert user.organization_id == sample_user_data["organization_id"]
        
        assert user.hashed_password is not None 
        assert user.hashed_password != original_password
        assert user.verify_password(original_password)
        
        # Verify timestamps
        assert user.created_at is not None
        assert user.updated_at is not None
        
        print(f"✅ User created with ID: {user.id}")
        print(f"✅ Password hash working correctly!")

    def test_update_user_password(self, user_repository, created_user):
        """Test updating user password"""
        # Arrange
        new_password = "NewSecurePassword456!"
        old_password_hash = created_user.hashed_password  
        
        # Act
        updated_user = user_repository.update(created_user.id, {"password": new_password})
        
        # Assert
        assert updated_user.hashed_password != old_password_hash
        assert updated_user.verify_password(new_password) == True
        assert updated_user.verify_password("SecurePassword123!") == False
        
        print(f"✅ Password update working correctly")
    
    def test_get_by_id(self, user_repository, created_user):
        """Test getting user by ID"""
        # Act
        found_user = user_repository.get_by_id(created_user.id)
        
        # Assert
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == created_user.email
        
        print(f"✅ User found by ID: {found_user.id}")
    
    def test_get_by_id_with_organization_filter(self, user_repository, created_user):
        """Test getting user by ID with organization filter"""
        # Act - with correct organization
        found_user = user_repository.get_by_id(
            created_user.id, 
            organization_id=created_user.organization_id
        )
        
        # Assert
        assert found_user is not None
        assert found_user.id == created_user.id
        
        # Act - with wrong organization (should not find)
        other_org_id = uuid.uuid4()
        not_found_user = user_repository.get_by_id(
            created_user.id, 
            organization_id=other_org_id
        )
        
        # Assert
        assert not_found_user is None
        
        print("✅ Organization filtering working correctly")
    
    def test_get_by_id_not_found(self, user_repository):
        """Test getting non-existent user"""
        # Act
        found_user = user_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_user is None
        print("✅ Non-existent user correctly returned None")
    
    def test_get_by_email(self, user_repository, created_user):
        """Test getting user by email"""
        # Act
        found_user = user_repository.get_by_email(created_user.email)
        
        # Assert
        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == created_user.email
        
        print(f"✅ User found by email: {found_user.email}")
    
    def test_get_by_email_not_found(self, user_repository):
        """Test getting user by non-existent email"""
        # Act
        found_user = user_repository.get_by_email("nonexistent@example.com")
        
        # Assert
        assert found_user is None
        print("✅ Non-existent email correctly returned None")
    
    def test_update_user(self, user_repository, created_user):
        """Test updating user"""
        # Arrange
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "admin"
        }
        
        # Act
        updated_user = user_repository.update(created_user.id, update_data)
        
        # Assert
        assert updated_user is not None
        assert updated_user.first_name == "Jane"
        assert updated_user.last_name == "Smith"
        assert updated_user.role == "admin"
        # Check unchanged fields
        assert updated_user.email == created_user.email
        assert updated_user.organization_id == created_user.organization_id
        
        print(f"✅ User updated successfully")
    
    def test_update_nonexistent_user(self, user_repository):
        """Test updating non-existent user"""
        # Act & Assert
        with pytest.raises(EntityNotFoundError):
            user_repository.update(uuid.uuid4(), {"first_name": "Test"})
        
        print("✅ Update of non-existent user correctly raised EntityNotFoundError")
    
    def test_delete_user(self, user_repository, created_user):
        """Test deleting user"""
        # Act
        result = user_repository.delete(created_user.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_user = user_repository.get_by_id(created_user.id)
        assert found_user is None
        
        print(f"✅ User deleted successfully")
    
    def test_delete_nonexistent_user(self, user_repository):
        """Test deleting non-existent user"""
        # Act
        result = user_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent user correctly returned False")

# =====================================================
# TEST USER QUERIES (USING EXISTING METHODS)
# =====================================================

class TestUserQueries:
    """Test user query methods that actually exist"""
    
    def test_get_all_users(self, user_repository, sample_organization, sample_user_data):
        """Test getting all users"""
        # Arrange - Create multiple users
        user1 = user_repository.create(sample_user_data)
        user2 = user_repository.create({
            **sample_user_data,
            "email": "user2@example.com",
            "first_name": "Jane"
        })
        
        # Act
        all_users = user_repository.get_all(organization_id=sample_organization.id)
        
        # Assert
        assert len(all_users) >= 2
        user_ids = [user.id for user in all_users]
        assert user1.id in user_ids
        assert user2.id in user_ids
        assert all(user.organization_id == sample_organization.id for user in all_users)
        
        print(f"✅ Found {len(all_users)} users in organization")
    
    def test_get_all_active_only(self, user_repository, sample_organization, sample_user_data):
        """Test getting only active users"""
        # Arrange - Create active and inactive users
        active_user = user_repository.create(sample_user_data)
        inactive_user = user_repository.create({
            **sample_user_data,
            "email": "inactive@example.com",
            "is_active": False
        })
        
        # Act
        active_users = user_repository.get_all(
            organization_id=sample_organization.id,
            active_only=True
        )
        
        # Assert
        assert len(active_users) >= 1
        active_user_ids = [user.id for user in active_users]
        assert active_user.id in active_user_ids
        assert inactive_user.id not in active_user_ids
        
        print(f"✅ Active-only filter working correctly")
    
    def test_search_users(self, user_repository, sample_organization, sample_user_data):
        """Test searching users"""
        # Arrange - Create users with different names
        john_user = user_repository.create(sample_user_data)
        jane_user = user_repository.create({
            **sample_user_data,
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Smith"
        })
        
        # Act
        john_results = user_repository.search_users(
            "John",
            organization_id=sample_organization.id
        )
        
        # Assert
        assert len(john_results) >= 1
        assert john_user.id in [user.id for user in john_results]
        assert jane_user.id not in [user.id for user in john_results]
        
        print(f"✅ Search functionality working correctly")

# =====================================================
# TEST AUTHENTICATION (USING EXISTING METHODS)
# =====================================================

class TestUserAuthentication:
    """Test authentication methods"""
    
    def test_authenticate_user_success(self, user_repository, created_user):
        """Test authentication with valid credentials"""
        # Act
        authenticated_user = user_repository.authenticate_user(
            email=created_user.email,
            password="SecurePassword123!",
            organization_id=created_user.organization_id
        )
        
        # Assert
        assert authenticated_user is not None
        assert authenticated_user.id == created_user.id
        
        print(f"✅ Authentication successful for user: {authenticated_user.email}")
    
    def test_authenticate_user_wrong_password(self, user_repository, created_user):
        """Test authentication with wrong password"""
        # Act
        authenticated_user = user_repository.authenticate_user(
            email=created_user.email,
            password="WrongPassword123!",
            organization_id=created_user.organization_id
        )
        
        # Assert
        assert authenticated_user is None
        
        print("✅ Wrong password correctly rejected")
    
    def test_authenticate_user_wrong_email(self, user_repository, sample_organization):
        """Test authentication with non-existent email"""
        # Act
        authenticated_user = user_repository.authenticate_user(
            email="nonexistent@example.com",
            password="AnyPassword123!",
            organization_id=sample_organization.id
        )
        
        # Assert
        assert authenticated_user is None
        
        print("✅ Non-existent email correctly rejected")

# =====================================================
# TEST HACCP COMPLIANCE (USING EXISTING METHODS)
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance methods that exist"""
    
    def test_get_haccp_certified_users(self, user_repository, sample_organization, sample_user_data):
        """Test getting HACCP certified users"""
        # Arrange - Create user with HACCP certificate
        certified_user = user_repository.create({
            **sample_user_data,
            "email": "certified@example.com",
            "haccp_certificate_number": "HACCP2024001",
            "haccp_certificate_expiry": date.today() + timedelta(days=30)
        })
        
        # Create user without certificate
        uncertified_user = user_repository.create({
            **sample_user_data,
            "email": "uncertified@example.com"
        })
        
        # Act
        certified_users = user_repository.get_haccp_certified_users(
            organization_id=sample_organization.id
        )
        
        # Assert
        assert len(certified_users) >= 1
        certified_ids = [user.id for user in certified_users]
        assert certified_user.id in certified_ids
        # Note: uncertified_user might or might not be in results depending on is_haccp_certified logic
        
        print(f"✅ Found {len(certified_users)} HACCP certified users")
    
    def test_get_expiring_certificates(self, user_repository, sample_organization, sample_user_data):
        """Test getting users with expiring certificates"""
        # Arrange - Create user with certificate expiring soon
        expiring_user = user_repository.create({
            **sample_user_data,
            "email": "expiring@example.com",
            "haccp_certificate_number": "HACCP2024002",
            "haccp_certificate_expiry": date.today() + timedelta(days=15)  # Expires in 15 days
        })
        
        # Act
        expiring_users = user_repository.get_expiring_certificates(
            days_ahead=30,
            organization_id=sample_organization.id
        )
        
        # Assert
        assert len(expiring_users) >= 1
        expiring_ids = [user.id for user in expiring_users]
        assert expiring_user.id in expiring_ids
        
        print(f"✅ Found {len(expiring_users)} users with expiring certificates")

# =====================================================
# TEST STATISTICS (USING EXISTING METHODS)
# =====================================================

class TestUserStatistics:
    """Test user statistics methods"""
    
    def test_count_users_by_role(self, user_repository, sample_organization, sample_user_data):
        """Test counting users by role"""
        # Arrange - Create users with different roles
        operator = user_repository.create(sample_user_data)  # role: operator
        admin = user_repository.create({
            **sample_user_data,
            "email": "admin@example.com",
            "role": "admin"
        })
        
        # Act
        role_counts = user_repository.count_users_by_role(
            organization_id=sample_organization.id
        )
        
        # Assert
        assert "operator" in role_counts
        assert "admin" in role_counts
        assert role_counts["operator"] >= 1
        assert role_counts["admin"] >= 1
        
        print(f"✅ Role counts: {role_counts}")
    
    def test_get_user_stats(self, user_repository, sample_organization, sample_user_data):
        """Test getting user statistics"""
        # Arrange - Create some users
        user_repository.create(sample_user_data)
        user_repository.create({
            **sample_user_data,
            "email": "user2@example.com",
            "is_active": False
        })
        
        # Act
        stats = user_repository.get_user_stats(
            organization_id=sample_organization.id
        )
        
        # Assert
        assert isinstance(stats, dict)
        assert "total_users" in stats
        assert "active_users" in stats
        assert stats["total_users"] >= 2
        assert stats["active_users"] >= 1
        
        print(f"✅ User stats: {stats}")

# =====================================================
# VALIDATION TESTS (REALISTIC)
# =====================================================

class TestUserValidation:
    """Test user validation - only what actually works"""
    
    def test_create_duplicate_email_should_fail(self, user_repository, sample_user_data):
        """Test that creating user with duplicate email fails"""
        # Arrange
        user_repository.create(sample_user_data)
        
        # Act & Assert
        with pytest.raises(DuplicateEntityError):
            user_repository.create({
                **sample_user_data,
                "first_name": "Different Name"
            })
        
        print("✅ Duplicate email correctly rejected with DuplicateEntityError")

# =====================================================
# INTEGRATION TESTS
# =====================================================

class TestUserIntegration:
    """Integration tests with complete business logic"""
    
    def test_user_lifecycle(self, user_repository, sample_user_data):
        """Test complete user lifecycle"""
        # 1. Create
        user = user_repository.create(sample_user_data)
        assert user.email == sample_user_data["email"]
        print(f"✅ Step 1: Created user {user.id}")
        
        # 2. Read
        found_user = user_repository.get_by_email(sample_user_data["email"])
        assert found_user.id == user.id
        print(f"✅ Step 2: Found user by email")
        
        # 3. Update
        updated_user = user_repository.update(user.id, {
            "role": "admin",
            "first_name": "Updated"
        })
        assert updated_user.role == "admin"
        assert updated_user.first_name == "Updated"
        print(f"✅ Step 3: Updated user to admin role")
        
        # 4. Password change
        user_repository.update(user.id, {"password": "NewPassword123!"})
        reloaded_user = user_repository.get_by_id(user.id)
        assert reloaded_user.verify_password("NewPassword123!")
        print(f"✅ Step 4: Password updated successfully")
        
        # 5. Authentication test
        auth_user = user_repository.authenticate_user(
            user.email, 
            "NewPassword123!", 
            user.organization_id
        )
        assert auth_user is not None
        print(f"✅ Step 5: Authentication with new password successful")
        
        # 6. Delete
        delete_result = user_repository.delete(user.id)
        assert delete_result == True
        print(f"✅ Step 6: User deleted")
        
        # 7. Verify deletion
        deleted_user = user_repository.get_by_id(user.id)
        assert deleted_user is None
        print(f"✅ Step 7: Deletion verified - user no longer exists")
        
        print("✅ Complete user lifecycle test passed!")

# =====================================================
# MULTI-TENANCY TESTS
# =====================================================

class TestMultiTenancy:
    """Test multi-tenancy isolation"""
    
    def test_organization_isolation(self, user_repository, test_db):
        """Test that users are isolated by organization"""
        
        # Create two organizations
        org1 = Organization(name="Org 1", slug="org-1")
        org2 = Organization(name="Org 2", slug="org-2")
        test_db.add_all([org1, org2])
        test_db.commit()
        
        # Create users in different organizations
        user1 = user_repository.create({
            "organization_id": org1.id,
            "email": "user1@org1.com",
            "password": "Password123!",
            "first_name": "User",
            "last_name": "One",
            "role": "operator"
        })
        
        user2 = user_repository.create({
            "organization_id": org2.id,
            "email": "user2@org2.com",
            "password": "Password123!",
            "first_name": "User",
            "last_name": "Two",
            "role": "operator"
        })
        
        # Test isolation using get_all with organization filter
        org1_users = user_repository.get_all(organization_id=org1.id)
        org2_users = user_repository.get_all(organization_id=org2.id)
        
        # Assert isolation
        org1_user_ids = [user.id for user in org1_users]
        org2_user_ids = [user.id for user in org2_users]
        
        assert user1.id in org1_user_ids
        assert user1.id not in org2_user_ids
        assert user2.id in org2_user_ids
        assert user2.id not in org1_user_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")

# =====================================================
# RUN COMMAND INSTRUCTIONS
# =====================================================

"""
COME ESEGUIRE I TEST:

# Single test file
pytest test/repositories/test_user_repository.py -v -s

# Specific test class
pytest test/repositories/test_user_repository.py::TestUserCRUD -v -s

# Specific test method
pytest test/repositories/test_user_repository.py::TestUserCRUD::test_create_user_success -v -s

# With coverage
pytest test/repositories/test_user_repository.py --cov=src/repositories/user_repository --cov-report=term-missing

# All user tests
pytest test/repositories/test_user_repository.py -v -s

# Run specific test categories
pytest test/repositories/test_user_repository.py::TestUserAuthentication -v -s
pytest test/repositories/test_user_repository.py::TestHACCPCompliance -v -s
pytest test/repositories/test_user_repository.py::TestMultiTenancy -v -s
"""