"""001_create_base_tables

Revision ID: 001
Revises: 
Create Date: 2025-06-13 10:00:00.000000

Crea le tabelle base per Ice Pulse HACCP system:
- organizations (multi-tenancy)
- users (authentication)
- locations (dove sono i sensori)
- sensors (dispositivi IoT)
- alerts (sistema allarmi)
- audit_log (tracciabilità HACCP)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Crea tabelle base per Ice Pulse HACCP"""
    
    # =====================================================
    # 1. ORGANIZATIONS (Multi-tenancy)
    # =====================================================
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, 
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('subscription_plan', sa.String(20), nullable=False, default='free'),
        sa.Column('max_sensors', sa.Integer, nullable=False, default=10),
        sa.Column('timezone', sa.String(50), nullable=False, default='Europe/Rome'),
        
        # Configurazioni HACCP specifiche
        sa.Column('haccp_settings', postgresql.JSONB, nullable=True),
        sa.Column('retention_months', sa.Integer, nullable=False, default=24),
        sa.Column('auto_archive_enabled', sa.Boolean, nullable=False, default=True),
        
        # Audit timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Constraints
        sa.CheckConstraint('max_sensors > 0', name='chk_max_sensors_positive'),
        sa.CheckConstraint('retention_months >= 6', name='chk_retention_min_6_months'),
    )
    
    # =====================================================
    # 2. USERS (Authentication & Authorization)
    # =====================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, default='operator'),
        
        # Account status
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean, nullable=False, default=False),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer, nullable=False, default=0),
        
        # HACCP specific
        sa.Column('haccp_certificate_number', sa.String(100), nullable=True),
        sa.Column('haccp_certificate_expiry', sa.Date, nullable=True),
        
        # Audit timestamps  
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_users_organization'),
                              
        # Constraints
        sa.CheckConstraint("role IN ('admin', 'manager', 'operator', 'viewer')", 
                          name='chk_user_role_valid'),
        sa.CheckConstraint('failed_login_attempts >= 0', 
                          name='chk_failed_attempts_positive'),
    )
    
    # =====================================================
    # 3. LOCATIONS (Dove sono fisicamente i sensori)
    # =====================================================
    op.create_table(
        'locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('location_type', sa.String(20), nullable=False),
        
        # Temperature/humidity thresholds per location type
        sa.Column('temperature_min', sa.DECIMAL(5,2), nullable=True),
        sa.Column('temperature_max', sa.DECIMAL(5,2), nullable=True),
        sa.Column('humidity_min', sa.DECIMAL(5,2), nullable=True),
        sa.Column('humidity_max', sa.DECIMAL(5,2), nullable=True),
        
        # Physical location info
        sa.Column('floor', sa.String(20), nullable=True),
        sa.Column('zone', sa.String(50), nullable=True),
        sa.Column('coordinates', postgresql.JSONB, nullable=True),
        
        # Audit timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_locations_organization'),
                              
        # Constraints
        sa.CheckConstraint(
            "location_type IN ('freezer', 'fridge', 'cold_room', 'outdoor', 'kitchen', 'storage')", 
            name='chk_location_type_valid'
        ),
        sa.CheckConstraint(
            'temperature_min IS NULL OR temperature_max IS NULL OR temperature_min < temperature_max', 
            name='chk_temperature_range_valid'
        ),
    )
    
    # =====================================================
    # 4. SENSORS (Dispositivi IoT)
    # =====================================================
    op.create_table(
        'sensors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_id', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('sensor_type', sa.String(30), nullable=False, default='temperature_humidity'),
        sa.Column('status', sa.String(20), nullable=False, default='offline'),
        
        # Hardware info
        sa.Column('mac_address', sa.String(17), nullable=True),
        sa.Column('firmware_version', sa.String(20), nullable=True),
        sa.Column('hardware_model', sa.String(50), nullable=True),
        sa.Column('battery_level', sa.Integer, nullable=False, default=100),
        
        # Configuration
        sa.Column('reading_interval_seconds', sa.Integer, nullable=False, default=300),
        sa.Column('alert_thresholds', postgresql.JSONB, nullable=True),
        
        # Last communication
        sa.Column('last_seen_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_reading_at', sa.TIMESTAMP(timezone=True), nullable=True),
        
        # HACCP Calibration info
        sa.Column('last_calibration_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('calibration_due_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('accuracy_specification', sa.DECIMAL(3,2), nullable=False, default=0.5),
        
        # Audit timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys  
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_sensors_organization'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], 
                              ondelete='SET NULL', name='fk_sensors_location'),
                              
        # Constraints
        sa.CheckConstraint(
            "sensor_type IN ('temperature_humidity', 'temperature_pressure', 'multi_sensor')", 
            name='chk_sensor_type_valid'
        ),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'warning', 'error', 'maintenance')", 
            name='chk_sensor_status_valid'
        ),
        sa.CheckConstraint('battery_level >= 0 AND battery_level <= 100', 
                          name='chk_battery_level_valid'),
        sa.CheckConstraint('reading_interval_seconds > 0', 
                          name='chk_reading_interval_positive'),
        sa.CheckConstraint('accuracy_specification > 0', 
                          name='chk_accuracy_positive'),
    )
    
    # =====================================================
    # 5. ALERTS (Sistema di allarmi)
    # =====================================================
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sensor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('alert_type', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, default='medium'),
        sa.Column('message', sa.Text, nullable=False),
        
        # Alert values
        sa.Column('threshold_value', sa.DECIMAL(10,2), nullable=True),
        sa.Column('current_value', sa.DECIMAL(10,2), nullable=True),
        sa.Column('deviation_duration_minutes', sa.Integer, nullable=True),
        
        # Resolution tracking
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('acknowledged_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text, nullable=True),
        
        # HACCP specific
        sa.Column('requires_corrective_action', sa.Boolean, nullable=False, default=False),
        sa.Column('corrective_action_taken', sa.Text, nullable=True),
        sa.Column('haccp_compliance_impact', sa.Boolean, nullable=False, default=False),
        
        # Audit timestamps
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_alerts_organization'),
        sa.ForeignKeyConstraint(['sensor_id'], ['sensors.id'], 
                              ondelete='RESTRICT', name='fk_alerts_sensor'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], 
                              ondelete='SET NULL', name='fk_alerts_acknowledged_by'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], 
                              ondelete='SET NULL', name='fk_alerts_resolved_by'),
                              
        # Constraints
        sa.CheckConstraint(
            "alert_type IN ('temperature_high', 'temperature_low', 'humidity_high', 'humidity_low', 'offline', 'battery_low', 'calibration_due', 'sensor_failure')", 
            name='chk_alert_type_valid'
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')", 
            name='chk_alert_severity_valid'
        ),
        sa.CheckConstraint(
            "status IN ('active', 'acknowledged', 'resolved', 'dismissed')", 
            name='chk_alert_status_valid'
        ),
    )
    
    # =====================================================
    # 6. AUDIT_LOG (HACCP compliance - tracciabilità)
    # =====================================================
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Change tracking
        sa.Column('old_values', postgresql.JSONB, nullable=True),
        sa.Column('new_values', postgresql.JSONB, nullable=True),
        sa.Column('changes_summary', sa.Text, nullable=True),
        
        # Request context
        sa.Column('ip_address', postgresql.INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        
        # HACCP compliance specific
        sa.Column('haccp_relevant', sa.Boolean, nullable=False, default=False),
        sa.Column('compliance_impact', sa.String(20), nullable=True),
        
        # Timestamp
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_audit_log_organization'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], 
                              ondelete='SET NULL', name='fk_audit_log_user'),
                              
        # Constraints
        sa.CheckConstraint(
            "compliance_impact IS NULL OR compliance_impact IN ('none', 'low', 'medium', 'high', 'critical')", 
            name='chk_compliance_impact_valid'
        ),
    )

    # =====================================================
    # 7. TRIGGER PER AUTO-UPDATE TIMESTAMPS
    # =====================================================
    op.execute("""
        -- Function per auto-update di updated_at
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        -- Trigger per organizations
        CREATE TRIGGER tr_organizations_updated_at
            BEFORE UPDATE ON organizations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        -- Trigger per users
        CREATE TRIGGER tr_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        -- Trigger per locations
        CREATE TRIGGER tr_locations_updated_at
            BEFORE UPDATE ON locations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        -- Trigger per sensors
        CREATE TRIGGER tr_sensors_updated_at
            BEFORE UPDATE ON sensors
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
            
        -- Trigger per alerts
        CREATE TRIGGER tr_alerts_updated_at
            BEFORE UPDATE ON alerts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade() -> None:
    """Rimuove tutte le tabelle base e trigger"""
    
    # Drop trigger
    op.execute("""
        DROP TRIGGER IF EXISTS tr_alerts_updated_at ON alerts;
        DROP TRIGGER IF EXISTS tr_sensors_updated_at ON sensors;
        DROP TRIGGER IF EXISTS tr_locations_updated_at ON locations;
        DROP TRIGGER IF EXISTS tr_users_updated_at ON users;
        DROP TRIGGER IF EXISTS tr_organizations_updated_at ON organizations;
        DROP FUNCTION IF EXISTS update_updated_at_column();
    """)
    
    # Drop tables (ordine inverso per FK)
    op.drop_table('audit_log')
    op.drop_table('alerts')
    op.drop_table('sensors')
    op.drop_table('locations')
    op.drop_table('users')
    op.drop_table('organizations')