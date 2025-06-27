# =====================================================
# src/repositories/report_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime

from src.models.report import Report, ReportStatus, ScheduleFrequency
from .base import BaseRepository
import uuid

class ReportRepository(BaseRepository[Report]):
    """Repository per Reports con query per scheduling"""
    
    def __init__(self, db: Session):
        super().__init__(Report, db)
    
    def get_by_organization(self, organization_id: uuid.UUID) -> List[Report]:
        """Get reports by organization"""
        return self.db.query(Report).filter(Report.organization_id == organization_id).order_by(
            desc(Report.created_at)
        ).all()
    
    def get_scheduled_reports(self, organization_id: Optional[uuid.UUID] = None) -> List[Report]:
        """Get scheduled reports"""
        query = self.db.query(Report).filter(
            and_(
                Report.schedule_frequency != ScheduleFrequency.MANUAL,
                Report.is_active_schedule == True
            )
        )
        if organization_id:
            query = query.filter(Report.organization_id == organization_id)
        return query.all()
    
    def get_reports_due_for_generation(self) -> List[Report]:
        """Get reports due for auto-generation"""
        return self.db.query(Report).filter(
            and_(
                Report.is_active_schedule == True,
                Report.next_generation_date <= datetime.utcnow(),
                Report.status != ReportStatus.GENERATING
            )
        ).all()
    
    def get_by_type(self, organization_id: uuid.UUID, report_type: str) -> List[Report]:
        """Get reports by type"""
        return self.db.query(Report).filter(
            and_(Report.organization_id == organization_id, Report.report_type == report_type)
        ).order_by(desc(Report.created_at)).all()
    
    def get_completed_reports(self, organization_id: uuid.UUID, limit: int = 50) -> List[Report]:
        """Get completed reports"""
        return self.db.query(Report).filter(
            and_(Report.organization_id == organization_id, Report.status == ReportStatus.COMPLETED)
        ).order_by(desc(Report.generation_completed_at)).limit(limit).all()
