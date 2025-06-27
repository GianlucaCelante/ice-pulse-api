# =====================================================
# src/repositories/organization_repository.py
# =====================================================
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.models.organization import Organization
from .base import BaseRepository

class OrganizationRepository(BaseRepository[Organization]):
    """Repository per Organizations con query specifiche"""
    
    def __init__(self, db: Session):
        super().__init__(Organization, db)
    
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        return self.db.query(Organization).filter(Organization.slug == slug).first()
    
    def get_by_subscription_plan(self, plan: str) -> List[Organization]:
        """Get organizations by subscription plan"""
        return self.db.query(Organization).filter(Organization.subscription_plan == plan).all()
    
    def get_premium_organizations(self) -> List[Organization]:
        """Get premium/enterprise organizations"""
        return self.db.query(Organization).filter(
            Organization.subscription_plan.in_(["premium", "enterprise"])
        ).all()
    
    def search_by_name(self, search_term: str) -> List[Organization]:
        """Search organizations by name"""
        return self.db.query(Organization).filter(
            Organization.name.ilike(f"%{search_term}%")
        ).all()
    
    def get_with_sensor_count(self) -> List[Dict]:
        """Get organizations with sensor count"""
        from src.models.sensor import Sensor
        from sqlalchemy import func
        results = self.db.query(
            Organization,
            func.count(Sensor.id).label('sensor_count')
        ).outerjoin(Sensor, Sensor.organization_id == Organization.id
        ).group_by(Organization.id).all()
        return [
            {
                "organization": org,
                "sensor_count": sensor_count
            }
            for org, sensor_count in results
        ]