# =====================================================
# src/repositories/env_config_repository.py
# =====================================================
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.env_config import EnvConfig
from .base import BaseRepository
import uuid

class EnvConfigRepository(BaseRepository[EnvConfig]):
    """Repository per EnvConfig con query per configuration management"""
    
    def __init__(self, db: Session):
        super().__init__(EnvConfig, db)
    
    def get_by_key(self, key: str, organization_id: Optional[uuid.UUID] = None) -> Optional[EnvConfig]:
        """Get config by key"""
        return self.db.query(EnvConfig).filter(
            and_(EnvConfig.key == key, EnvConfig.organization_id == organization_id)
        ).first()
    
    def get_with_fallback(self, key: str, organization_id: Optional[uuid.UUID] = None) -> Optional[EnvConfig]:
        """Get config with global fallback"""
        # Try organization-specific first
        if organization_id:
            org_config = self.get_by_key(key, organization_id)
            if org_config:
                return org_config
        
        # Fallback to global
        return self.get_by_key(key, None)
    
    def get_by_prefix(self, prefix: str, organization_id: Optional[uuid.UUID] = None) -> List[EnvConfig]:
        """Get configs by key prefix (e.g., 'email.')"""
        query = self.db.query(EnvConfig).filter(EnvConfig.key.like(f"{prefix}%"))
        if organization_id is not None:
            query = query.filter(EnvConfig.organization_id == organization_id)
        return query.all()
    
    def get_organization_configs(self, organization_id: uuid.UUID) -> List[EnvConfig]:
        """Get all configs for organization"""
        return self.db.query(EnvConfig).filter(EnvConfig.organization_id == organization_id).all()
    
    def get_global_configs(self) -> List[EnvConfig]:
        """Get global configs"""
        return self.db.query(EnvConfig).filter(EnvConfig.organization_id.is_(None)).all()
    
    def set_config(self, key: str, value: Any, organization_id: Optional[uuid.UUID] = None) -> EnvConfig:
        """Set config value (create or update)"""
        config = self.get_by_key(key, organization_id)
        
        if not config:
            config = EnvConfig(key=key, organization_id=organization_id)
            self.db.add(config)
        
        config.set_typed_value(value)
        self.db.commit()
        self.db.refresh(config)
        return config
    
    def bulk_set_configs(self, configs: Dict[str, Any], organization_id: Optional[uuid.UUID] = None) -> List[EnvConfig]:
        """Set multiple configs at once"""
        results = []
        for key, value in configs.items():
            config = self.set_config(key, value, organization_id)
            results.append(config)
        return results
    
    def delete_by_key(self, key: str, organization_id: Optional[uuid.UUID] = None) -> bool:
        """Delete config by key"""
        config = self.get_by_key(key, organization_id)
        if not config:
            return False
        
        self.db.delete(config)
        self.db.commit()
        return True

# =====================================================
# USAGE EXAMPLES
# =====================================================

"""
ESEMPI DI USO DEI REPOSITORY:

# Setup
db = get_database_session()
sensor_repo = SensorRepository(db)
alert_repo = AlertRepository(db)
config_repo = EnvConfigRepository(db)

# Sensor operations
online_sensors = sensor_repo.get_online_sensors(org_id)
low_battery = sensor_repo.get_low_battery_sensors(org_id, threshold=15)
needs_calibration = sensor_repo.get_sensors_needing_calibration(org_id)

# Alert operations  
critical_alerts = alert_repo.get_critical_alerts(org_id)
unresolved = alert_repo.get_unresolved_alerts(org_id)

# Config operations
smtp_host = config_repo.get_with_fallback("email.smtp.host", org_id)
config_repo.set_config("temperature.default_min", -18.0, org_id)

# Reading analytics
reading_repo = ReadingRepository(db)
temp_stats = reading_repo.get_temperature_stats(sensor_id, start_date, end_date)
deviations = reading_repo.get_deviation_readings(org_id, start_date, end_date)

# Report scheduling
report_repo = ReportRepository(db)
due_reports = report_repo.get_reports_due_for_generation()
scheduled = report_repo.get_scheduled_reports(org_id)

# Audit compliance
audit_repo = AuditLogRepository(db)
haccp_logs = audit_repo.get_haccp_relevant(org_id)
user_activity = audit_repo.get_by_user(user_id)
"""