# =====================================================
# src/models/audit_log.py - SIMPLIFIED
# =====================================================
from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .user import User

class AuditLog(BaseModel):
    """
    AuditLog model - tracciabilità semplificata.
    
    DESIGN SEMPLIFICATO:
    - Solo campi essenziali per MVP
    - Facile da implementare
    - Expandibile in futuro
    """
    
    __tablename__ = "audit_log"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    user: Mapped[Optional["User"]] = relationship("User")
    
    # ==========================================
    # WHAT HAPPENED
    # ==========================================
    
    action: Mapped[str] = mapped_column(String(100), index=True)  # "sensor_created", "reading_added"
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # "sensor", "reading"
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    
    # ==========================================
    # CHANGE DETAILS
    # ==========================================
    
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB()),
        nullable=True
    )
    
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB()),
        nullable=True
    )
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==========================================
    # CONTEXT (simplified)
    # ==========================================
    
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==========================================
    # HACCP RELEVANCE
    # ==========================================
    
    haccp_relevant: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"AuditLog(action={self.action}, resource={self.resource_type}:{self.resource_id})"
    
    @property
    def user_display_name(self) -> str:
        if self.user and hasattr(self.user, 'full_name'):
            return self.user.full_name
        return "Sistema" if self.user_id is None else "Utente sconosciuto"
    
    @property
    def has_changes(self) -> bool:
        return self.old_values is not None or self.new_values is not None