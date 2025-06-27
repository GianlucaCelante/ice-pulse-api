# =====================================================
# src/models/sensor.py - SQLAlchemy 2.0
# =====================================================
from sqlalchemy import String, Integer, DECIMAL, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .location import Location
    from .reading import Reading
    from .alert import Alert
    from .calibration import Calibration

class Sensor(BaseModel):
    """
    Sensor model - dispositivi IoT per monitoraggio.
    
    Gestisce i dispositivi fisici, configurazioni, stato online/offline,
    e tracciamento calibrazioni HACCP.
    """
    
    __tablename__ = "sensors"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="sensors"
    )
    
    location: Mapped[Optional["Location"]] = relationship(
        "Location",
        back_populates="sensors"
    )
    
    readings: Mapped[List["Reading"]] = relationship(
        "Reading",
        back_populates="sensor",
        cascade="all, delete-orphan"
    )
    
    alerts: Mapped[List["Alert"]] = relationship(
        "Alert",
        back_populates="sensor",
        cascade="all, delete-orphan"
    )
    
    calibrations: Mapped[List["Calibration"]] = relationship(
        "Calibration",
        back_populates="sensor",
        cascade="all, delete-orphan"
    )
    
    # ==========================================
    # DEVICE IDENTIFICATION
    # ==========================================
    
    device_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    sensor_type: Mapped[str] = mapped_column(String(30), default="temperature_humidity")
    status: Mapped[str] = mapped_column(String(20), default="offline", index=True)
    
    # ==========================================
    # HARDWARE INFO
    # ==========================================
    
    mac_address: Mapped[Optional[str]] = mapped_column(String(17), nullable=True, index=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hardware_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    battery_level: Mapped[int] = mapped_column(Integer, default=100)  # 0-100%
    
    # ==========================================
    # CONFIGURATION
    # ==========================================
    
    reading_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)  # 5 min
    alert_thresholds: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True
    )
    
    # ==========================================
    # COMMUNICATION TRACKING
    # ==========================================
    
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    last_reading_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    
    # ==========================================
    # HACCP CALIBRATION
    # ==========================================
    
    last_calibration_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    calibration_due_date: Mapped[Optional[date]] = mapped_column(nullable=True, index=True)
    accuracy_specification: Mapped[float] = mapped_column(DECIMAL(3,2), default=0.5)  # ±0.5°C
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "sensor_type IN ('temperature_humidity', 'temperature_pressure', 'multi_sensor')",
            name='chk_sensor_type_valid'
        ),
        CheckConstraint(
            "status IN ('online', 'offline', 'warning', 'error', 'maintenance')",
            name='chk_sensor_status_valid'
        ),
        CheckConstraint('battery_level >= 0 AND battery_level <= 100', name='chk_battery_level_valid'),
        CheckConstraint('reading_interval_seconds > 0', name='chk_reading_interval_positive'),
        CheckConstraint('accuracy_specification > 0', name='chk_accuracy_positive'),
        CheckConstraint(
            "mac_address IS NULL OR mac_address ~ '^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'",
            name='chk_mac_address_format'
        ),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Sensor(device_id={self.device_id}, name={self.name})"
    
    @property
    def is_online(self) -> bool:
        """Verifica se sensore è online (visto negli ultimi 15 min)"""
        if not self.last_seen_at:
            return False
        threshold = datetime.utcnow() - timedelta(minutes=15)
        return self.last_seen_at > threshold
    
    @property
    def is_calibration_due(self) -> bool:
        """Verifica se calibrazione è in scadenza (prossimi 30 giorni)"""
        if not self.calibration_due_date:
            return True  # Se non c'è data, assume necessaria
        warning_threshold = date.today() + timedelta(days=30)
        return self.calibration_due_date <= warning_threshold
    
    @property
    def location_name(self) -> Optional[str]:
        """Nome della location dove si trova il sensore"""
        return self.location.name if self.location else None
    
    def get_alert_threshold(self, measurement_type: str) -> Optional[Dict[str, float]]:
        """Ottiene soglie allarme per tipo misurazione"""
        if not self.alert_thresholds:
            return None
        return self.alert_thresholds.get(measurement_type)
    
    def set_alert_threshold(self, measurement_type: str, min_val: Optional[float], max_val: Optional[float]):
        """Imposta soglie allarme"""
        if not self.alert_thresholds:
            self.alert_thresholds = {}
        
        threshold = {}
        if min_val is not None:
            threshold['min'] = min_val
        if max_val is not None:
            threshold['max'] = max_val
        
        self.alert_thresholds[measurement_type] = threshold
