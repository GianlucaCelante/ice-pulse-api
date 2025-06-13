# test_migrations.py
import glob
import importlib.util

print("=== Testing migration files ===")

for f in glob.glob('alembic/versions/*.py'):
    print(f'Testing {f}...')
    try:
        with open(f) as file:
            compile(file.read(), f, 'exec')
        print('✅ Syntax OK')
        
        # Test import
        spec = importlib.util.spec_from_file_location('test', f)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {f}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f'  Revision: {module.revision}')
        print(f'  Down revision: {module.down_revision}')
        
    except Exception as e:
        print(f'❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        break

print("=== Done ===")