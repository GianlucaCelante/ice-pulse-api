# =====================================================
# src/schemas/reading.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional
from datetime import datetime
import uuid

class ReadingBase(BaseModel):
    """Base schema for Reading"""
    timestamp: datetime = Field(..., description="Reading timestamp")
    temperature: Optional[float] = Field(None, ge=-40, le=100, description="Temperature in Celsius")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="Humidity percentage")
    pressure: Optional[float] = Field(None, ge=0, description="Pressure in mbar")
    battery_voltage: Optional[float] = Field(None, ge=0, le=5, description="Battery voltage")
    rssi: Optional[int] = Field(None, description="Signal strength")
    data_quality_score: Optional[float] = Field(None, ge=0, le=1, description="Data quality score")
    is_manual_entry: bool = Field(default=False, description="Manual entry flag")

class ReadingCreate(ReadingBase):
    """Schema for creating reading (from IoT sensors)"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    sensor_id: uuid.UUID = Field(..., description="Sensor ID")
    device_id: Optional[str] = Field(None, description="Device ID for validation")

class ReadingBulkCreate(BaseModel):
    """Schema for bulk reading creation"""
    sensor_id: uuid.UUID = Field(..., description="Sensor ID")
    readings: list[ReadingBase] = Field(..., description="List of readings")
    
    @validator('readings')
    def validate_readings_length(cls, v):
        if len(v) < 1:
            raise ValueError('At least 1 reading is required')
        if len(v) > 1000:
            raise ValueError('Maximum 1000 readings allowed per bulk operation')
        return v
    
class ReadingUpdate(BaseModel):
    """Schema for updating reading (manual corrections)"""
    temperature: Optional[float] = Field(None, ge=-40, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    manual_verification: bool = Field(default=True, description="Mark as manually verified")
    corrective_action_required: Optional[bool] = None

class ReadingResponse(ReadingBase):
    """Schema for reading API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    sensor_id: uuid.UUID
    alert_id: Optional[uuid.UUID]
    
    # HACCP compliance fields
    temperature_deviation: bool
    humidity_deviation: bool
    deviation_detected: bool
    corrective_action_required: bool
    manual_verification: bool
    haccp_compliance_status: str
    alert_generated: bool
    
    created_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_compliant(self) -> bool:
        return self.haccp_compliance_status == "compliant"
    
    @computed_field
    @property
    def has_deviation(self) -> bool:
        return self.deviation_detected
    
    @computed_field
    @property
    def requires_action(self) -> bool:
        return self.corrective_action_required
    
    @computed_field
    @property
    def sensor_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_sensor_name', None)

    class Config:
        from_attributes = True

class ReadingSummary(BaseModel):
    """Summary schema for reading listings"""
    id: uuid.UUID
    timestamp: datetime
    temperature: Optional[float]
    humidity: Optional[float]
    sensor_name: str
    haccp_compliance_status: str
    deviation_detected: bool

    class Config:
        from_attributes = True

class ReadingStats(BaseModel):
    """Schema for reading statistics"""
    sensor_id: uuid.UUID
    start_date: datetime
    end_date: datetime
    total_readings: int
    compliant_readings: int
    deviation_readings: int
    avg_temperature: Optional[float]
    min_temperature: Optional[float]
    max_temperature: Optional[float]
    avg_humidity: Optional[float]
    compliance_percentage: float