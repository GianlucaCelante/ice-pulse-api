# =====================================================
# src/models/alert.py - SQLAlchemy 2.0
# =====================================================
from sqlalchemy import String, Text, DECIMAL, Integer, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .sensor import Sensor
    from .user import User

class Alert(BaseModel):
    """
    Alert model - sistema allarmi per deviazioni HACCP.
    
    Traccia tutte le violazioni di soglie, gestisce acknowledgment
    e risoluzione degli allarmi.
    """
    
    __tablename__ = "alerts"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    sensor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="alerts"
    )
    
    sensor: Mapped[Optional["Sensor"]] = relationship(
        "Sensor",
        back_populates="alerts"
    )
    
    acknowledged_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[acknowledged_by]
    )
    
    resolved_by_user: Mapped[Optional["User"]] = relationship(
        "User", 
        foreign_keys=[resolved_by]
    )
    
    # ==========================================
    # ALERT INFO
    # ==========================================
    
    alert_type: Mapped[str] = mapped_column(String(30))  # temperature_high, offline, etc.
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    message: Mapped[str] = mapped_column(Text)
    
    # ==========================================
    # ALERT VALUES
    # ==========================================
    
    threshold_value: Mapped[Optional[float]] = mapped_column(DECIMAL(10,2), nullable=True)
    current_value: Mapped[Optional[float]] = mapped_column(DECIMAL(10,2), nullable=True)
    deviation_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # ==========================================
    # STATUS TRACKING
    # ==========================================
    
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # ==========================================
    # HACCP COMPLIANCE
    # ==========================================
    
    requires_corrective_action: Mapped[bool] = mapped_column(Boolean, default=False)
    corrective_action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_haccp_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('temperature_high', 'temperature_low', 'humidity_high', 'humidity_low', 'sensor_offline', 'battery_low', 'calibration_due')",
            name='chk_alert_type_valid'
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name='chk_alert_severity_valid'
        ),
        CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved', 'dismissed')",
            name='chk_alert_status_valid'
        ),
        CheckConstraint('deviation_duration_minutes >= 0', name='chk_deviation_duration_positive'),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Alert(type={self.alert_type}, severity={self.severity}, status={self.status})"
    
    @property
    def is_active(self) -> bool:
        """Verifica se alert è ancora attivo"""
        return self.status == "active"
    
    @property
    def is_acknowledged(self) -> bool:
        """Verifica se alert è stato riconosciuto"""
        return self.acknowledged_at is not None
    
    @property
    def is_resolved(self) -> bool:
        """Verifica se alert è stato risolto"""
        return self.status == "resolved"
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Durata alert in ore"""
        if not self.resolved_at:
            end_time = datetime.utcnow()
        else:
            end_time = self.resolved_at
        
        duration = end_time - self.created_at
        return duration.total_seconds() / 3600
    
    def acknowledge(self, user_id: uuid.UUID) -> None:
        """Riconosce l'alert"""
        self.status = "acknowledged"
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
    
    def resolve(self, user_id: uuid.UUID, corrective_action: Optional[str] = None) -> None:
        """Risolve l'alert"""
        self.status = "resolved"
        self.resolved_by = user_id
        self.resolved_at = datetime.utcnow()
        if corrective_action:
            self.corrective_action_taken = corrective_action