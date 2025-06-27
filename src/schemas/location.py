# =====================================================
# src/schemas/location.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class LocationBase(BaseModel):
    """Base schema for Location"""
    name: str = Field(..., min_length=1, max_length=100, description="Location name")
    description: Optional[str] = Field(None, description="Location description")
    location_type: str = Field(..., description="Type of location")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature threshold")
    temperature_max: Optional[float] = Field(None, description="Maximum temperature threshold")
    humidity_min: Optional[float] = Field(None, ge=0, le=100, description="Minimum humidity threshold")
    humidity_max: Optional[float] = Field(None, ge=0, le=100, description="Maximum humidity threshold")
    floor: Optional[str] = Field(None, max_length=20, description="Floor designation")
    zone: Optional[str] = Field(None, max_length=50, description="Zone designation")
    coordinates: Optional[Dict[str, float]] = Field(None, description="GPS coordinates")

    @validator('location_type')
    def validate_location_type(cls, v):
        allowed_types = ['freezer', 'fridge', 'cold_room', 'outdoor', 'kitchen', 'storage']
        if v not in allowed_types:
            raise ValueError(f'Location type must be one of: {allowed_types}')
        return v

    @validator('temperature_max')
    def validate_temperature_range(cls, v, values):
        if v is not None and 'temperature_min' in values:
            temp_min = values.get('temperature_min')
            if temp_min is not None and v <= temp_min:
                raise ValueError('Temperature max must be greater than temperature min')
        return v

    @validator('coordinates')
    def validate_coordinates(cls, v):
        if v is not None:
            if 'lat' not in v or 'lng' not in v:
                raise ValueError('Coordinates must contain lat and lng fields')
            lat, lng = v['lat'], v['lng']
            if not (-90 <= lat <= 90):
                raise ValueError('Latitude must be between -90 and 90')
            if not (-180 <= lng <= 180):
                raise ValueError('Longitude must be between -180 and 180')
        return v

class LocationCreate(LocationBase):
    """Schema for creating location"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")

class LocationUpdate(BaseModel):
    """Schema for updating location"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    location_type: Optional[str] = None
    temperature_min: Optional[float] = None
    temperature_max: Optional[float] = None
    humidity_min: Optional[float] = Field(None, ge=0, le=100)
    humidity_max: Optional[float] = Field(None, ge=0, le=100)
    floor: Optional[str] = Field(None, max_length=20)
    zone: Optional[str] = Field(None, max_length=50)
    coordinates: Optional[Dict[str, float]] = None

    @validator('location_type')
    def validate_location_type(cls, v):
        if v is not None:
            allowed_types = ['freezer', 'fridge', 'cold_room', 'outdoor', 'kitchen', 'storage']
            if v not in allowed_types:
                raise ValueError(f'Location type must be one of: {allowed_types}')
        return v

class LocationResponse(LocationBase):
    """Schema for location API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def sensor_count(self) -> int:
        # Populated by service layer
        return getattr(self, '_sensor_count', 0)
    
    @computed_field
    @property
    def temperature_range(self) -> Dict[str, Optional[float]]:
        return {
            "min": self.temperature_min,
            "max": self.temperature_max
        }

    class Config:
        from_attributes = True

class LocationSummary(BaseModel):
    """Summary schema for location listings"""
    id: uuid.UUID
    name: str
    location_type: str
    sensor_count: int
    temperature_range: Dict[str, Optional[float]]

    class Config:
        from_attributes = True