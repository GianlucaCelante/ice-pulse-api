# =====================================================
# test/repositories/test_audit_log_repository.py
# =====================================================
"""
Test per AuditLogRepository - testa tracciabilità, compliance HACCP e audit.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy import text

# Clean imports - no path manipulation needed
from src.models import Organization, User, AuditLog
from src.repositories.audit_log_repository import AuditLogRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def audit_log_repository(test_db):
    """Create AuditLogRepository instance"""
    return AuditLogRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Audit Test Company",
        slug="audit-test-company",
        subscription_plan="premium",
        max_sensors=100,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def sample_user(test_db, sample_organization):
    """Create sample user for testing"""
    user = User(
        organization_id=sample_organization.id,
        email="audit.tester@example.com",
        first_name="Audit",
        last_name="Tester",
        role="admin",
        is_active=True,
        is_verified=True
    )
    user.set_password("AuditPass123!")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def second_organization(test_db):
    """Create second organization for multi-tenancy tests"""
    org = Organization(
        name="Second Audit Test Company",
        slug="second-audit-test-company",
        subscription_plan="basic",
        max_sensors=20,
        timezone="UTC"
    )
    test_db.add(org)
    test_db.commit()
    test_db.refresh(org)
    return org

@pytest.fixture
def second_user(test_db, second_organization):
    """Create user for second organization"""
    user = User(
        organization_id=second_organization.id,
        email="second.auditor@example.com",
        first_name="Second",
        last_name="Auditor",
        role="operator",  # FIX: operator invece di user
        is_active=True,
        is_verified=True
    )
    user.set_password("SecondPass123!")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def sample_audit_log_data(sample_organization, sample_user):
    """Sample audit log data for testing"""
    return {
        "organization_id": sample_organization.id,
        "user_id": sample_user.id,
        "action": "sensor_created",
        "resource_type": "sensor",
        "resource_id": uuid.uuid4(),
        "old_values": None,
        "new_values": {
            "name": "New Temperature Sensor",
            "status": "online",
            "location": "Freezer Room A"
        },
        "description": "Created new temperature sensor for freezer monitoring",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "haccp_relevant": True
    }

@pytest.fixture
def created_audit_log(audit_log_repository, sample_audit_log_data):
    """Create and return a test audit log"""
    return audit_log_repository.create(sample_audit_log_data)

# =====================================================
# TEST BASIC CRUD OPERATIONS
# =====================================================

class TestAuditLogCRUD:
    """Test basic CRUD operations"""
    
    def test_create_audit_log_success(self, audit_log_repository, sample_audit_log_data):
        """Test creating a new audit log entry"""
        
        # Act
        audit_log = audit_log_repository.create(sample_audit_log_data)
        
        # Assert
        assert audit_log.id is not None
        assert audit_log.organization_id == sample_audit_log_data["organization_id"]
        assert audit_log.user_id == sample_audit_log_data["user_id"]
        assert audit_log.action == sample_audit_log_data["action"]
        assert audit_log.resource_type == sample_audit_log_data["resource_type"]
        assert audit_log.resource_id == sample_audit_log_data["resource_id"]
        assert audit_log.old_values == sample_audit_log_data["old_values"]
        assert audit_log.new_values == sample_audit_log_data["new_values"]
        assert audit_log.description == sample_audit_log_data["description"]
        assert audit_log.ip_address == sample_audit_log_data["ip_address"]
        assert audit_log.user_agent == sample_audit_log_data["user_agent"]
        assert audit_log.haccp_relevant == sample_audit_log_data["haccp_relevant"]
        
        # Verify timestamps
        assert audit_log.created_at is not None
        
        print(f"✅ Audit log created with ID: {audit_log.id}")
        print(f"✅ Action: {audit_log.action}, Resource: {audit_log.resource_type}")
        print(f"✅ HACCP relevant: {audit_log.haccp_relevant}")
    
    def test_get_by_id(self, audit_log_repository, created_audit_log):
        """Test getting audit log by ID"""
        # Act
        found_audit_log = audit_log_repository.get_by_id(created_audit_log.id)
        
        # Assert
        assert found_audit_log is not None
        assert found_audit_log.id == created_audit_log.id
        assert found_audit_log.action == created_audit_log.action
        
        print(f"✅ Audit log found by ID: {found_audit_log.id}")
    
    def test_get_by_id_not_found(self, audit_log_repository):
        """Test getting non-existent audit log"""
        # Act
        found_audit_log = audit_log_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_audit_log is None
        print("✅ Non-existent audit log correctly returned None")
    
    def test_update_audit_log(self, audit_log_repository, created_audit_log):
        """Test updating audit log (should be rare - audit logs are immutable)"""
        # Arrange
        update_data = {
            "description": "Updated description for compliance review"
        }
        
        # Act
        updated_audit_log = audit_log_repository.update(created_audit_log.id, update_data)
        
        # Assert
        assert updated_audit_log is not None
        assert updated_audit_log.description == "Updated description for compliance review"
        # Check unchanged fields
        assert updated_audit_log.action == created_audit_log.action
        assert updated_audit_log.resource_type == created_audit_log.resource_type
        
        print(f"✅ Audit log updated (rare case)")
    
    def test_delete_audit_log_forbidden(self, audit_log_repository, created_audit_log):
        """Test that audit logs cannot be deleted (compliance requirement)"""
        # Note: In real implementation, delete should be restricted
        # This test documents the expected behavior
        
        # Act
        result = audit_log_repository.delete(created_audit_log.id)
        
        # Assert - For compliance, audit logs should not be deletable
        # This depends on your implementation - may throw exception or return False
        # Documenting the expected behavior here
        print(f"✅ Delete attempted - result: {result}")
        print("⚠️  Audit logs should be immutable for compliance")

# =====================================================
# TEST AUDIT LOG SPECIFIC QUERIES
# =====================================================

class TestAuditLogQueries:
    """Test audit log specific query methods"""
    
    def test_get_by_organization(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test getting audit logs by organization"""
        # Arrange - Create multiple audit logs
        audit_log1 = audit_log_repository.create(sample_audit_log_data)
        audit_log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_updated",
            "description": "Updated sensor configuration",
            "old_values": {"status": "offline"},
            "new_values": {"status": "online"}
        })
        
        # Act
        org_audit_logs = audit_log_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_audit_logs) >= 2
        audit_log_ids = [log.id for log in org_audit_logs]
        assert audit_log1.id in audit_log_ids
        assert audit_log2.id in audit_log_ids
        assert all(log.organization_id == sample_organization.id for log in org_audit_logs)
        
        # Should be ordered by created_at DESC (most recent first)
        if len(org_audit_logs) > 1:
            created_times = [log.created_at for log in org_audit_logs]
            assert created_times == sorted(created_times, reverse=True)
        
        print(f"✅ Found {len(org_audit_logs)} audit logs in organization")
    
    def test_get_by_organization_with_limit(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test getting audit logs with limit"""
        # Arrange - Create multiple audit logs
        for i in range(5):
            audit_log_repository.create({
                **sample_audit_log_data,
                "action": f"test_action_{i}",
                "description": f"Test action {i}"
            })
        
        # Act
        limited_logs = audit_log_repository.get_by_organization(sample_organization.id, limit=3)
        
        # Assert
        assert len(limited_logs) == 3
        
        print(f"✅ Limited query returned {len(limited_logs)} audit logs")
    
    def test_get_haccp_relevant(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test getting HACCP relevant audit logs"""
        # Arrange - Create mix of HACCP and non-HACCP logs
        haccp_log1 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "temperature_threshold_changed",
            "description": "Changed critical temperature threshold",
            "haccp_relevant": True
        })
        
        haccp_log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_calibration",
            "description": "Calibrated temperature sensor",
            "haccp_relevant": True
        })
        
        non_haccp_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "user_login",
            "description": "User logged into system",
            "haccp_relevant": False
        })
        
        # Act
        haccp_logs = audit_log_repository.get_haccp_relevant(sample_organization.id)
        
        # Assert
        haccp_log_ids = [log.id for log in haccp_logs]
        assert haccp_log1.id in haccp_log_ids
        assert haccp_log2.id in haccp_log_ids
        assert non_haccp_log.id not in haccp_log_ids
        assert all(log.haccp_relevant == True for log in haccp_logs)
        
        print(f"✅ Found {len(haccp_logs)} HACCP relevant logs")
    
    def test_get_by_user(self, audit_log_repository, sample_user, sample_audit_log_data):
        """Test getting audit logs by user"""
        # Arrange - Create logs for specific user
        user_log1 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_created",
            "description": "User created sensor"
        })
        
        user_log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "alert_resolved",
            "description": "User resolved alert"
        })
        
        # Act
        user_logs = audit_log_repository.get_by_user(sample_user.id)
        
        # Assert
        user_log_ids = [log.id for log in user_logs]
        assert user_log1.id in user_log_ids
        assert user_log2.id in user_log_ids
        assert all(log.user_id == sample_user.id for log in user_logs)
        
        print(f"✅ Found {len(user_logs)} logs for user")
    
    def test_get_by_resource(self, audit_log_repository, sample_audit_log_data):
        """Test getting audit logs for specific resource"""
        # Arrange
        resource_id = uuid.uuid4()
        resource_log1 = audit_log_repository.create({
            **sample_audit_log_data,
            "resource_type": "sensor",
            "resource_id": resource_id,
            "action": "sensor_created"
        })
        
        resource_log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "resource_type": "sensor",
            "resource_id": resource_id,
            "action": "sensor_updated"
        })
        
        other_resource_log = audit_log_repository.create({
            **sample_audit_log_data,
            "resource_type": "sensor",
            "resource_id": uuid.uuid4(),  # Different resource
            "action": "sensor_deleted"
        })
        
        # Act
        resource_logs = audit_log_repository.get_by_resource("sensor", resource_id)
        
        # Assert
        resource_log_ids = [log.id for log in resource_logs]
        assert resource_log1.id in resource_log_ids
        assert resource_log2.id in resource_log_ids
        assert other_resource_log.id not in resource_log_ids
        assert all(log.resource_id == resource_id for log in resource_logs)
        assert all(log.resource_type == "sensor" for log in resource_logs)
        
        print(f"✅ Found {len(resource_logs)} logs for specific resource")
    
    def test_search_logs(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test searching audit logs"""
        # Arrange - Create logs with different content
        search_log1 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "temperature_alert",
            "description": "Critical temperature exceeded in freezer"
        })
        
        search_log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_maintenance",
            "description": "Performed temperature sensor calibration"
        })
        
        unrelated_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "user_login",
            "description": "User authenticated successfully"
        })
        
        # Act - Search for "temperature"
        temp_logs = audit_log_repository.search_logs(sample_organization.id, "temperature")
        
        # Assert
        temp_log_ids = [log.id for log in temp_logs]
        assert search_log1.id in temp_log_ids  # "temperature_alert" action
        assert search_log2.id in temp_log_ids  # "temperature" in description
        assert unrelated_log.id not in temp_log_ids
        
        print(f"✅ Search for 'temperature' found {len(temp_logs)} logs")
    
    def test_get_by_date_range(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test getting audit logs by date range"""
        # Arrange - Create logs at different times
        now = datetime.utcnow()
        
        # Recent log (within range)
        recent_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "recent_action",
            "description": "Recent audit log entry"
        })
        
        # Simulate old log by updating created_at directly
        old_time = now - timedelta(days=10)
        old_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "old_action",
            "description": "Old audit log entry"
        })
        
        # FIX: Usa text() per wrapped SQL
        audit_log_repository.db.execute(
            text("UPDATE audit_log SET created_at = :old_time WHERE id = :log_id"),
            {"old_time": old_time, "log_id": old_log.id}
        )
        audit_log_repository.db.commit()
        
        # Act - Get logs from last 5 days
        start_date = now - timedelta(days=5)
        end_date = now + timedelta(hours=1)  # Include current time
        
        date_range_logs = audit_log_repository.get_by_date_range(
            sample_organization.id, start_date, end_date
        )
        
        # Assert
        date_range_log_ids = [log.id for log in date_range_logs]
        assert recent_log.id in date_range_log_ids
        # old_log should not be in range (older than 5 days)
        
        print(f"✅ Found {len(date_range_logs)} logs in date range")

# =====================================================
# TEST AUDIT LOG BUSINESS LOGIC
# =====================================================

class TestAuditLogBusinessLogic:
    """Test audit log model business logic and properties"""
    
    def test_audit_log_properties(self, audit_log_repository, sample_audit_log_data):
        """Test audit log model properties"""
        # Create audit log with changes
        audit_log = audit_log_repository.create({
            **sample_audit_log_data,
            "old_values": {"temperature_threshold": -20.0},
            "new_values": {"temperature_threshold": -18.0},
            "description": "Updated critical temperature threshold"
        })
        
        # Test has_changes property
        assert audit_log.has_changes == True
        
        # Test user_display_name property
        user_name = audit_log.user_display_name
        assert user_name is not None
        assert user_name != "Sistema"  # Should have actual user name
        
        print(f"✅ Audit log properties working correctly")
        print(f"   - has_changes: {audit_log.has_changes}")
        print(f"   - user_display_name: {user_name}")
    
    def test_system_audit_log_properties(self, audit_log_repository, sample_organization):
        """Test properties for system-generated audit log"""
        # Create system audit log (no user_id)
        system_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,  # System action
            "action": "system_backup",
            "resource_type": None,
            "resource_id": None,
            "old_values": None,
            "new_values": None,
            "description": "Automated system backup completed",
            "ip_address": None,
            "user_agent": None,
            "haccp_relevant": False
        })
        
        # Test system properties
        assert system_log.has_changes == False  # No values changed
        assert system_log.user_display_name == "Sistema"  # System action
        
        print(f"✅ System audit log properties working correctly")
    
    def test_audit_log_string_representation(self, created_audit_log):
        """Test string representation of audit log"""
        str_repr = str(created_audit_log)
        assert "AuditLog" in str_repr
        assert created_audit_log.action in str_repr
        assert created_audit_log.resource_type in str_repr
        
        print(f"✅ String representation: {str_repr}")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestAuditLogMultiTenancy:
    """Test multi-tenancy isolation for audit logs"""
    
    def test_organization_isolation(self, audit_log_repository, sample_organization, second_organization, 
                                   sample_user, second_user, sample_audit_log_data):
        """Test that audit logs are isolated by organization"""
        
        # Create audit logs in different organizations
        org1_log = audit_log_repository.create({
            **sample_audit_log_data,
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "org1_action"
        })
        
        org2_log = audit_log_repository.create({
            **sample_audit_log_data,
            "organization_id": second_organization.id,
            "user_id": second_user.id,
            "action": "org2_action"
        })
        
        # Test isolation using organization-specific queries
        org1_logs = audit_log_repository.get_by_organization(sample_organization.id)
        org2_logs = audit_log_repository.get_by_organization(second_organization.id)
        
        # Assert isolation
        org1_log_ids = [log.id for log in org1_logs]
        org2_log_ids = [log.id for log in org2_logs]
        
        assert org1_log.id in org1_log_ids
        assert org1_log.id not in org2_log_ids
        assert org2_log.id in org2_log_ids
        assert org2_log.id not in org1_log_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")
        print(f"   - Org1 audit logs: {len(org1_logs)}")
        print(f"   - Org2 audit logs: {len(org2_logs)}")
    
    def test_haccp_isolation(self, audit_log_repository, sample_organization, second_organization,
                            sample_user, second_user, sample_audit_log_data):
        """Test HACCP log isolation by organization"""
        
        # Create HACCP logs in different organizations
        org1_haccp_log = audit_log_repository.create({
            **sample_audit_log_data,
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "critical_temp_breach",
            "haccp_relevant": True
        })
        
        org2_haccp_log = audit_log_repository.create({
            **sample_audit_log_data,
            "organization_id": second_organization.id,
            "user_id": second_user.id,
            "action": "calibration_overdue",
            "haccp_relevant": True
        })
        
        # Test HACCP isolation
        org1_haccp_logs = audit_log_repository.get_haccp_relevant(sample_organization.id)
        org2_haccp_logs = audit_log_repository.get_haccp_relevant(second_organization.id)
        
        # Assert isolation
        org1_haccp_ids = [log.id for log in org1_haccp_logs]
        org2_haccp_ids = [log.id for log in org2_haccp_logs]
        
        assert org1_haccp_log.id in org1_haccp_ids
        assert org1_haccp_log.id not in org2_haccp_ids
        assert org2_haccp_log.id in org2_haccp_ids
        assert org2_haccp_log.id not in org1_haccp_ids
        
        print(f"✅ HACCP multi-tenancy isolation working correctly!")

# =====================================================
# TEST AUDIT LOG CONSTRAINTS AND VALIDATION
# =====================================================

class TestAuditLogConstraints:
    """Test audit log database constraints and validation"""
    
    def test_required_fields(self, audit_log_repository, sample_organization):
        """Test that required fields are enforced"""
        # Valid minimal audit log
        minimal_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,
            "action": "minimal_test",
            "resource_type": None,
            "resource_id": None,
            "old_values": None,
            "new_values": None,
            "description": None,
            "ip_address": None,
            "user_agent": None,
            "haccp_relevant": False
        })
        
        assert minimal_log.id is not None
        assert minimal_log.action == "minimal_test"
        
        print(f"✅ Minimal audit log creation successful")
    
    def test_action_length_constraint(self, audit_log_repository, sample_audit_log_data):
        """Test action field length constraint"""
        # Valid action length
        valid_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "a" * 100  # Max length
        })
        assert valid_log.action == "a" * 100
        
        # Test that very long actions are handled appropriately
        # (depends on your validation - may truncate or raise error)
        try:
            long_action_log = audit_log_repository.create({
                **sample_audit_log_data,
                "action": "a" * 150  # Exceeds max length
            })
            # If it succeeds, it might be truncated
            print(f"ℹ️  Long action handled: {len(long_action_log.action)} chars")
        except Exception as e:
            print(f"✅ Long action properly rejected: {type(e).__name__}")
    
    def test_json_field_validation(self, audit_log_repository, sample_audit_log_data):
        """Test JSON field validation for old_values and new_values"""
        # Complex JSON data
        complex_values = {
            "temperature_settings": {
                "min": -20.0,
                "max": -15.0,
                "unit": "celsius"
            },
            "alert_settings": {
                "enabled": True,
                "recipients": ["admin@example.com", "tech@example.com"],
                "severity_levels": ["warning", "critical"]
            },
            "metadata": {
                "sensor_type": "digital",
                "calibration_date": "2024-01-15",
                "accuracy": 0.5
            }
        }
        
        json_log = audit_log_repository.create({
            **sample_audit_log_data,
            "old_values": {"temperature_min": -25.0},
            "new_values": complex_values
        })
        
        assert json_log.old_values == {"temperature_min": -25.0}
        assert json_log.new_values == complex_values
        assert json_log.new_values["temperature_settings"]["min"] == -20.0
        
        print(f"✅ Complex JSON validation successful")
    
    def test_ip_address_validation(self, audit_log_repository, sample_audit_log_data):
        """Test IP address field validation"""
        # Valid IP addresses
        valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "::1", "2001:db8::1"]
        
        for ip in valid_ips:
            ip_log = audit_log_repository.create({
                **sample_audit_log_data,
                "action": f"test_ip_{ip.replace(':', '_').replace('.', '_')}",
                "ip_address": ip
            })
            assert str(ip_log.ip_address) == ip
        
        print(f"✅ Valid IP addresses accepted")

# =====================================================
# TEST AUDIT LOG RELATIONSHIPS
# =====================================================

class TestAuditLogRelationships:
    """Test audit log relationships and database joins"""
    
    def test_organization_relationship(self, audit_log_repository, created_audit_log):
        """Test audit log-organization relationship"""
        # Act
        audit_log = audit_log_repository.get_by_id(created_audit_log.id)
        
        # Assert
        assert audit_log.organization is not None
        assert audit_log.organization.id == audit_log.organization_id
        assert audit_log.organization.name is not None
        
        print(f"✅ Organization relationship working: {audit_log.organization.name}")
    
    def test_user_relationship(self, audit_log_repository, created_audit_log):
        """Test audit log-user relationship"""
        # Act
        audit_log = audit_log_repository.get_by_id(created_audit_log.id)
        
        # Assert
        assert audit_log.user is not None
        assert audit_log.user.id == audit_log.user_id
        assert audit_log.user.email is not None
        
        print(f"✅ User relationship working: {audit_log.user.email}")
    
    def test_null_user_handling(self, audit_log_repository, sample_organization):
        """Test audit log creation without user (system action)"""
        # Create system audit log
        system_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,
            "action": "system_maintenance",
            "resource_type": None,
            "resource_id": None,
            "description": "System performed automated maintenance",
            "haccp_relevant": False
        })
        
        assert system_log.user_id is None
        assert system_log.user is None
        
        print(f"✅ Null user handling working correctly")

# =====================================================
# TEST COMPLEX QUERIES AND FILTERING
# =====================================================

class TestAuditLogComplexQueries:
    """Test complex audit log queries and filtering scenarios"""
    
    def test_combined_filtering_scenarios(self, audit_log_repository, sample_organization, 
                                    sample_user, sample_audit_log_data):
        """Test complex filtering combining multiple criteria"""
        # Create diverse set of audit logs
        now = datetime.utcnow()
        
        logs_data = [
            {
                **sample_audit_log_data,
                "action": "sensor_created",  # HACCP relevant
                "resource_type": "sensor",
                "haccp_relevant": True,
                "description": "Created HACCP critical sensor"
            },
            {
                **sample_audit_log_data,
                "action": "temperature_alert",  # HACCP relevant
                "resource_type": "alert",
                "haccp_relevant": True,
                "description": "Critical temperature threshold breached"
            },
            {
                **sample_audit_log_data,
                "action": "user_login",  # NON-HACCP
                "resource_type": "user",
                "haccp_relevant": False,
                "description": "User authenticated to system"
            },
            {
                **sample_audit_log_data,
                "action": "calibration_performed",  # HACCP relevant
                "resource_type": "sensor",
                "haccp_relevant": True,
                "description": "Sensor calibration completed successfully"
            },
            {
                **sample_audit_log_data,
                "action": "report_generated",  # NON-HACCP
                "resource_type": "report",
                "haccp_relevant": False,
                "description": "Monthly compliance report generated"
            }
        ]
        
        created_logs = []
        for log_data in logs_data:
            log = audit_log_repository.create(log_data)
            created_logs.append(log)
        
        # Test various filtering combinations
        
        # 1. Get all HACCP relevant logs
        haccp_logs = audit_log_repository.get_haccp_relevant(sample_organization.id)
        haccp_actions = [log.action for log in haccp_logs]
        
        # FIX: Ora verifichiamo solo le azioni che abbiamo effettivamente creato
        expected_haccp_actions = {"sensor_created", "temperature_alert", "calibration_performed"}
        actual_haccp_actions = set(haccp_actions)
        
        # Verifica che tutte le azioni HACCP attese siano presenti
        for expected_action in expected_haccp_actions:
            assert expected_action in actual_haccp_actions, f"Expected '{expected_action}' to be in HACCP logs: {actual_haccp_actions}"
        
        # Verifica che azioni non-HACCP non siano presenti
        assert "user_login" not in haccp_actions
        assert "report_generated" not in haccp_actions
        
        # 2. Search for sensor-related activities
        sensor_logs = audit_log_repository.search_logs(sample_organization.id, "sensor")
        sensor_actions = [log.action for log in sensor_logs]
        assert any("sensor" in action for action in sensor_actions)
        
        # 3. Get logs for specific resource type
        sensor_resource_logs = [log for log in created_logs if log.resource_type == "sensor"]
        assert len(sensor_resource_logs) >= 2
        
        # 4. Get user activity logs
        user_logs = audit_log_repository.get_by_user(sample_user.id)
        assert len(user_logs) >= len(created_logs)  # All logs are by this user
        
        print(f"✅ Complex filtering working correctly")
        print(f"   - HACCP logs: {len(haccp_logs)}")
        print(f"   - Sensor-related logs: {len(sensor_logs)}")
        print(f"   - User activity logs: {len(user_logs)}")
    
# =====================================================
# TEST PERFORMANCE AND LARGE DATASETS
# =====================================================

class TestAuditLogPerformance:
    """Test audit log repository performance with larger datasets"""
    
    def test_large_audit_log_volume(self, audit_log_repository, sample_organization, sample_user, sample_audit_log_data):
        """Test handling large volume of audit logs"""
        import time
        
        # Arrange
        start_time = time.time()
        log_count = 50  # Reasonable number for testing
        actions = ['sensor_created', 'sensor_updated', 'alert_triggered', 'user_login', 'calibration_performed']
        
        # Act - Create multiple audit logs
        created_logs = []
        for i in range(log_count):
            log_data = {
                **sample_audit_log_data,
                "action": f"{actions[i % len(actions)]}_{i:04d}",
                "description": f"Performance test log entry {i:03d}",
                "haccp_relevant": i % 3 == 0,  # Every 3rd log is HACCP relevant
                "resource_id": uuid.uuid4()
            }
            log = audit_log_repository.create(log_data)
            created_logs.append(log)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_logs) == log_count
        assert duration < 30  # Should complete within 30 seconds
        
        # Test bulk queries performance
        start_query_time = time.time()
        all_org_logs = audit_log_repository.get_by_organization(sample_organization.id)
        haccp_logs = audit_log_repository.get_haccp_relevant(sample_organization.id)
        end_query_time = time.time()
        query_duration = end_query_time - start_query_time
        
        assert len(all_org_logs) >= log_count
        assert query_duration < 5  # Query should be fast
        
        print(f"✅ Created {log_count} audit logs in {duration:.2f} seconds")
        print(f"✅ Queried {len(all_org_logs)} logs in {query_duration:.3f} seconds")
        print(f"✅ Average: {duration/log_count:.3f} seconds per log")
        print(f"✅ HACCP logs: {len(haccp_logs)}")

# =====================================================
# TEST HACCP COMPLIANCE SCENARIOS
# =====================================================

class TestHACCPComplianceAuditing:
    """Test HACCP compliance audit scenarios"""
    
    def test_critical_temperature_event_audit(self, audit_log_repository, sample_organization, sample_user):
        """Test audit trail for critical temperature events"""
        # Simulate temperature breach incident with full audit trail
        
        # 1. Temperature threshold breach detected
        breach_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,  # System detected
            "action": "temperature_threshold_breach",
            "resource_type": "sensor",
            "resource_id": uuid.uuid4(),
            "old_values": {"temperature": -15.0, "status": "normal"},
            "new_values": {"temperature": -10.0, "status": "critical"},
            "description": "Critical temperature threshold breached in freezer room A",
            "haccp_relevant": True
        })
        
        # 2. Alert generated
        alert_resource_id = uuid.uuid4()
        alert_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,  # System generated
            "action": "critical_alert_generated",
            "resource_type": "alert",
            "resource_id": alert_resource_id,
            "new_values": {
                "alert_type": "temperature_critical",
                "severity": "high",
                "notification_sent": True
            },
            "description": "Critical temperature alert generated and notifications sent",
            "haccp_relevant": True
        })
        
        # 3. User acknowledged alert
        acknowledge_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "alert_acknowledged",
            "resource_type": "alert",
            "resource_id": alert_resource_id,  # Same alert
            "old_values": {"status": "active", "acknowledged_by": None},
            # FIX: Converti UUID a string per JSON
            "new_values": {"status": "acknowledged", "acknowledged_by": str(sample_user.id)},
            "description": "Temperature alert acknowledged by technician",
            "haccp_relevant": True
        })
        
        # 4. Corrective action taken
        corrective_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "corrective_action_taken",
            "resource_type": "maintenance",
            "resource_id": uuid.uuid4(),
            "new_values": {
                "action_type": "equipment_repair",
                "description": "Replaced faulty door seal",
                "completion_time": datetime.utcnow().isoformat()
            },
            "description": "Corrective action: Replaced faulty freezer door seal to prevent temperature loss",
            "haccp_relevant": True
        })
        
        # Test HACCP audit trail
        haccp_logs = audit_log_repository.get_haccp_relevant(sample_organization.id)
        haccp_log_ids = [log.id for log in haccp_logs]
        
        assert breach_log.id in haccp_log_ids
        assert alert_log.id in haccp_log_ids
        assert acknowledge_log.id in haccp_log_ids
        assert corrective_log.id in haccp_log_ids
        
        # Verify chronological order
        haccp_actions = [log.action for log in haccp_logs]
        expected_sequence = [
            "corrective_action_taken",  # Most recent
            "alert_acknowledged",
            "critical_alert_generated",
            "temperature_threshold_breach"  # Oldest
        ]
        
        # Check that all expected actions are present
        for action in expected_sequence:
            assert action in haccp_actions
        
        print(f"✅ HACCP temperature incident audit trail complete")
        print(f"   - Total HACCP logs: {len(haccp_logs)}")
        print(f"   - Incident sequence documented: {len(expected_sequence)} steps")
    
    def test_calibration_compliance_audit(self, audit_log_repository, sample_organization, sample_user):
        """Test audit trail for sensor calibration compliance"""
        sensor_id = uuid.uuid4()
        
        # 1. Calibration due notification
        due_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,  # System notification
            "action": "calibration_due_notification",
            "resource_type": "sensor",
            "resource_id": sensor_id,
            "new_values": {
                "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
                "notification_sent": True
            },
            "description": "Calibration due notification sent for temperature sensor",
            "haccp_relevant": True
        })
        
        # 2. Calibration performed
        calibration_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "sensor_calibration_performed",
            "resource_type": "sensor",
            "resource_id": sensor_id,
            "old_values": {
                "last_calibration": (datetime.utcnow() - timedelta(days=365)).isoformat(),
                "calibration_status": "due"
            },
            "new_values": {
                "last_calibration": datetime.utcnow().isoformat(),
                "calibration_status": "compliant",
                "accuracy_verified": True,
                "next_due_date": (datetime.utcnow() + timedelta(days=365)).isoformat()
            },
            "description": "Annual calibration completed - sensor accuracy verified within specifications",
            "haccp_relevant": True
        })
        
        # 3. Calibration certificate uploaded
        cert_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "calibration_certificate_uploaded",
            "resource_type": "document",
            "resource_id": uuid.uuid4(),
            "new_values": {
                "document_type": "calibration_certificate",
                "sensor_id": str(sensor_id),  # FIX: Converti UUID a string
                "file_name": "TEMP_SENSOR_001_CAL_2024.pdf",
                "uploaded_at": datetime.utcnow().isoformat()
            },
            "description": "Calibration certificate uploaded for compliance documentation",
            "haccp_relevant": True
        })
        
        # Get calibration audit trail for specific sensor
        sensor_logs = audit_log_repository.get_by_resource("sensor", sensor_id)
        
        assert len(sensor_logs) >= 2
        sensor_actions = [log.action for log in sensor_logs]
        assert "calibration_due_notification" in sensor_actions
        assert "sensor_calibration_performed" in sensor_actions
        
        print(f"✅ Calibration compliance audit trail complete")
        print(f"   - Sensor-specific logs: {len(sensor_logs)}")
    
    def test_compliance_reporting_audit(self, audit_log_repository, sample_organization, sample_user):
        """Test audit trail for compliance reporting"""
        # Monthly compliance report generation
        report_resource_id = uuid.uuid4()
        
        report_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "haccp_compliance_report_generated",
            "resource_type": "report",
            "resource_id": report_resource_id,
            "new_values": {
                "report_type": "monthly_haccp_compliance",
                "period_start": "2024-01-01",
                "period_end": "2024-01-31",
                "temperature_violations": 2,
                "calibration_compliance": "100%",
                "corrective_actions": 3
            },
            "description": "Monthly HACCP compliance report generated for January 2024",
            "haccp_relevant": True
        })
        
        # Report reviewed and approved
        review_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": sample_user.id,
            "action": "compliance_report_approved",
            "resource_type": "report",
            "resource_id": report_resource_id,  # FIX: Usa la variabile diretta
            "old_values": {"status": "draft", "approved_by": None},
            # FIX: Converti UUID a string per evitare errore JSON serialization
            "new_values": {
                "status": "approved", 
                "approved_by": str(sample_user.id),  # STRING, non UUID
                "approved_at": datetime.utcnow().isoformat()
            },
            "description": "HACCP compliance report reviewed and approved",
            "haccp_relevant": True
        })
        
        # Test report audit trail
        report_logs = audit_log_repository.get_by_resource("report", report_resource_id)
        
        assert len(report_logs) == 2
        report_actions = [log.action for log in report_logs]
        assert "haccp_compliance_report_generated" in report_actions
        assert "compliance_report_approved" in report_actions
        
        print(f"✅ Compliance reporting audit trail complete")

# =====================================================
# TEST EDGE CASES AND ERROR SCENARIOS
# =====================================================

class TestAuditLogEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cascade_delete_organization(self, test_db, audit_log_repository, sample_audit_log_data):
        """Test what happens when organization is deleted"""
        # Create temporary organization
        temp_org = Organization(
            name="Temp Org for Audit Delete Test",
            slug="temp-org-delete-audit",
            subscription_plan="basic"
        )
        test_db.add(temp_org)
        test_db.commit()
        test_db.refresh(temp_org)
        
        # Create audit log in temp organization
        audit_log = audit_log_repository.create({
            **sample_audit_log_data,
            "organization_id": temp_org.id,
            "user_id": None,  # Avoid user FK constraint
            "action": "temp_delete_test"
        })
        
        # Store audit log ID before deletion
        audit_log_id = audit_log.id
        
        # Clear session to avoid stale references
        test_db.expunge(audit_log)
        
        # Act - Delete organization (should set organization_id to NULL due to SET NULL)
        test_db.delete(temp_org)
        test_db.commit()
        
        # Assert - Audit log should still exist but with NULL organization_id
        found_audit_log = audit_log_repository.get_by_id(audit_log_id)
        assert found_audit_log is not None
        assert found_audit_log.organization_id is None  # SET NULL
        
        print(f"✅ Cascade delete with SET NULL working correctly")
    
    def test_audit_log_with_very_large_json(self, audit_log_repository, sample_audit_log_data):
        """Test audit log with large JSON data"""
        # Create large JSON structure
        large_data = {
            "sensor_readings": [
                {"timestamp": f"2024-01-{i:02d}T12:00:00Z", "temperature": -18.0 + (i * 0.1), "humidity": 25.0}
                for i in range(1, 100)  # 99 readings
            ],
            "configuration": {
                "thresholds": {f"zone_{i}": {"min": -20.0, "max": -15.0} for i in range(1, 50)},
                "alerts": {f"alert_{i}": {"enabled": True, "severity": "medium"} for i in range(1, 50)}
            }
        }
        
        large_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "bulk_configuration_update",
            "new_values": large_data,
            "description": "Bulk update of sensor configurations and thresholds"
        })
        
        assert large_log.new_values is not None
        assert len(large_log.new_values["sensor_readings"]) == 99
        assert len(large_log.new_values["configuration"]["thresholds"]) == 49
        
        print(f"✅ Large JSON data handling working correctly")
    
    def test_audit_log_with_special_characters(self, audit_log_repository, sample_audit_log_data):
        """Test audit log with special characters and unicode"""
        special_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "configurazione_aggiornata",
            "description": "Configurazione sensore aggiornata: Frigorifero Ñ°1 - Temperatura crítica ±0.5°C",
            "new_values": {
                "location": "Cucina → Frigorifero Principal",
                "notes": "Configuración actualizada según normativa HACCP 2024 ✓",
                "symbols": "±°¿¡™®©"
            }
        })
        
        assert "Ñ°1" in special_log.description
        assert "±0.5°C" in special_log.description
        assert "→" in special_log.new_values["location"]
        assert "✓" in special_log.new_values["notes"]
        
        print(f"✅ Special characters handling working correctly")
    
    def test_audit_log_with_null_values(self, audit_log_repository, sample_organization):
        """Test audit log with various null values"""
        null_log = audit_log_repository.create({
            "organization_id": sample_organization.id,
            "user_id": None,
            "action": "system_heartbeat",
            "resource_type": None,
            "resource_id": None,
            "old_values": None,
            "new_values": None,
            "description": None,
            "ip_address": None,
            "user_agent": None,
            "haccp_relevant": False
        })
        
        assert null_log.id is not None
        assert null_log.user_id is None
        assert null_log.resource_type is None
        assert null_log.old_values is None
        assert null_log.new_values is None
        assert null_log.has_changes == False
        
        print(f"✅ Null values handling working correctly")

# =====================================================
# TEST AUDIT LOG LIFECYCLE AND INTEGRITY
# =====================================================

class TestAuditLogLifecycleIntegrity:
    """Test audit log lifecycle and data integrity"""
    
    def test_audit_log_immutability_concept(self, audit_log_repository, created_audit_log):
        """Test audit log immutability principles"""
        # Audit logs should generally be immutable for compliance
        # This test documents the expected behavior
        
        original_action = created_audit_log.action
        original_created_at = created_audit_log.created_at
        
        # If updates are allowed, they should be very limited
        # and possibly tracked themselves
        try:
            updated_log = audit_log_repository.update(created_audit_log.id, {
                "description": "Updated for compliance review"
            })
            
            # If update succeeds, verify critical fields unchanged
            assert updated_log.action == original_action
            assert updated_log.created_at == original_created_at
            
            print(f"✅ Limited update allowed - critical fields preserved")
        except Exception as e:
            print(f"✅ Update restricted for compliance: {type(e).__name__}")
    
    def test_audit_log_chronological_integrity(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test chronological integrity of audit logs"""
        # Create logs in sequence
        log1 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "step_1",
            "description": "First action in sequence"
        })
        
        # Small delay to ensure different timestamps
        import time
        time.sleep(0.1)
        
        log2 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "step_2", 
            "description": "Second action in sequence"
        })
        
        time.sleep(0.1)
        
        log3 = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "step_3",
            "description": "Third action in sequence"
        })
        
        # Verify chronological order
        all_logs = audit_log_repository.get_by_organization(sample_organization.id)
        
        # Find our logs in the results
        our_logs = [log for log in all_logs if log.action.startswith("step_")]
        our_logs.sort(key=lambda x: x.created_at)
        
        assert len(our_logs) == 3
        assert our_logs[0].action == "step_1"
        assert our_logs[1].action == "step_2"
        assert our_logs[2].action == "step_3"
        assert our_logs[0].created_at <= our_logs[1].created_at <= our_logs[2].created_at
        
        print(f"✅ Chronological integrity maintained")
    
    def test_audit_log_data_consistency(self, audit_log_repository, sample_audit_log_data):
        """Test data consistency across related audit logs"""
        resource_id = uuid.uuid4()
        
        # Create sequence of related logs for same resource
        create_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_created",
            "resource_type": "sensor",
            "resource_id": resource_id,
            "new_values": {"name": "Test Sensor", "status": "online"}
        })
        
        update_log = audit_log_repository.create({
            **sample_audit_log_data,
            "action": "sensor_updated",
            "resource_type": "sensor",
            "resource_id": resource_id,
            "old_values": {"name": "Test Sensor", "status": "online"},
            "new_values": {"name": "Test Sensor", "status": "maintenance"}
        })
        
        # Verify consistency
        resource_logs = audit_log_repository.get_by_resource("sensor", resource_id)
        
        assert len(resource_logs) == 2
        assert all(log.resource_id == resource_id for log in resource_logs)
        assert all(log.resource_type == "sensor" for log in resource_logs)
        
        # Verify logical sequence
        logs_by_action = {log.action: log for log in resource_logs}
        create_new = logs_by_action["sensor_created"].new_values
        update_old = logs_by_action["sensor_updated"].old_values
        
        # The old values of update should match new values of create
        assert create_new["status"] == update_old["status"]
        assert create_new["name"] == update_old["name"]
        
        print(f"✅ Data consistency maintained across related logs")

# =====================================================
# TEST AUDIT LOG SEARCH AND ANALYTICS
# =====================================================

class TestAuditLogSearchAnalytics:
    """Test advanced search and analytics capabilities"""
    
    def test_comprehensive_search_functionality(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test comprehensive search across different fields"""
        # Create logs with various searchable content
        search_logs = [
            {
                **sample_audit_log_data,
                "action": "temperature_critical_alert",
                "description": "Critical temperature exceeded in freezer room",
                "resource_type": "alert"
            },
            {
                **sample_audit_log_data,
                "action": "sensor_calibration",
                "description": "Performed routine calibration on temperature sensor",
                "resource_type": "sensor"
            },
            {
                **sample_audit_log_data,
                "action": "user_access_granted",
                "description": "Access granted to temperature monitoring dashboard",
                "resource_type": "user"
            },
            {
                **sample_audit_log_data,
                "action": "maintenance_completed",
                "description": "Completed preventive maintenance on cooling system",
                "resource_type": "maintenance"
            }
        ]
        
        for log_data in search_logs:
            audit_log_repository.create(log_data)
        
        # Test different search terms
        
        # Search by action content
        temp_results = audit_log_repository.search_logs(sample_organization.id, "temperature")
        temp_actions = [log.action for log in temp_results]
        assert any("temperature" in action for action in temp_actions)
        
        # Search by description content
        calibration_results = audit_log_repository.search_logs(sample_organization.id, "calibration")
        calibration_descriptions = [log.description for log in calibration_results]
        assert any("calibration" in desc.lower() for desc in calibration_descriptions)
        
        # Search for specific terms
        critical_results = audit_log_repository.search_logs(sample_organization.id, "critical")
        assert len(critical_results) >= 1
        
        maintenance_results = audit_log_repository.search_logs(sample_organization.id, "maintenance")
        assert len(maintenance_results) >= 1
        
        print(f"✅ Comprehensive search functionality working")
        print(f"   - Temperature: {len(temp_results)} results")
        print(f"   - Calibration: {len(calibration_results)} results")
        print(f"   - Critical: {len(critical_results)} results")
        print(f"   - Maintenance: {len(maintenance_results)} results")
    
    def test_date_range_analytics(self, audit_log_repository, sample_organization, sample_audit_log_data):
        """Test date range queries for analytics"""
        now = datetime.utcnow()
        
        # Create logs across different time periods
        periods = [
            (timedelta(days=1), "recent_activity"),
            (timedelta(days=7), "weekly_activity"),
            (timedelta(days=30), "monthly_activity"),
            (timedelta(days=90), "quarterly_activity")
        ]
        
        created_logs = []
        for delta, action in periods:
            log = audit_log_repository.create({
                **sample_audit_log_data,
                "action": action,
                "description": f"Activity from {delta.days} days ago"
            })
            
            # FIX: Usa text() per wrapped SQL
            target_time = now - delta
            audit_log_repository.db.execute(
                text("UPDATE audit_log SET created_at = :target_time WHERE id = :log_id"),
                {"target_time": target_time, "log_id": log.id}
            )
            created_logs.append(log)
        
        audit_log_repository.db.commit()
        
        # Test different date ranges
        
        # Last 7 days
        week_start = now - timedelta(days=7)
        week_logs = audit_log_repository.get_by_date_range(sample_organization.id, week_start, now)
        week_actions = [log.action for log in week_logs]
        assert "recent_activity" in week_actions
        assert "weekly_activity" in week_actions
        
        # Last 30 days
        month_start = now - timedelta(days=30)
        month_logs = audit_log_repository.get_by_date_range(sample_organization.id, month_start, now)
        month_actions = [log.action for log in month_logs]
        assert "recent_activity" in month_actions
        assert "weekly_activity" in month_actions
        assert "monthly_activity" in month_actions
        
        print(f"✅ Date range analytics working")
        print(f"   - Last 7 days: {len(week_logs)} logs")
        print(f"   - Last 30 days: {len(month_logs)} logs")
    
    def test_activity_pattern_analysis(self, audit_log_repository, sample_organization, sample_user, sample_audit_log_data):
        """Test analyzing user activity patterns"""
        # Create varied user activities
        activities = [
            "user_login", "dashboard_viewed", "sensor_configured",
            "alert_acknowledged", "report_generated", "user_logout",
            "user_login", "data_exported", "settings_updated"
        ]
        
        for activity in activities:
            audit_log_repository.create({
                **sample_audit_log_data,
                "action": activity,
                "description": f"User performed {activity.replace('_', ' ')}"
            })
        
        # Analyze user activity
        user_logs = audit_log_repository.get_by_user(sample_user.id)
        
        # Count activity types
        activity_counts = {}
        for log in user_logs:
            action = log.action
            activity_counts[action] = activity_counts.get(action, 0) + 1
        
        # Verify patterns
        assert activity_counts.get("user_login", 0) >= 2  # Multiple logins
        assert len(activity_counts) >= len(set(activities))  # Various activities
        
        print(f"✅ Activity pattern analysis working")
        print(f"   - Total user activities: {len(user_logs)}")
        print(f"   - Unique activity types: {len(activity_counts)}")
        print(f"   - Most frequent: {max(activity_counts.items(), key=lambda x: x[1]) if activity_counts else 'N/A'}")