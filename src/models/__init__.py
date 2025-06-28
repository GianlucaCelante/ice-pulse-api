# =====================================================
# src/models/__init__.py
# =====================================================
"""
Models package initialization.

Import all models to ensure they are registered with SQLAlchemy metadata.
This is CRITICAL for foreign key resolution during create_all() operations.

IMPORTANT: Every time you add a new model, import it here!
"""

# Base model MUST be imported first
from .base import BaseModel

# Core business models (order matters for foreign keys)
from .organization import Organization
from .location import Location
from .sensor import Sensor
from .reading import Reading
from .audit_log import AuditLog
from .report import Report
from .calibration import Calibration
from .alert import Alert
from .user import User
from .env_config import EnvConfig

# Additional models (import as they are created)
# Uncomment these as you create the corresponding model files:
# from .user import User
# from .alert import Alert
# from .calibration import Calibration

# Export all models for easy importing
__all__ = [
    # Base
    "BaseModel",
    
    # Core models
    "Organization",
    "Location", 
    "Sensor",
    "Reading",
    "AuditLog",
    "Report",
    
    # Additional models (uncomment as needed)
     "User",
     "Alert", 
     "Calibration",
     "EnvConfig",
    

]

# Model registration verification
def verify_models_registered():
    """
    Utility function to verify all models are properly registered
    with SQLAlchemy metadata. Useful for debugging.
    """
    tables = BaseModel.metadata.tables
    print(f"📊 Registered tables: {len(tables)}")
    for table_name in sorted(tables.keys()):
        print(f"  - {table_name}")
    return len(tables)

# Optional: Auto-verify on import (comment out in production)
if __name__ != "__main__":
    # Only run verification if not being executed directly
    import os
    if os.getenv("DEBUG_MODELS", "false").lower() == "true":
        verify_models_registered()