# =====================================================
# src/schemas/env_config.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Any, Union, Dict, List
import uuid
import json
from datetime import datetime

class EnvConfigBase(BaseModel):
    """Base schema for EnvConfig"""
    key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    value: str = Field(..., description="Configuration value (as string)")
    value_type: str = Field(default="string", description="Type of the value")
    description: Optional[str] = Field(None, description="Description of this config")
    is_encrypted: bool = Field(default=False, description="Is this value encrypted")
    is_readonly: bool = Field(default=False, description="Is this config readonly")

    @validator('value_type')
    def validate_value_type(cls, v):
        allowed_types = ['string', 'int', 'float', 'bool', 'json']
        if v not in allowed_types:
            raise ValueError(f'Value type must be one of: {allowed_types}')
        return v

    @validator('key')
    def validate_key_format(cls, v):
        # Basic validation for key format (could be more strict)
        if not v.replace('.', '').replace('_', '').replace('-', '').isalnum():
            raise ValueError('Key can only contain letters, numbers, dots, underscores, and hyphens')
        return v

class EnvConfigCreate(EnvConfigBase):
    """Schema for creating env config"""
    organization_id: Optional[uuid.UUID] = Field(None, description="Organization ID (null for global)")

class EnvConfigCreateTyped(BaseModel):
    """Schema for creating env config with typed value"""
    organization_id: Optional[uuid.UUID] = Field(None, description="Organization ID (null for global)")
    key: str = Field(..., min_length=1, max_length=200, description="Configuration key")
    value: Any = Field(..., description="Configuration value (will be auto-typed)")
    description: Optional[str] = Field(None, description="Description of this config")
    is_readonly: bool = Field(default=False, description="Is this config readonly")

class EnvConfigUpdate(BaseModel):
    """Schema for updating env config"""
    value: Optional[str] = None
    value_type: Optional[str] = None
    description: Optional[str] = None
    is_readonly: Optional[bool] = None

    @validator('value_type')
    def validate_value_type(cls, v):
        if v is not None:
            allowed_types = ['string', 'int', 'float', 'bool', 'json']
            if v not in allowed_types:
                raise ValueError(f'Value type must be one of: {allowed_types}')
        return v

class EnvConfigUpdateTyped(BaseModel):
    """Schema for updating env config with typed value"""
    value: Any = Field(..., description="Configuration value (will be auto-typed)")
    description: Optional[str] = None
    is_readonly: Optional[bool] = None

class EnvConfigBulkSet(BaseModel):
    """Schema for setting multiple configs at once"""
    organization_id: Optional[uuid.UUID] = Field(None, description="Organization ID (null for global)")
    configs: Dict[str, Any] = Field(..., description="Dictionary of key-value pairs")
    
    @validator('configs')
    def validate_configs_not_empty(cls, v):
        if not v:
            raise ValueError('Configs dictionary cannot be empty')
        return v

class EnvConfigResponse(EnvConfigBase):
    """Schema for env config API responses"""
    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    @computed_field
    @property
    def typed_value(self) -> Any:
        # Populated by service layer using get_typed_value()
        return getattr(self, '_typed_value', self.value)
    
    @computed_field
    @property
    def scope(self) -> str:
        return "global" if self.organization_id is None else "organization"
    
    @computed_field
    @property
    def organization_name(self) -> Optional[str]:
        # Populated by service layer
        return getattr(self, '_organization_name', None)

    class Config:
        from_attributes = True

class EnvConfigSummary(BaseModel):
    """Summary schema for env config listings"""
    id: uuid.UUID
    key: str
    value_type: str
    scope: str
    organization_name: Optional[str]
    description: Optional[str]
    is_readonly: bool

    class Config:
        from_attributes = True

class EnvConfigQuery(BaseModel):
    """Schema for querying configs"""
    key: str = Field(..., description="Configuration key to get")
    organization_id: Optional[uuid.UUID] = Field(None, description="Organization ID")
    default: Optional[Any] = Field(None, description="Default value if not found")

class EnvConfigQueryResponse(BaseModel):
    """Schema for config query response"""
    key: str
    value: Any
    found: bool
    scope: str  # "organization", "global", "default"
    source_id: Optional[uuid.UUID] = None  # ID of the config record that provided the value

class EnvConfigGroupResponse(BaseModel):
    """Schema for grouped configs (e.g., all email.* configs)"""
    prefix: str
    configs: Dict[str, Any]
    total_count: int

# =====================================================
# HELPER SCHEMAS FOR COMMON PATTERNS
# =====================================================

class EmailConfig(BaseModel):
    """Schema for email configuration group"""
    smtp_host: str
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str
    from_name: Optional[str] = None

class TemperatureThresholds(BaseModel):
    """Schema for temperature threshold configs"""
    freezer_min: float = -25.0
    freezer_max: float = -15.0
    fridge_min: float = 0.0
    fridge_max: float = 8.0
    room_min: float = 15.0
    room_max: float = 25.0

class ReportConfig(BaseModel):
    """Schema for report configuration"""
    auto_generation: bool = True
    default_frequency: str = "monthly"
    email_recipients: List[str] = []
    include_charts: bool = True
    retention_months: int = 24

class SystemMaintenanceConfig(BaseModel):
    """Schema for system maintenance configuration"""
    maintenance_mode: bool = False
    maintenance_message: Optional[str] = None
    scheduled_downtime_start: Optional[datetime] = None
    scheduled_downtime_end: Optional[datetime] = None