# =====================================================
# src/schemas/alert.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional
from datetime import datetime
import uuid

class AlertBase(BaseModel):
    """Base schema for Alert"""
    alert_type: str = Field(..., description="Type of alert")
    severity: str = Field(default="medium", description="Alert severity")
    message: str = Field(..., min_length=1, description="Alert message")
    threshold_value: Optional[float] = Field(None, description="Threshold value that was violated")
    current_value: Optional[float] = Field(None, description="Current sensor value")
    deviation_duration_minutes: Optional[int] = Field(None, ge=0, description="Duration of deviation in minutes")
    requires_corrective_action: bool = Field(default=False, description="Requires corrective action")
    is_haccp_critical: bool = Field(default=False, description="HACCP critical alert")

    @validator('alert_type')
    def validate_alert_type(cls, v):
        allowed_types = [
            'temperature_high', 'temperature_low', 'humidity_high', 'humidity_low',
            'sensor_offline', 'battery_low', 'calibration_due'
        ]
        if v not in allowed_types:
            raise ValueError(f'Alert type must be one of: {allowed_types}')
        return v

    @validator('severity')
    def validate_severity(cls, v):
        allowed_severities = ['low', 'medium', 'high', 'critical']
        if v not in allowed_severities:
            raise ValueError(f'Severity must be one of: {allowed_severities}')
        return v

class AlertCreate(AlertBase):
    """Schema for creating alert"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    sensor_id: Optional[uuid.UUID] = Field(None, description="Sensor ID")

class AlertUpdate(BaseModel):
    """Schema for updating alert"""
    message: Optional[str] = Field(None, min_length=1)
    corrective_action_taken: Optional[str] = Field(None, description="Corrective action description")

class AlertAcknowledge(BaseModel):
    """Schema for acknowledging alert"""
    acknowledged_by: uuid.UUID = Field(..., description="User ID acknowledging the alert")

class AlertResolve(BaseModel):
    """Schema for resolving alert"""
    resolved_by: uuid.UUID = Field(..., description="User ID resolving the alert")
    corrective_action_taken: Optional[str] = Field(None, description="Corrective action taken")

class AlertResponse(AlertBase):
    """Schema for alert API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    sensor_id: Optional[uuid.UUID]
    status: str
    acknowledged_by: Optional[uuid.UUID]
    resolved_by: Optional[uuid.UUID]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    corrective_action_taken: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_active(self) -> bool:
        return self.status == "active"
    
    @computed_field
    @property
    def is_acknowledged(self) -> bool:
        return self.acknowledged_at is not None
    
    @computed_field
    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved"
    
    @computed_field
    @property
    def duration_hours(self) -> Optional[float]:
        # Populated by service layer
        return getattr(self, '_duration_hours', None)
    
    @computed_field
    @property
    def sensor_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_sensor_name', None)

    class Config:
        from_attributes = True

class AlertSummary(BaseModel):
    """Summary schema for alert listings"""
    id: uuid.UUID
    alert_type: str
    severity: str
    status: str
    sensor_name: Optional[str]
    message: str
    created_at: datetime
    is_haccp_critical: bool

    class Config:
        from_attributes = True