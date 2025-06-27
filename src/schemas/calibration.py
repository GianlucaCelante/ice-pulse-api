# =====================================================
# src/schemas/calibration.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional
from datetime import datetime, date
import uuid

class CalibrationBase(BaseModel):
    """Base schema for Calibration"""
    calibration_type: str = Field(..., description="Type of calibration")
    calibration_method: Optional[str] = Field(None, max_length=50, description="Calibration method used")
    accuracy_achieved: float = Field(..., gt=0, description="Accuracy achieved")
    calibration_passed: bool = Field(..., description="Whether calibration passed")
    notes: Optional[str] = Field(None, description="Calibration notes")
    
    # Technician info
    technician_name: Optional[str] = Field(None, max_length=100, description="Technician name")
    technician_certificate: Optional[str] = Field(None, max_length=100, description="Technician certificate")
    
    # Reference equipment
    reference_equipment_model: Optional[str] = Field(None, max_length=100, description="Reference equipment model")
    reference_equipment_serial: Optional[str] = Field(None, max_length=100, description="Reference equipment serial")
    reference_equipment_cert_date: Optional[date] = Field(None, description="Reference equipment certification date")
    
    # Scheduling
    scheduled_date: Optional[datetime] = Field(None, description="Scheduled calibration date")
    next_calibration_due: date = Field(..., description="Next calibration due date")

    @validator('calibration_type')
    def validate_calibration_type(cls, v):
        allowed_types = ['routine', 'corrective', 'verification', 'initial']
        if v not in allowed_types:
            raise ValueError(f'Calibration type must be one of: {allowed_types}')
        return v

    @validator('next_calibration_due')
    def validate_next_calibration_due(cls, v):
        if v <= date.today():
            raise ValueError('Next calibration due date must be in the future')
        return v

class CalibrationCreate(CalibrationBase):
    """Schema for creating calibration"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    sensor_id: uuid.UUID = Field(..., description="Sensor ID")
    calibrated_by: Optional[uuid.UUID] = Field(None, description="User ID who performed calibration")

class CalibrationUpdate(BaseModel):
    """Schema for updating calibration"""
    accuracy_achieved: Optional[float] = Field(None, gt=0)
    calibration_passed: Optional[bool] = None
    notes: Optional[str] = None
    technician_name: Optional[str] = Field(None, max_length=100)
    technician_certificate: Optional[str] = Field(None, max_length=100)
    next_calibration_due: Optional[date] = None

class CalibrationSchedule(BaseModel):
    """Schema for scheduling calibration"""
    sensor_id: uuid.UUID = Field(..., description="Sensor ID")
    scheduled_date: datetime = Field(..., description="Scheduled date")
    calibration_type: str = Field(default="routine", description="Type of calibration")
    assigned_technician: Optional[uuid.UUID] = Field(None, description="Assigned technician user ID")

class CalibrationResponse(CalibrationBase):
    """Schema for calibration API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    sensor_id: uuid.UUID
    calibrated_by: Optional[uuid.UUID]
    calibrated_at: datetime
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_passed(self) -> bool:
        return self.calibration_passed
    
    @computed_field
    @property
    def is_due_soon(self) -> bool:
        # Populated by service layer (default 30 days warning)
        return getattr(self, '_is_due_soon', False)
    
    @computed_field
    @property
    def days_until_due(self) -> int:
        delta = self.next_calibration_due - date.today()
        return delta.days
    
    @computed_field
    @property
    def sensor_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_sensor_name', None)
    
    @computed_field
    @property
    def technician_display_name(self) -> Optional[str]:
        # Populated by service layer (User.full_name)
        return getattr(self, '_technician_display_name', self.technician_name)

    class Config:
        from_attributes = True

class CalibrationSummary(BaseModel):
    """Summary schema for calibration listings"""
    id: uuid.UUID
    sensor_name: str
    calibration_type: str
    calibration_passed: bool
    calibrated_at: datetime
    next_calibration_due: date
    days_until_due: int
    is_due_soon: bool

    class Config:
        from_attributes = True

class CalibrationReport(BaseModel):
    """Schema for calibration reports"""
    organization_id: uuid.UUID
    period_start: date
    period_end: date
    total_calibrations: int
    passed_calibrations: int
    failed_calibrations: int
    overdue_calibrations: int
    due_soon_calibrations: int
    compliance_percentage: float
    sensors_requiring_calibration: list[CalibrationSummary]