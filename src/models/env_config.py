# =====================================================
# src/models/env_config.py - ENVIRONMENT/RUNTIME CONFIGURATION TABLE
# =====================================================
from sqlalchemy import String, Text, Boolean, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any, Union
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization

class EnvConfig(BaseModel):
    """
    EnvConfig model - configurazioni runtime per sistema e organizzazioni.
    
    PATTERN KEY-VALUE con typing:
    - Global config (organization_id = NULL)
    - Per-organization config  
    - Type-safe value storage
    """
    
    __tablename__ = "env_config"
    
    # ==========================================
    # SCOPE - Global vs Organization
    # ==========================================
    
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )  # NULL = global setting
    
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    
    # ==========================================
    # KEY-VALUE PAIR
    # ==========================================
    
    key: Mapped[str] = mapped_column(String(200), index=True)  # "email.smtp.host"
    value: Mapped[str] = mapped_column(Text)  # Sempre string, ma typed
    value_type: Mapped[str] = mapped_column(String(20), default="string")  # string, int, float, bool, json
    
    # ==========================================
    # METADATA
    # ==========================================
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================
    # CONSTRAINTS & INDEXES
    # ==========================================
    
    __table_args__ = (
        # Unique constraint: organization + key
        Index('idx_env_config_org_key', 'organization_id', 'key', unique=True),
        CheckConstraint(
            "value_type IN ('string', 'int', 'float', 'bool', 'json')",
            name='chk_value_type_valid'
        ),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        org_scope = f"org:{self.organization_id}" if self.organization_id else "global"
        return f"EnvConfig({org_scope}, {self.key}={self.value})"
    
    def get_typed_value(self) -> Any:
        """Ritorna il valore convertito nel tipo corretto"""
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        else:  # string
            return self.value
    
    def set_typed_value(self, value: Any) -> None:
        """Imposta un valore con auto-detection del tipo"""
        if isinstance(value, bool):
            self.value_type = "bool"
            self.value = str(value).lower()
        elif isinstance(value, int):
            self.value_type = "int"
            self.value = str(value)
        elif isinstance(value, float):
            self.value_type = "float"
            self.value = str(value)
        elif isinstance(value, (dict, list)):
            self.value_type = "json"
            import json
            self.value = json.dumps(value)
        else:
            self.value_type = "string"
            self.value = str(value)
    
    @classmethod
    def get_config(cls, session, key: str, organization_id: Optional[uuid.UUID] = None, default: Any = None) -> Any:
        """Helper per ottenere una config con fallback"""
        config = session.query(cls).filter_by(
            key=key,
            organization_id=organization_id
        ).first()
        
        if config:
            return config.get_typed_value()
        
        # Fallback to global config se non trovato per organization
        if organization_id is not None:
            global_config = session.query(cls).filter_by(
                key=key,
                organization_id=None
            ).first()
            if global_config:
                return global_config.get_typed_value()
        
        return default
    
    @classmethod
    def set_config(cls, session, key: str, value: Any, organization_id: Optional[uuid.UUID] = None) -> 'EnvConfig':
        """Helper per impostare una config"""
        config = session.query(cls).filter_by(
            key=key,
            organization_id=organization_id
        ).first()
        
        if not config:
            config = cls(key=key, organization_id=organization_id)
            session.add(config)
        
        config.set_typed_value(value)
        return config

# =====================================================
# ESEMPI DI USO ENV_CONFIG
# =====================================================

"""
ESEMPI PRATICI di config che userai:

# Global config
EnvConfig.set_config(session, "system.maintenance_mode", False)
EnvConfig.set_config(session, "email.smtp.host", "smtp.gmail.com")
EnvConfig.set_config(session, "features.auto_reports", True)

# Per-organization config
EnvConfig.set_config(session, "alerts.email_recipients", 
                    ["admin@company.com", "manager@company.com"], 
                    organization_id=org.id)

EnvConfig.set_config(session, "temperature.default_min", -18.0, 
                    organization_id=org.id)

EnvConfig.set_config(session, "reports.auto_generation", 
                    {"frequency": "monthly", "day": 1, "hour": 8}, 
                    organization_id=org.id)

# Lettura con fallback
smtp_host = EnvConfig.get_config(session, "email.smtp.host", 
                                default="localhost")

temp_min = EnvConfig.get_config(session, "temperature.default_min", 
                               organization_id=org.id, 
                               default=-20.0)
"""