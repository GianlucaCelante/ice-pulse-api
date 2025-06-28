# =====================================================
# src/models/user.py - REFACTORED per FastAPI-Users
# =====================================================
from sqlalchemy import String, Boolean, Integer, Date, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional
import uuid

from fastapi_users.db import SQLAlchemyBaseUserTableUUID  # 🆕 FastAPI-Users base
from .base import BaseModel

# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization

class User(SQLAlchemyBaseUserTableUUID, BaseModel):
    """
    User model con FastAPI-Users compatibility.
    
    Eredita da SQLAlchemyBaseUserTableUUID che fornisce:
    - id: Mapped[uuid.UUID] (primary key)
    - email: Mapped[str] (unique)
    - hashed_password: Mapped[str]
    - is_active: Mapped[bool] = True
    - is_verified: Mapped[bool] = False  
    - is_superuser: Mapped[bool] = False
    
    Aggiungiamo solo i campi custom per Ice Pulse.
    """
    
    __tablename__ = "users"
    
    # ==========================================
    # ICE PULSE CUSTOM FIELDS
    # ==========================================
    
    # Multi-tenancy
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    # Personal info
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Authorization
    role: Mapped[str] = mapped_column(String(20), default="operator")
    
    # Contact info
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Login tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # HACCP compliance
    haccp_certificate_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    haccp_certificate_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # ==========================================
    # RELATIONSHIPS
    # ==========================================
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users"
    )
    
    # ==========================================
    # CONSTRAINTS  
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'manager', 'operator', 'viewer')",
            name='chk_user_role_valid'
        ),
        CheckConstraint(
            'failed_login_attempts >= 0',
            name='chk_failed_attempts_positive'
        ),
        CheckConstraint(
            'haccp_certificate_expiry IS NULL OR haccp_certificate_expiry > CURRENT_DATE',
            name='chk_haccp_cert_future'
        ),
    )
    
    # ==========================================
    # PASSWORD MANAGEMENT METHODS
    # ==========================================
    
    def set_password(self, password: str) -> None:
        """
        Hash e imposta password.
        
        Args:
            password: Password in plain text da hashare
        """
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.hashed_password = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verifica password confrontando con hash.
        
        Args:
            password: Password in plain text da verificare
            
        Returns:
            bool: True se password corretta
        """
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(password, self.hashed_password)
    
    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================
    
    def __str__(self) -> str:
        return f"User(email={self.email}, role={self.role})"
    
    @property
    def full_name(self) -> str:
        """Computed property: nome completo"""
        parts = [self.first_name, self.last_name]
        return " ".join(part for part in parts if part) or self.email.split("@")[0]
    
    @property
    def display_name(self) -> str:
        """Nome per UI: preferisce nome completo, fallback su email"""
        return self.full_name
    
    @property
    def is_admin(self) -> bool:
        """Check se utente è admin"""
        return self.role == "admin"
    
    @property
    def is_haccp_certified(self) -> bool:
        """Check se certificato HACCP valido"""
        if not self.haccp_certificate_number or not self.haccp_certificate_expiry:
            return False
        return self.haccp_certificate_expiry > date.today()
    
    def is_haccp_expiring_soon(self, days_warning: int = 30) -> bool:
        """Check se certificato HACCP scade entro X giorni"""
        if not self.is_haccp_certified:
            return False
        
        from datetime import timedelta
        warning_date = date.today() + timedelta(days=days_warning)
        if self.haccp_certificate_expiry is None:
            return False
        return self.haccp_certificate_expiry <= warning_date
    
    def is_account_locked(self, max_attempts: int = 5) -> bool:
        """Check se account bloccato per troppi tentativi"""
        return self.failed_login_attempts >= max_attempts
    
    @property
    def can_manage_users(self) -> bool:
        """Check se può gestire altri utenti"""
        return self.role in ["admin", "manager"]
    
    @property
    def can_access_sensors(self) -> bool:
        """Check se può accedere ai sensori"""
        return self.role in ["admin", "manager", "operator"]
    
    # ==========================================
    # SECURITY METHODS
    # ==========================================
    
    def update_last_login(self) -> None:
        """Aggiorna timestamp ultimo login"""
        self.last_login_at = datetime.utcnow()
    
    def increment_failed_attempts(self) -> None:
        """Incrementa contatore tentativi falliti"""
        self.failed_login_attempts += 1
    
    def reset_failed_attempts(self) -> None:
        """Reset contatore tentativi falliti"""
        self.failed_login_attempts = 0
    
    # ==========================================
    # MULTI-TENANCY HELPERS
    # ==========================================
    
    def belongs_to_organization(self, org_id: uuid.UUID) -> bool:
        """Check se appartiene all'organizzazione"""
        return self.organization_id == org_id
    
    def can_access_organization(self, org_id: uuid.UUID) -> bool:
        """Check se può accedere ai dati dell'organizzazione"""
        return self.belongs_to_organization(org_id)
    
    # ==========================================
    # HACCP HELPERS
    # ==========================================
    
    def set_haccp_certificate(self, number: str, expiry: date) -> None:
        """Imposta certificato HACCP"""
        self.haccp_certificate_number = number
        self.haccp_certificate_expiry = expiry
    
    def clear_haccp_certificate(self) -> None:
        """Rimuovi certificato HACCP"""
        self.haccp_certificate_number = None
        self.haccp_certificate_expiry = None