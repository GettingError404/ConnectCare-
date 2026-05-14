import os
import subprocess
import pytest


def _has_db():
    return bool(os.getenv("DATABASE_URL"))


@pytest.mark.skipif(not _has_db(), reason="DATABASE_URL not configured")
def test_alembic_upgrade_head_and_downgrade():
    # Run alembic upgrade head
    res = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    assert res.returncode == 0, f"alembic upgrade failed: {res.stdout}\n{res.stderr}"

    # then downgrade to base and upgrade again to validate migrations are reversible
    res2 = subprocess.run(["alembic", "downgrade", "base"], capture_output=True, text=True)
    assert res2.returncode == 0, f"alembic downgrade failed: {res2.stdout}\n{res2.stderr}"

    res3 = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    assert res3.returncode == 0, f"alembic upgrade (second) failed: {res3.stdout}\n{res3.stderr}"
