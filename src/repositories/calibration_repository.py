# =====================================================
# src/repositories/calibration_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, date, timedelta

from src.models.calibration import Calibration
from .base import BaseRepository
import uuid

class CalibrationRepository(BaseRepository[Calibration]):
    """Repository per Calibrations con query HACCP compliance"""
    
    def __init__(self, db: Session):
        super().__init__(Calibration, db)
    
    def get_by_organization(self, organization_id: uuid.UUID) -> List[Calibration]:
        """Get calibrations by organization"""
        return self.db.query(Calibration).filter(Calibration.organization_id == organization_id).order_by(
            desc(Calibration.calibrated_at)
        ).all()
    
    def get_by_sensor(self, sensor_id: uuid.UUID) -> List[Calibration]:
        """Get calibrations for sensor"""
        return self.db.query(Calibration).filter(Calibration.sensor_id == sensor_id).order_by(
            desc(Calibration.calibrated_at)
        ).all()
    
    def get_latest_calibration(self, sensor_id: uuid.UUID) -> Optional[Calibration]:
        """Get latest calibration for sensor"""
        return self.db.query(Calibration).filter(Calibration.sensor_id == sensor_id).order_by(
            desc(Calibration.calibrated_at)
        ).first()
    
    def get_passed_calibrations(self, organization_id: uuid.UUID, start_date: date, end_date: date) -> List[Calibration]:
        """Get passed calibrations in date range"""
        return self.db.query(Calibration).filter(
            and_(
                Calibration.organization_id == organization_id,
                Calibration.calibration_passed == True,
                Calibration.calibrated_at >= start_date,
                Calibration.calibrated_at <= end_date
            )
        ).order_by(desc(Calibration.calibrated_at)).all()
    
    def get_failed_calibrations(self, organization_id: uuid.UUID, start_date: date, end_date: date) -> List[Calibration]:
        """Get failed calibrations in date range"""
        return self.db.query(Calibration).filter(
            and_(
                Calibration.organization_id == organization_id,
                Calibration.calibration_passed == False,
                Calibration.calibrated_at >= start_date,
                Calibration.calibrated_at <= end_date
            )
        ).order_by(desc(Calibration.calibrated_at)).all()
    
    def get_calibrations_due_soon(self, organization_id: uuid.UUID, days_ahead: int = 30) -> List[Calibration]:
        """Get calibrations due in next X days"""
        due_date = date.today() + timedelta(days=days_ahead)
        return self.db.query(Calibration).filter(
            and_(
                Calibration.organization_id == organization_id,
                Calibration.next_calibration_due <= due_date,
                Calibration.next_calibration_due > date.today()
            )
        ).order_by(Calibration.next_calibration_due).all()
    
    def get_overdue_calibrations(self, organization_id: uuid.UUID) -> List[Calibration]:
        """Get overdue calibrations"""
        return self.db.query(Calibration).filter(
            and_(
                Calibration.organization_id == organization_id,
                Calibration.next_calibration_due < date.today()
            )
        ).order_by(Calibration.next_calibration_due).all()
    
    def get_by_technician(self, technician_id: uuid.UUID, start_date: date, end_date: date) -> List[Calibration]:
        """Get calibrations by technician in date range"""
        return self.db.query(Calibration).filter(
            and_(
                Calibration.calibrated_by == technician_id,
                Calibration.calibrated_at >= start_date,
                Calibration.calibrated_at <= end_date
            )
        ).order_by(desc(Calibration.calibrated_at)).all()