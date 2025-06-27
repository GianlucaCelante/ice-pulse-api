# =====================================================
# src/schemas/report.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from enum import Enum
import uuid

# Enum mirrors per Pydantic
class ReportTypeEnum(str, Enum):
    HACCP_MONTHLY = "haccp_monthly"
    TEMPERATURE_SUMMARY = "temperature_summary"
    SENSOR_STATUS = "sensor_status"
    ALERT_SUMMARY = "alert_summary"

class ReportStatusEnum(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class ScheduleFrequencyEnum(str, Enum):
    MANUAL = "manual"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ReportAutoConfig(BaseModel):
    """Schema per configurazione auto-generation"""
    email_recipients: Optional[List[str]] = Field(None, description="Email recipients for auto-generated reports")
    include_charts: bool = Field(default=False, description="Include charts in report")
    format: str = Field(default="pdf", description="Report format")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['pdf', 'excel', 'json']
        if v not in allowed_formats:
            raise ValueError(f'Format must be one of: {allowed_formats}')
        return v

class ReportBase(BaseModel):
    """Base schema for Report"""
    report_type: ReportTypeEnum = Field(..., description="Type of report")
    report_name: str = Field(..., min_length=1, max_length=200, description="Report name")
    period_start: date = Field(..., description="Report period start date")
    period_end: date = Field(..., description="Report period end date")

    @validator('period_end')
    def validate_period(cls, v, values):
        if 'period_start' in values and v < values['period_start']:
            raise ValueError('Period end must be after period start')
        return v

class ReportCreate(ReportBase):
    """Schema for creating report"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    generated_by: Optional[uuid.UUID] = Field(None, description="User ID who requested the report")

class ReportScheduleSetup(BaseModel):
    """Schema for setting up auto-scheduling"""
    report_type: ReportTypeEnum = Field(..., description="Type of report to schedule")
    report_name: str = Field(..., min_length=1, max_length=200, description="Report name")
    schedule_frequency: ScheduleFrequencyEnum = Field(..., description="How often to generate")
    auto_config: Optional[ReportAutoConfig] = Field(None, description="Auto-generation configuration")
    
    @validator('schedule_frequency')
    def validate_schedule_frequency(cls, v):
        if v == ScheduleFrequencyEnum.MANUAL:
            raise ValueError('Cannot schedule manual reports')
        return v

class ReportUpdate(BaseModel):
    """Schema for updating report"""
    report_name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active_schedule: Optional[bool] = Field(None, description="Enable/disable auto-generation")
    auto_config: Optional[ReportAutoConfig] = None

class ReportResponse(ReportBase):
    """Schema for report API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    generated_by: Optional[uuid.UUID]
    status: ReportStatusEnum
    generation_started_at: Optional[datetime]
    generation_completed_at: Optional[datetime]
    generation_error: Optional[str]
    report_data: Optional[Dict[str, Any]]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    is_auto_generated: bool
    schedule_frequency: ScheduleFrequencyEnum
    next_generation_date: Optional[datetime]
    is_active_schedule: bool
    auto_config: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def is_completed(self) -> bool:
        return self.status == ReportStatusEnum.COMPLETED
    
    @computed_field
    @property
    def is_scheduled_report(self) -> bool:
        return self.schedule_frequency != ScheduleFrequencyEnum.MANUAL
    
    @computed_field
    @property
    def is_due_for_generation(self) -> bool:
        # Populated by service layer
        return getattr(self, '_is_due_for_generation', False)
    
    @computed_field
    @property
    def file_size_mb(self) -> Optional[float]:
        if not self.file_size_bytes:
            return None
        return round(self.file_size_bytes / (1024 * 1024), 2)
    
    @computed_field
    @property
    def generation_duration_seconds(self) -> Optional[int]:
        if not self.generation_started_at or not self.generation_completed_at:
            return None
        delta = self.generation_completed_at - self.generation_started_at
        return int(delta.total_seconds())
    
    @computed_field
    @property
    def generated_by_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_generated_by_name', None)

    class Config:
        from_attributes = True

class ReportSummary(BaseModel):
    """Summary schema for report listings"""
    id: uuid.UUID
    report_type: ReportTypeEnum
    report_name: str
    status: ReportStatusEnum
    period_start: date
    period_end: date
    is_scheduled_report: bool
    file_size_mb: Optional[float]
    generated_by_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ReportScheduleStatus(BaseModel):
    """Schema for scheduled reports status"""
    id: uuid.UUID
    report_type: ReportTypeEnum
    report_name: str
    schedule_frequency: ScheduleFrequencyEnum
    next_generation_date: Optional[datetime]
    is_active_schedule: bool
    last_generated_at: Optional[datetime]
    is_due_for_generation: bool

    class Config:
        from_attributes = True