# =====================================================
# src/schemas/audit_log.py - Complete Pydantic Schemas
# =====================================================
from pydantic import BaseModel, Field, validator, computed_field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

class AuditLogCreate(BaseModel):
    """Schema for creating audit log entries"""
    organization_id: Optional[uuid.UUID] = Field(None, description="Organization ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID performing action")
    action: str = Field(..., min_length=1, max_length=100, description="Action performed")
    resource_type: Optional[str] = Field(None, max_length=50, description="Type of resource affected")
    resource_id: Optional[uuid.UUID] = Field(None, description="ID of resource affected")
    old_values: Optional[Dict[str, Any]] = Field(None, description="Previous values")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values")
    description: Optional[str] = Field(None, description="Human readable description")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    haccp_relevant: bool = Field(default=False, description="Is this HACCP relevant")

class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs"""
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[uuid.UUID] = None
    haccp_relevant: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_term: Optional[str] = Field(None, description="Search in action or description")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('End date must be after start date')
        return v

class AuditLogResponse(BaseModel):
    """Schema for audit log API responses"""
    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    user_id: Optional[uuid.UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[uuid.UUID]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    description: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    haccp_relevant: bool
    created_at: datetime

    # Computed fields
    @computed_field
    @property
    def user_display_name(self) -> str:
        # Populated by service layer
        return getattr(self, '_user_display_name', "Sistema" if self.user_id is None else "Utente sconosciuto")
    
    @computed_field
    @property
    def organization_name(self) -> str:
        # Populated by service layer
        return getattr(self, '_organization_name', "N/A")
    
    @computed_field
    @property
    def has_changes(self) -> bool:
        return self.old_values is not None or self.new_values is not None
    
    @computed_field
    @property
    def changed_fields(self) -> List[str]:
        # Populated by service layer
        return getattr(self, '_changed_fields', [])
    
    @computed_field
    @property
    def change_summary(self) -> str:
        if self.description:
            return self.description
        changed_fields = self.changed_fields
        if not changed_fields:
            return f"Azione: {self.action}"
        return f"Modificati: {', '.join(changed_fields)}"

    class Config:
        from_attributes = True

class AuditLogSummary(BaseModel):
    """Summary schema for audit log listings"""
    id: uuid.UUID
    action: str
    resource_type: Optional[str]
    user_display_name: str
    organization_name: str
    haccp_relevant: bool
    change_summary: str
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogStats(BaseModel):
    """Schema for audit log statistics"""
    organization_id: Optional[uuid.UUID]
    period_start: datetime
    period_end: datetime
    total_events: int
    haccp_relevant_events: int
    user_actions: int
    system_actions: int
    most_frequent_actions: List[Dict[str, Any]]
    users_activity: List[Dict[str, Any]]