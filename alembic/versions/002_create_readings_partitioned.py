"""002_create_readings_partitioned

Revision ID: 002
Revises: 001
Create Date: 2025-06-13 10:15:00.000000

Crea la tabella readings con partitioning mensile per performance ottimali:
- readings_master (tabella madre)
- Partizioni automatiche per mese
- Trigger per routing automatico
- Function per gestione partizioni future
- Calibrations table per HACCP compliance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Crea readings partitioned table + calibrations"""
    
    # =====================================================
    # 1. READINGS MASTER TABLE (Partitioned)
    # =====================================================
    op.execute("""
        -- Tabella principale READINGS (partitioned by timestamp)
        CREATE TABLE readings (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            sensor_id UUID NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            
            -- Sensor measurements
            temperature DECIMAL(6,3) NULL,
            humidity DECIMAL(5,2) NULL,
            pressure DECIMAL(7,2) NULL,
            battery_voltage DECIMAL(4,3) NULL,
            
            -- Data quality indicators
            rssi INTEGER NULL,                         -- Signal strength
            data_quality_score DECIMAL(3,2) NULL,     -- 0.00-1.00 quality score
            is_manual_entry BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- HACCP compliance fields
            temperature_deviation BOOLEAN NOT NULL DEFAULT FALSE,
            humidity_deviation BOOLEAN NOT NULL DEFAULT FALSE,
            deviation_detected BOOLEAN NOT NULL DEFAULT FALSE,
            corrective_action_required BOOLEAN NOT NULL DEFAULT FALSE,
            manual_verification BOOLEAN NOT NULL DEFAULT FALSE,
            haccp_compliance_status VARCHAR(20) NOT NULL DEFAULT 'compliant',
            
            -- Alert correlation
            alert_generated BOOLEAN NOT NULL DEFAULT FALSE,
            alert_id UUID NULL,
            
            -- Metadata
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            
            -- Primary key include timestamp per partitioning
            PRIMARY KEY (id, timestamp),
            
            -- Foreign keys
            CONSTRAINT fk_readings_organization 
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE RESTRICT,
            CONSTRAINT fk_readings_sensor 
                FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE RESTRICT,
            CONSTRAINT fk_readings_alert 
                FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE SET NULL,
                
            -- Check constraints
            CONSTRAINT chk_temperature_range 
                CHECK (temperature IS NULL OR temperature BETWEEN -80.0 AND 100.0),
            CONSTRAINT chk_humidity_range 
                CHECK (humidity IS NULL OR humidity BETWEEN 0.0 AND 100.0),
            CONSTRAINT chk_pressure_range 
                CHECK (pressure IS NULL OR pressure BETWEEN 0.0 AND 2000.0),
            CONSTRAINT chk_battery_voltage_range 
                CHECK (battery_voltage IS NULL OR battery_voltage BETWEEN 0.0 AND 5.0),
            CONSTRAINT chk_data_quality_range 
                CHECK (data_quality_score IS NULL OR data_quality_score BETWEEN 0.0 AND 1.0),
            CONSTRAINT chk_haccp_status_valid 
                CHECK (haccp_compliance_status IN ('compliant', 'deviation', 'critical', 'under_review'))
                
        ) PARTITION BY RANGE (timestamp);
    """)
    
    # =====================================================
    # 2. CALIBRATIONS TABLE (Per HACCP compliance)
    # =====================================================
    op.create_table(
        'calibrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                 server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sensor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calibration_type', sa.String(30), nullable=False, default='routine'),
        
        # Calibration data
        sa.Column('reference_temperature', sa.DECIMAL(6,3), nullable=True),
        sa.Column('measured_temperature', sa.DECIMAL(6,3), nullable=True),
        sa.Column('temperature_offset', sa.DECIMAL(6,3), nullable=True),
        sa.Column('reference_humidity', sa.DECIMAL(5,2), nullable=True),
        sa.Column('measured_humidity', sa.DECIMAL(5,2), nullable=True),
        sa.Column('humidity_offset', sa.DECIMAL(5,2), nullable=True),
        
        # Calibration results
        sa.Column('accuracy_achieved', sa.DECIMAL(4,3), nullable=False),
        sa.Column('calibration_passed', sa.Boolean, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        
        # Technician info
        sa.Column('calibrated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('technician_name', sa.String(100), nullable=True),
        sa.Column('technician_certificate', sa.String(100), nullable=True),
        
        # Equipment used
        sa.Column('reference_equipment_model', sa.String(100), nullable=True),
        sa.Column('reference_equipment_serial', sa.String(100), nullable=True),
        sa.Column('reference_equipment_cert_date', sa.Date, nullable=True),
        
        # Scheduling
        sa.Column('scheduled_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('calibrated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('next_calibration_due', sa.TIMESTAMP(timezone=True), nullable=False),
        
        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False,
                 server_default=sa.func.now()),
                 
        # Foreign Keys
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], 
                              ondelete='RESTRICT', name='fk_calibrations_organization'),
        sa.ForeignKeyConstraint(['sensor_id'], ['sensors.id'], 
                              ondelete='RESTRICT', name='fk_calibrations_sensor'),
        sa.ForeignKeyConstraint(['calibrated_by'], ['users.id'], 
                              ondelete='SET NULL', name='fk_calibrations_user'),
                              
        # Constraints
        sa.CheckConstraint(
            "calibration_type IN ('routine', 'corrective', 'verification', 'initial')", 
            name='chk_calibration_type_valid'
        ),
        sa.CheckConstraint('accuracy_achieved >= 0', name='chk_accuracy_positive'),
        sa.CheckConstraint('next_calibration_due > calibrated_at', 
                          name='chk_next_calibration_future'),
    )
    
    # =====================================================
    # 3. AUTO-PARTITIONING FUNCTIONS
    # =====================================================
    op.execute("""
        -- Function per creare partizioni automaticamente
        CREATE OR REPLACE FUNCTION create_readings_partition(target_date DATE)
        RETURNS TEXT AS $$
        DECLARE
            partition_name TEXT;
            start_date DATE;
            end_date DATE;
        BEGIN
            -- Calcola primo e ultimo giorno del mese
            start_date := DATE_TRUNC('month', target_date)::DATE;
            end_date := (DATE_TRUNC('month', target_date) + INTERVAL '1 month')::DATE;
            
            -- Nome partizione formato: readings_YYYY_MM
            partition_name := 'readings_' || TO_CHAR(target_date, 'YYYY_MM');
            
            -- Crea partizione se non esiste
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I PARTITION OF readings
                FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            
            -- Crea indici specifici per la partizione
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS %I ON %I (sensor_id, timestamp DESC)',
                'idx_' || partition_name || '_sensor_timestamp', partition_name
            );
            
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS %I ON %I (organization_id, timestamp DESC)',
                'idx_' || partition_name || '_org_timestamp', partition_name
            );
            
            EXECUTE format('
                CREATE INDEX IF NOT EXISTS %I ON %I (timestamp, deviation_detected) 
                WHERE deviation_detected = TRUE',
                'idx_' || partition_name || '_deviations', partition_name
            );
            
            RETURN 'Created partition: ' || partition_name;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # =====================================================
    # 4. TRIGGER PER AUTO-PARTITION CREATION
    # =====================================================
    op.execute("""
        -- Function trigger per creare partizioni al volo
        CREATE OR REPLACE FUNCTION readings_partition_trigger()
        RETURNS TRIGGER AS $$
        DECLARE
            partition_exists BOOLEAN;
            partition_name TEXT;
        BEGIN
            partition_name := 'readings_' || TO_CHAR(NEW.timestamp, 'YYYY_MM');
            
            -- Verifica se la partizione esiste
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = partition_name
            ) INTO partition_exists;
            
            -- Se non esiste, creala
            IF NOT partition_exists THEN
                PERFORM create_readings_partition(NEW.timestamp::DATE);
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Trigger BEFORE INSERT per auto-creation
        CREATE TRIGGER tr_readings_auto_partition
            BEFORE INSERT ON readings
            FOR EACH ROW
            EXECUTE FUNCTION readings_partition_trigger();
    """)
    
    # =====================================================
    # 5. FUNCTION PER PRE-CREAZIONE PARTIZIONI FUTURE
    # =====================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION ensure_future_partitions(months_ahead INTEGER DEFAULT 3)
        RETURNS TEXT AS $$
        DECLARE
            target_month DATE;
            i INTEGER;
            result TEXT := '';
        BEGIN
            -- Crea partizioni per i prossimi N mesi
            FOR i IN 0..months_ahead LOOP
                target_month := (DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL)::DATE;
                result := result || create_readings_partition(target_month) || E'\n';
            END LOOP;
            
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
        
        -- Crea subito partizioni per questo mese e i prossimi 3
        SELECT ensure_future_partitions(3);
    """)
    
    # =====================================================
    # 6. FUNCTION PER ARCHIVE AUTOMATICO
    # =====================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION archive_old_readings(archive_months_ago INTEGER DEFAULT 24)
        RETURNS TEXT AS $$
        DECLARE
            archive_date DATE;
            partition_name TEXT;
            archive_table_name TEXT;
            result TEXT := '';
        BEGIN
            -- Calcola data di archivio (default: 24 mesi fa)
            archive_date := (DATE_TRUNC('month', CURRENT_DATE) - (archive_months_ago || ' months')::INTERVAL)::DATE;
            partition_name := 'readings_' || TO_CHAR(archive_date, 'YYYY_MM');
            archive_table_name := 'readings_archive_' || TO_CHAR(archive_date, 'YYYY_MM');
            
            -- Verifica se la partizione esiste
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = partition_name) THEN
                -- Crea tabella archive se non esiste
                EXECUTE format('
                    CREATE TABLE IF NOT EXISTS %I (LIKE readings INCLUDING ALL)',
                    archive_table_name
                );
                
                -- Sposta dati nella tabella archive
                EXECUTE format('
                    INSERT INTO %I SELECT * FROM %I',
                    archive_table_name, partition_name
                );
                
                -- Detach e drop partizione
                EXECUTE format('
                    ALTER TABLE readings DETACH PARTITION %I',
                    partition_name
                );
                
                EXECUTE format('DROP TABLE %I', partition_name);
                
                result := 'Archived partition: ' || partition_name || ' to ' || archive_table_name;
            ELSE
                result := 'Partition ' || partition_name || ' not found';
            END IF;
            
            RETURN result;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # =====================================================
    # 7. TRIGGER PER CALIBRATIONS AUTO-UPDATE
    # =====================================================
    op.execute("""
        -- Trigger per auto-update calibrations.updated_at
        CREATE TRIGGER tr_calibrations_updated_at
            BEFORE UPDATE ON calibrations
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade() -> None:
    """Rimuove readings partitioned table e calibrations"""
    
    # Drop trigger e functions
    op.execute("""
        DROP TRIGGER IF EXISTS tr_calibrations_updated_at ON calibrations;
        DROP TRIGGER IF EXISTS tr_readings_auto_partition ON readings;
        DROP FUNCTION IF EXISTS archive_old_readings(INTEGER);
        DROP FUNCTION IF EXISTS ensure_future_partitions(INTEGER);
        DROP FUNCTION IF EXISTS readings_partition_trigger();
        DROP FUNCTION IF EXISTS create_readings_partition(DATE);
    """)
    
    # Drop partizioni esistenti (se presenti)
    op.execute("""
        DO $$
        DECLARE
            partition_name TEXT;
        BEGIN
            FOR partition_name IN 
                SELECT schemaname||'.'||tablename 
                FROM pg_tables 
                WHERE tablename LIKE 'readings_%' 
                AND schemaname = 'public'
            LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || partition_name || ' CASCADE';
            END LOOP;
        END $$;
    """)
    
    # Drop tabelle
    op.drop_table('calibrations')
    op.execute('DROP TABLE IF EXISTS readings CASCADE')