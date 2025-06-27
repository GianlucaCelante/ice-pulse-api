# =====================================================
# src/models/location.py - SQLAlchemy 2.0
# =====================================================
from sqlalchemy import String, Text, DECIMAL, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from typing import List, Dict, Any, Optional
import uuid

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .sensor import Sensor

class Location(BaseModel):
    """
    Location model - dove sono fisicamente i sensori.
    
    Definisce le zone fisiche (freezer, fridge, etc.) con le loro
    soglie di temperatura/umidità specifiche.
    """
    
    __tablename__ = "locations"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="locations"
    )
    
    sensors: Mapped[List["Sensor"]] = relationship(
        "Sensor",
        back_populates="location",
        cascade="all, delete-orphan"
    )
    
    # ==========================================
    # BASIC INFO
    # ==========================================
    
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_type: Mapped[str] = mapped_column(String(20))  # freezer, fridge, etc.
    
    # ==========================================
    # TEMPERATURE/HUMIDITY THRESHOLDS
    # ==========================================
    
    temperature_min: Mapped[Optional[float]] = mapped_column(DECIMAL(5,2), nullable=True)
    temperature_max: Mapped[Optional[float]] = mapped_column(DECIMAL(5,2), nullable=True)
    humidity_min: Mapped[Optional[float]] = mapped_column(DECIMAL(5,2), nullable=True)
    humidity_max: Mapped[Optional[float]] = mapped_column(DECIMAL(5,2), nullable=True)
    
    # ==========================================
    # PHYSICAL LOCATION INFO
    # ==========================================
    
    floor: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coordinates: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB()),
        nullable=True
    )  # {"lat": 45.123, "lng": 12.456}
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint(
            "location_type IN ('freezer', 'fridge', 'cold_room', 'outdoor', 'kitchen', 'storage')",
            name='chk_location_type_valid'
        ),
        CheckConstraint(
            'temperature_min IS NULL OR temperature_max IS NULL OR temperature_min < temperature_max',
            name='chk_temperature_range_valid'
        ),
        CheckConstraint(
            "coordinates IS NULL OR (coordinates ? 'lat' AND coordinates ? 'lng')",
            name='chk_coordinates_structure'
        ),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Location(name={self.name}, type={self.location_type})"
    
    @property
    def sensor_count(self) -> int:
        """Numero di sensori in questa location"""
        return len(self.sensors) if self.sensors else 0
    
    def is_temperature_valid(self, temp: float) -> bool:
        """Verifica se temperatura è nei range validi"""
        if self.temperature_min is not None and temp < float(self.temperature_min):
            return False
        if self.temperature_max is not None and temp > float(self.temperature_max):
            return False
        return True
    
    def is_humidity_valid(self, humidity: float) -> bool:
        """Verifica se umidità è nei range validi"""
        if self.humidity_min is not None and humidity < float(self.humidity_min):
            return False
        if self.humidity_max is not None and humidity > float(self.humidity_max):
            return False
        return True
    
    def get_temperature_range(self) -> Dict[str, Optional[float]]:
        """Range temperature per questa location"""
        return {
            "min": float(self.temperature_min) if self.temperature_min else None,
            "max": float(self.temperature_max) if self.temperature_max else None
        }