# src/schemas/organization.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class OrganizationBase(BaseModel):
    """Base schema for Organization"""
    name: str = Field(..., min_length=1, max_length=200, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z0-9-]+$', description="URL-friendly slug")
    subscription_plan: str = Field(default="free", description="Subscription plan")
    max_sensors: int = Field(default=10, ge=1, description="Maximum number of sensors")
    timezone: str = Field(default="UTC", description="Organization timezone")
    haccp_settings: Optional[Dict[str, Any]] = Field(None, description="HACCP configuration settings")
    retention_months: int = Field(default=24, ge=6, description="Data retention period in months")
    auto_archive_enabled: bool = Field(default=True, description="Enable automatic data archiving")

    @validator('subscription_plan')
    def validate_subscription_plan(cls, v):
        allowed_plans = ['free', 'basic', 'premium', 'enterprise']
        if v not in allowed_plans:
            raise ValueError(f'Subscription plan must be one of: {allowed_plans}')
        return v

    @validator('slug')
    def validate_slug(cls, v):
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug can only contain letters, numbers, hyphens and underscores')
        return v.lower()

class OrganizationCreate(OrganizationBase):
    """Schema for creating organization"""
    pass

class OrganizationUpdate(BaseModel):
    """Schema for updating organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    subscription_plan: Optional[str] = None
    max_sensors: Optional[int] = Field(None, ge=1)
    timezone: Optional[str] = None
    haccp_settings: Optional[Dict[str, Any]] = None
    retention_months: Optional[int] = Field(None, ge=6)
    auto_archive_enabled: Optional[bool] = None

    @validator('subscription_plan')
    def validate_subscription_plan(cls, v):
        if v is not None:
            allowed_plans = ['free', 'basic', 'premium', 'enterprise']
            if v not in allowed_plans:
                raise ValueError(f'Subscription plan must be one of: {allowed_plans}')
        return v

class OrganizationResponse(OrganizationBase):
    """Schema for organization API responses"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationSummary(BaseModel):
    """Summary schema for organization listings"""
    id: uuid.UUID
    name: str
    slug: str
    subscription_plan: str
    created_at: datetime

    class Config:
        from_attributes = True


# src/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime, date
import uuid

class UserBase(BaseModel):
    """Base schema for User"""
    email: EmailStr = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, max_length=100, description="Last name")
    role: str = Field(default="operator", description="User role")
    is_active: bool = Field(default=True, description="Account active status")
    haccp_certificate_number: Optional[str] = Field(None, max_length=100, description="HACCP certificate number")
    haccp_certificate_expiry: Optional[date] = Field(None, description="HACCP certificate expiry date")

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'manager', 'operator', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v

    @validator('haccp_certificate_expiry')
    def validate_cert_expiry(cls, v, values):
        if v and 'haccp_certificate_number' in values:
            cert_number = values.get('haccp_certificate_number')
            if cert_number and not v:
                raise ValueError('Certificate expiry date required when certificate number is provided')
            if v < date.today():
                raise ValueError('Certificate expiry date cannot be in the past')
        return v

class UserCreate(UserBase):
    """Schema for creating user"""
    organization_id: uuid.UUID = Field(..., description="Organization ID")
    password: str = Field(..., min_length=8, description="User password")

    @validator('password')
    def validate_password(cls, v):
        # Basic password validation
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    """Schema for updating user"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    haccp_certificate_number: Optional[str] = Field(None, max_length=100)
    haccp_certificate_expiry: Optional[date] = None

    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            allowed_roles = ['admin', 'manager', 'operator', 'viewer']
            if v not in allowed_roles:
                raise ValueError(f'Role must be one of: {allowed_roles}')
        return v

class UserPasswordUpdate(BaseModel):
    """Schema for password updates"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserResponse(UserBase):
    """Schema for user API responses"""
    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    is_verified: bool
    is_haccp_certified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserSummary(BaseModel):
    """Summary schema for user listings"""
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    is_haccp_certified: bool
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

class UserLoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse