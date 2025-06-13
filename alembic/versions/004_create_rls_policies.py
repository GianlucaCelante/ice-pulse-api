"""004_create_rls_policies

Revision ID: 004
Revises: 003
Create Date: 2025-06-13 10:45:00.000000

Crea Row Level Security (RLS) policies per multi-tenancy sicuro:
- Isolamento completo dati tra organizzazioni
- Policies per tutte le tabelle principali
- Roles e permessi per diversi tipi di utenti
- Security functions per controllo accessi
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Crea RLS policies per multi-tenancy sicuro"""
    
    # =====================================================
    # 1. SECURITY FUNCTIONS PER RLS
    # =====================================================
    op.execute("""
        -- Function per ottenere organization_id dell'utente corrente
        CREATE OR REPLACE FUNCTION current_user_organization_id()
        RETURNS UUID AS $$
        BEGIN
            -- Questo sarà impostato dall'applicazione via SET LOCAL
            RETURN COALESCE(
                current_setting('app.current_organization_id', true)::UUID,
                '00000000-0000-0000-0000-000000000000'::UUID
            );
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        -- Function per ottenere user_id dell'utente corrente
        CREATE OR REPLACE FUNCTION current_user_id()
        RETURNS UUID AS $$
        BEGIN
            RETURN COALESCE(
                current_setting('app.current_user_id', true)::UUID,
                '00000000-0000-0000-0000-000000000000'::UUID
            );
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        -- Function per ottenere il ruolo dell'utente corrente
        CREATE OR REPLACE FUNCTION current_user_role()
        RETURNS TEXT AS $$
        BEGIN
            RETURN COALESCE(
                current_setting('app.current_user_role', true),
                'viewer'
            );
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
        
        -- Function per verificare se l'utente può accedere all'organizzazione
        CREATE OR REPLACE FUNCTION can_access_organization(org_id UUID)
        RETURNS BOOLEAN AS $$
        BEGIN
            -- Admin possono accedere a tutto (per maintenance)
            IF current_user_role() = 'admin' THEN
                RETURN TRUE;
            END IF;
            
            -- Gli altri utenti solo alla propria organizzazione
            RETURN org_id = current_user_organization_id();
        END;
        $$ LANGUAGE plpgsql STABLE SECURITY DEFINER;
    """)
    
    # =====================================================
    # 2. ABILITAZIONE RLS SU TUTTE LE TABELLE
    # =====================================================
    op.execute("""
        -- Abilita RLS su tutte le tabelle principali
        ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE sensors ENABLE ROW LEVEL SECURITY;
        ALTER TABLE readings ENABLE ROW LEVEL SECURITY;
        ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
        ALTER TABLE calibrations ENABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
    """)
    
    # =====================================================
    # 3. POLICIES PER ORGANIZATIONS
    # =====================================================
    op.execute("""
        -- ORGANIZATIONS: Solo la propria organizzazione
        CREATE POLICY org_isolation_policy ON organizations
            FOR ALL
            USING (can_access_organization(id));
            
        -- ORGANIZATIONS: Policy per creazione (solo admin)
        CREATE POLICY org_creation_policy ON organizations
            FOR INSERT
            WITH CHECK (current_user_role() = 'admin');
    """)
    
    # =====================================================
    # 4. POLICIES PER USERS
    # =====================================================
    op.execute("""
        -- USERS: Solo utenti della propria organizzazione
        CREATE POLICY users_isolation_policy ON users
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- USERS: Creazione utenti (admin e manager)
        CREATE POLICY users_creation_policy ON users
            FOR INSERT
            WITH CHECK (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager')
            );
            
        -- USERS: Aggiornamento (se stesso o admin/manager)
        CREATE POLICY users_update_policy ON users
            FOR UPDATE
            USING (
                can_access_organization(organization_id) AND
                (id = current_user_id() OR current_user_role() IN ('admin', 'manager'))
            );
    """)
    
    # =====================================================
    # 5. POLICIES PER LOCATIONS
    # =====================================================
    op.execute("""
        -- LOCATIONS: Solo della propria organizzazione
        CREATE POLICY locations_isolation_policy ON locations
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- LOCATIONS: Creazione e modifica (admin e manager)
        CREATE POLICY locations_modification_policy ON locations
            FOR INSERT
            WITH CHECK (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager')
            );
    """)
    
    # =====================================================
    # 6. POLICIES PER SENSORS
    # =====================================================
    op.execute("""
        -- SENSORS: Solo della propria organizzazione
        CREATE POLICY sensors_isolation_policy ON sensors
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- SENSORS: Creazione e modifica (admin, manager, operator)
        CREATE POLICY sensors_modification_policy ON sensors
            FOR INSERT
            WITH CHECK (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator')
            );
            
        -- SENSORS: Update status per tutti gli utenti attivi
        CREATE POLICY sensors_status_update_policy ON sensors
            FOR UPDATE
            USING (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator')
            );
    """)
    
    # =====================================================
    # 7. POLICIES PER READINGS (Time-series data)
    # =====================================================
    op.execute("""
        -- READINGS: Solo della propria organizzazione
        CREATE POLICY readings_isolation_policy ON readings
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- READINGS: Inserimento dati (sensori + operatori)
        CREATE POLICY readings_insert_policy ON readings
            FOR INSERT
            WITH CHECK (can_access_organization(organization_id));
            
        -- READINGS: Update per correzioni (admin, manager, operator)
        CREATE POLICY readings_update_policy ON readings
            FOR UPDATE
            USING (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator')
            );
            
        -- READINGS: Viewer possono solo leggere
        CREATE POLICY readings_viewer_policy ON readings
            FOR SELECT
            USING (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator', 'viewer')
            );
    """)
    
    # =====================================================
    # 8. POLICIES PER ALERTS
    # =====================================================
    op.execute("""
        -- ALERTS: Solo della propria organizzazione
        CREATE POLICY alerts_isolation_policy ON alerts
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- ALERTS: Creazione automatica (sistema)
        CREATE POLICY alerts_creation_policy ON alerts
            FOR INSERT
            WITH CHECK (can_access_organization(organization_id));
            
        -- ALERTS: Acknowledge e risoluzione
        CREATE POLICY alerts_resolution_policy ON alerts
            FOR UPDATE
            USING (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator')
            );
    """)
    
    # =====================================================
    # 9. POLICIES PER CALIBRATIONS
    # =====================================================
    op.execute("""
        -- CALIBRATIONS: Solo della propria organizzazione
        CREATE POLICY calibrations_isolation_policy ON calibrations
            FOR ALL
            USING (can_access_organization(organization_id));
            
        -- CALIBRATIONS: Creazione (admin, manager, operator autorizzati)
        CREATE POLICY calibrations_creation_policy ON calibrations
            FOR INSERT
            WITH CHECK (
                can_access_organization(organization_id) AND
                current_user_role() IN ('admin', 'manager', 'operator')
            );
    """)
    
    # =====================================================
    # 10. POLICIES PER AUDIT_LOG
    # =====================================================
    op.execute("""
        -- AUDIT_LOG: Solo della propria organizzazione (se specificata)
        CREATE POLICY audit_isolation_policy ON audit_log
            FOR ALL
            USING (
                organization_id IS NULL OR 
                can_access_organization(organization_id)
            );
            
        -- AUDIT_LOG: Inserimento sempre permesso (per sistema)
        CREATE POLICY audit_creation_policy ON audit_log
            FOR INSERT
            WITH CHECK (TRUE);  -- Il sistema può sempre loggare
            
        -- AUDIT_LOG: Solo lettura per utenti normali
        CREATE POLICY audit_readonly_policy ON audit_log
            FOR UPDATE
            USING (current_user_role() = 'admin');  -- Solo admin possono modificare audit
    """)
    
    # =====================================================
    # 11. DATABASE ROLES E PERMESSI
    # =====================================================
    op.execute("""
        -- Crea roles per diversi tipi di accesso
        DO $$
        BEGIN
            -- Role per applicazione (connection pooling)
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ice_pulse_app') THEN
                CREATE ROLE ice_pulse_app LOGIN;
            END IF;
            
            -- Role per API readonly (dashboard, reports)
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ice_pulse_readonly') THEN
                CREATE ROLE ice_pulse_readonly LOGIN;
            END IF;
            
            -- Role per sensori IoT (solo insert readings)
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ice_pulse_sensor') THEN
                CREATE ROLE ice_pulse_sensor LOGIN;
            END IF;
            
            -- Role per admin (accesso completo)
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ice_pulse_admin') THEN
                CREATE ROLE ice_pulse_admin LOGIN;
            END IF;
        END $$;
        
        -- Permessi per ice_pulse_app (applicazione principale)
        GRANT USAGE ON SCHEMA public TO ice_pulse_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ice_pulse_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ice_pulse_app;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO ice_pulse_app;
        
        -- Permessi per ice_pulse_readonly (dashboard, analytics)
        GRANT USAGE ON SCHEMA public TO ice_pulse_readonly;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO ice_pulse_readonly;
        GRANT EXECUTE ON FUNCTION current_user_organization_id() TO ice_pulse_readonly;
        GRANT EXECUTE ON FUNCTION current_user_id() TO ice_pulse_readonly;
        GRANT EXECUTE ON FUNCTION current_user_role() TO ice_pulse_readonly;
        GRANT EXECUTE ON FUNCTION can_access_organization(UUID) TO ice_pulse_readonly;
        
        -- Permessi per ice_pulse_sensor (solo inserimento readings)
        GRANT USAGE ON SCHEMA public TO ice_pulse_sensor;
        GRANT SELECT ON sensors TO ice_pulse_sensor;
        GRANT INSERT ON readings TO ice_pulse_sensor;
        GRANT INSERT ON alerts TO ice_pulse_sensor;  -- Per alert automatici
        GRANT EXECUTE ON FUNCTION current_user_organization_id() TO ice_pulse_sensor;
        
        -- Permessi per ice_pulse_admin (accesso completo)
        GRANT ALL PRIVILEGES ON SCHEMA public TO ice_pulse_admin;
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ice_pulse_admin;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ice_pulse_admin;
        GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO ice_pulse_admin;
    """)
    
    # =====================================================
    # 12. SECURITY CONTEXT HELPERS
    # =====================================================
    op.execute("""
        -- Function per impostare il contesto utente (usata dall'app)
        CREATE OR REPLACE FUNCTION set_user_context(
            p_user_id UUID,
            p_organization_id UUID,
            p_role TEXT
        )
        RETURNS VOID AS $
        BEGIN
            -- Imposta variabili di sessione per RLS
            PERFORM set_config('app.current_user_id', p_user_id::TEXT, false);
            PERFORM set_config('app.current_organization_id', p_organization_id::TEXT, false);
            PERFORM set_config('app.current_user_role', p_role, false);
        END;
        $ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function per impostare contesto sensore (per IoT)
        CREATE OR REPLACE FUNCTION set_sensor_context(
            p_sensor_id UUID,
            p_organization_id UUID
        )
        RETURNS VOID AS $
        BEGIN
            PERFORM set_config('app.current_organization_id', p_organization_id::TEXT, false);
            PERFORM set_config('app.current_user_role', 'sensor', false);
            PERFORM set_config('app.current_sensor_id', p_sensor_id::TEXT, false);
        END;
        $ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Function per pulire il contesto
        CREATE OR REPLACE FUNCTION clear_user_context()
        RETURNS VOID AS $
        BEGIN
            PERFORM set_config('app.current_user_id', NULL, false);
            PERFORM set_config('app.current_organization_id', NULL, false);
            PERFORM set_config('app.current_user_role', NULL, false);
            PERFORM set_config('app.current_sensor_id', NULL, false);
        END;
        $ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # =====================================================
    # 13. AUDIT TRIGGER PER TRACCIARE ACCESSI RLS
    # =====================================================
    op.execute("""
        -- Function per loggare accessi con RLS
        CREATE OR REPLACE FUNCTION log_rls_access()
        RETURNS TRIGGER AS $
        BEGIN
            -- Log solo per operazioni sensibili
            IF TG_OP IN ('INSERT', 'UPDATE', 'DELETE') THEN
                INSERT INTO audit_log (
                    organization_id,
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    old_values,
                    new_values,
                    haccp_relevant,
                    ip_address,
                    created_at
                ) VALUES (
                    current_user_organization_id(),
                    current_user_id(),
                    TG_OP,
                    TG_TABLE_NAME,
                    COALESCE(NEW.id, OLD.id),
                    CASE WHEN TG_OP != 'INSERT' THEN row_to_json(OLD) ELSE NULL END,
                    CASE WHEN TG_OP != 'DELETE' THEN row_to_json(NEW) ELSE NULL END,
                    CASE WHEN TG_TABLE_NAME IN ('readings', 'sensors', 'calibrations', 'alerts') THEN TRUE ELSE FALSE END,
                    inet_client_addr(),
                    CURRENT_TIMESTAMP
                );
            END IF;
            
            RETURN COALESCE(NEW, OLD);
        END;
        $ LANGUAGE plpgsql;
        
        -- Applica trigger di audit a tabelle critiche
        CREATE TRIGGER tr_sensors_audit AFTER INSERT OR UPDATE OR DELETE ON sensors
            FOR EACH ROW EXECUTE FUNCTION log_rls_access();
            
        CREATE TRIGGER tr_calibrations_audit AFTER INSERT OR UPDATE OR DELETE ON calibrations
            FOR EACH ROW EXECUTE FUNCTION log_rls_access();
            
        CREATE TRIGGER tr_alerts_audit AFTER INSERT OR UPDATE OR DELETE ON alerts
            FOR EACH ROW EXECUTE FUNCTION log_rls_access();
    """)
    
    # =====================================================
    # 14. POLICIES SPECIALI PER PARTIZIONI READINGS
    # =====================================================
    op.execute("""
        -- Function per applicare RLS alle nuove partizioni readings
        CREATE OR REPLACE FUNCTION apply_rls_to_readings_partition()
        RETURNS EVENT_TRIGGER AS $
        DECLARE
            obj RECORD;
        BEGIN
            -- Applica RLS alle nuove partizioni di readings
            FOR obj IN SELECT * FROM pg_event_trigger_ddl_commands()
            WHERE object_type = 'table' AND schema_name = 'public'
            AND object_identity LIKE 'public.readings_%'
            LOOP
                EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', obj.object_identity);
                -- Le policies vengono ereditate dalla tabella madre
            END LOOP;
        END;
        $ LANGUAGE plpgsql;
        
        -- Event trigger per auto-RLS su nuove partizioni
        CREATE EVENT TRIGGER readings_partition_rls
            ON ddl_command_end
            WHEN tag IN ('CREATE TABLE')
            EXECUTE FUNCTION apply_rls_to_readings_partition();
    """)
    
    # =====================================================
    # 15. FUNZIONI DI UTILITÀ PER TESTING RLS
    # =====================================================
    op.execute("""
        -- Function per testare l'isolamento RLS (solo per development)
        CREATE OR REPLACE FUNCTION test_rls_isolation(
            p_user_id UUID,
            p_organization_id UUID,
            p_role TEXT
        )
        RETURNS TABLE(
            table_name TEXT,
            accessible_rows BIGINT,
            total_rows BIGINT,
            isolation_effective BOOLEAN
        ) AS $
        DECLARE
            original_user_id TEXT;
            original_org_id TEXT;
            original_role TEXT;
        BEGIN
            -- Salva contesto originale
            original_user_id := current_setting('app.current_user_id', true);
            original_org_id := current_setting('app.current_organization_id', true);
            original_role := current_setting('app.current_user_role', true);
            
            -- Imposta nuovo contesto
            PERFORM set_user_context(p_user_id, p_organization_id, p_role);
            
            -- Test su tutte le tabelle principali
            RETURN QUERY
            SELECT 'organizations'::TEXT, 
                   (SELECT count(*) FROM organizations)::BIGINT,
                   (SELECT count(*) FROM organizations)::BIGINT,  -- Dovrebbe essere = accessible
                   TRUE;
                   
            RETURN QUERY
            SELECT 'users'::TEXT,
                   (SELECT count(*) FROM users)::BIGINT,
                   (SELECT count(*) FROM users WHERE organization_id = p_organization_id)::BIGINT,
                   (SELECT count(*) FROM users) <= (SELECT count(*) FROM users WHERE organization_id = p_organization_id);
            
            -- Ripristina contesto originale
            IF original_user_id IS NOT NULL THEN
                PERFORM set_config('app.current_user_id', original_user_id, false);
                PERFORM set_config('app.current_organization_id', original_org_id, false);
                PERFORM set_config('app.current_user_role', original_role, false);
            ELSE
                PERFORM clear_user_context();
            END IF;
        END;
        $ LANGUAGE plpgsql;
    """)

def downgrade() -> None:
    """Rimuove tutte le RLS policies e security functions"""
    
    # =====================================================
    # 1. RIMUOVI EVENT TRIGGERS
    # =====================================================
    op.execute("""
        DROP EVENT TRIGGER IF EXISTS readings_partition_rls;
        DROP FUNCTION IF EXISTS apply_rls_to_readings_partition();
    """)
    
    # =====================================================
    # 2. RIMUOVI AUDIT TRIGGERS
    # =====================================================
    op.execute("""
        DROP TRIGGER IF EXISTS tr_alerts_audit ON alerts;
        DROP TRIGGER IF EXISTS tr_calibrations_audit ON calibrations;
        DROP TRIGGER IF EXISTS tr_sensors_audit ON sensors;
        DROP FUNCTION IF EXISTS log_rls_access();
    """)
    
    # =====================================================
    # 3. RIMUOVI TUTTE LE POLICIES
    # =====================================================
    op.execute("""
        -- Organizations policies
        DROP POLICY IF EXISTS org_creation_policy ON organizations;
        DROP POLICY IF EXISTS org_isolation_policy ON organizations;
        
        -- Users policies
        DROP POLICY IF EXISTS users_update_policy ON users;
        DROP POLICY IF EXISTS users_creation_policy ON users;
        DROP POLICY IF EXISTS users_isolation_policy ON users;
        
        -- Locations policies
        DROP POLICY IF EXISTS locations_modification_policy ON locations;
        DROP POLICY IF EXISTS locations_isolation_policy ON locations;
        
        -- Sensors policies
        DROP POLICY IF EXISTS sensors_status_update_policy ON sensors;
        DROP POLICY IF EXISTS sensors_modification_policy ON sensors;
        DROP POLICY IF EXISTS sensors_isolation_policy ON sensors;
        
        -- Readings policies
        DROP POLICY IF EXISTS readings_viewer_policy ON readings;
        DROP POLICY IF EXISTS readings_update_policy ON readings;
        DROP POLICY IF EXISTS readings_insert_policy ON readings;
        DROP POLICY IF EXISTS readings_isolation_policy ON readings;
        
        -- Alerts policies
        DROP POLICY IF EXISTS alerts_resolution_policy ON alerts;
        DROP POLICY IF EXISTS alerts_creation_policy ON alerts;
        DROP POLICY IF EXISTS alerts_isolation_policy ON alerts;
        
        -- Calibrations policies
        DROP POLICY IF EXISTS calibrations_creation_policy ON calibrations;
        DROP POLICY IF EXISTS calibrations_isolation_policy ON calibrations;
        
        -- Audit log policies
        DROP POLICY IF EXISTS audit_readonly_policy ON audit_log;
        DROP POLICY IF EXISTS audit_creation_policy ON audit_log;
        DROP POLICY IF EXISTS audit_isolation_policy ON audit_log;
    """)
    
    # =====================================================
    # 4. DISABILITA RLS
    # =====================================================
    op.execute("""
        ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY;
        ALTER TABLE calibrations DISABLE ROW LEVEL SECURITY;
        ALTER TABLE alerts DISABLE ROW LEVEL SECURITY;
        ALTER TABLE readings DISABLE ROW LEVEL SECURITY;
        ALTER TABLE sensors DISABLE ROW LEVEL SECURITY;
        ALTER TABLE locations DISABLE ROW LEVEL SECURITY;
        ALTER TABLE users DISABLE ROW LEVEL SECURITY;
        ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
    """)
    
    # =====================================================
    # 5. RIMUOVI FUNCTIONS
    # =====================================================
    op.execute("""
        DROP FUNCTION IF EXISTS test_rls_isolation(UUID, UUID, TEXT);
        DROP FUNCTION IF EXISTS clear_user_context();
        DROP FUNCTION IF EXISTS set_sensor_context(UUID, UUID);
        DROP FUNCTION IF EXISTS set_user_context(UUID, UUID, TEXT);
        DROP FUNCTION IF EXISTS can_access_organization(UUID);
        DROP FUNCTION IF EXISTS current_user_role();
        DROP FUNCTION IF EXISTS current_user_id();
        DROP FUNCTION IF EXISTS current_user_organization_id();
    """)
    
    # =====================================================
    # 6. RIMUOVI ROLES (opzionale - potrebbe causare errori se in uso)
    # =====================================================
    op.execute("""
        -- ATTENZIONE: Questo potrebbe causare errori se i roles sono in uso
        -- Decommenta solo se sei sicuro
        
        -- REVOKE ALL PRIVILEGES ON SCHEMA public FROM ice_pulse_admin;
        -- REVOKE ALL PRIVILEGES ON SCHEMA public FROM ice_pulse_sensor;
        -- REVOKE ALL PRIVILEGES ON SCHEMA public FROM ice_pulse_readonly;
        -- REVOKE ALL PRIVILEGES ON SCHEMA public FROM ice_pulse_app;
        
        -- DROP ROLE IF EXISTS ice_pulse_admin;
        -- DROP ROLE IF EXISTS ice_pulse_sensor;
        -- DROP ROLE IF EXISTS ice_pulse_readonly;
        -- DROP ROLE IF EXISTS ice_pulse_app;
    """)