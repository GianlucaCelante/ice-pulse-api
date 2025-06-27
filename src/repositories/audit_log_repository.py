# =====================================================
# src/repositories/audit_log_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime

from src.models.audit_log import AuditLog
from .base import BaseRepository
import uuid

class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository per AuditLog con query per compliance"""
    
    def __init__(self, db: Session):
        super().__init__(AuditLog, db)
    
    def get_by_organization(self, organization_id: uuid.UUID, limit: int = 1000) -> List[AuditLog]:
        """Get audit logs by organization"""
        return self.db.query(AuditLog).filter(AuditLog.organization_id == organization_id).order_by(
            desc(AuditLog.created_at)
        ).limit(limit).all()
    
    def get_haccp_relevant(self, organization_id: uuid.UUID, limit: int = 500) -> List[AuditLog]:
        """Get HACCP relevant audit logs"""
        return self.db.query(AuditLog).filter(
            and_(AuditLog.organization_id == organization_id, AuditLog.haccp_relevant == True)
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_by_user(self, user_id: uuid.UUID, limit: int = 500) -> List[AuditLog]:
        """Get audit logs by user"""
        return self.db.query(AuditLog).filter(AuditLog.user_id == user_id).order_by(
            desc(AuditLog.created_at)
        ).limit(limit).all()
    
    def get_by_resource(self, resource_type: str, resource_id: uuid.UUID) -> List[AuditLog]:
        """Get audit logs for specific resource"""
        return self.db.query(AuditLog).filter(
            and_(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
        ).order_by(desc(AuditLog.created_at)).all()
    
    def search_logs(self, organization_id: uuid.UUID, search_term: str, limit: int = 100) -> List[AuditLog]:
        """Search audit logs"""
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.organization_id == organization_id,
                or_(
                    AuditLog.action.ilike(f"%{search_term}%"),
                    AuditLog.description.ilike(f"%{search_term}%")
                )
            )
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def get_by_date_range(self, organization_id: uuid.UUID, start_date: datetime, end_date: datetime) -> List[AuditLog]:
        """Get audit logs in date range"""
        return self.db.query(AuditLog).filter(
            and_(
                AuditLog.organization_id == organization_id,
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).order_by(desc(AuditLog.created_at)).all()