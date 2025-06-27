# =====================================================
# src/repositories/location_repository.py
# =====================================================
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from src.models.location import Location
from .base import BaseRepository
import uuid

class LocationRepository(BaseRepository[Location]):
    """Repository per Locations con query specifiche"""
    
    def __init__(self, db: Session):
        super().__init__(Location, db)
    
    def get_by_organization(self, organization_id: uuid.UUID) -> List[Location]:
        """Get locations by organization"""
        return self.db.query(Location).filter(Location.organization_id == organization_id).all()
    
    def get_by_type(self, organization_id: uuid.UUID, location_type: str) -> List[Location]:
        """Get locations by type"""
        return self.db.query(Location).filter(
            and_(Location.organization_id == organization_id, Location.location_type == location_type)
        ).all()
    
    def get_freezers(self, organization_id: uuid.UUID) -> List[Location]:
        """Get freezer locations"""
        return self.get_by_type(organization_id, "freezer")
    
    def get_fridges(self, organization_id: uuid.UUID) -> List[Location]:
        """Get fridge locations"""
        return self.get_by_type(organization_id, "fridge")
    
    def search_by_name(self, organization_id: uuid.UUID, search_term: str) -> List[Location]:
        """Search locations by name"""
        return self.db.query(Location).filter(
            and_(
                Location.organization_id == organization_id,
                Location.name.ilike(f"%{search_term}%")
            )
        ).all()
    
    # removed inline import of func; now imported at the top

    def get_with_sensor_count(self, organization_id: uuid.UUID) -> List[dict]:
        """Get locations with sensor count"""
        from src.models.sensor import Sensor
        result = (
            self.db.query(
                Location,
                func.count(Sensor.id).label('sensor_count')
            )
            .outerjoin(Sensor, Sensor.location_id == Location.id)
            .filter(Location.organization_id == organization_id)
            .group_by(Location.id)
            .all()
        )
        return [
            {
                "location": row[0],
                "sensor_count": row[1]
            }
            for row in result
        ]