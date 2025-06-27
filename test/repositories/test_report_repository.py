# =====================================================
# test/repositories/test_report_repository.py
# =====================================================
"""
Test per ReportRepository - testa gestione reports manuali e scheduling automatico.

Usa conftest.py per setup condiviso e import automatici.
"""

import pytest
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal

# Clean imports - no path manipulation needed
from src.models import Organization, User, Report
from src.models.report import ReportType, ReportStatus, ScheduleFrequency
from src.repositories.report_repository import ReportRepository

# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def report_repository(test_db):
    """Create ReportRepository instance"""
    return ReportRepository(test_db)

@pytest.fixture
def sample_organization(test_db):
    """Create sample organization for testing"""
    org = Organization(
        name="Report Test Company",
        slug="report-test-company",
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
        email="report_user@example.com",
        first_name="Report",
        last_name="User",
        role="admin",
        is_active=True,
        is_verified=True
    )
    user.set_password("ReportPassword123!")
    
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def sample_report_data(sample_organization, sample_user):
    """Sample report data for testing"""
    return {
        "organization_id": sample_organization.id,
        "generated_by": sample_user.id,
        "report_type": ReportType.HACCP_MONTHLY,
        "report_name": "Monthly HACCP Compliance Report",
        "period_start": date.today().replace(day=1),  # First of month
        "period_end": date.today(),
        "status": ReportStatus.PENDING,
        "is_auto_generated": False,
        "schedule_frequency": ScheduleFrequency.MANUAL,
        "is_active_schedule": False
    }

@pytest.fixture
def created_report(report_repository, sample_report_data):
    """Create and return a test report"""
    return report_repository.create(sample_report_data)

@pytest.fixture
def second_organization(test_db):
    """Create second organization for multi-tenancy tests"""
    org = Organization(
        name="Second Report Test Company",
        slug="second-report-test-company",
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

class TestReportCRUD:
    """Test basic CRUD operations"""
    
    def test_create_report_success(self, report_repository, sample_report_data):
        """Test creating a new report"""
        
        # Act
        report = report_repository.create(sample_report_data)
        
        # Assert
        assert report.id is not None
        assert report.organization_id == sample_report_data["organization_id"]
        assert report.generated_by == sample_report_data["generated_by"]
        assert report.report_type == sample_report_data["report_type"]
        assert report.report_name == sample_report_data["report_name"]
        assert report.period_start == sample_report_data["period_start"]
        assert report.period_end == sample_report_data["period_end"]
        assert report.status == sample_report_data["status"]
        assert report.is_auto_generated == sample_report_data["is_auto_generated"]
        assert report.schedule_frequency == sample_report_data["schedule_frequency"]
        assert report.is_active_schedule == sample_report_data["is_active_schedule"]
        
        # Verify timestamps
        assert report.created_at is not None
        assert report.updated_at is not None
        
        print(f"✅ Report created with ID: {report.id}")
        print(f"✅ Type: {report.report_type.value}, Status: {report.status.value}")
        print(f"✅ Period: {report.period_start} to {report.period_end}")
    
    def test_get_by_id(self, report_repository, created_report):
        """Test getting report by ID"""
        # Act
        found_report = report_repository.get_by_id(created_report.id)
        
        # Assert
        assert found_report is not None
        assert found_report.id == created_report.id
        assert found_report.report_name == created_report.report_name
        assert found_report.report_type == created_report.report_type
        
        print(f"✅ Report found by ID: {found_report.id}")
    
    def test_get_by_id_not_found(self, report_repository):
        """Test getting non-existent report"""
        # Act
        found_report = report_repository.get_by_id(uuid.uuid4())
        
        # Assert
        assert found_report is None
        print("✅ Non-existent report correctly returned None")
    
    def test_update_report(self, report_repository, created_report):
        """Test updating report"""
        # Arrange
        update_data = {
            "status": ReportStatus.GENERATING,
            "generation_started_at": datetime.utcnow(),
            "report_name": "Updated HACCP Report"
        }
        
        # Act
        updated_report = report_repository.update(created_report.id, update_data)
        
        # Assert
        assert updated_report is not None
        assert updated_report.status == ReportStatus.GENERATING
        assert updated_report.generation_started_at is not None
        assert updated_report.report_name == "Updated HACCP Report"
        # Check unchanged fields
        assert updated_report.report_type == created_report.report_type
        assert updated_report.organization_id == created_report.organization_id
        
        print(f"✅ Report updated successfully")
    
    def test_delete_report(self, report_repository, created_report):
        """Test deleting report"""
        # Act
        result = report_repository.delete(created_report.id)
        
        # Assert
        assert result == True
        
        # Verify it's deleted
        found_report = report_repository.get_by_id(created_report.id)
        assert found_report is None
        
        print(f"✅ Report deleted successfully")
    
    def test_delete_nonexistent_report(self, report_repository):
        """Test deleting non-existent report"""
        # Act
        result = report_repository.delete(uuid.uuid4())
        
        # Assert
        assert result == False
        print("✅ Delete of non-existent report correctly returned False")

# =====================================================
# TEST REPORT-SPECIFIC QUERIES
# =====================================================

class TestReportQueries:
    """Test report-specific query methods"""
    
    def test_get_by_organization(self, report_repository, sample_organization, sample_report_data):
        """Test getting reports by organization"""
        # Arrange - Create multiple reports
        report1 = report_repository.create(sample_report_data)
        report2 = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.TEMPERATURE_SUMMARY,
            "report_name": "Temperature Summary Report"
        })
        
        # Act
        org_reports = report_repository.get_by_organization(sample_organization.id)
        
        # Assert
        assert len(org_reports) >= 2
        report_ids = [rep.id for rep in org_reports]
        assert report1.id in report_ids
        assert report2.id in report_ids
        assert all(rep.organization_id == sample_organization.id for rep in org_reports)
        
        # Should be ordered by created_at DESC
        creation_times = [rep.created_at for rep in org_reports]
        assert creation_times == sorted(creation_times, reverse=True)
        
        print(f"✅ Found {len(org_reports)} reports in organization")
    
    def test_get_by_type(self, report_repository, sample_organization, sample_report_data):
        """Test getting reports by type"""
        # Arrange - Create reports of different types
        haccp_report = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.HACCP_MONTHLY,
            "report_name": "HACCP Monthly Report"
        })
        
        temp_report = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.TEMPERATURE_SUMMARY,
            "report_name": "Temperature Summary"
        })
        
        sensor_report = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.SENSOR_STATUS,
            "report_name": "Sensor Status Report"
        })
        
        # Act
        haccp_reports = report_repository.get_by_type(sample_organization.id, ReportType.HACCP_MONTHLY)
        temp_reports = report_repository.get_by_type(sample_organization.id, ReportType.TEMPERATURE_SUMMARY)
        
        # Assert
        haccp_ids = [rep.id for rep in haccp_reports]
        temp_ids = [rep.id for rep in temp_reports]
        
        assert haccp_report.id in haccp_ids
        assert temp_report.id in temp_ids
        assert sensor_report.id not in haccp_ids
        assert sensor_report.id not in temp_ids
        assert all(rep.report_type == ReportType.HACCP_MONTHLY for rep in haccp_reports)
        assert all(rep.report_type == ReportType.TEMPERATURE_SUMMARY for rep in temp_reports)
        
        print(f"✅ Found {len(haccp_reports)} HACCP reports and {len(temp_reports)} temperature reports")
    
    def test_get_completed_reports(self, report_repository, sample_organization, sample_report_data):
        """Test getting completed reports"""
        # Arrange - Create reports with different statuses
        completed_report1 = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "generation_completed_at": datetime.utcnow() - timedelta(days=1),
            "report_name": "Completed Report 1"
        })
        
        completed_report2 = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "generation_completed_at": datetime.utcnow() - timedelta(hours=12),
            "report_name": "Completed Report 2"
        })
        
        pending_report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.PENDING,
            "report_name": "Pending Report"
        })
        
        # Act
        completed_reports = report_repository.get_completed_reports(sample_organization.id, limit=50)
        
        # Assert
        completed_ids = [rep.id for rep in completed_reports]
        assert completed_report1.id in completed_ids
        assert completed_report2.id in completed_ids
        assert pending_report.id not in completed_ids
        assert all(rep.status == ReportStatus.COMPLETED for rep in completed_reports)
        
        # Should be ordered by generation_completed_at DESC
        completion_times = [rep.generation_completed_at for rep in completed_reports if rep.generation_completed_at]
        if len(completion_times) > 1:
            assert completion_times == sorted(completion_times, reverse=True)
        
        print(f"✅ Found {len(completed_reports)} completed reports")

# =====================================================
# TEST SCHEDULING FUNCTIONALITY
# =====================================================

class TestReportScheduling:
    """Test report scheduling functionality"""
    
    def test_get_scheduled_reports(self, report_repository, sample_organization, sample_report_data):
        """Test getting scheduled reports"""
        # Arrange - Create scheduled and manual reports
        scheduled_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.WEEKLY,
            "is_active_schedule": True,
            "next_generation_date": datetime.utcnow() + timedelta(days=7),
            "report_name": "Weekly Scheduled Report"
        })
        
        manual_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.MANUAL,
            "is_active_schedule": False,
            "report_name": "Manual Report"
        })
        
        inactive_scheduled = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.MONTHLY,
            "is_active_schedule": False,  # Inactive
            "report_name": "Inactive Scheduled Report"
        })
        
        # Act
        scheduled_reports = report_repository.get_scheduled_reports(sample_organization.id)
        
        # Assert
        scheduled_ids = [rep.id for rep in scheduled_reports]
        assert scheduled_report.id in scheduled_ids
        assert manual_report.id not in scheduled_ids
        assert inactive_scheduled.id not in scheduled_ids
        assert all(rep.schedule_frequency != ScheduleFrequency.MANUAL for rep in scheduled_reports)
        assert all(rep.is_active_schedule == True for rep in scheduled_reports)
        
        print(f"✅ Found {len(scheduled_reports)} active scheduled reports")
    
    def test_get_reports_due_for_generation(self, report_repository, sample_organization, sample_report_data):
        """Test getting reports due for auto-generation"""
        # Arrange - Create reports with different due dates
        due_now_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.WEEKLY,
            "is_active_schedule": True,
            "next_generation_date": datetime.utcnow() - timedelta(hours=1),  # Due 1 hour ago
            "status": ReportStatus.PENDING,
            "report_name": "Due Now Report"
        })
        
        due_later_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.MONTHLY,
            "is_active_schedule": True,
            "next_generation_date": datetime.utcnow() + timedelta(days=7),  # Due in 7 days
            "status": ReportStatus.PENDING,
            "report_name": "Due Later Report"
        })
        
        generating_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.WEEKLY,
            "is_active_schedule": True,
            "next_generation_date": datetime.utcnow() - timedelta(hours=2),  # Due but generating
            "status": ReportStatus.GENERATING,
            "report_name": "Currently Generating Report"
        })
        
        # Act
        due_reports = report_repository.get_reports_due_for_generation()
        
        # Assert
        due_ids = [rep.id for rep in due_reports]
        assert due_now_report.id in due_ids
        assert due_later_report.id not in due_ids
        assert generating_report.id not in due_ids
        
        for report in due_reports:
            assert report.is_active_schedule == True
            assert report.next_generation_date <= datetime.utcnow()
            assert report.status != ReportStatus.GENERATING
        
        print(f"✅ Found {len(due_reports)} reports due for generation")

# =====================================================
# TEST REPORT BUSINESS LOGIC
# =====================================================

class TestReportBusinessLogic:
    """Test report business logic and properties"""
    
    def test_report_properties(self, report_repository, sample_report_data):
        """Test report model properties"""
        # Create completed report
        completed_report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "schedule_frequency": ScheduleFrequency.WEEKLY
        })
        
        # Create manual report
        manual_report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.PENDING,
            "schedule_frequency": ScheduleFrequency.MANUAL
        })
        
        # Test properties
        assert completed_report.is_completed == True
        assert manual_report.is_completed == False
        
        assert completed_report.is_scheduled_report == True
        assert manual_report.is_scheduled_report == False
        
        print(f"✅ Report properties working correctly")
        print(f"   - Completed report is_completed: {completed_report.is_completed}")
        print(f"   - Manual report is_scheduled_report: {manual_report.is_scheduled_report}")
    
    def test_next_generation_calculation(self, report_repository, sample_report_data):
        """Test next generation date calculation"""
        # Create weekly scheduled report
        weekly_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.WEEKLY,
            "is_active_schedule": True
        })
        
        # Create monthly scheduled report
        monthly_report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.MONTHLY,
            "is_active_schedule": True
        })
        
        # Test calculation methods
        weekly_next = weekly_report.calculate_next_generation_date()
        monthly_next = monthly_report.calculate_next_generation_date()
        
        assert weekly_next is not None
        assert monthly_next is not None
        assert weekly_next > datetime.utcnow()
        assert monthly_next > datetime.utcnow()
        
        print(f"✅ Next generation calculation working correctly")
        print(f"   - Weekly next: {weekly_next}")
        print(f"   - Monthly next: {monthly_next}")
    
    def test_setup_auto_generation(self, report_repository, sample_report_data):
        """Test auto-generation setup"""
        # Create manual report
        report = report_repository.create(sample_report_data)
        
        # Setup auto-generation
        config = {
            "email_recipients": ["admin@company.com", "manager@company.com"],
            "include_charts": True,
            "format": "pdf"
        }
        
        # This would normally be done in the service layer
        report.setup_auto_generation(ScheduleFrequency.WEEKLY, config)
        report_repository.db.commit()
        
        # Refresh and verify
        report_repository.db.refresh(report)
        assert report.schedule_frequency == ScheduleFrequency.WEEKLY
        assert report.is_active_schedule == True
        assert report.auto_config == config
        assert report.next_generation_date is not None
        
        print(f"✅ Auto-generation setup working correctly")

# =====================================================
# TEST MULTI-TENANCY
# =====================================================

class TestReportMultiTenancy:
    """Test multi-tenancy isolation for reports"""
    
    def test_organization_isolation(self, report_repository, sample_organization, second_organization, sample_report_data):
        """Test that reports are isolated by organization"""
        
        # Create second org user
        second_user = User(
            organization_id=second_organization.id,
            email="second_user@example.com",
            first_name="Second",
            last_name="User",
            role="admin",
            is_active=True,
            is_verified=True
        )
        second_user.set_password("SecondUserPass123!")
        report_repository.db.add(second_user)
        report_repository.db.commit()
        report_repository.db.refresh(second_user)
        
        # Create reports in different organizations
        report1 = report_repository.create({
            **sample_report_data,
            "organization_id": sample_organization.id,
            "report_name": "Org1 Report"
        })
        
        report2 = report_repository.create({
            **sample_report_data,
            "organization_id": second_organization.id,
            "generated_by": second_user.id,
            "report_name": "Org2 Report"
        })
        
        # Test isolation using organization-specific queries
        org1_reports = report_repository.get_by_organization(sample_organization.id)
        org2_reports = report_repository.get_by_organization(second_organization.id)
        
        # Assert isolation
        org1_report_ids = [rep.id for rep in org1_reports]
        org2_report_ids = [rep.id for rep in org2_reports]
        
        assert report1.id in org1_report_ids
        assert report1.id not in org2_report_ids
        assert report2.id in org2_report_ids
        assert report2.id not in org1_report_ids
        
        print(f"✅ Multi-tenancy isolation working correctly!")
        print(f"   - Org1 reports: {len(org1_reports)}")
        print(f"   - Org2 reports: {len(org2_reports)}")

# =====================================================
# TEST REPORT STATUS WORKFLOW
# =====================================================

class TestReportStatusWorkflow:
    """Test report status workflow and transitions"""
    
    def test_complete_report_workflow(self, report_repository, sample_report_data):
        """Test complete report generation workflow"""
        # 1. Create pending report
        report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.PENDING,
            "report_name": "Workflow Test Report"
        })
        
        print(f"✅ Step 1: Report created with status PENDING")
        
        # 2. Start generation
        report = report_repository.update(report.id, {
            "status": ReportStatus.GENERATING,
            "generation_started_at": datetime.utcnow()
        })
        
        assert report.status == ReportStatus.GENERATING
        assert report.generation_started_at is not None
        print(f"✅ Step 2: Report status updated to GENERATING")
        
        # 3. Complete generation successfully
        completion_time = datetime.utcnow()
        report_data = {
            "total_sensors": 25,
            "compliance_rate": 98.5,
            "alerts_count": 3
        }
        
        report = report_repository.update(report.id, {
            "status": ReportStatus.COMPLETED,
            "generation_completed_at": completion_time,
            "report_data": report_data,
            "file_path": "/reports/workflow_test_report.pdf",
            "file_size_bytes": 1024000  # 1MB
        })
        
        assert report.status == ReportStatus.COMPLETED
        assert report.generation_completed_at == completion_time
        assert report.report_data == report_data
        assert report.file_path == "/reports/workflow_test_report.pdf"
        assert report.file_size_bytes == 1024000
        
        print(f"✅ Step 3: Report completed successfully")
        print(f"   - File: {report.file_path}")
        print(f"   - Size: {report.file_size_bytes} bytes")
        print(f"   - Data: {report.report_data}")
        
        print("✅ Complete report workflow test passed!")
    
    def test_failed_report_generation(self, report_repository, sample_report_data):
        """Test failed report generation scenario"""
        # Create and start report
        report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.GENERATING,
            "generation_started_at": datetime.utcnow(),
            "report_name": "Failed Report Test"
        })
        
        # Simulate generation failure
        report = report_repository.update(report.id, {
            "status": ReportStatus.FAILED,
            "generation_error": "Database connection timeout during report generation"
        })
        
        assert report.status == ReportStatus.FAILED
        assert report.generation_error is not None
        assert "timeout" in report.generation_error
        assert report.report_data is None
        assert report.file_path is None
        
        print(f"✅ Failed report generation handled correctly")
        print(f"   - Error: {report.generation_error}")

# =====================================================
# TEST PERFORMANCE AND LARGE DATASETS
# =====================================================

class TestReportPerformance:
    """Test report repository performance"""
    
    def test_large_report_volume(self, report_repository, sample_organization, sample_report_data, sample_user):
        """Test handling large volume of reports"""
        import time
        
        # Arrange
        start_time = time.time()
        report_count = 25  # Reasonable number for testing
        report_types = [ReportType.HACCP_MONTHLY, ReportType.TEMPERATURE_SUMMARY, 
                       ReportType.SENSOR_STATUS, ReportType.ALERT_SUMMARY]
        
        # Act - Create multiple reports
        created_reports = []
        for i in range(report_count):
            report_data = {
                **sample_report_data,
                "report_type": report_types[i % len(report_types)],
                "report_name": f"Performance Test Report {i:03d}",
                "period_start": date.today().replace(day=1) - timedelta(days=i*30),
                "period_end": date.today() - timedelta(days=i*30)
            }
            report = report_repository.create(report_data)
            created_reports.append(report)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert
        assert len(created_reports) == report_count
        assert duration < 15  # Should complete within 15 seconds
        
        # Test bulk queries performance
        start_query_time = time.time()
        all_org_reports = report_repository.get_by_organization(sample_organization.id)
        end_query_time = time.time()
        query_duration = end_query_time - start_query_time
        
        assert len(all_org_reports) >= report_count
        assert query_duration < 3  # Query should be fast
        
        print(f"✅ Created {report_count} reports in {duration:.2f} seconds")
        print(f"✅ Queried {len(all_org_reports)} reports in {query_duration:.3f} seconds")
        print(f"✅ Average: {duration/report_count:.3f} seconds per report")

# =====================================================
# TEST HACCP COMPLIANCE SCENARIOS
# =====================================================

class TestHACCPCompliance:
    """Test HACCP compliance scenarios for reports"""
    
    def test_haccp_monthly_report_generation(self, report_repository, sample_organization, sample_report_data):
        """Test HACCP monthly report generation"""
        # Arrange - Create HACCP monthly report
        haccp_report = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.HACCP_MONTHLY,
            "report_name": "HACCP Monthly Compliance Report - June 2025",
            "period_start": date(2025, 6, 1),
            "period_end": date(2025, 6, 30),
            "status": ReportStatus.COMPLETED,
            "report_data": {
                "compliance_rate": 97.8,
                "total_temperature_readings": 15680,
                "deviation_incidents": 12,
                "corrective_actions": 8,
                "calibration_events": 6,
                "critical_control_points": {
                    "freezer_compliance": 98.5,
                    "fridge_compliance": 97.2,
                    "cold_room_compliance": 98.1
                }
            }
        })
        
        # Test HACCP-specific data structure
        assert haccp_report.report_type == ReportType.HACCP_MONTHLY
        assert haccp_report.report_data["compliance_rate"] == 97.8
        assert "critical_control_points" in haccp_report.report_data
        assert haccp_report.report_data["deviation_incidents"] == 12
        
        print(f"✅ HACCP monthly report generated correctly")
        print(f"   - Compliance rate: {haccp_report.report_data['compliance_rate']}%")
        print(f"   - Total readings: {haccp_report.report_data['total_temperature_readings']}")
        print(f"   - Deviations: {haccp_report.report_data['deviation_incidents']}")
    
    def test_compliance_report_scheduling(self, report_repository, sample_organization, sample_report_data):
        """Test compliance report auto-scheduling"""
        # Create monthly scheduled HACCP report
        scheduled_haccp = report_repository.create({
            **sample_report_data,
            "report_type": ReportType.HACCP_MONTHLY,
            "report_name": "Auto-Generated HACCP Monthly Report",
            "schedule_frequency": ScheduleFrequency.MONTHLY,
            "is_active_schedule": True,
            "is_auto_generated": True,
            "auto_config": {
                "email_recipients": ["quality@company.com", "manager@company.com"],
                "include_charts": True,
                "format": "pdf"
            }
        })
        
        # Calculate next generation date
        next_date = scheduled_haccp.calculate_next_generation_date()
        scheduled_haccp.next_generation_date = next_date
        report_repository.db.commit()
        
        # Verify scheduling setup
        assert scheduled_haccp.is_scheduled_report == True
        assert scheduled_haccp.schedule_frequency == ScheduleFrequency.MONTHLY
        assert scheduled_haccp.next_generation_date is not None
        assert scheduled_haccp.auto_config["email_recipients"] == ["quality@company.com", "manager@company.com"]
        
        # Test that it appears in scheduled reports
        scheduled_reports = report_repository.get_scheduled_reports(sample_organization.id)
        scheduled_ids = [rep.id for rep in scheduled_reports]
        assert scheduled_haccp.id in scheduled_ids
        
        print(f"✅ HACCP compliance report scheduling working correctly")
        print(f"   - Next generation: {scheduled_haccp.next_generation_date}")
        print(f"   - Recipients: {scheduled_haccp.auto_config['email_recipients']}")

# =====================================================
# TEST REPORT CONSTRAINTS AND VALIDATION
# =====================================================

class TestReportConstraints:
    """Test report database constraints and validation"""
    
    def test_period_constraint_validation(self, report_repository, sample_report_data):
        """Test that period_start <= period_end constraint works"""
        # Valid period should work
        valid_report = report_repository.create({
            **sample_report_data,
            "period_start": date(2025, 6, 1),
            "period_end": date(2025, 6, 30),
            "report_name": "Valid Period Report"
        })
        assert valid_report.period_start <= valid_report.period_end
        
        # Invalid period should fail
        try:
            report_repository.create({
                **sample_report_data,
                "period_start": date(2025, 6, 30),  # After end date
                "period_end": date(2025, 6, 1),    # Before start date
                "report_name": "Invalid Period Report"
            })
            assert False, "Should have failed due to invalid period"
        except Exception as e:
            assert "chk_report_period_valid" in str(e) or "constraint" in str(e).lower()
        
        print(f"✅ Period constraint validation working correctly")
    
    def test_file_size_constraint(self, report_repository, sample_report_data):
        """Test file size constraint validation"""
        # Valid file size
        valid_report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "file_size_bytes": 1024000,  # 1MB
            "report_name": "Valid File Size Report"
        })
        assert valid_report.file_size_bytes >= 0
        
        # Zero file size should be allowed
        zero_size_report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "file_size_bytes": 0,
            "report_name": "Zero Size Report"
        })
        assert zero_size_report.file_size_bytes == 0
        
        print(f"✅ File size constraint validation working correctly")
    
    def test_report_type_enum_validation(self, report_repository, sample_report_data):
        """Test report type enum validation"""
        # All valid report types should work
        valid_types = [ReportType.HACCP_MONTHLY, ReportType.TEMPERATURE_SUMMARY, 
                      ReportType.SENSOR_STATUS, ReportType.ALERT_SUMMARY]
        
        for report_type in valid_types:
            report = report_repository.create({
                **sample_report_data,
                "report_type": report_type,
                "report_name": f"Test {report_type.value} Report"
            })
            assert report.report_type == report_type
        
        print(f"✅ All valid report types work correctly")

# =====================================================
# TEST REPORT RELATIONSHIPS
# =====================================================

class TestReportRelationships:
    """Test report relationships and database joins"""
    
    def test_organization_relationship(self, report_repository, created_report):
        """Test report-organization relationship"""
        # Act
        report = report_repository.get_by_id(created_report.id)
        
        # Assert
        assert report.organization is not None
        assert report.organization.id == report.organization_id
        assert report.organization.name is not None
        
        print(f"✅ Organization relationship working: {report.organization.name}")
    
    def test_user_relationship(self, report_repository, created_report):
        """Test report-user relationship"""
        # Act
        report = report_repository.get_by_id(created_report.id)
        
        # Assert
        assert report.user is not None
        assert report.user.id == report.generated_by
        assert report.user.email is not None
        
        print(f"✅ User relationship working: {report.user.email}")
    
    def test_null_user_handling(self, report_repository, sample_report_data):
        """Test report creation without user (system-generated)"""
        # Create report without user
        system_report = report_repository.create({
            **sample_report_data,
            "generated_by": None,  # System-generated report
            "is_auto_generated": True,
            "report_name": "System Generated Report"
        })
        
        assert system_report.generated_by is None
        assert system_report.user is None
        assert system_report.is_auto_generated == True
        
        print(f"✅ Null user handling working correctly")

# =====================================================
# TEST COMPLEX QUERIES AND FILTERING
# =====================================================

class TestReportComplexQueries:
    """Test complex report queries and filtering scenarios"""
    
    def test_combined_filtering(self, report_repository, sample_organization, sample_report_data):
        """Test complex filtering combining multiple criteria"""
        # Create diverse set of reports
        reports_data = [
            {
                **sample_report_data,
                "report_type": ReportType.HACCP_MONTHLY,
                "status": ReportStatus.COMPLETED,
                "schedule_frequency": ScheduleFrequency.MONTHLY,
                "is_active_schedule": True,
                "report_name": "Monthly HACCP Scheduled"
            },
            {
                **sample_report_data,
                "report_type": ReportType.TEMPERATURE_SUMMARY,
                "status": ReportStatus.COMPLETED,
                "schedule_frequency": ScheduleFrequency.WEEKLY,
                "is_active_schedule": True,
                "report_name": "Weekly Temperature Summary"
            },
            {
                **sample_report_data,
                "report_type": ReportType.SENSOR_STATUS,
                "status": ReportStatus.PENDING,
                "schedule_frequency": ScheduleFrequency.MANUAL,
                "is_active_schedule": False,
                "report_name": "Manual Sensor Status"
            },
            {
                **sample_report_data,
                "report_type": ReportType.ALERT_SUMMARY,
                "status": ReportStatus.FAILED,
                "schedule_frequency": ScheduleFrequency.WEEKLY,
                "is_active_schedule": False,
                "report_name": "Failed Alert Summary"
            }
        ]
        
        created_reports = []
        for report_data in reports_data:
            report = report_repository.create(report_data)
            created_reports.append(report)
        
        # Test various filtering combinations
        
        # 1. Get all completed reports
        completed_reports = report_repository.get_completed_reports(sample_organization.id)
        completed_names = [rep.report_name for rep in completed_reports]
        assert any("Monthly HACCP Scheduled" in name for name in completed_names)
        assert any("Weekly Temperature Summary" in name for name in completed_names)
        
        # 2. Get scheduled reports
        scheduled_reports = report_repository.get_scheduled_reports(sample_organization.id)
        scheduled_names = [rep.report_name for rep in scheduled_reports]
        assert any("Monthly HACCP Scheduled" in name for name in scheduled_names)
        assert any("Weekly Temperature Summary" in name for name in scheduled_names)
        
        # 3. Get reports by type
        haccp_reports = report_repository.get_by_type(sample_organization.id, ReportType.HACCP_MONTHLY)
        sensor_reports = report_repository.get_by_type(sample_organization.id, ReportType.SENSOR_STATUS)
        
        assert len(haccp_reports) >= 1
        assert len(sensor_reports) >= 1
        
        print(f"✅ Complex filtering working correctly")
        print(f"   - Completed reports: {len(completed_reports)}")
        print(f"   - Scheduled reports: {len(scheduled_reports)}")
        print(f"   - HACCP reports: {len(haccp_reports)}")
        print(f"   - Sensor reports: {len(sensor_reports)}")

# =====================================================
# TEST DATA INTEGRITY AND CONSISTENCY
# =====================================================

class TestReportDataIntegrity:
    """Test data integrity and consistency"""
    
    def test_report_data_json_handling(self, report_repository, sample_report_data):
        """Test JSON report_data field handling"""
        # Test complex nested data structure
        complex_data = {
            "summary": {
                "total_sensors": 45,
                "total_readings": 32400,
                "compliance_rate": 98.7
            },
            "details": {
                "locations": [
                    {"name": "Main Freezer", "compliance": 99.1, "alerts": 2},
                    {"name": "Secondary Fridge", "compliance": 98.3, "alerts": 5}
                ],
                "temperature_stats": {
                    "min": -25.4,
                    "max": 8.2,
                    "avg": -12.8
                }
            },
            "charts": {
                "temperature_trend": "base64_encoded_chart_data_here",
                "compliance_pie": "base64_encoded_pie_chart_here"
            }
        }
        
        report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "report_data": complex_data,
            "report_name": "Complex Data Report"
        })
        
        # Verify data integrity
        assert report.report_data == complex_data
        assert report.report_data["summary"]["compliance_rate"] == 98.7
        assert len(report.report_data["details"]["locations"]) == 2
        assert report.report_data["details"]["locations"][0]["name"] == "Main Freezer"
        
        print(f"✅ JSON data handling working correctly")
        print(f"   - Complex nested structure preserved")
        print(f"   - Compliance rate: {report.report_data['summary']['compliance_rate']}%")
    
    def test_auto_config_json_handling(self, report_repository, sample_report_data):
        """Test auto_config JSON field handling"""
        auto_config = {
            "email_recipients": ["admin@company.com", "quality@company.com"],
            "include_charts": True,
            "format": "pdf",
            "delivery_options": {
                "schedule": "first_monday_of_month",
                "timezone": "UTC",
                "compress": True
            },
            "customizations": {
                "logo": "company_logo.png",
                "color_scheme": "blue",
                "language": "en"
            }
        }
        
        report = report_repository.create({
            **sample_report_data,
            "schedule_frequency": ScheduleFrequency.MONTHLY,
            "is_active_schedule": True,
            "auto_config": auto_config,
            "report_name": "Auto Config Test Report"
        })
        
        # Verify auto_config integrity
        assert report.auto_config == auto_config
        assert report.auto_config["email_recipients"] == ["admin@company.com", "quality@company.com"]
        assert report.auto_config["delivery_options"]["compress"] == True
        
        print(f"✅ Auto config JSON handling working correctly")

# =====================================================
# TEST EDGE CASES AND ERROR SCENARIOS
# =====================================================

class TestReportEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cascade_delete_organization(self, test_db, report_repository, sample_report_data):
        """Test what happens when organization is deleted"""
        # Create temporary organization
        temp_org = Organization(
            name="Temp Org for Delete Test",
            slug="temp-org-delete-reports",
            subscription_plan="basic"
        )
        test_db.add(temp_org)
        test_db.commit()
        test_db.refresh(temp_org)
        
        # Create report in temp organization
        report = report_repository.create({
            **sample_report_data,
            "organization_id": temp_org.id,
            "generated_by": None,  # Avoid user FK issues
            "report_name": "Report to be deleted"
        })
        
        # Store the report ID before deletion
        report_id = report.id
        
        # Clear the session to avoid stale references
        test_db.expunge(report)  # Remove from session
        
        # Act - Delete organization (should cascade)
        test_db.delete(temp_org)
        test_db.commit()
        
        # Assert - Report should be gone due to CASCADE
        found_report = report_repository.get_by_id(report_id)
        assert found_report is None
        
        print(f"✅ Cascade delete working correctly")
    
    def test_large_report_data_handling(self, report_repository, sample_report_data):
        """Test handling of large report data"""
        # Create large report data (simulating big analytics report)
        large_data = {
            "metadata": {
                "generation_time": "2025-06-27T15:30:00Z",
                "data_points": 50000,
                "processing_time_ms": 12500
            },
            "sensor_readings": [
                {
                    "sensor_id": f"SENSOR_{i:05d}",
                    "readings_count": 720,  # 24 hours * 30 readings/hour
                    "avg_temp": round(-18.0 + (i % 10) * 0.1, 2),
                    "compliance_rate": round(95.0 + (i % 5), 1)
                }
                for i in range(100)  # 100 sensors
            ],
            "daily_summaries": [
                {
                    "date": f"2025-06-{day:02d}",
                    "total_readings": 72000,
                    "deviations": day % 3,  # Varies by day
                    "compliance": round(97.0 + (day % 3) * 0.5, 1)
                }
                for day in range(1, 31)  # 30 days
            ]
        }
        
        report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.COMPLETED,
            "report_data": large_data,
            "file_size_bytes": 5 * 1024 * 1024,  # 5MB
            "report_name": "Large Data Report"
        })
        
        # Verify large data handling
        assert len(report.report_data["sensor_readings"]) == 100
        assert len(report.report_data["daily_summaries"]) == 30
        assert report.report_data["metadata"]["data_points"] == 50000
        
        print(f"✅ Large report data handling working correctly")
        print(f"   - Sensor readings: {len(report.report_data['sensor_readings'])}")
        print(f"   - Daily summaries: {len(report.report_data['daily_summaries'])}")
        print(f"   - File size: {report.file_size_bytes} bytes")
    
    def test_concurrent_report_generation(self, report_repository, sample_organization, sample_report_data):
        """Test concurrent report generation scenarios"""
        # Create multiple reports with same type (simulating concurrent generation)
        concurrent_reports = []
        for i in range(3):
            report = report_repository.create({
                **sample_report_data,
                "report_type": ReportType.HACCP_MONTHLY,
                "status": ReportStatus.GENERATING,
                "generation_started_at": datetime.utcnow(),
                "report_name": f"Concurrent Report {i+1}"
            })
            concurrent_reports.append(report)
        
        # Verify all reports can be created and are independent
        assert len(concurrent_reports) == 3
        assert all(rep.status == ReportStatus.GENERATING for rep in concurrent_reports)
        assert len(set(rep.id for rep in concurrent_reports)) == 3  # All unique IDs
        
        # Complete them in different orders
        for i, report in enumerate(concurrent_reports):
            report_repository.update(report.id, {
                "status": ReportStatus.COMPLETED,
                "generation_completed_at": datetime.utcnow() + timedelta(seconds=i),
                "report_data": {"report_number": i+1}
            })
        
        print(f"✅ Concurrent report generation handled correctly")

# =====================================================
# TEST REPORT AUDIT AND LIFECYCLE
# =====================================================

class TestReportAuditScenarios:
    """Test report audit and lifecycle scenarios"""
    
    def test_report_lifecycle_tracking(self, report_repository, sample_report_data):
        """Test tracking of report lifecycle events"""
        # Create report
        report = report_repository.create(sample_report_data)
        creation_time = report.created_at
        initial_update_time = report.updated_at
        
        # Wait a moment and update
        import time
        time.sleep(0.1)
        
        updated_report = report_repository.update(report.id, {
            "status": ReportStatus.GENERATING,
            "generation_started_at": datetime.utcnow(),
            "report_name": "Updated Report Name"
        })
        
        # Timestamps should reflect the changes
        assert updated_report.created_at == creation_time  # Should not change
        assert updated_report.updated_at > initial_update_time  # Should be updated
        
        print(f"✅ Report lifecycle tracking working")
        print(f"   - Created: {creation_time}")
        print(f"   - Updated: {updated_report.updated_at}")
    
    def test_report_generation_metrics(self, report_repository, sample_report_data):
        """Test generation time and performance metrics"""
        # Create and complete report with timing
        start_time = datetime.utcnow()
        
        report = report_repository.create({
            **sample_report_data,
            "status": ReportStatus.GENERATING,
            "generation_started_at": start_time,
            "report_name": "Metrics Test Report"
        })
        
        # Simulate processing time
        import time
        time.sleep(0.1)
        
        end_time = datetime.utcnow()
        report = report_repository.update(report.id, {
            "status": ReportStatus.COMPLETED,
            "generation_completed_at": end_time,
            "report_data": {"processing_info": "test metrics"},
            "file_size_bytes": 2048000  # 2MB
        })
        
        # Calculate metrics
        generation_duration = (report.generation_completed_at - report.generation_started_at).total_seconds()
        
        assert generation_duration > 0
        assert report.file_size_bytes == 2048000
        assert report.status == ReportStatus.COMPLETED
        
        print(f"✅ Report generation metrics working")
        print(f"   - Generation time: {generation_duration:.3f} seconds")
        print(f"   - File size: {report.file_size_bytes} bytes")
        print(f"   - Status: {report.status.value}")