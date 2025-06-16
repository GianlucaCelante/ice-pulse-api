# tests/test_organization.py
"""
Test completi per il model Organization.

COME ESEGUIRE:
pytest tests/test_organization.py -v --cov=src/models/organization
"""


import sys
import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import BaseModel
from src.models.organization import Organization, HACCPSettingsSchema

# ==========================================
# SETUP TEST DATABASE
# ==========================================

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def test_engine():
    """Crea engine per test database"""
    # Database in memoria per test veloci
    engine = create_engine("sqlite:///:memory:", echo=False)
    BaseModel.metadata.create_all(engine)
    yield engine

@pytest.fixture
def db_session(test_engine):
    """Crea sessione database per ogni test"""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def sample_organization():
    """Crea un'organizzazione di esempio per i test"""
    return Organization(
        name="Pizza di Mario",
        slug="pizza-di-mario",
        subscription_plan="premium",
        max_sensors=50,
        timezone="Europe/Rome"
    )

# ==========================================
# TEST CREAZIONE E CAMPI BASE
# ==========================================

class TestOrganizationCreation:
    """Test per creazione e campi base"""
    
    def test_create_minimal_organization(self, db_session):
        """Test creazione con campi minimi obbligatori"""
        org = Organization(
            name="Test Company",
            slug="test-company"
        )
        
        db_session.add(org)
        db_session.commit()
        
        # Verifica campi obbligatori
        assert org.id is not None
        assert getattr(org, 'name') == "Test Company"
        assert getattr(org, 'slug') == "test-company"
        
        # Verifica default values
        assert getattr(org, 'subscription_plan') == "free"
        assert getattr(org, 'max_sensors') == 10
        assert getattr(org, 'timezone') == "UTC"
        assert getattr(org, 'retention_months') == 24
        assert getattr(org, 'auto_archive_enabled') == True
        assert getattr(org, 'haccp_settings') is None
        
        # Verifica timestamps
        assert getattr(org, 'created_at') is not None
        assert getattr(org, 'updated_at') is not None
    
    def test_create_full_organization(self, db_session):
        """Test creazione con tutti i campi"""
        org = Organization(
            name="Premium Pizza Co",
            slug="premium-pizza",
            subscription_plan="enterprise",
            max_sensors=100,
            timezone="America/New_York",
            retention_months=36,
            auto_archive_enabled=False
        )
        
        db_session.add(org)
        db_session.commit()
        
        assert getattr(org, 'name') == "Premium Pizza Co"
        assert getattr(org, 'subscription_plan') == "enterprise"
        assert getattr(org, 'max_sensors') == 100
        assert getattr(org, 'timezone') == "America/New_York"
        assert getattr(org, 'retention_months') == 36
        assert getattr(org, 'auto_archive_enabled') == False
    
    def test_slug_uniqueness(self, db_session):
        """Test che lo slug sia univoco"""
        org1 = Organization(name="Company 1", slug="same-slug")
        org2 = Organization(name="Company 2", slug="same-slug")
        
        db_session.add(org1)
        db_session.commit()
        
        db_session.add(org2)
        
        # Dovrebbe sollevare errore per slug duplicato
        with pytest.raises(Exception):  # IntegrityError in produzione
            db_session.commit()

# ==========================================
# TEST BUSINESS LOGIC
# ==========================================

class TestOrganizationBusinessLogic:
    """Test per logica business dell'organizzazione"""
    
    def test_is_premium_method(self):
        """Test metodo is_premium()"""
        
        # Test piani premium
        premium_org = Organization(name="Premium", slug="premium", subscription_plan="premium")
        enterprise_org = Organization(name="Enterprise", slug="enterprise", subscription_plan="enterprise")
        
        assert premium_org.is_premium() == True
        assert enterprise_org.is_premium() == True
        
        # Test piani non premium
        free_org = Organization(name="Free", slug="free", subscription_plan="free")
        basic_org = Organization(name="Basic", slug="basic", subscription_plan="basic")
        
        assert free_org.is_premium() == False
        assert basic_org.is_premium() == False
    
    def test_can_add_sensor_method(self):
        """Test metodo can_add_sensor()"""
        
        org = Organization(name="Test", slug="test", max_sensors=10)
        
        # Test sotto il limite
        assert org.can_add_sensor(5) == True
        assert org.can_add_sensor(9) == True
        
        # Test al limite
        assert org.can_add_sensor(10) == False
        
        # Test sopra il limite
        assert org.can_add_sensor(15) == False
        
        # Test edge case
        assert org.can_add_sensor(0) == True
    
    def test_get_sensors_remaining_method(self):
        """Test metodo get_sensors_remaining()"""
        
        org = Organization(name="Test", slug="test", max_sensors=20)
        
        # Test calcolo corretto
        assert org.get_sensors_remaining(5) == 15
        assert org.get_sensors_remaining(10) == 10
        assert org.get_sensors_remaining(20) == 0
        
        # Test non può essere negativo
        assert org.get_sensors_remaining(25) == 0
        assert org.get_sensors_remaining(30) == 0

# ==========================================
# TEST HACCP SETTINGS
# ==========================================

class TestHACCPSettings:
    """Test per gestione impostazioni HACCP"""
    
    def test_get_haccp_setting_empty(self):
        """Test get_haccp_setting con settings vuoti"""
        
        org = Organization(name="Test", slug="test")
        
        # Settings non inizializzati
        assert org.get_haccp_setting("temperature_max") is None
        assert org.get_haccp_setting("temperature_max", 8.0) == 8.0
        assert org.get_haccp_setting("nonexistent", "default") == "default"
    
    def test_set_and_get_haccp_setting(self, db_session):
        """Test set e get delle impostazioni HACCP"""
        
        org = Organization(name="HACCP Test", slug="haccp-test")
        db_session.add(org)
        db_session.commit()
        
        # Test impostazione singola
        org.set_haccp_setting("temperature_max", 8.0)
        assert org.get_haccp_setting("temperature_max") == 8.0
        
        # Test impostazioni multiple
        org.set_haccp_setting("temperature_min", -20.0)
        org.set_haccp_setting("alert_emails", ["admin@test.com"])
        org.set_haccp_setting("require_verification", True)
        
        db_session.commit()
        
        # Verifica tutte le impostazioni
        assert org.get_haccp_setting("temperature_max") == 8.0
        assert org.get_haccp_setting("temperature_min") == -20.0
        assert org.get_haccp_setting("alert_emails") == ["admin@test.com"]
        assert org.get_haccp_setting("require_verification") == True
        
        # Test get con default per chiavi inesistenti
        assert org.get_haccp_setting("nonexistent", "default") == "default"
    
    def test_get_all_haccp_settings(self):
        """Test get_all_haccp_settings()"""
        
        org = Organization(name="Test", slug="test")
        
        # Test settings vuoti
        assert org.get_all_haccp_settings() == {}
        
        # Test con settings
        org.set_haccp_setting("temp_max", 8.0)
        org.set_haccp_setting("temp_min", -20.0)
        
        all_settings = org.get_all_haccp_settings()
        expected = {"temp_max": 8.0, "temp_min": -20.0}
        assert all_settings == expected
    
    def test_haccp_settings_persistence(self, db_session):
        """Test che le impostazioni HACCP persistano nel database"""
        
        org = Organization(name="Persistence Test", slug="persistence-test")
        org.set_haccp_setting("temperature_max", 5.0)
        org.set_haccp_setting("compliance_standards", ["HACCP", "ISO22000"])
        
        db_session.add(org)
        db_session.commit()
        
        # Ricarica dal database
        org_id = org.id
        db_session.expunge(org)  # Rimuove dalla sessione
        
        loaded_org = db_session.get(Organization, org_id)
        
        # Verifica persistenza
        assert loaded_org.get_haccp_setting("temperature_max") == 5.0
        assert loaded_org.get_haccp_setting("compliance_standards") == ["HACCP", "ISO22000"]

# ==========================================
# TEST VALIDAZIONE
# ==========================================

class TestOrganizationValidation:
    """Test per validazione campi"""
    
    def test_validate_timezone(self):
        """Test validazione timezone"""
        
        org = Organization(name="Test", slug="test")
        
        # Test timezone validi
        assert org.validate_timezone("UTC") == True
        assert org.validate_timezone("Europe/Rome") == True
        assert org.validate_timezone("America/New_York") == True
        
        # Test timezone non validi
        assert org.validate_timezone("Invalid/Timezone") == False
        assert org.validate_timezone("") == False
        assert org.validate_timezone("UTC+5") == False
    
    def test_database_constraints(self, db_session):
        """Test constraint del database"""
        
        # Test max_sensors > 0
        with pytest.raises(Exception):
            org = Organization(name="Test", slug="test-negative", max_sensors=-5)
            db_session.add(org)
            db_session.commit()
        
        # Test retention_months >= 6  
        with pytest.raises(Exception):
            org = Organization(name="Test", slug="test-retention", retention_months=3)
            db_session.add(org)
            db_session.commit()

# ==========================================
# TEST SERIALIZATION
# ==========================================

class TestOrganizationSerialization:
    """Test per conversione in dizionario"""
    
    def test_to_dict_basic(self, sample_organization):
        """Test to_dict() base"""
        
        org_dict = sample_organization.to_dict()
        
        # Verifica campi base
        assert org_dict['name'] == "Pizza di Mario"
        assert org_dict['slug'] == "pizza-di-mario"
        assert org_dict['subscription_plan'] == "premium"
        assert org_dict['max_sensors'] == 50
        assert org_dict['timezone'] == "Europe/Rome"
        
        # Verifica campi calcolati
        assert org_dict['is_premium'] == True
        
        # Verifica presenza campi
        assert 'id' in org_dict
        assert 'created_at' in org_dict
        assert 'updated_at' in org_dict
    
    def test_to_dict_with_haccp_settings(self):
        """Test to_dict() con impostazioni HACCP"""
        
        org = Organization(name="HACCP Test", slug="haccp-test")
        org.set_haccp_setting("temperature_max", 8.0)
        org.set_haccp_setting("alert_emails", ["test@example.com"])
        
        org_dict = org.to_dict()
        
        expected_haccp = {
            "temperature_max": 8.0,
            "alert_emails": ["test@example.com"]
        }
        
        assert org_dict['haccp_settings'] == expected_haccp
    
    def test_to_dict_without_relationships(self, sample_organization):
        """Test to_dict() senza relationships"""
        
        org_dict = sample_organization.to_dict(include_relationships=False)
        assert 'users' not in org_dict
    
    def test_to_dict_with_relationships(self, sample_organization):
        """Test to_dict() con relationships"""
        
        org_dict = sample_organization.to_dict(include_relationships=True)
        assert 'users' in org_dict
        assert org_dict['users'] == []  # Lista vuota perché non ci sono utenti

# ==========================================
# TEST STRING REPRESENTATION
# ==========================================

class TestOrganizationStringMethods:
    """Test per metodi __str__ e __repr__"""
    
    def test_str_method(self):
        """Test metodo __str__"""
        
        org = Organization(name="Test Company", slug="test")
        assert str(org) == "Test Company"
        
        # Test con nome None (edge case)
        org_no_name = Organization(slug="test")
        # Il comportamento dipende da come gestiamo None nel __str__
        str_result = str(org_no_name)
        assert isinstance(str_result, str)  # Deve essere sempre stringa
    
    def test_repr_method(self):
        """Test metodo __repr__"""
        
        org = Organization(name="Test Company", slug="test-company")
        repr_str = repr(org)
        
        assert "Organization" in repr_str
        assert "Test Company" in repr_str or str(org.id) in repr_str

# ==========================================
# TEST HACCP SETTINGS SCHEMA
# ==========================================

class TestHACCPSettingsSchema:
    """Test per schema HACCP settings"""
    
    def test_default_settings(self):
        """Test impostazioni default"""
        
        defaults = HACCPSettingsSchema.get_default_settings()
        
        # Verifica presenza campi essenziali
        assert 'temperature_min' in defaults
        assert 'temperature_max' in defaults
        assert 'humidity_min' in defaults
        assert 'humidity_max' in defaults
        assert 'alert_delay_minutes' in defaults
        
        # Verifica tipi
        assert isinstance(defaults['temperature_min'], (int, float))
        assert isinstance(defaults['temperature_max'], (int, float))
        assert isinstance(defaults['alert_delay_minutes'], int)
        assert isinstance(defaults['notification_emails'], list)
    
    def test_apply_default_settings(self):
        """Test applicazione impostazioni default"""
        
        org = Organization(name="Default Test", slug="default-test")
        defaults = HACCPSettingsSchema.get_default_settings()
        
        # Applica tutte le impostazioni default
        for key, value in defaults.items():
            org.set_haccp_setting(key, value)
        
        # Verifica applicazione
        assert org.get_haccp_setting("temperature_min") == defaults["temperature_min"]
        assert org.get_haccp_setting("require_manual_verification") == defaults["require_manual_verification"]

# ==========================================
# TEST EDGE CASES
# ==========================================

class TestOrganizationEdgeCases:
    """Test per casi limite e errori"""
    
    def test_none_values(self):
        """Test gestione valori None"""
        
        org = Organization(name="None Test", slug="none-test")
        
        # Test get_haccp_setting con None
        assert org.get_haccp_setting("nonexistent") is None
        assert org.get_haccp_setting("nonexistent", "default") == "default"
        
        # Test metodi con valori None
        assert org.get_all_haccp_settings() == {}
    
    def test_empty_string_values(self):
        """Test gestione stringhe vuote"""
        
        # Test timezone validation con stringa vuota
        org = Organization(name="Empty Test", slug="empty-test")
        assert org.validate_timezone("") == False
    
    def test_invalid_sensor_counts(self):
        """Test con numeri sensori non validi"""
        
        org = Organization(name="Test", slug="test", max_sensors=10)
        
        # Test con numeri negativi
        assert org.can_add_sensor(-5) == True  # Negative count è comunque < max
        assert org.get_sensors_remaining(-5) == 15  # max - (-5) = 15, ma limitato a 0?
        
        # Test con numeri molto grandi
        assert org.can_add_sensor(1000000) == False
        assert org.get_sensors_remaining(1000000) == 0

# ==========================================
# PERFORMANCE TESTS (opzionali)
# ==========================================

@pytest.mark.performance
class TestOrganizationPerformance:
    """Test performance (esegui solo quando necessario)"""
    
    def test_bulk_haccp_settings(self):
        """Test performance con molte impostazioni HACCP"""
        
        org = Organization(name="Performance Test", slug="perf-test")
        
        # Imposta 100 settings
        import time
        start = time.time()
        
        for i in range(100):
            org.set_haccp_setting(f"setting_{i}", f"value_{i}")
        
        end = time.time()
        
        # Deve essere veloce (< 1 secondo)
        assert (end - start) < 1.0
        
        # Verifica che tutto sia stato impostato
        assert org.get_haccp_setting("setting_0") == "value_0"
        assert org.get_haccp_setting("setting_99") == "value_99"

# ==========================================
# INTEGRATION TESTS
# ==========================================

class TestOrganizationIntegration:
    """Test integrazione con database reale"""
    
    def test_full_crud_cycle(self, db_session):
        """Test completo Create-Read-Update-Delete"""
        
        # CREATE
        org = Organization(
            name="CRUD Test Company",
            slug="crud-test",
            subscription_plan="basic"
        )
        org.set_haccp_setting("temperature_max", 6.0)
        
        db_session.add(org)
        db_session.commit()
        org_id = org.id
        
        # READ
        loaded_org = db_session.get(Organization, org_id)
        assert loaded_org is not None
        assert getattr(loaded_org, 'name') == "CRUD Test Company"
        assert loaded_org.get_haccp_setting("temperature_max") == 6.0
        
        # UPDATE
        loaded_org.set_haccp_setting("temperature_max", 8.0)
        # Usa update_from_dict se disponibile nella BaseModel
        # loaded_org.update_from_dict({"subscription_plan": "premium"})
        db_session.commit()
        
        # Verifica update
        db_session.refresh(loaded_org)
        assert loaded_org.get_haccp_setting("temperature_max") == 8.0
        
        # DELETE
        db_session.delete(loaded_org)
        db_session.commit()
        
        # Verifica delete
        deleted_org = db_session.get(Organization, org_id)
        assert deleted_org is None

if __name__ == "__main__":
    # Esegui test se file chiamato direttamente
    pytest.main([__file__, "-v"])