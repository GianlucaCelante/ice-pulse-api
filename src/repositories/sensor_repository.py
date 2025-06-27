# =====================================================
# src/repositories/sensor_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta

from src.models.sensor import Sensor
from .base import BaseRepository
import uuid

class SensorRepository(BaseRepository[Sensor]):
    """Repository per Sensors con query specifiche"""
    
    def __init__(self, db: Session):
        super().__init__(Sensor, db)
    
    def get_by_organization(self, organization_id: uuid.UUID, include_location: bool = False) -> List[Sensor]:
        """Get sensors by organization"""
        query = self.db.query(Sensor).filter(Sensor.organization_id == organization_id)
        if include_location:
            query = query.options(joinedload(Sensor.location))
        return query.all()
    
    def get_by_device_id(self, device_id: str) -> Optional[Sensor]:
        """Get sensor by device ID"""
        return self.db.query(Sensor).filter(Sensor.device_id == device_id).first()
    
    def get_by_location(self, location_id: uuid.UUID) -> List[Sensor]:
        """Get sensors by location"""
        return self.db.query(Sensor).filter(Sensor.location_id == location_id).all()
    
    def get_by_status(self, organization_id: uuid.UUID, status: str) -> List[Sensor]:
        """Get sensors by status"""
        return self.db.query(Sensor).filter(
            and_(Sensor.organization_id == organization_id, Sensor.status == status)
        ).all()
    
    def get_online_sensors(self, organization_id: uuid.UUID) -> List[Sensor]:
        """Get online sensors"""
        return self.get_by_status(organization_id, "online")
    
    def get_offline_sensors(self, organization_id: uuid.UUID) -> List[Sensor]:
        """Get offline sensors"""
        return self.get_by_status(organization_id, "offline")
    
    def get_sensors_needing_calibration(self, organization_id: uuid.UUID, days_ahead: int = 30) -> List[Sensor]:
        """Get sensors needing calibration"""
        from datetime import date
        threshold_date = date.today() + timedelta(days=days_ahead)
        return self.db.query(Sensor).filter(
            and_(
                Sensor.organization_id == organization_id,
                or_(
                    Sensor.calibration_due_date.is_(None),
                    Sensor.calibration_due_date <= threshold_date
                )
            )
        ).all()
    
    def get_low_battery_sensors(self, organization_id: uuid.UUID, threshold: int = 20) -> List[Sensor]:
        """Get sensors with low battery"""
        return self.db.query(Sensor).filter(
            and_(
                Sensor.organization_id == organization_id,
                Sensor.battery_level <= threshold
            )
        ).all()
    
    def get_recently_seen(self, organization_id: uuid.UUID, hours: int = 24) -> List[Sensor]:
        """Get sensors seen in last X hours"""
        threshold_time = datetime.utcnow() - timedelta(hours=hours)
        return self.db.query(Sensor).filter(
            and_(
                Sensor.organization_id == organization_id,
                Sensor.last_seen_at >= threshold_time
            )
        ).order_by(desc(Sensor.last_seen_at)).all()