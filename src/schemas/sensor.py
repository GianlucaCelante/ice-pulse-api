# =====================================================
# src/schemas/sensor.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Dict, Any
from datetime import datetime, date
import uuid
import re

class SensorBase(BaseModel):
    """Base schema for Sensor"""
    device_id: str = Field(..., min_length=1, max_length=50, description="Unique device identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Sensor name")
    sensor_type: str = Field(default="temperature_humidity", description="Type of sensor")
    mac_address: Optional[str] = Field(None, description="MAC address")
    firmware_version: Optional[str] = Field(None, max_length=20, description="Firmware version")
    hardware_model: Optional[str] = Field(None, max_length=50, description="Hardware model")
    reading_interval_seconds: int = Field(default=300, ge=30, le=3600, description="Reading interval in seconds")
    alert_thresholds: Optional[Dict[str, Dict[str, float]]] = Field(None, description="Alert thresholds configuration")
    accuracy_specification: float = Field(default=0.5, gt=0, description="Accuracy specification")

    @validator('sensor_type')
    def validate_sensor_type(cls, v):
        allowed_types = ['temperature_humidity', 'temperature_pressure', 'multi_sensor']
        if v not in allowed_types:
            raise ValueError(f'Sensor type must be one of: {allowed_types}')
        return v

    @validator('mac_address')
    def validate_mac_address(cls, v):
        if v is not None:
            pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            if not re.match(pattern, v):
                raise ValueError('Invalid MAC address format. Use XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')
        return v

    @validator('alert_thresholds')
    def validate_alert_thresholds(cls, v):
        if v is not None:
            for measurement_type, thresholds in v.items():
                if not isinstance(thresholds, dict):
                    raise ValueError(f'Thresholds for {measurement_type} must be a dictionary')
                if 'min' in thresholds and 'max' in thresholds:
                    if thresholds['min'] >= thresholds['max']:
                        raise ValueError(f'Min threshold must be less than max threshold for {measurement_type}')
        return v

class SensorCreate(SensorBase):
    """Schema for creating sensor"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    location_id: Optional[uuid.UUID] = Field(None, description="Location ID")

class SensorUpdate(BaseModel):
    """Schema for updating sensor"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    location_id: Optional[uuid.UUID] = None
    firmware_version: Optional[str] = Field(None, max_length=20)
    reading_interval_seconds: Optional[int] = Field(None, ge=30, le=3600)
    alert_thresholds: Optional[Dict[str, Dict[str, float]]] = None
    accuracy_specification: Optional[float] = Field(None, gt=0)

class SensorStatusUpdate(BaseModel):
    """Schema for sensor status updates (from IoT devices)"""
    status: str = Field(..., description="Sensor status")
    battery_level: Optional[int] = Field(None, ge=0, le=100, description="Battery level percentage")
    firmware_version: Optional[str] = Field(None, max_length=20)
    last_seen_at: Optional[datetime] = Field(None, description="Last communication timestamp")

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['online', 'offline', 'warning', 'error', 'maintenance']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

class SensorResponse(SensorBase):
    """Schema for sensor API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    location_id: Optional[uuid.UUID]
    status: str
    battery_level: int
    last_seen_at: Optional[datetime]
    last_reading_at: Optional[datetime]
    last_calibration_date: Optional[date]
    calibration_due_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_online(self) -> bool:
        # Populated by service layer
        return getattr(self, '_is_online', False)
    
    @computed_field
    @property
    def is_calibration_due(self) -> bool:
        # Populated by service layer
        return getattr(self, '_is_calibration_due', False)
    
    @computed_field
    @property
    def location_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_location_name', None)

    class Config:
        from_attributes = True

class SensorSummary(BaseModel):
    """Summary schema for sensor listings"""
    id: uuid.UUID
    device_id: str
    name: str
    sensor_type: str
    status: str
    battery_level: int
    location_name: Optional[str]
    is_online: bool
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True