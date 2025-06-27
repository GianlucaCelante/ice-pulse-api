# =====================================================
# src/models/reading.py - SQLAlchemy 2.0 (Partitioned Table)
# =====================================================
from sqlalchemy import String, DECIMAL, Integer, Boolean, ForeignKey, CheckConstraint
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
    from .alert import Alert

class Reading(BaseModel):
    """
    Reading model - dati sensori (tabella partitioned per performance).
    
    NOTA: Questa tabella è partizionata per mese nel database PostgreSQL.
    Contiene tutti i dati di temperatura/umidità con metadati HACCP.
    """
    
    __tablename__ = "readings"
    
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
    
    alert_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True
    )
    
    organization: Mapped["Organization"] = relationship("Organization")
    sensor: Mapped["Sensor"] = relationship("Sensor", back_populates="readings")
    alert: Mapped[Optional["Alert"]] = relationship("Alert")
    
    # ==========================================
    # TIMESTAMP (PARTITION KEY)
    # ==========================================
    
    timestamp: Mapped[datetime] = mapped_column(index=True)  # Partition key
    
    # ==========================================
    # SENSOR MEASUREMENTS
    # ==========================================
    
    temperature: Mapped[Optional[float]] = mapped_column(DECIMAL(6,3), nullable=True)  # -40.000 to 999.999
    humidity: Mapped[Optional[float]] = mapped_column(DECIMAL(5,2), nullable=True)     # 0.00 to 100.00
    pressure: Mapped[Optional[float]] = mapped_column(DECIMAL(7,2), nullable=True)     # Pressure in mbar
    battery_voltage: Mapped[Optional[float]] = mapped_column(DECIMAL(4,3), nullable=True)  # Battery voltage
    
    # ==========================================
    # DATA QUALITY
    # ==========================================
    
    rssi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Signal strength
    data_quality_score: Mapped[Optional[float]] = mapped_column(DECIMAL(3,2), nullable=True)  # 0.00-1.00
    is_manual_entry: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================
    # HACCP COMPLIANCE FIELDS
    # ==========================================
    
    temperature_deviation: Mapped[bool] = mapped_column(Boolean, default=False)
    humidity_deviation: Mapped[bool] = mapped_column(Boolean, default=False)
    deviation_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    corrective_action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    haccp_compliance_status: Mapped[str] = mapped_column(String(20), default="compliant")
    
    # ==========================================
    # ALERT CORRELATION
    # ==========================================
    
    alert_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "haccp_compliance_status IN ('compliant', 'deviation', 'critical_deviation', 'manual_override')",
            name='chk_haccp_compliance_status_valid'
        ),
        CheckConstraint('temperature IS NULL OR temperature BETWEEN -40 AND 100', name='chk_temperature_range'),
        CheckConstraint('humidity IS NULL OR humidity BETWEEN 0 AND 100', name='chk_humidity_range'),
        CheckConstraint('data_quality_score IS NULL OR data_quality_score BETWEEN 0 AND 1', name='chk_quality_score_range'),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Reading(sensor={self.sensor_id}, temp={self.temperature}, time={self.timestamp})"
    
    @property
    def is_compliant(self) -> bool:
        """Verifica se reading è HACCP compliant"""
        return self.haccp_compliance_status == "compliant"
    
    @property
    def has_deviation(self) -> bool:
        """Verifica se ha deviazioni di temperatura/umidità"""
        return self.deviation_detected
    
    @property
    def requires_action(self) -> bool:
        """Verifica se richiede azione correttiva"""
        return self.corrective_action_required
    
    def mark_deviation(self, deviation_type: str) -> None:
        """Marca una deviazione rilevata"""
        self.deviation_detected = True
        
        if deviation_type == "temperature":
            self.temperature_deviation = True
        elif deviation_type == "humidity":
            self.humidity_deviation = True
        
        # Auto-set compliance status
        if self.haccp_compliance_status == "compliant":
            self.haccp_compliance_status = "deviation"
