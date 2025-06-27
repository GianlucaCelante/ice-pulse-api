# =====================================================
# src/models/base.py - COMPLETAMENTE REFACTORED
# =====================================================
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from typing import Dict, Any
import uuid

class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base"""
    pass

class BaseModel(Base):
    """
    Base model per tutti i modelli con SQLAlchemy 2.0 syntax.
    
    NOVITÀ SQLAlchemy 2.0:
    - Mapped[type] invece di Column()
    - mapped_column() con typing completo
    - DeclarativeBase invece di declarative_base()
    """
    
    __abstract__ = True
    
    # Primary key con UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Timestamps automatici
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        """Rappresentazione debug"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per JSON API"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):  # Skip SQLAlchemy internal attrs
                if isinstance(value, uuid.UUID):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result