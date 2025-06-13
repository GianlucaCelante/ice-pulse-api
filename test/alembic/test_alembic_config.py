# test_alembic_config.py
import os
from alembic.config import Config
from alembic.script import ScriptDirectory

print("=== ALEMBIC CONFIGURATION TEST ===")

# Test 1: File paths
print("\n1. FILE PATHS:")
print(f"Current dir: {os.getcwd()}")
print(f"alembic.ini exists: {os.path.exists('alembic.ini')}")
print(f"alembic/ dir exists: {os.path.exists('alembic')}")
print(f"alembic/versions/ exists: {os.path.exists('alembic/versions')}")

if os.path.exists('alembic/versions'):
    files = [f for f in os.listdir('alembic/versions') if f.endswith('.py')]
    print(f"Migration files: {files}")

# Test 2: Alembic config
print("\n2. ALEMBIC CONFIG:")
try:
    cfg = Config('alembic.ini')
    print(f"Script location: {cfg.get_main_option('script_location')}")
    print(f"Version locations: {cfg.get_main_option('version_locations')}")
    print("✅ Config loaded successfully")
except Exception as e:
    print(f"❌ Config error: {e}")

# Test 3: Script directory
print("\n3. SCRIPT DIRECTORY:")
try:
    cfg = Config('alembic.ini')
    script = ScriptDirectory.from_config(cfg)
    print(f"Script dir path: {script.dir}")
    print(f"Versions dir(s): {script.versions}")  # script.versions is a list of version directories
    
    revisions = list(script.walk_revisions())
    print(f"Revisions found: {len(revisions)}")
    
    for rev in revisions:
        print(f"  - {rev.revision}: {rev.doc[:50] if rev.doc else 'No description'}")
        
    if len(revisions) == 0:
        print("❌ NO REVISIONS FOUND!")
    else:
        print("✅ Revisions loaded successfully")
        
except Exception as e:
    print(f"❌ Script directory error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== TEST COMPLETE ===")