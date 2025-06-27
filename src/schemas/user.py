# src/schemas/user.py - REFACTORED CON COMPUTED FIELDS
# =====================================================
from pydantic import BaseModel, EmailStr, Field, validator, computed_field
from typing import Optional
from datetime import datetime, date
import uuid

class UserBase(BaseModel):
    """Base schema per User"""
    email: EmailStr = Field(...)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="operator")
    is_active: bool = Field(default=True)
    haccp_certificate_number: Optional[str] = Field(None, max_length=100)
    haccp_certificate_expiry: Optional[date] = Field(None)

    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['admin', 'manager', 'operator', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {allowed_roles}')
        return v

class UserCreate(UserBase):
    """Schema per creare user"""
    organization_id: uuid.UUID = Field(...)
    password: str = Field(..., min_length=8)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserUpdate(BaseModel):
    """Schema per aggiornare user"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = None
    is_active: Optional[bool] = None
    haccp_certificate_number: Optional[str] = Field(None, max_length=100)
    haccp_certificate_expiry: Optional[date] = None

class UserResponse(UserBase):
    """Schema per response API"""
    id: uuid.UUID
    organization_id: uuid.UUID
    is_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Computed fields usando @computed_field
    @computed_field
    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        result = " ".join(part for part in parts if part)
        return result if result else self.email.split("@")[0]
    
    @computed_field
    @property
    def is_haccp_certified(self) -> bool:
        return (
            self.haccp_certificate_number is not None and
            self.haccp_certificate_expiry is not None and
            self.haccp_certificate_expiry > date.today()
        )
    
    @computed_field
    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    class Config:
        from_attributes = True