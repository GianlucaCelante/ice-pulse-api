# =====================================================
# src/services/unit_of_work.py - Transaction Management
# =====================================================
from contextlib import contextmanager
from sqlalchemy.orm import Session
from .repository_factory import RepositoryFactory

class UnitOfWork:
    """
    Unit of Work pattern per transaction management.
    
    PATTERN: Gestisce transazioni e rollback automatico
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repositories = RepositoryFactory(db)
    
    def commit(self):
        """Commit transaction"""
        self.db.commit()
    
    def rollback(self):
        """Rollback transaction"""
        self.db.rollback()
    
    @contextmanager
    def transaction(self):
        """Context manager per transazioni automatiche"""
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise

# =====================================================
# ADVANCED USAGE EXAMPLES
# =====================================================

"""
ESEMPI AVANZATI CON REPOSITORY FACTORY:

# Basic usage
def get_sensor_dashboard_data(org_id: uuid.UUID, db: Session):
    repos = RepositoryFactory(db)
    
    # Get all data needed for dashboard
    sensors = repos.sensors.get_by_organization(org_id, include_location=True)
    active_alerts = repos.alerts.get_active_alerts(org_id)
    low_battery = repos.sensors.get_low_battery_sensors(org_id)
    
    return {
        "sensors": sensors,
        "active_alerts": active_alerts, 
        "low_battery_sensors": low_battery
    }

# Transaction management
def create_sensor_with_audit(sensor_data: dict, user_id: uuid.UUID, db: Session):
    with UnitOfWork(db).transaction() as uow:
        # Create sensor
        sensor = uow.repositories.sensors.create(sensor_data)
        
        # Log audit event
        audit_data = {
            "organization_id": sensor.organization_id,
            "user_id": user_id,
            "action": "sensor_created",
            "resource_type": "sensor", 
            "resource_id": sensor.id,
            "new_values": sensor_data,
            "haccp_relevant": True
        }
        uow.repositories.audit_logs.create(audit_data)
        
        return sensor

# Complex analytics query
def get_compliance_report_data(org_id: uuid.UUID, start_date: date, end_date: date, db: Session):
    repos = RepositoryFactory(db)
    
    # Get all needed data
    total_readings = repos.readings.get_by_organization(org_id, start_date, end_date)
    deviations = repos.readings.get_deviation_readings(org_id, start_date, end_date)
    failed_calibrations = repos.calibrations.get_failed_calibrations(org_id, start_date, end_date)
    critical_alerts = repos.alerts.get_critical_alerts(org_id)
    
    # Calculate compliance metrics
    compliance_rate = ((len(total_readings) - len(deviations)) / len(total_readings) * 100) if total_readings else 100
    
    return {
        "total_readings": len(total_readings),
        "deviation_readings": len(deviations),
        "compliance_rate": compliance_rate,
        "failed_calibrations": len(failed_calibrations),
        "critical_alerts": len(critical_alerts)
    }

# Config management
def setup_organization_defaults(org_id: uuid.UUID, db: Session):
    config_repo = EnvConfigRepository(db)
    
    # Setup default configs for new organization
    defaults = {
        "temperature.freezer_min": -25.0,
        "temperature.freezer_max": -15.0,
        "temperature.fridge_min": 0.0,
        "temperature.fridge_max": 8.0,
        "alerts.email_enabled": True,
        "reports.auto_generate": True,
        "reports.frequency": "monthly"
    }
    
    config_repo.bulk_set_configs(defaults, org_id)

# Scheduled reports processing
def process_scheduled_reports(db: Session):
    repos = RepositoryFactory(db)
    
    # Get reports due for generation
    due_reports = repos.reports.get_reports_due_for_generation()
    
    for report in due_reports:
        try:
            # Mark as generating
            repos.reports.update(report.id, {"status": "generating"})
            
            # Generate report (business logic)
            generate_report_content(report, repos)
            
            # Mark as completed and update next run
            repos.reports.update(report.id, {
                "status": "completed",
                "generation_completed_at": datetime.utcnow()
            })
            
            # Update next generation date
            report.update_next_generation_date()
            repos.reports.update(report.id, {
                "next_generation_date": report.next_generation_date
            })
            
        except Exception as e:
            # Mark as failed
            repos.reports.update(report.id, {
                "status": "failed",
                "generation_error": str(e)
            })
"""