# test/test_organization_simple.py
"""
Test semplificati per Organization model.
Metti questo file direttamente in test/ (non in sottocartelle).
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Gli import dovrebbero funzionare ora con conftest.py
from src.models.base import BaseModel
from src.models.organization import Organization, HACCPSettingsSchema

# ==========================================
# TEST BASE
# ==========================================

def test_organization_creation():
    """Test creazione organizzazione"""
    org = Organization(
        name="Test Company",
        slug="test-company"
    )
    
    # Verifica campi base
    assert getattr(org, 'name') == "Test Company"
    assert getattr(org, 'slug') == "test-company"
    
    # Verifica default values
    assert getattr(org, 'subscription_plan') == "free"
    assert getattr(org, 'max_sensors') == 10
    assert getattr(org, 'timezone') == "UTC"

def test_organization_is_premium():
    """Test metodo is_premium()"""
    
    # Test premium
    premium_org = Organization(name="Premium", slug="premium", subscription_plan="premium")
    assert premium_org.is_premium() == True
    
    # Test free
    free_org = Organization(name="Free", slug="free", subscription_plan="free")
    assert free_org.is_premium() == False

def test_organization_can_add_sensor():
    """Test metodo can_add_sensor()"""
    
    org = Organization(name="Test", slug="test", max_sensors=10)
    
    # Test sotto il limite
    assert org.can_add_sensor(5) == True
    assert org.can_add_sensor(9) == True
    
    # Test al limite e sopra
    assert org.can_add_sensor(10) == False
    assert org.can_add_sensor(15) == False

def test_haccp_settings():
    """Test gestione impostazioni HACCP"""
    
    org = Organization(name="HACCP Test", slug="haccp-test")
    
    # Test get vuoto
    assert org.get_haccp_setting("temperature_max") is None
    assert org.get_haccp_setting("temperature_max", 8.0) == 8.0
    
    # Test set/get
    org.set_haccp_setting("temperature_max", 5.0)
    org.set_haccp_setting("alert_emails", ["admin@test.com"])
    
    assert org.get_haccp_setting("temperature_max") == 5.0
    assert org.get_haccp_setting("alert_emails") == ["admin@test.com"]
    
    # Test get_all
    all_settings = org.get_all_haccp_settings()
    assert "temperature_max" in all_settings
    assert "alert_emails" in all_settings

def test_organization_to_dict():
    """Test serialization to_dict()"""
    
    org = Organization(
        name="Dict Test",
        slug="dict-test",
        subscription_plan="enterprise"
    )
    
    org_dict = org.to_dict()
    
    assert org_dict['name'] == "Dict Test"
    assert org_dict['slug'] == "dict-test"
    assert org_dict['subscription_plan'] == "enterprise"
    assert org_dict['is_premium'] == True
    assert 'id' in org_dict

def test_organization_str():
    """Test metodo __str__"""
    
    org = Organization(name="String Test", slug="string-test")
    assert str(org) == "String Test"

# ==========================================
# TEST CON DATABASE
# ==========================================

def test_organization_database_persistence(db_session):
    """Test persistenza nel database"""
    
    org = Organization(
        name="DB Test Company",
        slug="db-test",
        subscription_plan="premium"
    )
    
    # Aggiungi impostazioni HACCP
    org.set_haccp_setting("temperature_max", 8.0)
    org.set_haccp_setting("compliance_standards", ["HACCP", "ISO22000"])
    
    # Salva nel database
    db_session.add(org)
    db_session.commit()
    
    # Verifica che sia stato salvato
    assert org.id is not None
    assert getattr(org, 'created_at') is not None
    assert getattr(org, 'updated_at') is not None
    
    # Ricarica dal database
    org_id = org.id
    loaded_org = db_session.get(Organization, org_id)
    
    assert loaded_org is not None
    assert getattr(loaded_org, 'name') == "DB Test Company"
    assert getattr(loaded_org, 'subscription_plan') == "premium"
    
    # Verifica persistenza HACCP settings
    assert loaded_org.get_haccp_setting("temperature_max") == 8.0
    assert loaded_org.get_haccp_setting("compliance_standards") == ["HACCP", "ISO22000"]

def test_organization_update(db_session):
    """Test aggiornamento organizzazione"""
    
    org = Organization(name="Update Test", slug="update-test")
    db_session.add(org)
    db_session.commit()
    
    # Update values (simulando getattr per accesso sicuro)
    org.name = "Updated Name"
    org.subscription_plan = "premium"
    org.set_haccp_setting("new_setting", "new_value")
    
    db_session.commit()
    
    # Verifica update
    db_session.refresh(org)
    assert getattr(org, 'name') == "Updated Name"
    assert getattr(org, 'subscription_plan') == "premium"
    assert org.get_haccp_setting("new_setting") == "new_value"

# ==========================================
# TEST HACCP SETTINGS SCHEMA
# ==========================================

def test_haccp_settings_schema():
    """Test schema HACCP settings"""
    
    defaults = HACCPSettingsSchema.get_default_settings()
    
    # Verifica presenza campi essenziali
    assert 'temperature_min' in defaults
    assert 'temperature_max' in defaults
    assert 'humidity_min' in defaults
    assert 'humidity_max' in defaults
    
    # Verifica tipi
    assert isinstance(defaults['temperature_min'], (int, float))
    assert isinstance(defaults['alert_delay_minutes'], int)
    assert isinstance(defaults['notification_emails'], list)

def test_apply_default_haccp_settings():
    """Test applicazione impostazioni HACCP default"""
    
    org = Organization(name="Default HACCP", slug="default-haccp")
    defaults = HACCPSettingsSchema.get_default_settings()
    
    # Applica settings default
    for key, value in defaults.items():
        org.set_haccp_setting(key, value)
    
    # Verifica applicazione
    assert org.get_haccp_setting("temperature_min") == defaults["temperature_min"]
    assert org.get_haccp_setting("require_manual_verification") == defaults["require_manual_verification"]

# ==========================================
# TEST EDGE CASES
# ==========================================

def test_organization_edge_cases():
    """Test casi limite"""
    
    org = Organization(name="Edge Test", slug="edge-test", max_sensors=5)
    
    # Test numeri negativi
    assert org.can_add_sensor(-1) == True  # Negative < max
    assert org.get_sensors_remaining(-1) == 6  # 5 - (-1) = 6
    
    # Test zero
    assert org.can_add_sensor(0) == True
    assert org.get_sensors_remaining(0) == 5
    
    # Test esatto al limite
    assert org.can_add_sensor(5) == False
    assert org.get_sensors_remaining(5) == 0
    
    # Test over limit
    assert org.get_sensors_remaining(10) == 0  # Non può essere negativo

if __name__ == "__main__":
    print("Esegui con: pytest test/test_organization_simple.py -v")