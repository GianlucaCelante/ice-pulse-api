# test_alembic_commands.py
from alembic.config import Config
from alembic import command
import io
import sys

print("=== ALEMBIC COMMANDS TEST ===")

# Capture alembic output
def capture_alembic_command(func, *args, **kwargs):
    """Capture output from alembic commands"""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = buffer = io.StringIO()
    sys.stderr = error_buffer = io.StringIO()
    
    try:
        result = func(*args, **kwargs)
        output = buffer.getvalue()
        errors = error_buffer.getvalue()
        return output, errors, None
    except Exception as e:
        output = buffer.getvalue()
        errors = error_buffer.getvalue()
        return output, errors, str(e)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

# Test alembic commands
cfg = Config('alembic.ini')

print("\n1. ALEMBIC CURRENT:")
output, errors, exception = capture_alembic_command(command.current, cfg, verbose=True)
print(f"Output: {output}")
print(f"Errors: {errors}")
if exception:
    print(f"Exception: {exception}")

print("\n2. ALEMBIC HISTORY:")
output, errors, exception = capture_alembic_command(command.history, cfg, verbose=True)
print(f"Output: {output}")
print(f"Errors: {errors}")
if exception:
    print(f"Exception: {exception}")

print("\n3. ALEMBIC HEADS:")
output, errors, exception = capture_alembic_command(command.heads, cfg, verbose=True)
print(f"Output: {output}")
print(f"Errors: {errors}")
if exception:
    print(f"Exception: {exception}")

print("\n=== TEST COMPLETE ===")