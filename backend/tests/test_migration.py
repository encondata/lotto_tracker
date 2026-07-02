import os
import subprocess
import sys


def test_no_migration_drift():
    # After `alembic upgrade head`, autogenerate should detect no changes.
    env = {**os.environ,
           "DATABASE_URL": "postgresql+psycopg://lotto:lotto@localhost:5433/lotto"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "check"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
