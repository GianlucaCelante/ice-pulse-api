# =====================================================
# src/models/calibration.py - SQLAlchemy 2.0
# =====================================================
from sqlalchemy import String, Text, Boolean, DECIMAL, Date, ForeignKey, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, date, timedelta
from typing import Optional
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .sensor import Sensor
    from .user import User

class Calibration(BaseModel):
    """
    Calibration model - tarature sensori per compliance HACCP.
    
    Traccia le calibrazioni dei sensori, certificati tecnici,
    e programmazione calibrazioni future.
    """
    
    __tablename__ = "calibrations"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True
    )
    
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="RESTRICT"),
        index=True
    )
    
    calibrated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    organization: Mapped["Organization"] = relationship("Organization")
    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="calibrations")
    technician: Mapped[Optional["User"]] = relationship("User")
    
    # ==========================================
    # CALIBRATION INFO
    # ==========================================
    
    calibration_type: Mapped[str] = mapped_column(String(20))  # routine, corrective, verification
    calibration_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    accuracy_achieved: Mapped[float] = mapped_column(DECIMAL(4,3))  # ±0.123°C
    calibration_passed: Mapped[bool] = mapped_column(Boolean)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ==========================================
    # TECHNICIAN INFO
    # ==========================================
    
    technician_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    technician_certificate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ==========================================
    # REFERENCE EQUIPMENT
    # ==========================================
    
    reference_equipment_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_equipment_serial: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_equipment_cert_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # ==========================================
    # SCHEDULING
    # ==========================================
    
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    calibrated_at: Mapped[datetime] = mapped_column(server_default=func.now())
    next_calibration_due: Mapped[date] = mapped_column(Date)
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "calibration_type IN ('routine', 'corrective', 'verification', 'initial')",
            name='chk_calibration_type_valid'
        ),
        CheckConstraint('accuracy_achieved >= 0', name='chk_accuracy_positive'),
        CheckConstraint('next_calibration_due > calibrated_at::date', name='chk_next_calibration_future'),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Calibration(sensor={self.sensor_id}, type={self.calibration_type}, passed={self.calibration_passed})"
    
    @property
    def is_passed(self) -> bool:
        """Verifica se calibrazione è passata"""
        return self.calibration_passed
    
    @property
    def is_due_soon(self, warning_days: int = 30) -> bool:
        """Verifica se prossima calibrazione è in scadenza"""
        warning_date = date.today() + timedelta(days=warning_days)
        return self.next_calibration_due <= warning_date
    
    @property
    def days_until_due(self) -> int:
        """Giorni rimanenti fino alla prossima calibrazione"""
        delta = self.next_calibration_due - date.today()
        return delta.days
    
    def mark_as_passed(self, accuracy: float, notes: Optional[str] = None) -> None:
        """Marca calibrazione come passata"""
        self.calibration_passed = True
        self.accuracy_achieved = accuracy
        if notes:
            self.notes = notes
    
    def mark_as_failed(self, notes: str) -> None:
        """Marca calibrazione come fallita"""
        self.calibration_passed = False
        self.notes = notes