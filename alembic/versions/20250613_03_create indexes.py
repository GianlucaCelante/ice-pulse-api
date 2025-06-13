"""003_create_indexes

Revision ID: 003
Revises: 002
Create Date: 2025-01-01 10:30:00.000000

Crea tutti gli indici ottimizzati per performance:
- Indici time-series per readings
- Indici per query dashboard frequenti
- Indici per compliance e audit
- Indici per ricerche full-text
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Crea tutti gli indici per performance ottimali"""
    
    # =====================================================
    # ORGANIZATIONS - Query frequenti per multi-tenancy
    # =====================================================
    
    # Ricerca per slug (login/routing)
    op.create_index(
        'idx_organizations_slug', 
        'organizations', 
        ['slug']
    )
    
    # Ricerca per subscription plan (analytics)
    op.create_index(
        'idx_organizations_subscription_plan', 
        'organizations', 
        ['subscription_plan', 'created_at']
    )
    
    # =====================================================
    # USERS - Authentication e authorization
    # =====================================================
    
    # Login veloce
    op.create_index(
        'idx_users_email_active', 
        'users', 
        ['email', 'is_active']
    )
    
    # Query per organizzazione
    op.create_index(
        'idx_users_organization_role', 
        'users', 
        ['organization_id', 'role', 'is_active']
    )
    
    # Ricerca certificati HACCP in scadenza
    op.create_index(
        'idx_users_haccp_certificate_expiry', 
        'users', 
        ['organization_id', 'haccp_certificate_expiry']
    )
    
    # =====================================================
    # LOCATIONS - Gestione spazi fisici
    # =====================================================
    
    # Query per organizzazione e tipo
    op.create_index(
        'idx_locations_organization_type', 
        'locations', 
        ['organization_id', 'location_type']
    )
    
    # Ricerca full-text per nome location
    op.execute("""
        CREATE INDEX idx_locations_name_fulltext 
        ON locations 
        USING gin(to_tsvector('italian', name || ' ' || COALESCE(description, '')))
    """)
    
    # =====================================================
    # SENSORS - Dispositivi IoT
    # =====================================================
    
    # Query dashboard principale (sensori attivi per org)
    op.create_index(
        'idx_sensors_organization_status', 
        'sensors', 
        ['organization_id', 'status', 'last_seen_at DESC']
    )
    
    # Ricerca per device_id (API IoT)
    op.create_index(
        'idx_sensors_device_id', 
        'sensors', 
        ['device_id']
    )
    
    # Sensori per location
    op.create_index(
        'idx_sensors_location', 
        'sensors', 
        ['location_id', 'status']
    )
    
    # Calibrazioni in scadenza (HACCP critical)
    op.create_index(
        'idx_sensors_calibration_due', 
        'sensors', 
        ['organization_id', 'calibration_due_date']
    )
    
    # MAC address lookup (troubleshooting)
    op.create_index(
        'idx_sensors_mac_address', 
        'sensors', 
        ['mac_address']
    )
    
    # Ricerca full-text sensori
    op.execute("""
        CREATE INDEX idx_sensors_name_fulltext 
        ON sensors 
        USING gin(to_tsvector('italian', name))
    """)
    
    # =====================================================
    # READINGS - Time Series (Performance Critical!)
    # =====================================================
    
    # NOTA: Gli indici principali sono già creati nelle partizioni
    # durante la creazione automatica, qui aggiungiamo indici globali
    
    # Indice globale per organization (cross-partition queries)
    op.execute("""
        -- Indice per query dashboard org-wide
        -- Usato per: "tutti i sensori della mia org nelle ultime 24h"
        CREATE INDEX idx_readings_organization_timestamp_global 
        ON readings (organization_id, timestamp DESC, sensor_id)
    """)
    
    # Indice per deviazioni HACCP (compliance queries)
    op.execute("""
        CREATE INDEX idx_readings_compliance_deviations 
        ON readings (organization_id, deviation_detected, timestamp DESC) 
        WHERE deviation_detected = TRUE
    """)
    
    # Indice per azioni correttive (audit queries)
    op.execute("""
        CREATE INDEX idx_readings_corrective_actions 
        ON readings (organization_id, corrective_action_required, timestamp DESC) 
        WHERE corrective_action_required = TRUE
    """)
    
    # Indice per letture manuali (verifiche HACCP)
    op.execute("""
        CREATE INDEX idx_readings_manual_verification 
        ON readings (organization_id, manual_verification, timestamp DESC) 
        WHERE manual_verification = TRUE
    """)
    
    # =====================================================
    # ALERTS - Sistema allarmi
    # =====================================================
    
    # Dashboard alert attivi
    op.create_index(
        'idx_alerts_organization_active', 
        'alerts', 
        ['organization_id', 'status', 'severity', 'created_at DESC']
    )
    
    # Alert per sensore (troubleshooting)
    op.create_index(
        'idx_alerts_sensor_timestamp', 
        'alerts', 
        ['sensor_id', 'created_at DESC']
    )
    
    # Alert HACCP critici
    op.execute("""
        CREATE INDEX idx_alerts_haccp_critical 
        ON alerts (organization_id, haccp_compliance_impact, created_at DESC) 
        WHERE haccp_compliance_impact = TRUE
    """)
    
    # Alert non risolti (monitoring)
    op.execute("""
        CREATE INDEX idx_alerts_unresolved 
        ON alerts (organization_id, alert_type, created_at DESC) 
        WHERE status IN ('active', 'acknowledged')
    """)
    
    # =====================================================
    # AUDIT_LOG - Tracciabilità HACCP
    # =====================================================
    
    # Query audit per organizzazione
    op.create_index(
        'idx_audit_log_organization_action', 
        'audit_log', 
        ['organization_id', 'action', 'created_at DESC']
    )
    
    # Audit per utente specifico
    op.create_index(
        'idx_audit_log_user', 
        'audit_log', 
        ['user_id', 'created_at DESC']
    )
    
    # Audit per risorsa (es: tutti i cambiamenti a un sensore)
    op.create_index(
        'idx_audit_log_resource', 
        'audit_log', 
        ['resource_type', 'resource_id', 'created_at DESC']
    )
    
    # Eventi HACCP rilevanti (compliance)
    op.execute("""
        CREATE INDEX idx_audit_log_haccp_relevant 
        ON audit_log (organization_id, haccp_relevant, created_at DESC) 
        WHERE haccp_relevant = TRUE
    """)
    
    # =====================================================
    # INDICI COMPOSITI PER QUERY COMPLESSE
    # =====================================================
    
    # Dashboard main query: sensori + ultima lettura + alert attivi
    op.execute("""
        -- Ottimizza: sensori con status + location per org
        CREATE INDEX idx_sensors_dashboard_composite 
        ON sensors (organization_id, status, location_id, last_seen_at DESC)
        INCLUDE (name, battery_level)
    """)
    
    # Report HACCP: compliance per periodo
    op.execute("""
        -- Ottimizza: report compliance per periodo
        CREATE INDEX idx_readings_haccp_report 
        ON readings (organization_id, haccp_compliance_status, timestamp) 
        INCLUDE (sensor_id, temperature, deviation_detected)
    """)
    
    # =====================================================
    # INDICI PER STATISTICHE E ANALYTICS
    # =====================================================
    
    # Statistiche uso per organization
    op.execute("""
        CREATE INDEX idx_readings_stats_daily 
        ON readings (organization_id, DATE(timestamp), sensor_id)
    """)
    
    # Performance monitoring
    op.execute("""
        CREATE INDEX idx_sensors_performance_monitoring 
        ON sensors (organization_id, last_seen_at, status)
        WHERE status = 'offline'
    """)

def downgrade() -> None:
    """Rimuove tutti gli indici creati"""
    
    # Performance monitoring
    op.drop_index('idx_sensors_performance_monitoring')
    op.drop_index('idx_readings_stats_daily')
    
    # Indici compositi complessi
    op.drop_index('idx_readings_haccp_report')
    op.drop_index('idx_sensors_dashboard_composite')
    
    # Audit log
    op.drop_index('idx_audit_log_haccp_relevant')
    op.drop_index('idx_audit_log_resource')
    op.drop_index('idx_audit_log_user')
    op.drop_index('idx_audit_log_organization_action')
    
    # Alerts
    op.drop_index('idx_alerts_unresolved')
    op.drop_index('idx_alerts_haccp_critical')
    op.drop_index('idx_alerts_sensor_timestamp')
    op.drop_index('idx_alerts_organization_active')
    
    # Readings
    op.drop_index('idx_readings_manual_verification')
    op.drop_index('idx_readings_corrective_actions')
    op.drop_index('idx_readings_compliance_deviations')
    op.drop_index('idx_readings_organization_timestamp_global')
    
    # Sensors
    op.drop_index('idx_sensors_name_fulltext')
    op.drop_index('idx_sensors_mac_address')
    op.drop_index('idx_sensors_calibration_due')
    op.drop_index('idx_sensors_location')
    op.drop_index('idx_sensors_device_id')
    op.drop_index('idx_sensors_organization_status')
    
    # Locations
    op.drop_index('idx_locations_name_fulltext')
    op.drop_index('idx_locations_organization_type')
    
    # Users
    op.drop_index('idx_users_haccp_certificate_expiry')
    op.drop_index('idx_users_organization_role')
    op.drop_index('idx_users_email_active')
    
    # Organizations
    op.drop_index('idx_organizations_subscription_plan')
    op.drop_index('idx_organizations_slug')