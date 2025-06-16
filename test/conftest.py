# test/conftest.py
"""
Configurazione globale per tutti i test.
Questo file viene caricato automaticamente da pytest.
"""

import sys
import os
from pathlib import Path

# Aggiungi src al PYTHONPATH per tutti i test
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import dopo aver fixato il path
from src.models.base import BaseModel

# ==========================================
# FIXTURES GLOBALI (disponibili per tutti i test)
# ==========================================

@pytest.fixture(scope="session")
def test_engine():
    """Engine database per tutti i test della sessione"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    BaseModel.metadata.create_all(engine)
    yield engine

@pytest.fixture
def db_session(test_engine):
    """Sessione database per ogni test (auto-rollback)"""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_organization():
    """Organizzazione di esempio per i test"""
    from src.models.organization import Organization
    return Organization(
        name="Test Company",
        slug="test-company",
        subscription_plan="premium",
        max_sensors=50,
        timezone="Europe/Rome"
    )