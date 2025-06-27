# =====================================================
# tests/repositories/test_organization_repository.py
# =====================================================
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

from datetime import datetime
import uuid
import subprocess
import time

# FIXED IMPORTS per SQLAlchemy 2.0
from src.models.base import BaseModel
from src.models.organization import Organization
from src.repositories.organization_repository import OrganizationRepository

# =====================================================
# CUSTOM POSTGRESQL SETUP (No external dependencies)
# =====================================================

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
        engine = create_engine(db_url, echo=False)  # Disable SQL logging for cleaner output
        
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

@pytest.fixture
def organization_repo(test_db):
    """Create OrganizationRepository instance"""
    return OrganizationRepository(test_db)

@pytest.fixture
def sample_organization_data():
    """Sample organization data for testing"""
    return {
        "name": "Test Company",
        "slug": "test-company",
        "subscription_plan": "premium",
        "max_sensors": 50,
        "timezone": "Europe/Rome",
        "haccp_settings": {"temperature_min": -20, "temperature_max": 8},
        "retention_months": 24,
        "auto_archive_enabled": True
    }

@pytest.fixture
def created_organization(organization_repo, sample_organization_data):
    """Create and return a test organization"""
    return organization_repo.create(sample_organization_data)

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestOrganizationCRUD:
    """Test basic CRUD operations"""
    
    def test_create_organization(self, organization_repo, sample_organization_data):
        """Test creating a new organization"""
        
        session = organization_repo.db
        try:
            result = session.execute(text("SELECT current_database(), version()"))
            db_info = result.fetchone()
            print(f"🔍 DB TYPE: PostgreSQL - {db_info}")
            assert "PostgreSQL" in str(db_info), f"Expected PostgreSQL, got: {db_info}"
        except Exception as e:
            print(f"❌ PostgreSQL query failed: {e}")
            try:
                result = session.execute(text("SELECT sqlite_version()"))
                sqlite_version = result.fetchone()[0]
                print(f"🔍 DB TYPE: SQLite {sqlite_version}")
                pytest.fail("Test is using SQLite instead of PostgreSQL!")
            except Exception as sqlite_e:
                pytest.fail(f"Unable to identify database type. PostgreSQL error: {e}, SQLite error: {sqlite_e}")
        
        # Act
        org = organization_repo.create(sample_organization_data)
        
        # Assert
        assert org.id is not None
        assert org.name == "Test Company"
        assert org.slug == "test-company"
        assert org.subscription_plan == "premium"
        assert org.max_sensors == 50
        assert org.timezone == "Europe/Rome"
        assert org.haccp_settings == {"temperature_min": -20, "temperature_max": 8}
        assert org.retention_months == 24
        assert org.auto_archive_enabled == True
        assert org.created_at is not None
        assert org.updated_at is not None
        
        print(f"✅ Organization created with ID: {org.id}")
        print(f"✅ HACCP settings: {org.haccp_settings}")
        print(f"✅ PostgreSQL JSONB working correctly!")
    
    def test_get_by_id(self, organization_repo, created_organization):
        """Test getting organization by ID"""
        # Act
        found_org = organization_repo.get_by_id(created_organization.id)
        
        # Assert
        assert found_org is not None
        assert found_org.id == created_organization.id
        assert found_org.name == created_organization.name
        assert found_org.slug == created_organization.slug
    
    def test_get_by_id_not_found(self, organization_repo):
        """Test getting non-existent organization"""
        # Act
        found_org = organization_repo.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_org is None
    
    def test_update_organization(self, organization_repo, created_organization):
        """Test updating organization"""
        # Arrange
        update_data = {
            "name": "Updated Company Name",
            "max_sensors": 100,
            "subscription_plan": "enterprise"
        }
        
        # Act
        updated_org = organization_repo.update(created_organization.id, update_data)
        
        # Assert
        assert updated_org is not None
        assert updated_org.name == "Updated Company Name"
        assert updated_org.max_sensors == 100
        assert updated_org.subscription_plan == "enterprise"
        # Check unchanged fields
        assert updated_org.slug == created_organization.slug
        assert updated_org.timezone == created_organization.timezone
    
    def test_update_nonexistent_organization(self, organization_repo):
        """Test updating non-existent organization"""
        # Act
        result = organization_repo.update(uuid.uuid4(), {"name": "Test"})
        
        # Assert
        assert result is None
    
    def test_delete_organization(self, organization_repo, created_organization):
        """Test deleting organization"""
        # Act
        result = organization_repo.delete(created_organization.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_org = organization_repo.get_by_id(created_organization.id)
        assert found_org is None
    
    def test_delete_nonexistent_organization(self, organization_repo):
        """Test deleting non-existent organization"""
        # Act
        result = organization_repo.delete(uuid.uuid4())
        
        # Assert
        assert result == False
    
    def test_exists(self, organization_repo, created_organization):
        """Test exists method"""
        # Test existing
        assert organization_repo.exists(created_organization.id) == True
        
        # Test non-existing
        assert organization_repo.exists(uuid.uuid4()) == False
    
    def test_count(self, organization_repo, sample_organization_data):
        """Test count method"""
        # Initial count
        initial_count = organization_repo.count()
        
        # Create organizations
        organization_repo.create(sample_organization_data)
        organization_repo.create({**sample_organization_data, "slug": "test-company-2", "name": "Test Company 2"})
        
        # Check count
        new_count = organization_repo.count()
        assert new_count == initial_count + 2

# =====================================================
# TEST ORGANIZATION-SPECIFIC QUERIES
# =====================================================

class TestOrganizationQueries:
    """Test organization-specific query methods"""
    
    def test_get_by_slug(self, organization_repo, created_organization):
        """Test getting organization by slug"""
        # Act
        found_org = organization_repo.get_by_slug("test-company")
        
        # Assert
        assert found_org is not None
        assert found_org.id == created_organization.id
        assert found_org.slug == "test-company"
    
    def test_get_by_slug_not_found(self, organization_repo):
        """Test getting organization by non-existent slug"""
        # Act
        found_org = organization_repo.get_by_slug("non-existent-slug")
        
        # Assert
        assert found_org is None
    
    def test_get_by_subscription_plan(self, organization_repo, sample_organization_data):
        """Test getting organizations by subscription plan"""
        # Arrange - Create multiple organizations
        org1 = organization_repo.create(sample_organization_data)
        org2 = organization_repo.create({
            **sample_organization_data, 
            "slug": "test-company-2", 
            "name": "Test Company 2", 
            "subscription_plan": "free"
        })
        org3 = organization_repo.create({
            **sample_organization_data, 
            "slug": "test-company-3", 
            "name": "Test Company 3", 
            "subscription_plan": "premium"
        })
        
        # Act
        premium_orgs = organization_repo.get_by_subscription_plan("premium")
        free_orgs = organization_repo.get_by_subscription_plan("free")
        
        # Assert
        assert len(premium_orgs) == 2
        assert len(free_orgs) == 1
        
        premium_ids = [org.id for org in premium_orgs]
        assert org1.id in premium_ids
        assert org3.id in premium_ids
        assert free_orgs[0].id == org2.id
    
    def test_get_premium_organizations(self, organization_repo, sample_organization_data):
        """Test getting premium/enterprise organizations"""
        # Arrange
        free_org = organization_repo.create({
            **sample_organization_data, 
            "slug": "free-org", 
            "name": "Free Org", 
            "subscription_plan": "free"
        })
        premium_org = organization_repo.create({
            **sample_organization_data, 
            "slug": "premium-org", 
            "name": "Premium Org", 
            "subscription_plan": "premium"
        })
        enterprise_org = organization_repo.create({
            **sample_organization_data, 
            "slug": "enterprise-org", 
            "name": "Enterprise Org", 
            "subscription_plan": "enterprise"
        })
        
        # Act
        premium_orgs = organization_repo.get_premium_organizations()
        
        # Assert
        assert len(premium_orgs) == 2
        premium_ids = [org.id for org in premium_orgs]
        assert premium_org.id in premium_ids
        assert enterprise_org.id in premium_ids
        assert free_org.id not in premium_ids
    
    def test_search_by_name(self, organization_repo, sample_organization_data):
        """Test searching organizations by name"""
        # Arrange
        org1 = organization_repo.create({
            **sample_organization_data, 
            "slug": "pizza-mario", 
            "name": "Pizza di Mario"
        })
        org2 = organization_repo.create({
            **sample_organization_data, 
            "slug": "gelato-luigi", 
            "name": "Gelato di Luigi"
        })
        org3 = organization_repo.create({
            **sample_organization_data, 
            "slug": "ristorante-paolo", 
            "name": "Ristorante Paolo"
        })
        
        # Act & Assert
        # Search for "mario"
        mario_results = organization_repo.search_by_name("mario")
        assert len(mario_results) == 1
        assert mario_results[0].id == org1.id
        
        # Search for "di" (should find Mario and Luigi)
        di_results = organization_repo.search_by_name("di")
        assert len(di_results) == 2
        
        # Search case insensitive
        upper_results = organization_repo.search_by_name("MARIO")
        assert len(upper_results) == 1
        assert upper_results[0].id == org1.id
        
        # Search non-existent
        no_results = organization_repo.search_by_name("nonexistent")
        assert len(no_results) == 0

# =====================================================
# TEST EDGE CASES & VALIDATION
# =====================================================

class TestOrganizationEdgeCases:
    """Test edge cases and validation"""
    
    def test_create_with_minimal_data(self, organization_repo):
        """Test creating organization with minimal required data"""
        # Arrange
        minimal_data = {
            "name": "Minimal Org",
            "slug": "minimal-org"
        }
        
        # Act
        org = organization_repo.create(minimal_data)
        
        # Assert
        assert org.id is not None
        assert org.name == "Minimal Org"
        assert org.slug == "minimal-org"
        # Check defaults
        assert org.subscription_plan == "free"
        assert org.max_sensors == 10
        assert org.timezone == "UTC"
        assert org.retention_months == 24
        assert org.auto_archive_enabled == True
        assert org.haccp_settings is None
    
    def test_create_duplicate_slug_should_fail(self, organization_repo, sample_organization_data):
        """Test that creating organization with duplicate slug fails"""
        # Arrange
        organization_repo.create(sample_organization_data)
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise IntegrityError
            organization_repo.create({
                **sample_organization_data, 
                "name": "Different Name"
            })
    
    def test_update_with_invalid_field(self, organization_repo, created_organization):
        """Test updating with invalid field should be ignored"""
        # Act
        updated_org = organization_repo.update(created_organization.id, {
            "name": "Updated Name",
            "invalid_field": "should be ignored"
        })
        
        # Assert
        assert updated_org.name == "Updated Name"
        assert not hasattr(updated_org, "invalid_field")
    
    def test_get_all_with_pagination(self, organization_repo, sample_organization_data):
        """Test get_all with pagination"""
        # Arrange - Create multiple organizations
        for i in range(5):
            organization_repo.create({
                **sample_organization_data,
                "slug": f"test-org-{i}",
                "name": f"Test Org {i}"
            })
        
        # Act
        first_page = organization_repo.get_all(skip=0, limit=2)
        second_page = organization_repo.get_all(skip=2, limit=2)
        
        # Assert
        assert len(first_page) == 2
        assert len(second_page) == 2
        
        # Ensure different results
        first_page_ids = [org.id for org in first_page]
        second_page_ids = [org.id for org in second_page]
        assert not any(id in second_page_ids for id in first_page_ids)

# =====================================================
# INTEGRATION TESTS
# =====================================================

class TestOrganizationIntegration:
    """Integration tests with business logic"""
    
    def test_organization_lifecycle(self, organization_repo, sample_organization_data):
        """Test complete organization lifecycle"""
        # 1. Create
        org = organization_repo.create(sample_organization_data)
        assert org.name == "Test Company"
        
        # 2. Read
        found_org = organization_repo.get_by_slug("test-company")
        assert found_org.id == org.id
        
        # 3. Update
        updated_org = organization_repo.update(org.id, {
            "subscription_plan": "enterprise",
            "max_sensors": 200
        })
        assert updated_org.subscription_plan == "enterprise"
        
        # 4. Verify update persisted
        reloaded_org = organization_repo.get_by_id(org.id)
        assert reloaded_org.subscription_plan == "enterprise"
        assert reloaded_org.max_sensors == 200
        
        # 5. Delete
        delete_result = organization_repo.delete(org.id)
        assert delete_result == True
        
        # 6. Verify deletion
        deleted_org = organization_repo.get_by_id(org.id)
        assert deleted_org is None

# =====================================================
# RUN TESTS COMMAND
# =====================================================

"""
COME ESEGUIRE I TEST:

# Single test file
pytest tests/repositories/test_organization_repository.py -v

# Specific test class
pytest tests/repositories/test_organization_repository.py::TestOrganizationCRUD -v

# Specific test method
pytest tests/repositories/test_organization_repository.py::TestOrganizationCRUD::test_create_organization -v

# With coverage
pytest tests/repositories/test_organization_repository.py --cov=src/repositories/organization_repository --cov-report=term-missing

# Watch mode (run on file changes)
pytest-watch tests/repositories/test_organization_repository.py
"""