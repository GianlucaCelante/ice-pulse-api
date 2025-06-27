# =====================================================
# src/repositories/base_repository.py - Generic CRUD Repository
# =====================================================
from typing import Generic, TypeVar, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
import uuid

from src.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    """
    Base repository con CRUD operations generiche.
    
    PATTERN: Repository centralizza data access logic
    - Evita query duplicate nel codebase
    - Single source of truth per data operations
    - Facilita testing e mocking
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    # ==========================================
    # BASIC CRUD OPERATIONS
    # ==========================================
    
    def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create new record"""
        db_obj = self.model(**obj_data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        """Get record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_by_ids(self, ids: List[uuid.UUID]) -> List[ModelType]:
        """Get multiple records by IDs"""
        return self.db.query(self.model).filter(self.model.id.in_(ids)).all()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def update(self, id: uuid.UUID, update_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update record by ID"""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: uuid.UUID) -> bool:
        """Delete record by ID"""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return False
        
        self.db.delete(db_obj)
        self.db.commit()
        return True
    
    def count(self) -> int:
        """Count total records"""
        return self.db.query(self.model).count()
    
    def exists(self, id: uuid.UUID) -> bool:
        """Check if record exists"""
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
