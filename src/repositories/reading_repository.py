# =====================================================
# src/repositories/reading_repository.py
# =====================================================
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
from datetime import datetime, date

from src.models.reading import Reading
from .base import BaseRepository
import uuid

class ReadingRepository(BaseRepository[Reading]):
    """Repository per Readings con query specifiche per analytics"""
    
    def __init__(self, db: Session):
        super().__init__(Reading, db)
    
    def get_by_sensor(self, sensor_id: uuid.UUID, limit: int = 1000) -> List[Reading]:
        """Get readings for sensor"""
        return self.db.query(Reading).filter(Reading.sensor_id == sensor_id).order_by(
            desc(Reading.timestamp)
        ).limit(limit).all()
    
    def get_latest_reading(self, sensor_id: uuid.UUID) -> Optional[Reading]:
        """Get latest reading for sensor"""
        return self.db.query(Reading).filter(Reading.sensor_id == sensor_id).order_by(
            desc(Reading.timestamp)
        ).first()
    
    def get_readings_by_date_range(self, sensor_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[Reading]:
        """Get readings in date range"""
        return self.db.query(Reading).filter(
            and_(
                Reading.sensor_id == sensor_id,
                Reading.timestamp >= start_date,
                Reading.timestamp <= end_date
            )
        ).order_by(Reading.timestamp).all()
    
    def get_deviation_readings(self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[Reading]:
        """Get readings with deviations"""
        return self.db.query(Reading).filter(
            and_(
                Reading.organization_id == organization_id,
                Reading.deviation_detected == True,
                Reading.timestamp >= start_date,
                Reading.timestamp <= end_date
            )
        ).order_by(desc(Reading.timestamp)).all()
    
    def get_manual_readings(self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[Reading]:
        """Get manual readings"""
        return self.db.query(Reading).filter(
            and_(
                Reading.organization_id == organization_id,
                Reading.is_manual_entry == True,
                Reading.timestamp >= start_date,
                Reading.timestamp <= end_date
            )
        ).order_by(desc(Reading.timestamp)).all()
    
    def get_temperature_stats(self, sensor_id: uuid.UUID, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get temperature statistics for sensor"""
        stats = self.db.query(
            func.min(Reading.temperature).label('min_temp'),
            func.max(Reading.temperature).label('max_temp'),
            func.avg(Reading.temperature).label('avg_temp'),
            func.count(Reading.id).label('reading_count'),
            func.sum(func.case([(Reading.deviation_detected == True, 1)], else_=0)).label('deviation_count')
        ).filter(
            and_(
                Reading.sensor_id == sensor_id,
                Reading.timestamp >= start_date,
                Reading.timestamp <= end_date,
                Reading.temperature.isnot(None)
            )
        ).first()
        
        if stats is None:
            return {
                'min_temperature': None,
                'max_temperature': None,
                'avg_temperature': None,
                'total_readings': 0,
                'deviation_readings': 0,
                'compliance_percentage': 100
            }
        return {
            'min_temperature': float(stats.min_temp) if stats.min_temp is not None else None,
            'max_temperature': float(stats.max_temp) if stats.max_temp is not None else None,
            'avg_temperature': float(stats.avg_temp) if stats.avg_temp is not None else None,
            'total_readings': stats.reading_count,
            'deviation_readings': stats.deviation_count,
            'compliance_percentage': ((stats.reading_count - stats.deviation_count) / stats.reading_count * 100) if stats.reading_count > 0 else 100
        }