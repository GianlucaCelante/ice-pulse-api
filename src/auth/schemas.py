# =====================================================
# src/auth/schemas.py - FastAPI-Users Schemas
# =====================================================
import uuid
from typing import Optional
from datetime import date
from pydantic import BaseModel, EmailStr, Field, validator
from fastapi_users import schemas

# =====================================================
# BASE USER SCHEMAS
# =====================================================

class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema per leggere dati utente (response API)."""
    
    # Campi FastAPI-Users standard
    id: uuid.UUID
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False
    
    # Campi custom Ice Pulse
    organization_id: uuid.UUID
    first_name: str
    last_name: str
    role: str
    phone: Optional[str] = None
    
    # HACCP compliance fields
    haccp_certificate_number: Optional[str] = None
    haccp_certificate_expiry: Optional[date] = None
    
    # Audit fields (read-only)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserCreate(schemas.BaseUserCreate):
    """Schema per creare nuovo utente."""
    
    # Campi FastAPI-Users standard
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    is_active: bool = True
    is_verified: bool = False
    
    # Campi custom Ice Pulse (required)
    organization_id: uuid.UUID = Field(..., description="ID organizzazione di appartenenza")
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., description="Ruolo utente: admin, manager, operator, viewer")
    
    # Campi opzionali
    phone: Optional[str] = Field(None, max_length=20)
    haccp_certificate_number: Optional[str] = Field(None, max_length=50)
    haccp_certificate_expiry: Optional[date] = None
    
    @validator('role')
    def validate_role(cls, v):
        """Validazione ruolo utente."""
        allowed_roles = ['admin', 'manager', 'operator', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validazione formato telefono."""
        if v is not None:
            # Rimuovi spazi e caratteri speciali
            cleaned = ''.join(filter(str.isdigit, v))
            if len(cleaned) < 8 or len(cleaned) > 15:
                raise ValueError('Phone number must be between 8 and 15 digits')
        return v

class UserUpdate(schemas.BaseUserUpdate):
    """Schema per aggiornare utente esistente."""
    
    # Campi FastAPI-Users standard (tutti opzionali)
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    
    # Campi custom Ice Pulse (tutti opzionali)
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=20)
    
    # HACCP fields
    haccp_certificate_number: Optional[str] = Field(None, max_length=50)
    haccp_certificate_expiry: Optional[date] = None
    
    @validator('role')
    def validate_role(cls, v):
        """Validazione ruolo utente."""
        if v is not None:
            allowed_roles = ['admin', 'manager', 'operator', 'viewer']
            if v not in allowed_roles:
                raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validazione formato telefono."""
        if v is not None:
            cleaned = ''.join(filter(str.isdigit, v))
            if len(cleaned) < 8 or len(cleaned) > 15:
                raise ValueError('Phone number must be between 8 and 15 digits')
        return v

# =====================================================
# CUSTOM SCHEMAS PER ICE PULSE
# =====================================================

class UserInvite(BaseModel):
    """Schema per invitare nuovo utente (admin-only)."""
    
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    role: str = Field(..., description="Ruolo utente: admin, manager, operator, viewer")
    phone: Optional[str] = Field(None, max_length=20)
    
    # Auto-assign organization_id dell'admin che invita
    send_welcome_email: bool = Field(True, description="Invia email di benvenuto")
    
    @validator('role')
    def validate_role(cls, v):
        """Validazione ruolo utente."""
        allowed_roles = ['admin', 'manager', 'operator', 'viewer']
        if v not in allowed_roles:
            raise ValueError(f'Role must be one of: {", ".join(allowed_roles)}')
        return v

class UserProfile(BaseModel):
    """Schema per profilo utente (self-service)."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    
    # Non permettiamo cambio email/role via self-service
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validazione formato telefono."""
        if v is not None:
            cleaned = ''.join(filter(str.isdigit, v))
            if len(cleaned) < 8 or len(cleaned) > 15:
                raise ValueError('Phone number must be between 8 and 15 digits')
        return v

class PasswordChange(BaseModel):
    """Schema per cambio password."""
    
    current_password: str = Field(..., description="Password attuale")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nuova password")
    confirm_password: str = Field(..., description="Conferma nuova password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validazione che le password coincidano."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New password and confirmation do not match')
        return v

class UserStats(BaseModel):
    """Schema per statistiche utente (analytics)."""
    
    total_logins: int
    last_login: Optional[str] = None
    account_created: str
    haccp_certificate_status: str  # "valid", "expiring", "expired", "none"
    organization_name: str
    
class OrganizationUserList(BaseModel):
    """Schema per lista utenti organizzazione."""
    
    users: list[UserRead]
    total_count: int
    active_count: int
    by_role: dict[str, int]  # {"admin": 1, "manager": 2, "operator": 5}

# =====================================================
# AUTHENTICATION RESPONSE SCHEMAS
# =====================================================

class LoginResponse(BaseModel):
    """Schema per response login."""
    
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    expires_in: int  # secondi
    
class TokenRefresh(BaseModel):
    """Schema per refresh token."""
    
    refresh_token: str

class LogoutResponse(BaseModel):
    """Schema per response logout."""
    
    message: str = "Successfully logged out"
    logged_out_at: str