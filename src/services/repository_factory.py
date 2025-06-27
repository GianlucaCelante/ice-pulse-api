# =====================================================
# src/services/repository_factory.py - Dependency Injection Helper
# =====================================================
from sqlalchemy.orm import Session
from typing import Type, TypeVar

from ..repositories import OrganizationRepository
from ..repositories import UserRepository
from ..repositories import LocationRepository
from ..repositories import SensorRepository
from ..repositories import AlertRepository
from ..repositories import ReadingRepository
from ..repositories import ReportRepository
from ..repositories import AuditLogRepository
from ..repositories import EnvConfigRepository
from ..repositories import CalibrationRepository

T = TypeVar('T')

class RepositoryFactory:
    """
    Factory per creare repository con dependency injection.
    
    PATTERN: Centralizza creazione repository per easy testing e DI
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    @property
    def organizations(self) -> OrganizationRepository:
        return OrganizationRepository(self.db)
    
    @property
    def users(self) -> UserRepository:
        return UserRepository(self.db)
    
    @property
    def locations(self) -> LocationRepository:
        return LocationRepository(self.db)
    
    @property
    def sensors(self) -> SensorRepository:
        return SensorRepository(self.db)
    
    @property
    def alerts(self) -> AlertRepository:
        return AlertRepository(self.db)
    
    @property
    def readings(self) -> ReadingRepository:
        return ReadingRepository(self.db)
    
    @property
    def reports(self) -> ReportRepository:
        return ReportRepository(self.db)
    
    @property
    def audit_logs(self) -> AuditLogRepository:
        return AuditLogRepository(self.db)
    
    @property
    def env_configs(self) -> EnvConfigRepository:
        return EnvConfigRepository(self.db)
    
    @property
    def calibrations(self) -> CalibrationRepository:
        return CalibrationRepository(self.db)
