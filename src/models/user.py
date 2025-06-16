# src/models/user.py
from sqlalchemy import Column, String, Boolean, Integer, Date, TIMESTAMP, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from passlib.context import CryptContext

from src.database.connection import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Organization relationship (multi-tenancy)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Authentication
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)  # TEXT type for modern hashing algorithms
    
    # Personal info
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Authorization
    role = Column(String(20), nullable=False, default="operator")
    
    # Account status
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    
    # HACCP specific fields
    haccp_certificate_number = Column(String(100), nullable=True)
    haccp_certificate_expiry = Column(Date, nullable=True)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    acknowledged_alerts = relationship("Alert", foreign_keys="Alert.acknowledged_by", back_populates="acknowledged_by_user")
    resolved_alerts = relationship("Alert", foreign_keys="Alert.resolved_by", back_populates="resolved_by_user")
    calibrations = relationship("Calibration", back_populates="calibrated_by_user")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager', 'operator', 'viewer')", name='chk_user_role_valid'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
    
    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.email})" if self.first_name else self.email
    
    # Authentication methods
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storing"""
        return pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash"""
        return pwd_context.verify(password, self.password_hash)
    
    def set_password(self, password: str) -> None:
        """Set user password (hashed)"""
        self.password_hash = self.hash_password(password)
    
    # Account status methods
    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed attempts"""
        return self.failed_login_attempts >= 5
    
    def reset_failed_attempts(self) -> None:
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        
    def increment_failed_attempts(self) -> None:
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
    
    def record_login(self) -> None:
        """Record successful login"""
        self.last_login_at = datetime.utcnow()
        self.reset_failed_attempts()
    
    # Authorization methods
    def has_permission(self, action: str) -> bool:
        """Check if user has permission for action"""
        permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_settings'],
            'manager': ['read', 'write', 'delete', 'manage_users'],
            'operator': ['read', 'write'],
            'viewer': ['read']
        }
        
        user_permissions = permissions.get(self.role, [])
        return action in user_permissions
    
    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role in ['admin', 'manager']
    
    def can_modify_settings(self) -> bool:
        """Check if user can modify organization settings"""
        return self.role == 'admin'
    
    # HACCP methods
    def is_haccp_certified(self) -> bool:
        """Check if user has valid HACCP certification"""
        if not self.haccp_certificate_number or not self.haccp_certificate_expiry:
            return False
        return self.haccp_certificate_expiry > date.today()
    
    def days_until_cert_expiry(self) -> Optional[int]:
        """Get days until HACCP certificate expires"""
        if not self.haccp_certificate_expiry:
            return None
        delta = self.haccp_certificate_expiry - date.today()
        return delta.days
    
    def needs_cert_renewal(self, warning_days: int = 30) -> bool:
        """Check if HACCP certificate needs renewal soon"""
        days_left = self.days_until_cert_expiry()
        return days_left is not None and days_left <= warning_days
    
    # Profile methods
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0]  # Use email prefix as fallback
    
    @property
    def display_name(self) -> str:
        """Get user's display name for UI"""
        return self.full_name
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        data = {
            'id': str(self.id),
            'organization_id': str(self.organization_id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'haccp_certificate_number': self.haccp_certificate_number,
            'haccp_certificate_expiry': self.haccp_certificate_expiry.isoformat() if self.haccp_certificate_expiry else None,
            'is_haccp_certified': self.is_haccp_certified(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'is_account_locked': self.is_account_locked(),
            })
        
        return data

# Role hierarchy for permissions
class UserRole:
    """User role constants and utilities"""
    
    ADMIN = "admin"
    MANAGER = "manager" 
    OPERATOR = "operator"
    VIEWER = "viewer"
    
    ALL_ROLES = [ADMIN, MANAGER, OPERATOR, VIEWER]
    
    ROLE_HIERARCHY = {
        ADMIN: 4,
        MANAGER: 3,
        OPERATOR: 2,
        VIEWER: 1
    }
    
    @classmethod
    def has_higher_or_equal_role(cls, user_role: str, required_role: str) -> bool:
        """Check if user role is higher or equal to required role"""
        user_level = cls.ROLE_HIERARCHY.get(user_role, 0)
        required_level = cls.ROLE_HIERARCHY.get(required_role, 0)
        return user_level >= required_level