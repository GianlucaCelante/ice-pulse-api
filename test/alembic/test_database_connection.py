# test_database_connection.py
import os
import psycopg2

print("=== DATABASE CONNECTION TEST ===")

# Test environment variables
print("\n1. ENVIRONMENT VARIABLES:")
env_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
for var in env_vars:
    value = os.getenv(var, 'NOT SET')
    if var == 'DB_PASSWORD':
        value = '***' if value != 'NOT SET' else 'NOT SET'
    print(f"{var}: {value}")

# Test database connection
print("\n2. DATABASE CONNECTION:")
try:
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    database = os.getenv('DB_NAME', 'icepulse')
    user = os.getenv('DB_USER', 'icepulse')
    password = os.getenv('DB_PASSWORD', 'password123')
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT version();")
    version_row = cursor.fetchone()
    if version_row is not None:
        version = version_row[0]
        print(f"✅ Connection successful")
        print(f"PostgreSQL version: {version}")
    else:
        print("✅ Connection successful, but could not fetch PostgreSQL version.")
    
    # Check alembic_version table
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'alembic_version'
        );
    """)
    result = cursor.fetchone()
    alembic_table_exists = result[0] if result is not None else False
    print(f"alembic_version table exists: {alembic_table_exists}")
    
    if alembic_table_exists:
        cursor.execute("SELECT version_num FROM alembic_version;")
        versions = cursor.fetchall()
        if versions:
            print(f"Current alembic version: {versions}")
        else:
            print("alembic_version table is empty")
    
    # List all tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables in database: {tables}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")

print("\n=== TEST COMPLETE ===")