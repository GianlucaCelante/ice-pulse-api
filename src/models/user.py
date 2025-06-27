# src/models/user.py - COMPLETAMENTE REFACTORED  
# =====================================================
from sqlalchemy import String, Boolean, Integer, Date, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date
from typing import Optional
from passlib.context import CryptContext
import uuid

from .base import BaseModel

# Forward reference
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(BaseModel):
    """
    User model con SQLAlchemy 2.0 syntax.
    
    Gestisce autenticazione, autorizzazione e compliance HACCP.
    """
    
    __tablename__ = "users"
    
    # ==========================================
    # FOREIGN KEY & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users"
    )
    
    # ==========================================
    # AUTHENTICATION FIELDS
    # ==========================================
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)  # TEXT type for bcrypt
    
    # ==========================================
    # PERSONAL INFO
    # ==========================================
    
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ==========================================
    # AUTHORIZATION & STATUS  
    # ==========================================
    
    role: Mapped[str] = mapped_column(String(20), default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================
    # LOGIN TRACKING
    # ==========================================
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    
    # ==========================================
    # HACCP COMPLIANCE
    # ==========================================
    
    haccp_certificate_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    haccp_certificate_expiry: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
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
    def is_haccp_certified(self) -> bool:
        """Computed property: verifica se ha certificazione HACCP valida"""
        return (
            self.haccp_certificate_number is not None and
            self.haccp_certificate_expiry is not None and
            self.haccp_certificate_expiry > date.today()
        )
    
    @property
    def is_admin(self) -> bool:
        """Verifica se ha ruolo admin"""
        return self.role == "admin"
    
    @property
    def can_manage_sensors(self) -> bool:
        """Verifica se può gestire sensori"""
        return self.role in ["admin", "manager"]
    
    def verify_password(self, password: str) -> bool:
        """Verifica la password"""
        return pwd_context.verify(password, self.password_hash)
    
    def set_password(self, password: str) -> None:
        """Imposta nuova password (con hash)"""
        self.password_hash = pwd_context.hash(password)
    
    def reset_failed_attempts(self) -> None:
        """Reset contatore tentativi falliti"""
        self.failed_login_attempts = 0
    
    def increment_failed_attempts(self) -> None:
        """Incrementa contatore tentativi falliti"""
        self.failed_login_attempts += 1
    
    def is_account_locked(self, max_attempts: int = 5) -> bool:
        """Verifica se account è bloccato per troppi tentativi"""
        return self.failed_login_attempts >= max_attempts
    
    def update_last_login(self) -> None:
        """Aggiorna timestamp ultimo login"""
        self.last_login_at = datetime.utcnow()
