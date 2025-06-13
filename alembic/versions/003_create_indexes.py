"""003_create_indexes

Revision ID: 003
Revises: 002
Create Date: 2025-06-13 10:30:00.000000

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
        ['organization_id', 'status', 'last_seen_at']
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
        ['organization_id', 'status', 'severity', 'created_at']
    )
    
    # Alert per sensore (troubleshooting)
    op.create_index(
        'idx_alerts_sensor_timestamp', 
        'alerts', 
        ['sensor_id', 'created_at']
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
        ['organization_id', 'action', 'created_at']
    )
    
    # Audit per utente specifico
    op.create_index(
        'idx_audit_log_user', 
        'audit_log', 
        ['user_id', 'created_at']
    )
    
    # Audit per risorsa (es: tutti i cambiamenti a un sensore)
    op.create_index(
        'idx_audit_log_resource', 
        'audit_log', 
        ['resource_type', 'resource_id', 'created_at']
    )
    
    # Eventi HACCP rilevanti (compliance)
    op.execute("""
        CREATE INDEX idx_audit_log_haccp_relevant 
        ON audit_log (organization_id, haccp_relevant, created_at DESC) 
        WHERE haccp_relevant = TRUE
    """)
    
    # =====================================================
    # CALIBRATIONS - HACCP compliance
    # =====================================================
    
    # Query per organizzazione e sensore
    op.create_index(
        'idx_calibrations_organization_sensor', 
        'calibrations', 
        ['organization_id', 'sensor_id', 'calibrated_at']
    )
    
    # Calibrazioni in scadenza
    op.create_index(
        'idx_calibrations_due_date', 
        'calibrations', 
        ['organization_id', 'next_calibration_due']
    )
    
    # Calibrazioni fallite (per follow-up)
    op.execute("""
        CREATE INDEX idx_calibrations_failed 
        ON calibrations (organization_id, calibrated_at DESC) 
        WHERE calibration_passed = FALSE
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
    
    # Query performance: sensori offline
    op.execute("""
        CREATE INDEX idx_sensors_offline_monitoring 
        ON sensors (organization_id, status, last_seen_at)
        WHERE status = 'offline'
    """)
    
    # =====================================================
    # INDICI PER STATISTICHE E ANALYTICS
    # =====================================================
    
    # Performance monitoring: battery basso
    op.execute("""
        CREATE INDEX idx_sensors_battery_low 
        ON sensors (organization_id, battery_level, last_seen_at)
        WHERE battery_level < 20
    """)
    
    # =====================================================
    # INDICI PARZIALI PER EFFICIENZA
    # =====================================================
    
    # Solo utenti attivi
    op.execute("""
        CREATE INDEX idx_users_active_only 
        ON users (organization_id, role)
        WHERE is_active = TRUE AND is_verified = TRUE
    """)
    
    # Solo sensori online
    op.execute("""
        CREATE INDEX idx_sensors_online_only 
        ON sensors (organization_id, location_id, last_reading_at DESC)
        WHERE status = 'online'
    """)
    
    # Solo alert aperti
    op.execute("""
        CREATE INDEX idx_alerts_open_only 
        ON alerts (organization_id, severity, created_at DESC)
        WHERE status IN ('active', 'acknowledged')
    """)

def downgrade() -> None:
    """Rimuove tutti gli indici creati"""
    
    # Indici parziali
    op.drop_index('idx_alerts_open_only', 'alerts')
    op.drop_index('idx_sensors_online_only', 'sensors')
    op.drop_index('idx_users_active_only', 'users')
    
    # Statistiche e analytics
    op.drop_index('idx_sensors_battery_low', 'sensors')
    op.drop_index('idx_readings_stats_daily', 'readings')
    
    # Query complesse
    op.drop_index('idx_sensors_offline_monitoring', 'sensors')
    op.drop_index('idx_readings_haccp_report', 'readings')
    op.drop_index('idx_sensors_dashboard_composite', 'sensors')
    
    # Calibrations
    op.drop_index('idx_calibrations_failed', 'calibrations')
    op.drop_index('idx_calibrations_due_date', 'calibrations')
    op.drop_index('idx_calibrations_organization_sensor', 'calibrations')
    
    # Audit log
    op.drop_index('idx_audit_log_haccp_relevant', 'audit_log')
    op.drop_index('idx_audit_log_resource', 'audit_log')
    op.drop_index('idx_audit_log_user', 'audit_log')
    op.drop_index('idx_audit_log_organization_action', 'audit_log')
    
    # Alerts
    op.drop_index('idx_alerts_unresolved', 'alerts')
    op.drop_index('idx_alerts_haccp_critical', 'alerts')
    op.drop_index('idx_alerts_sensor_timestamp', 'alerts')
    op.drop_index('idx_alerts_organization_active', 'alerts')
    
    # Readings
    op.drop_index('idx_readings_manual_verification', 'readings')
    op.drop_index('idx_readings_corrective_actions', 'readings')
    op.drop_index('idx_readings_compliance_deviations', 'readings')
    op.drop_index('idx_readings_organization_timestamp_global', 'readings')
    
    # Sensors
    op.drop_index('idx_sensors_name_fulltext', 'sensors')
    op.drop_index('idx_sensors_mac_address', 'sensors')
    op.drop_index('idx_sensors_calibration_due', 'sensors')
    op.drop_index('idx_sensors_location', 'sensors')
    op.drop_index('idx_sensors_device_id', 'sensors')
    op.drop_index('idx_sensors_organization_status', 'sensors')
    
    # Locations
    op.drop_index('idx_locations_name_fulltext', 'locations')
    op.drop_index('idx_locations_organization_type', 'locations')
    
    # Users
    op.drop_index('idx_users_haccp_certificate_expiry', 'users')
    op.drop_index('idx_users_organization_role', 'users')
    op.drop_index('idx_users_email_active', 'users')
    
    # Organizations
    op.drop_index('idx_organizations_subscription_plan', 'organizations')
    op.drop_index('idx_organizations_slug', 'organizations')