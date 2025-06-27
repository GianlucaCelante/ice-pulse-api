
# =====================================================
# src/models/report.py - SIMPLIFIED with AUTO-SCHEDULING
# =====================================================
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, CheckConstraint, Date, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.mutable import MutableDict
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
import uuid
import enum

from .base import BaseModel

# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .organization import Organization
    from .user import User

class ReportType(enum.Enum):
    """Tipi di report supportati"""
    HACCP_MONTHLY = "haccp_monthly"
    TEMPERATURE_SUMMARY = "temperature_summary"
    SENSOR_STATUS = "sensor_status"
    ALERT_SUMMARY = "alert_summary"

class ReportStatus(enum.Enum):
    """Stati del report"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class ScheduleFrequency(enum.Enum):
    """Frequenze di scheduling supportate"""
    MANUAL = "manual"          # No auto-generation
    WEEKLY = "weekly"          # Ogni settimana
    MONTHLY = "monthly"        # Primo del mese

class Report(BaseModel):
    """
    Report model - gestisce sia report manuali che automatici.
    
    DESIGN SEMPLIFICATO:
    - Una tabella fa tutto (manuale + scheduling)
    - Frequenze semplici (weekly/monthly)
    - Auto-generation tramite cron job
    """
    
    __tablename__ = "reports"
    
    # ==========================================
    # FOREIGN KEYS & RELATIONSHIPS
    # ==========================================
    
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True
    )
    
    generated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped[Optional["User"]] = relationship("User")
    
    # ==========================================
    # REPORT IDENTIFICATION
    # ==========================================
    
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType), index=True)
    report_name: Mapped[str] = mapped_column(String(200))
    
    # ==========================================
    # REPORT PERIOD
    # ==========================================
    
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    
    # ==========================================
    # REPORT STATUS & DATA
    # ==========================================
    
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.PENDING, index=True)
    generation_started_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    generation_completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    generation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Dati del report (JSON)
    report_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True
    )
    
    # File path se salvato come PDF/Excel
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # ==========================================
    # AUTO-SCHEDULING (Simple approach)
    # ==========================================
    
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    schedule_frequency: Mapped[ScheduleFrequency] = mapped_column(
        Enum(ScheduleFrequency), 
        default=ScheduleFrequency.MANUAL,
        index=True
    )
    
    # Per scheduling automatico
    next_generation_date: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    is_active_schedule: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Configurazione per auto-generation
    auto_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        MutableDict.as_mutable(JSONB),
        nullable=True
    )  # {"email_recipients": ["admin@company.com"], "include_charts": true}
    
    # ==========================================
    # CONSTRAINTS
    # ==========================================
    
    __table_args__ = (
        CheckConstraint('period_start <= period_end', name='chk_report_period_valid'),
        CheckConstraint('file_size_bytes >= 0', name='chk_file_size_positive'),
    )
    
    # ==========================================
    # BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        return f"Report(type={self.report_type.value}, period={self.period_start}-{self.period_end})"
    
    @property
    def is_completed(self) -> bool:
        return self.status == ReportStatus.COMPLETED
    
    @property
    def is_scheduled_report(self) -> bool:
        return self.schedule_frequency != ScheduleFrequency.MANUAL
    
    @property
    def is_due_for_generation(self) -> bool:
        """Verifica se è il momento di generare il report automatico"""
        if not self.is_active_schedule or not self.next_generation_date:
            return False
        return datetime.utcnow() >= self.next_generation_date
    
    def calculate_next_generation_date(self) -> Optional[datetime]:
        """Calcola la prossima data di generazione"""
        if self.schedule_frequency == ScheduleFrequency.MANUAL:
            return None
        
        now = datetime.utcnow()
        
        if self.schedule_frequency == ScheduleFrequency.WEEKLY:
            # Ogni lunedì alle 8:00
            days_ahead = 0 - now.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            next_date = now + timedelta(days=days_ahead)
            return next_date.replace(hour=8, minute=0, second=0, microsecond=0)
        
        elif self.schedule_frequency == ScheduleFrequency.MONTHLY:
            # Primo del mese alle 8:00
            if now.day == 1 and now.hour < 8:
                # È il primo del mese ma prima delle 8
                return now.replace(hour=8, minute=0, second=0, microsecond=0)
            else:
                # Prossimo primo del mese
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                return next_month.replace(hour=8, minute=0, second=0, microsecond=0)
        
        return None
    
    def setup_auto_generation(self, frequency: ScheduleFrequency, config: Optional[Dict[str, Any]] = None):
        """Configura la generazione automatica"""
        self.schedule_frequency = frequency
        self.is_active_schedule = True
        self.auto_config = config or {}
        self.next_generation_date = self.calculate_next_generation_date()
    
    def update_next_generation_date(self):
        """Aggiorna la prossima data dopo generazione"""
        self.next_generation_date = self.calculate_next_generation_date()
