#!/usr/bin/env bash
# cleanup.sh — AlgoChanakya filesystem cleanup
#
# Removes gitignored artifacts that accumulate during development:
# tmpclaude dirs, debug scripts, screenshots, test artifact dirs, etc.
#
# Usage:
#   bash scripts/cleanup.sh            # Execute cleanup
#   bash scripts/cleanup.sh --dry-run  # Preview only (no deletions)
#
# SAFE: Only deletes gitignored files. Never touches production.

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

DELETED_COUNT=0
DELETED_BYTES=0

# ── Helpers ───────────────────────────────────────────────────────────────────

log_info()  { echo "  [info]  $*"; }
log_del()   { echo "  [del]   $*"; }
log_skip()  { echo "  [skip]  $*"; }
log_dry()   { echo "  [dry]   would delete: $*"; }

# Remove a file. Counts bytes before deleting.
rm_file() {
    local f="$1"
    if [[ ! -e "$f" && ! -L "$f" ]]; then
        return 0
    fi
    local size
    size=$(stat -c%s "$f" 2>/dev/null || echo 0)
    if $DRY_RUN; then
        log_dry "$f (${size} bytes)"
    else
        rm -f -- "$f" && log_del "$f" || log_info "could not remove: $f"
    fi
    DELETED_COUNT=$((DELETED_COUNT + 1))
    DELETED_BYTES=$((DELETED_BYTES + size))
}

# Remove a directory tree. Estimates size (avoids slow find for large dirs).
rm_dir() {
    local d="$1"
    if [[ ! -d "$d" ]]; then
        return 0
    fi
    local size
    size=$(du -sb "$d" 2>/dev/null | cut -f1 || echo 0)
    if $DRY_RUN; then
        log_dry "$d/ (~${size} bytes)"
    else
        rm -rf -- "$d" && log_del "$d/" || log_info "could not remove: $d/"
    fi
    DELETED_COUNT=$((DELETED_COUNT + 1))
    DELETED_BYTES=$((DELETED_BYTES + size))
}

# ── Production Safety Guard ───────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ "$PROJECT_ROOT" == *"/Apps/algochanakya"* ]]; then
    echo "ERROR: Refusing to run in production folder: $PROJECT_ROOT"
    echo "       This script is only safe in the dev working directory."
    exit 1
fi

cd "$PROJECT_ROOT"
echo ""
echo "AlgoChanakya Cleanup Script"
echo "Project root: $PROJECT_ROOT"
if $DRY_RUN; then
    echo "Mode: DRY RUN (no files will be deleted)"
else
    echo "Mode: EXECUTE"
fi
echo ""

# ── Section 1: Corrupted / garbage filenames ──────────────────────────────────

echo "=== Section 1: Corrupted filenames ==="

# Shell expansion artifacts: {, and 80%
rm_file "{,"
rm_file "80%"
# Windows reserved device name (sometimes created as 0-byte file)
if [[ -f "nul" ]]; then
    rm_file "nul"
elif [[ -f "NUL" ]]; then
    rm_file "NUL"
fi
# Windows path mangling artifacts (D?AbhayVibeCoding*, C?AbhayVideCoding*)
for f in D?AbhayVibeCoding* C?AbhayVideCoding* D?AbhayVideCoding* C?AbhayVibeCoding*; do
    [[ -e "$f" ]] && rm_file "$f"
done
# Backend-level corrupted files
for f in backend/nul backend/NUL; do
    [[ -e "$f" ]] && rm_file "$f"
done

echo ""

# ── Section 2: tmpclaude working directories ───────────────────────────────────

echo "=== Section 2: tmpclaude temporary directories ==="

# Root-level tmpclaude dirs
for d in tmpclaude-*/; do
    [[ -d "$d" ]] && rm_dir "${d%/}"
done

# Backend-level tmpclaude dirs (if any)
for d in backend/tmpclaude-*/; do
    [[ -d "$d" ]] && rm_dir "${d%/}"
done

echo ""

# ── Section 3: Debug scripts at root ─────────────────────────────────────────

echo "=== Section 3: Root-level debug scripts ==="

# Explicit list — broad *.cjs glob risks catching legitimate files
ROOT_DEBUG_SCRIPTS=(
    "analyze-failures.cjs"
    "check-console-errors.cjs"
    "debug-api-call.cjs"
    "final-test.cjs"
    "login-and-open-dashboard.js"
    "open-dashboard.cjs"
    "open-dashboard-live.cjs"
    "open-dashboard-with-auth-state.cjs"
    "test-autopilot-api.cjs"
    "test-autopilot-orders.cjs"
    "test-cmp-fix.cjs"
    "test-cmp-fix.js"
    "test-iron-condor.cjs"
    "test-token.cjs"
    "verify-api.cjs"
    "verify-dashboard.cjs"
    "verify-positions.cjs"
    "verify-strategy.cjs"
    "test-analytics-api.js"
    "test-regime-api.js"
    "test_recommendations_api.ps1"
    "manual-test-strike-finders.js"
    "test-strike-finders.js"
    "test_strike_finder_fix.js"
)

for f in "${ROOT_DEBUG_SCRIPTS[@]}"; do
    rm_file "$f"
done

echo ""

# ── Section 4: Root-level screenshots ────────────────────────────────────────

echo "=== Section 4: Root-level PNG screenshots ==="

# *.png at root is safe — these are always gitignored artifacts
# (real assets live in frontend/src/assets/ or docs/assets/screenshots/)
for f in *.png; do
    [[ -f "$f" ]] && rm_file "$f"
done

echo ""

# ── Section 5: Ad-hoc screenshots/ directory at root ─────────────────────────

echo "=== Section 5: Root-level screenshots/ directory ==="

rm_dir "screenshots"

echo ""

# ── Section 6: Root-level report markdown files ───────────────────────────────

echo "=== Section 6: Root-level *_REPORT.md files ==="

for f in *_REPORT.md; do
    [[ -f "$f" ]] && rm_file "$f"
done

echo ""

# ── Section 7: Root-level logs and output files ───────────────────────────────

echo "=== Section 7: Root-level logs and output files ==="

ROOT_LOG_FILES=(
    "test-output.txt"
    "autopilot-test-results.txt"
    "paper-trading-test-summary.md"
    "TESTING-QUICK-START.md"
    "backend.log"
)

for f in "${ROOT_LOG_FILES[@]}"; do
    rm_file "$f"
done

# Also catch any *-output.txt files
for f in *-output.txt; do
    [[ -f "$f" ]] && rm_file "$f"
done

echo ""

# ── Section 8: Test artifact directories ─────────────────────────────────────

echo "=== Section 8: Test artifact directories ==="

rm_dir "allure-results"
rm_dir "test-results"
rm_dir "playwright-report"
rm_dir "frontend/dist"

echo ""

# ── Section 9: Backend stale files ───────────────────────────────────────────

echo "=== Section 9: Backend stale files ==="

BACKEND_STALE_FILES=(
    "backend/backend_test.txt"
    "backend/fix_tests.py"
    "backend/fix_test_mocks.py"
    "backend/phase5_test_results.txt"
    "backend/requirements_clean.txt"
    "backend/requirements_fixed.txt"
    "backend/test_db_connection.py"
    "backend/test_phase1_strike_selection.py"
    "backend/backend.log"
    "backend/.coverage"
    "backend/scripts/find_strategy.py"
    "backend/scripts/delete_test_strategies.py"
)

for f in "${BACKEND_STALE_FILES[@]}"; do
    rm_file "$f"
done

# Backend wildcard test scripts (test_*.py in backend root, not in tests/)
for f in backend/test_*.py; do
    [[ -f "$f" ]] && rm_file "$f"
done

echo ""

# ── Section 10: E2E debug screenshots ────────────────────────────────────────

echo "=== Section 10: E2E debug screenshots ==="

# tests/e2e/screenshots/ contains ad-hoc debug captures (not visual regression baselines)
# Visual regression baselines are in tests/e2e/specs/*-snapshots/ — NOT touched here
rm_dir "tests/e2e/screenshots"

# Also clean legacy tests/screenshots/ if present
rm_dir "tests/screenshots"

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────

echo "========================================"
if $DRY_RUN; then
    echo "DRY RUN complete."
    echo "Would delete: ${DELETED_COUNT} items (~${DELETED_BYTES} bytes)"
    echo ""
    echo "To execute: bash scripts/cleanup.sh"
else
    echo "Cleanup complete."
    echo "Deleted: ${DELETED_COUNT} items (~${DELETED_BYTES} bytes freed)"
fi
echo ""
echo "NOT touched (intentional):"
echo "  - docs/assets/screenshots/    (documentation assets)"
echo "  - tests/e2e/specs/*-snapshots/ (visual regression baselines)"
echo "  - .claude/ contents           (skills, hooks, sessions)"
echo "  - backend/logs/               (structured application logs)"
echo "  - frontend/src/               (source files)"
echo "  - C:\\Apps\\algochanakya        (production — never touched)"
echo ""
