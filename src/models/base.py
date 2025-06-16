# src/models/base.py
"""
Base model class che tutti gli altri models erediteranno.
FIXED per SQLAlchemy 2.0
"""

# IMPORTS - FIXED per SQLAlchemy 2.0
from sqlalchemy import Column, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base  # ← FIXED: import corretto
import uuid
from datetime import datetime
from typing import Dict, Any

# FIXED: Import corretto per SQLAlchemy 2.0
Base = declarative_base()

class BaseModel(Base):
    """
    Classe base per tutti i models.
    
    COSA FA:
    - Aggiunge automaticamente id, created_at, updated_at a ogni tabella
    - Fornisce metodi comuni come to_dict()
    - Gestisce automaticamente gli UUID come primary key
    """
    
    __abstract__ = True
    
    # PRIMARY KEY: UUID invece di auto-increment integer
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # TIMESTAMPS AUTOMATICI
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        """Rappresentazione per developer"""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte il model in dizionario per API JSON"""
        result = {}
        
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            if value is not None:
                if isinstance(value, uuid.UUID):
                    result[column.name] = str(value)
                elif isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
            else:
                result[column.name] = None
        
        return result
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Aggiorna il model da un dizionario"""
        valid_columns = {column.name for column in self.__table__.columns}
        
        for key, value in data.items():
            if key in valid_columns and key not in ('id', 'created_at'):
                setattr(self, key, value)
    
    @classmethod
    def get_table_name(cls) -> str:
        """Ritorna il nome della tabella"""
        return cls.__tablename__
    
    def is_new(self) -> bool:
        """Verifica se è un record nuovo (non ancora salvato)"""
        return getattr(self, 'created_at', None) is None