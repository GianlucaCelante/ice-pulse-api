# test/repositories/test_user_repository.py
"""
Test per UserRepository - FIXED seguendo pattern organization_repository
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

# FIXED IMPORTS per SQLAlchemy 2.0
from src.models.base import BaseModel
from src.models.organization import Organization
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.database.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    DatabaseError
)
# =====================================================
# POSTGRESQL SETUP (Copia da organization_repository)
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

# =====================================================
# FIXTURES USER REPOSITORY
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
        max_sensors=50
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def sample_user_data(sample_organization):
    """Sample user data for testing"""
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
def sample_user(user_repository, sample_user_data):
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
        
        # Verifica password hashata
        assert user.password_hash is not None
        assert user.password_hash != original_password
        assert user.verify_password(original_password)
        
        # Verifica timestamps
        assert user.created_at is not None
        assert user.updated_at is not None
        
        print(f"✅ User created with ID: {user.id}")
        print(f"✅ Password hash working correctly!")
    
    def test_create_user_duplicate_email(self, user_repository, sample_user_data, sample_user):
        """Test error for duplicate email"""
        
        duplicate_data = sample_user_data.copy()
        duplicate_data["email"] = sample_user.email
        
        with pytest.raises(DuplicateEntityError) as exc_info:
            user_repository.create(duplicate_data)
        
        assert "already exists" in str(exc_info.value)
    
    def test_get_by_id_success(self, user_repository, sample_user):
        """Test getting user by ID"""
        
        found_user = user_repository.get_by_id(sample_user.id)
        
        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email
    
    def test_get_by_id_not_found(self, user_repository):
        """Test getting non-existent user"""
        
        non_existent_id = uuid.uuid4()
        found_user = user_repository.get_by_id(non_existent_id)
        
        assert found_user is None
    
    def test_get_by_email_success(self, user_repository, sample_user):
        """Test getting user by email"""
        
        found_user = user_repository.get_by_email(sample_user.email)
        
        assert found_user is not None
        assert found_user.email == sample_user.email
        assert found_user.id == sample_user.id
    
    def test_update_user_success(self, user_repository, sample_user):
        """Test updating user"""
        
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "manager"
        }
        
        updated_user = user_repository.update(sample_user.id, update_data)
        
        assert updated_user.first_name == "Jane"
        assert updated_user.last_name == "Smith"
        assert updated_user.role == "manager"
        assert updated_user.email == sample_user.email  # Non modificato
    
    def test_update_user_password(self, user_repository, sample_user):
        """Test updating password"""
        
        new_password = "NewSecurePassword456!"
        update_data = {"password": new_password}
        
        updated_user = user_repository.update(sample_user.id, update_data)
        
        # Verifica che la nuova password funzioni
        assert updated_user.verify_password(new_password)
        # Verifica che la vecchia password non funzioni più
        assert not updated_user.verify_password("SecurePassword123!")
    
    def test_update_user_not_found(self, user_repository):
        """Test updating non-existent user"""
        
        non_existent_id = uuid.uuid4()
        update_data = {"first_name": "Test"}
        
        with pytest.raises(EntityNotFoundError):
            user_repository.update(non_existent_id, update_data)
    
    def test_delete_user_success(self, user_repository, sample_user):
        """Test deleting user"""
        
        user_id = sample_user.id
        result = user_repository.delete(user_id)
        
        assert result is True
        
        # Verifica che non esista più
        found_user = user_repository.get_by_id(user_id)
        assert found_user is None
    
    def test_delete_user_not_found(self, user_repository):
        """Test deleting non-existent user"""
        
        non_existent_id = uuid.uuid4()
        result = user_repository.delete(non_existent_id)
        
        assert result is False

# =====================================================
# TEST AUTHENTICATION
# =====================================================

class TestUserAuthentication:
    """Test authentication methods"""
    
    def test_authenticate_user_success(self, user_repository, sample_user):
        """Test authentication with valid credentials"""
        
        authenticated_user = user_repository.authenticate_user(
            email=sample_user.email,
            password="SecurePassword123!",
            organization_id=sample_user.organization_id
        )
        
        assert authenticated_user is not None
        assert authenticated_user.id == sample_user.id
        assert authenticated_user.last_login_at is not None
        assert authenticated_user.failed_login_attempts == 0
        
        print(f"✅ Authentication successful for user: {authenticated_user.email}")
    
    def test_authenticate_user_wrong_password(self, user_repository, sample_user):
        """Test authentication with wrong password"""
        
        authenticated_user = user_repository.authenticate_user(
            email=sample_user.email,
            password="WrongPassword123!",
            organization_id=sample_user.organization_id
        )
        
        assert authenticated_user is None
        
        # Verifica che failed_login_attempts sia incrementato
        user = user_repository.get_by_id(sample_user.id)
        assert user.failed_login_attempts == 1
    
    def test_authenticate_user_wrong_email(self, user_repository, sample_organization):
        """Test authentication with non-existent email"""
        
        authenticated_user = user_repository.authenticate_user(
            email="nonexistent@example.com",
            password="AnyPassword123!",
            organization_id=sample_organization.id
        )
        
        assert authenticated_user is None
    
    def test_authenticate_locked_account(self, user_repository, sample_user):
        """Test authentication with locked account"""
        
        # Simula tentativi falliti fino al blocco
        for _ in range(5):  # max_attempts default = 5
            user_repository.authenticate_user(
                email=sample_user.email,
                password="WrongPassword",
                organization_id=sample_user.organization_id
            )
        
        # Verifica che l'account sia bloccato
        user = user_repository.get_by_id(sample_user.id)
        assert user.is_account_locked()
        
        # Prova con password corretta ma account bloccato
        authenticated_user = user_repository.authenticate_user(
            email=sample_user.email,
            password="SecurePassword123!",
            organization_id=sample_user.organization_id
        )
        
        assert authenticated_user is None
        print(f"✅ Account lockout working correctly!")

# =====================================================
# TEST QUERY METHODS
# =====================================================

class TestUserQueries:
    """Test query methods"""
    
    def test_get_all_users(self, user_repository, sample_organization):
        """Test getting all users"""
        
        # Crea multipli utenti
        users_data = [
            {
                "organization_id": sample_organization.id,
                "email": f"user{i}@example.com",
                "password": "Password123!",
                "role": "operator"
            }
            for i in range(3)
        ]
        
        created_users = []
        for data in users_data:
            user = user_repository.create(data)
            created_users.append(user)
        
        # Test get_all
        all_users = user_repository.get_all(organization_id=sample_organization.id)
        
        assert len(all_users) == 3
        assert all(user.organization_id == sample_organization.id for user in all_users)
        print(f"✅ Retrieved {len(all_users)} users successfully!")
    
    def test_search_users(self, user_repository, sample_organization):
        """Test searching users"""
        
        # Crea utenti con nomi diversi
        user_repository.create({
            "organization_id": sample_organization.id,
            "email": "john.doe@example.com",
            "password": "Password123!",
            "first_name": "John",
            "last_name": "Doe"
        })
        
        user_repository.create({
            "organization_id": sample_organization.id,
            "email": "jane.smith@example.com",
            "password": "Password123!",
            "first_name": "Jane",
            "last_name": "Smith"
        })
        
        # Test ricerca per nome
        john_results = user_repository.search_users(
            "John",
            organization_id=sample_organization.id
        )
        assert len(john_results) == 1
        assert john_results[0].first_name == "John"
        
        print(f"✅ Search functionality working correctly!")

# =====================================================
# TEST HACCP COMPLIANCE
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance methods"""
    
    def test_get_haccp_certified_users(self, user_repository, sample_organization):
        """Test getting HACCP certified users"""
        
        # Utente con certificazione valida
        certified_user = user_repository.create({
            "organization_id": sample_organization.id,
            "email": "certified@example.com",
            "password": "Password123!",
            "haccp_certificate_number": "HACCP2024001",
            "haccp_certificate_expiry": date.today() + timedelta(days=30)
        })
        
        # Utente senza certificazione
        uncertified_user = user_repository.create({
            "organization_id": sample_organization.id,
            "email": "uncertified@example.com",
            "password": "Password123!"
        })
        
        certified_users = user_repository.get_haccp_certified_users(
            organization_id=sample_organization.id
        )
        
        assert len(certified_users) == 1
        assert certified_users[0].email == "certified@example.com"
        assert certified_users[0].is_haccp_certified is True
        
        print(f"✅ HACCP compliance checking working correctly!")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestMultiTenancy:
    """Test multi-tenancy isolation"""
    
    def test_organization_isolation(self, user_repository, test_db):
        """Test that users are isolated by organization"""
        
        # Crea due organizzazioni
        org1 = Organization(name="Org 1", slug="org-1")
        org2 = Organization(name="Org 2", slug="org-2")
        test_db.add_all([org1, org2])
        test_db.commit()
        
        # Crea utenti in organizzazioni diverse
        user1 = user_repository.create({
            "organization_id": org1.id,
            "email": "user1@org1.com",
            "password": "Password123!"
        })
        
        user2 = user_repository.create({
            "organization_id": org2.id,
            "email": "user2@org2.com",
            "password": "Password123!"
        })
        
        # Test che user1 non sia visibile da org2
        user1_from_org2 = user_repository.get_by_id(
            user1.id,
            organization_id=org2.id
        )
        assert user1_from_org2 is None
        
        # Test che user1 sia visibile da org1
        user1_from_org1 = user_repository.get_by_id(
            user1.id,
            organization_id=org1.id
        )
        assert user1_from_org1 is not None
        
        print(f"✅ Multi-tenancy isolation working correctly!")

# =====================================================
# RUN TESTS COMMAND
# =====================================================

"""
COME ESEGUIRE I TEST:

# Single test file
pytest test/repositories/test_user_repository.py -v

# Specific test class
pytest test/repositories/test_user_repository.py::TestUserCRUD -v

# Specific test method
pytest test/repositories/test_user_repository.py::TestUserCRUD::test_create_user_success -v

# With coverage
pytest test/repositories/test_user_repository.py --cov=src/repositories/user_repository --cov-report=term-missing
"""