"""
Unit tests for alembic-migration-guard.py.

Verifies the guard correctly distinguishes:
  - Real migrations with op.* calls (PASS)
  - Merge migrations with tuple down_revision (PASS — intentional)
  - Intentional no-op migrations with docstring marker (PASS)
  - Silent autogenerate failures (FAIL)

Run: python .github/scripts/tests/test_alembic_migration_guard.py
"""

import sys
import tempfile
from pathlib import Path

# Import the guard module dynamically
GUARD_PATH = Path(__file__).resolve().parents[1] / "alembic-migration-guard.py"
sys.path.insert(0, str(GUARD_PATH.parent))
import importlib.util
spec = importlib.util.spec_from_file_location("guard", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


REAL_MIGRATION = '''
"""add users table"""
from alembic import op
import sqlalchemy as sa

revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('users')
'''

RAW_SQL_MIGRATION = '''
"""raw sql fix"""
from alembic import op

revision = 'abc124'
down_revision = 'abc123'

def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN foo TEXT")

def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN foo")
'''

EMPTY_MIGRATION = '''
"""add new thing"""
from alembic import op

revision = 'abc125'
down_revision = 'abc124'

def upgrade() -> None:
    """Upgrade schema."""
    pass

def downgrade() -> None:
    """Downgrade schema."""
    pass
'''

MERGE_MIGRATION = '''
"""merge two heads"""
from typing import Sequence, Union
from alembic import op

revision: str = 'mergeabc'
down_revision: Union[str, Sequence[str], None] = ('head1', 'head2')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
'''

INTENTIONAL_NOOP_MIGRATION = '''
"""data backfill"""
from alembic import op

revision = 'abc126'
down_revision = 'abc125'

def upgrade() -> None:
    """This migration is intentional no-op; data is backfilled at runtime."""
    pass

def downgrade() -> None:
    pass
'''

EMPTY_DOWNGRADE_ONLY = '''
"""fix missing columns"""
from alembic import op

revision = 'abc127'
down_revision = 'abc126'

def upgrade() -> None:
    op.execute("ALTER TABLE x ADD COLUMN y TEXT")

def downgrade() -> None:
    """Downgrade not supported."""
    pass
'''

MISSING_UPGRADE = '''
"""broken migration"""
from alembic import op

revision = 'abc128'
down_revision = 'abc127'

def downgrade() -> None:
    op.drop_column('users', 'foo')
'''


CASES = [
    ("PASS: real migration with op.create_table", REAL_MIGRATION, []),
    ("PASS: real migration with op.execute raw SQL", RAW_SQL_MIGRATION, []),
    ("PASS: merge migration with tuple down_revision", MERGE_MIGRATION, []),
    ("PASS: intentional no-op with docstring marker", INTENTIONAL_NOOP_MIGRATION, []),
    (
        "PASS: empty downgrade() is allowed (policy: only check upgrade)",
        EMPTY_DOWNGRADE_ONLY,
        [],
    ),
    (
        "FAIL: silently-empty autogenerate output",
        EMPTY_MIGRATION,
        ["upgrade()"],
    ),
    (
        "FAIL: missing upgrade() function",
        MISSING_UPGRADE,
        ["upgrade()"],
    ),
]


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for label, source, expected_substrings in CASES:
            f = tmpdir / f"{label[:20].replace(':', '').replace(' ', '_')}.py"
            f.write_text(source, encoding="utf-8")

            problems = guard.check_migration(f)
            problem_blob = " ".join(problems)

            if not expected_substrings:
                # Expect NO problems
                ok = len(problems) == 0
            else:
                ok = all(sub in problem_blob for sub in expected_substrings)

            status = "OK" if ok else "BAD"
            print(f"[{status}] {label}")
            if not ok:
                failures.append(label)
                print(f"      problems reported: {problems}")

    print()
    if failures:
        print(f"FAILED: {len(failures)} / {len(CASES)}")
        for label in failures:
            print(f"   - {label}")
        return 1
    print(f"OK: all {len(CASES)} cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
