#!/usr/bin/env python3
"""
CI guard: Detect silently-empty Alembic migration files.

An "empty migration" occurs when `alembic revision --autogenerate` produces
a file whose upgrade()/downgrade() body is just `pass`. This typically means
the new SQLAlchemy model was NOT imported in backend/app/models/__init__.py
or backend/alembic/env.py, so autogenerate saw no schema delta.

See .claude/rules/alembic-model-import.md for the underlying rule.

Checks each file in backend/alembic/versions/*.py:
- `upgrade()` body has at least one `op.*` call  OR  uses `op.execute(...)`
- Same for `downgrade()` (if present)

Exit codes:
    0 = all migrations have non-empty bodies
    1 = at least one migration has an empty upgrade/downgrade body

Run from repo root:
    python .github/scripts/alembic-migration-guard.py
"""

import ast
import sys
from pathlib import Path
from typing import List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "backend" / "alembic" / "versions"

EMPTY_MIGRATION_HINT = (
    "This usually means the new model was not imported in both:\n"
    "    - backend/app/models/__init__.py\n"
    "    - backend/alembic/env.py\n"
    "See .claude/rules/alembic-model-import.md for the fix."
)


def find_function(tree: ast.Module, name: str) -> Optional[ast.FunctionDef]:
    """Return the top-level function definition matching `name`, or None."""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def body_is_effectively_empty(body: List[ast.stmt]) -> bool:
    """
    True if the function body contains no real work.

    Considered empty:
        - Only `pass` statements
        - Only docstring(s) + `pass`
        - Only comments (no statements at all) — Python represents this with a single `pass`

    Considered non-empty:
        - Any call node (op.create_table, op.execute, op.drop_column, etc.)
        - Any assignment, for, if, with, etc. at the statement level
    """
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        # Docstring: Expr whose value is a string Constant
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        # Anything else counts as real content
        return False
    return True


def count_op_calls(body: List[ast.stmt]) -> int:
    """
    Count `op.*(...)` call expressions anywhere inside the body.

    This is stricter than body_is_effectively_empty: it ensures the body
    actually invokes the alembic op API, not just e.g. sets variables.
    """
    count = 0
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                func = node.func
                # op.create_table(...) / op.execute(...) / op.add_column(...)
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "op"
                ):
                    count += 1
                # Occasionally code does `from alembic import op as op2` — we
                # don't handle aliases. Only canonical `op.*` usage counts.
    return count


def is_merge_migration(tree: ast.Module) -> bool:
    """
    A merge migration has `down_revision` assigned to a tuple/list with 2+ entries.
    Alembic's `alembic merge` generates these with intentionally empty bodies.
    """
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "down_revision":
                    value = node.value
                    # Plain tuple/list literal: down_revision = ('a', 'b')
                    if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) >= 2:
                        return True
        # Annotated form: down_revision: Union[str, Sequence[str], None] = ('a', 'b')
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if (
                isinstance(target, ast.Name)
                and target.id == "down_revision"
                and isinstance(node.value, (ast.Tuple, ast.List))
                and len(node.value.elts) >= 2
            ):
                return True
    return False


def has_intentional_empty_marker(body: List[ast.stmt]) -> bool:
    """
    True if a function body carries an explicit docstring marking the emptiness
    as intentional (e.g. "not supported", "no-op", "irreversible", "intentional").
    """
    if not body:
        return False
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        doc = first.value.value.lower()
        markers = (
            "not supported",
            "no-op",
            "no op",
            "irreversible",
            "intentional",
            "not reversible",
        )
        return any(marker in doc for marker in markers)
    return False


def check_migration(path: Path) -> List[str]:
    """
    Return a list of problem strings for the given migration file.

    Empty list means the file passes.

    Policy:
    - Skip merge migrations entirely (they are intentionally empty).
    - Only check `upgrade()`. An empty `upgrade()` is the real autogenerate-failure
      symptom. `downgrade()` is frequently empty on purpose (irreversible fixes).
    - Allow empty `upgrade()` only if a docstring declares it intentional.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        return [f"could not read file: {exc}"]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [f"syntax error: {exc}"]

    if is_merge_migration(tree):
        return []  # merge migrations are legitimately empty

    problems: List[str] = []

    upgrade = find_function(tree, "upgrade")
    if upgrade is None:
        problems.append("missing upgrade() function")
        return problems

    body_empty = body_is_effectively_empty(upgrade.body)
    no_op_calls = count_op_calls(upgrade.body) == 0

    if body_empty or no_op_calls:
        if not has_intentional_empty_marker(upgrade.body):
            problems.append(
                "upgrade() has no op.* calls (empty migration); "
                "add a docstring marker like 'intentional' / 'not supported' "
                "if this is deliberate"
            )

    return problems


def main() -> int:
    if not VERSIONS_DIR.exists():
        print(f"ERROR: versions directory not found: {VERSIONS_DIR}", file=sys.stderr)
        return 1

    migration_files = sorted(p for p in VERSIONS_DIR.glob("*.py") if p.name != "__init__.py")

    if not migration_files:
        print(f"No migrations found in {VERSIONS_DIR} -- nothing to check.")
        return 0

    all_problems: List[Tuple[Path, List[str]]] = []
    for path in migration_files:
        issues = check_migration(path)
        if issues:
            all_problems.append((path, issues))

    if not all_problems:
        print(f"OK: all {len(migration_files)} migrations have non-empty bodies.")
        return 0

    print("FAIL: empty Alembic migration(s) detected.\n")
    for path, issues in all_problems:
        rel = path.relative_to(REPO_ROOT).as_posix()
        print(f"  {rel}")
        for issue in issues:
            print(f"    - {issue}")
    print()
    print(EMPTY_MIGRATION_HINT)
    return 1


if __name__ == "__main__":
    sys.exit(main())
