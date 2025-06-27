# =====================================================
# src/models/organization.py
# =====================================================
from sqlalchemy import String, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from typing import List, Dict, Any, Optional

from .base import BaseModel

# Forward references per evitare circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User
    from .location import Location
    from .sensor import Sensor
    from .alert import Alert

class Organization(BaseModel):
    """
    Organization model con SQLAlchemy 2.0 syntax.
    
    Multi-tenant architecture: ogni org ha i suoi dati isolati.
    """
    
    __tablename__ = "organizations"
    
    # ==========================================
    # CAMPI BASE (REQUIRED)
    # ==========================================
    
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # ==========================================
    # SUBSCRIPTION & LIMITS
    # ==========================================
    
    subscription_plan: Mapped[str] = mapped_column(String(20), default="free")
    max_sensors: Mapped[int] = mapped_column(Integer, default=10)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # ==========================================
    # HACCP SETTINGS (JSON)
    # ==========================================
    
    haccp_settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True
    )
    
    # ==========================================
    # DATA RETENTION POLICIES
    # ==========================================
    
    retention_months: Mapped[int] = mapped_column(Integer, default=24)
    auto_archive_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # ==========================================
    # RELATIONSHIPS (SQLAlchemy 2.0 syntax)
    # ==========================================
    
    # One-to-many relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    locations: Mapped[List["Location"]] = relationship(
        "Location",
        back_populates="organization", 
        cascade="all, delete-orphan"
    )
    
    sensors: Mapped[List["Sensor"]] = relationship(
        "Sensor",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint('max_sensors > 0', name='chk_max_sensors_positive'),
        CheckConstraint('retention_months >= 6', name='chk_retention_min_6_months'),
        CheckConstraint(
            "haccp_settings IS NULL OR (haccp_settings ? 'temperature_min' AND haccp_settings ? 'temperature_max')", 
            name='chk_haccp_settings_structure'
        ),
    )
    
    # ==========================================
    # BUSINESS LOGIC METHODS
    # ==========================================
    
    def __str__(self) -> str:
        return f"Organization(name={self.name}, plan={self.subscription_plan})"
    
    def is_premium(self) -> bool:
        """Verifica se ha piano premium o superiore"""
        return self.subscription_plan in ["premium", "enterprise"]
    
    def can_add_sensor(self) -> bool:
        """Verifica se può aggiungere altri sensori"""
        current_sensors = len(self.sensors) if self.sensors else 0
        return current_sensors < self.max_sensors
    
    def get_haccp_setting(self, key: str, default: Any = None) -> Any:
        """Ottiene una singola impostazione HACCP"""
        if not self.haccp_settings:
            return default
        return self.haccp_settings.get(key, default)
    
    def set_haccp_setting(self, key: str, value: Any) -> None:
        """Imposta una singola impostazione HACCP"""
        if self.haccp_settings is None:
            self.haccp_settings = {}
        self.haccp_settings[key] = value
    
    def get_temperature_limits(self) -> Dict[str, Optional[float]]:
        """Ritorna i limiti di temperatura HACCP"""
        if not self.haccp_settings:
            return {"min": None, "max": None}
        
        return {
            "min": self.haccp_settings.get("temperature_min"),
            "max": self.haccp_settings.get("temperature_max")
        }