# src/schemas/organization.py - REFACTORED CON COMPUTED FIELDS
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class OrganizationBase(BaseModel):
    """Base schema per Organization"""
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$')
    subscription_plan: str = Field(default="free")
    max_sensors: int = Field(default=10, ge=1)
    timezone: str = Field(default="UTC")
    haccp_settings: Optional[Dict[str, Any]] = Field(None)
    retention_months: int = Field(default=24, ge=6)
    auto_archive_enabled: bool = Field(default=True)

    @validator('subscription_plan')
    def validate_subscription_plan(cls, v):
        allowed_plans = ['free', 'basic', 'premium', 'enterprise']
        if v not in allowed_plans:
            raise ValueError(f'Subscription plan must be one of: {allowed_plans}')
        return v

    @validator('slug')
    def validate_slug(cls, v):
        return v.lower()

class OrganizationCreate(OrganizationBase):
    """Schema per creare organization"""
    pass

class OrganizationUpdate(BaseModel):
    """Schema per aggiornare organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    subscription_plan: Optional[str] = None
    max_sensors: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    haccp_settings: Optional[Dict[str, Any]] = None
    retention_months: Optional[int] = Field(None, ge=6)
    auto_archive_enabled: Optional[bool] = None

class OrganizationResponse(OrganizationBase):
    """Schema per response API"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    @computed_field
    @property
    def is_premium(self) -> bool:
        return self.subscription_plan in ["premium", "enterprise"]
    
    @computed_field
    @property
    def user_count(self) -> int:
        # Questo sarà popolato dal service layer
        return getattr(self, '_user_count', 0)
    
    @computed_field
    @property
    def sensor_count(self) -> int:
        # Questo sarà popolato dal service layer
        return getattr(self, '_sensor_count', 0)

    class Config:
        from_attributes = True