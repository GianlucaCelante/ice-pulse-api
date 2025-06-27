# =====================================================
# src/repositories/alert_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta

from src.models.alert import Alert
from .base import BaseRepository
import uuid

class AlertRepository(BaseRepository[Alert]):
    """Repository per Alerts con query specifiche"""
    
    def __init__(self, db: Session):
        super().__init__(Alert, db)
    
    def get_by_organization(self, organization_id: uuid.UUID, include_sensor: bool = False) -> List[Alert]:
        """Get alerts by organization"""
        query = self.db.query(Alert).filter(Alert.organization_id == organization_id)
        if include_sensor:
            query = query.options(joinedload(Alert.sensor))
        return query.order_by(desc(Alert.created_at)).all()
    
    def get_active_alerts(self, organization_id: uuid.UUID) -> List[Alert]:
        """Get active alerts"""
        return self.db.query(Alert).filter(
            and_(Alert.organization_id == organization_id, Alert.status == "active")
        ).order_by(desc(Alert.created_at)).all()
    
    def get_critical_alerts(self, organization_id: uuid.UUID) -> List[Alert]:
        """Get critical alerts"""
        return self.db.query(Alert).filter(
            and_(
                Alert.organization_id == organization_id,
                Alert.severity == "critical",
                Alert.status.in_(["active", "acknowledged"])
            )
        ).order_by(desc(Alert.created_at)).all()
    
    def get_haccp_alerts(self, organization_id: uuid.UUID) -> List[Alert]:
        """Get HACCP critical alerts"""
        return self.db.query(Alert).filter(
            and_(
                Alert.organization_id == organization_id,
                Alert.is_haccp_critical == True
            )
        ).order_by(desc(Alert.created_at)).all()
    
    def get_unresolved_alerts(self, organization_id: uuid.UUID) -> List[Alert]:
        """Get unresolved alerts (active + acknowledged)"""
        return self.db.query(Alert).filter(
            and_(
                Alert.organization_id == organization_id,
                Alert.status.in_(["active", "acknowledged"])
            )
        ).order_by(desc(Alert.created_at)).all()
    
    def get_alerts_by_sensor(self, sensor_id: uuid.UUID, limit: int = 50) -> List[Alert]:
        """Get alerts for specific sensor"""
        return self.db.query(Alert).filter(Alert.sensor_id == sensor_id).order_by(
            desc(Alert.created_at)
        ).limit(limit).all()
    
    def get_alerts_by_date_range(self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[Alert]:
        """Get alerts in date range"""
        return self.db.query(Alert).filter(
            and_(
                Alert.organization_id == organization_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            )
        ).order_by(desc(Alert.created_at)).all()