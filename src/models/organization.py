# src/models/organization.py
"""
Model Organization per multi-tenancy.

COSA È MULTI-TENANCY?
Immagina un condominio: ogni appartamento (organization) ha i suoi inquilini (users)
e i suoi dati, ma condividono la stessa infrastruttura (database, app).
"""

# IMPORTS
from sqlalchemy import Column, String, Integer, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship, Mapped
from typing import List, Dict, Any, Optional

# Import della nostra base class
from .base import BaseModel

# Import per le relazioni (TYPE_CHECKING per evitare circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User

class Organization(BaseModel):
    """
    Model per le organizzazioni (aziende/clienti).
    
    OGNI ORGANIZZAZIONE HA:
    - I suoi utenti
    - I suoi sensori
    - Le sue impostazioni HACCP
    - I suoi limiti (es: max sensori)
    """
    
    # NOME TABELLA NEL DATABASE
    __tablename__ = "organizations"
    
    # ==========================================
    # CAMPI DELLA TABELLA
    # ==========================================
    
    # INFORMAZIONI BASE
    name = Column(
        String(200),        # Massimo 200 caratteri
        nullable=False      # Obbligatorio (NOT NULL nel database)
    )
    
    slug = Column(
        String(100),        # Es: "pizza-mario" per URL friendly
        nullable=False,
        unique=True,        # UNIQUE constraint nel database
        index=True          # Crea un indice per ricerche veloci
    )
    
    # SPIEGAZIONE SLUG:
    # Un "slug" è una versione URL-friendly del nome
    # "Pizza di Mario" → "pizza-di-mario"
    # Serve per URLs come: app.com/org/pizza-di-mario
    
    # SUBSCRIPTION E LIMITI
    subscription_plan = Column(
        String(20),
        nullable=False,
        default="free"      # Valore di default se non specificato
    )
    
    max_sensors = Column(
        Integer,
        nullable=False,
        default=10          # Piano free: max 10 sensori
    )
    
    # CONFIGURAZIONE
    timezone = Column(
        String(50),
        nullable=False,
        default="UTC"       # Sempre UTC di default, poi convertiremo per UI
    )
    
    # IMPOSTAZIONI HACCP (JSON nel database)
    haccp_settings = Column(
        MutableDict.as_mutable(JSONB),  # JSONB = JSON binario PostgreSQL (più veloce)
        nullable=True                   # Opzionale
    )
    
    # SPIEGAZIONE MutableDict.as_mutable:
    # Normalmente SQLAlchemy non sa quando modifichi un JSON
    # MutableDict "avvisa" SQLAlchemy quando cambi qualcosa dentro al JSON
    # Esempio: org.haccp_settings["temp_max"] = 8.0  ← SQLAlchemy lo rileva
    
    # POLITICHE DI RETENTION
    retention_months = Column(
        Integer,
        nullable=False,
        default=24          # 24 mesi = 2 anni di storico
    )
    
    auto_archive_enabled = Column(
        Boolean,
        nullable=False,
        default=True        # Archiviazione automatica attiva
    )
    
    # ==========================================
    # RELAZIONI CON ALTRE TABELLE
    # ==========================================
    
    # SPIEGAZIONE RELATIONSHIPS:
    # SQLAlchemy crea "collegamenti virtuali" tra tabelle
    # Non esistono fisicamente nel database, ma in Python puoi fare:
    # org.users → lista di tutti gli utenti dell'organizzazione
    
    # ATTENZIONE: Usiamo stringhe per evitare circular imports
    # "User" invece di User perché User potrebbe non essere ancora importato
    
    users: Mapped[List["User"]] = relationship(
        "User",                          # Classe target (come stringa)
        back_populates="organization",   # Campo corrispondente in User
        cascade="all, delete-orphan",    # Se elimini org → elimina anche users
        lazy="select"                    # Come caricare i dati (select = query separate)
    )
    
    # SPIEGAZIONE CASCADE:
    # "all, delete-orphan" = se elimini l'organizzazione, elimina anche tutti i suoi utenti
    # È come dire: "se chiude l'azienda, licenzia tutti i dipendenti"
    
    # Altri relationships (li creeremo dopo)
    # sensors: List["Sensor"] = relationship(...)
    # locations: List["Location"] = relationship(...)
    # alerts: List["Alert"] = relationship(...)
    
    # ==========================================
    # CONSTRAINTS (REGOLE DATABASE)
    # ==========================================
    
    __table_args__ = (
        # CHECK CONSTRAINTS = regole di validazione nel database
        CheckConstraint(
            'max_sensors > 0',                    # SQL condition
            name='chk_max_sensors_positive'       # Nome del constraint
        ),
        CheckConstraint(
            'retention_months >= 6',
            name='chk_retention_min_6_months'
        ),
    )
    
    # SPIEGAZIONE CHECK CONSTRAINTS:
    # Il database stesso verifica queste regole
    # Se provi a inserire max_sensors = -5 → ERRORE dal database
    # È una sicurezza extra oltre alla validazione Python
    
    # ==========================================
    # METODI DI BUSINESS LOGIC
    # ==========================================
    
    def __str__(self) -> str:
        """
        Rappresentazione "umana" dell'oggetto.
        Usata quando fai print(organization)
        """
        name_value = getattr(self, 'name', 'Unnamed Organization')
        return str(name_value)
    
    # METODI PER SUBSCRIPTION
    def is_premium(self) -> bool:
        """
        Verifica se l'organizzazione ha un piano premium.
        
        RETURN: True se premium/enterprise, False se free/basic
        """
        premium_plans = ['premium', 'enterprise']
        subscription_value = getattr(self, 'subscription_plan', 'free')
        return subscription_value in premium_plans
    
    def can_add_sensor(self, current_sensor_count: int) -> bool:
        """
        Verifica se l'organizzazione può aggiungere altri sensori.
        
        PARAMETERS:
        - current_sensor_count: numero attuale di sensori
        
        RETURN: True se può aggiungere, False se ha raggiunto il limite
        """
        # CORRETTO: Accesso sicuro al valore della colonna
        max_sensors_value = getattr(self, 'max_sensors', 10)
        return current_sensor_count < max_sensors_value
    
    def get_sensors_remaining(self, current_sensor_count: int) -> int:
        """
        Calcola quanti sensori può ancora aggiungere.
        """
        max_sensors_value = getattr(self, 'max_sensors', 10)
        remaining = max_sensors_value - current_sensor_count
        return max(0, remaining)  # Non può essere negativo
    
    # METODI PER HACCP SETTINGS
    def get_haccp_setting(self, key: str, default: Any = None) -> Any:
        """
        Ottiene una specifica impostazione HACCP.
        
        ESEMPIO:
        temp_max = org.get_haccp_setting("temperature_max", 8.0)
        
        PARAMETERS:
        - key: chiave dell'impostazione (es: "temperature_max")
        - default: valore di default se la chiave non esiste
        
        RETURN: valore dell'impostazione o default
        """
        # CORRETTO: Accesso sicuro al valore della colonna JSONB
        haccp_settings_value = getattr(self, 'haccp_settings', None)
        
        # Verifica se haccp_settings è None (non inizializzato)
        if haccp_settings_value is None:
            return default
        
        # .get() è un metodo dei dict che ritorna default se key non esiste
        return haccp_settings_value.get(key, default)
    
    def set_haccp_setting(self, key: str, value: Any) -> None:
        """
        Imposta una specifica impostazione HACCP.
        
        ESEMPIO:
        org.set_haccp_setting("temperature_max", 8.0)
        org.set_haccp_setting("alert_emails", ["admin@company.com"])
        """
        # CORRETTO: Accesso sicuro al valore della colonna
        haccp_settings_value = getattr(self, 'haccp_settings', None)
        
        # Se haccp_settings è None, inizializzalo come dict vuoto
        if haccp_settings_value is None:
            self.haccp_settings = {}
            haccp_settings_value = self.haccp_settings
        
        # Imposta il valore
        haccp_settings_value[key] = value
        
        # NOTA: Grazie a MutableDict, SQLAlchemy sa che abbiamo modificato il JSON
    
    def get_all_haccp_settings(self) -> Dict[str, Any]:
        """
        Ritorna tutte le impostazioni HACCP come dizionario.
        """
        haccp_settings_value = getattr(self, 'haccp_settings', None)
        return haccp_settings_value if haccp_settings_value is not None else {}
    
    # METODI PER VALIDAZIONE
    def validate_timezone(self, timezone: str) -> bool:
        """
        Valida se un timezone è valido.
        
        NOTA: Implementazione semplificata, in produzione useresti pytz
        """
        valid_timezones = [
            "UTC", "Europe/Rome", "Europe/London", "America/New_York", 
            "America/Los_Angeles", "Asia/Tokyo"
        ]
        return timezone in valid_timezones
    
    # OVERRIDE DEL METODO to_dict() DALLA BaseModel
    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Converte l'organizzazione in dizionario per API.
        
        OVERRIDE: Estende il metodo della BaseModel con funzionalità extra
        """
        # Chiama il metodo della classe parent (BaseModel)
        result = super().to_dict()
        
        # Aggiungi campi calcolati
        result['is_premium'] = self.is_premium()
        
        # Opzionalmente includi anche i relationships
        if include_relationships:
            # Convertiamo anche gli utenti (se caricati)
            if hasattr(self, 'users') and self.users:
                result['users'] = [user.to_dict() for user in self.users]
            else:
                result['users'] = []
        
        return result


# ==========================================
# CLASSE PER DOCUMENTARE HACCP SETTINGS
# ==========================================

class HACCPSettingsSchema:
    """
    Documentazione della struttura delle impostazioni HACCP.
    
    QUESTA NON È UNA TABELLA, ma solo documentazione per gli sviluppatori.
    
    Esempio di haccp_settings JSON:
    {
        "temperature_min": -20.0,
        "temperature_max": 8.0,
        "humidity_min": 30.0,
        "humidity_max": 80.0,
        "alert_delay_minutes": 15,
        "calibration_interval_months": 12,
        "notification_emails": ["manager@company.com", "haccp@company.com"],
        "require_manual_verification": true,
        "compliance_standards": ["HACCP", "ISO22000"],
        "critical_control_points": [
            {
                "name": "Cold Storage",
                "location_type": "freezer", 
                "temperature_range": [-22, -18],
                "monitoring_frequency_minutes": 30
            }
        ]
    }
    """
    
    # Valori di default comuni
    DEFAULT_SETTINGS = {
        "temperature_min": -20.0,
        "temperature_max": 8.0,
        "humidity_min": 30.0,
        "humidity_max": 80.0,
        "alert_delay_minutes": 15,
        "calibration_interval_months": 12,
        "require_manual_verification": True,
        "notification_emails": []
    }
    
    @classmethod
    def get_default_settings(cls) -> Dict[str, Any]:
        """Ritorna le impostazioni HACCP di default."""
        return cls.DEFAULT_SETTINGS.copy()


# ==========================================
# ESEMPI DI UTILIZZO (per capire meglio)
# ==========================================

# ESEMPIO 1: Creare una nuova organizzazione
def example_create_organization():
    """Esempio di come creare un'organizzazione"""
    
    org = Organization(
        name="Pizza di Mario",
        slug="pizza-di-mario",
        subscription_plan="premium",
        max_sensors=50,
        timezone="Europe/Rome"
    )
    
    # Imposta alcune impostazioni HACCP
    org.set_haccp_setting("temperature_max", 8.0)
    org.set_haccp_setting("alert_emails", ["mario@pizza.com"])
    
    return org

# ESEMPIO 2: Usare i metodi business
def example_business_logic():
    """Esempio di logica business"""
    
    org = Organization(name="Test", slug="test", max_sensors=10)
    
    # Verifica piano
    if org.is_premium():
        print("Organizzazione premium!")
    
    # Verifica limiti sensori
    current_sensors = 8
    if org.can_add_sensor(current_sensors):
        remaining = org.get_sensors_remaining(current_sensors)
        print(f"Puoi aggiungere ancora {remaining} sensori")
    
    # Ottieni impostazioni HACCP
    temp_max = org.get_haccp_setting("temperature_max", 5.0)
    print(f"Temperatura massima: {temp_max}°C")