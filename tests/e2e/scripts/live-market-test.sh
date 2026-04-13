#!/bin/bash
# Live Market Testing Session Launcher
# Usage: bash tests/e2e/scripts/live-market-test.sh [suite]
#   suite: optionchain | strategy | live | all (default: all)
#
# Handles everything autonomously:
#   1. Checks backend/frontend are running (starts them if not)
#   2. Verifies auth state (triggers global-setup if expired)
#   3. Runs the requested test suite with headed browser
#
# Run from project root: D:/Abhay/VibeCoding/algochanakya

set -e

SUITE="${1:-all}"
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================"
echo "  AlgoChanakya Live Market Test Session"
echo "  $(date '+%Y-%m-%d %H:%M:%S IST')"
echo "============================================"
echo ""

# --- Step 1: Check dev servers ---
echo "[1/3] Checking dev servers..."

BACKEND_UP=false
FRONTEND_UP=false

if curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/docs 2>/dev/null | grep -q "200"; then
  BACKEND_UP=true
  echo "  ✓ Backend running on :8001"
else
  echo "  ✗ Backend not running on :8001"
fi

if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null | grep -qE "200|304"; then
  FRONTEND_UP=true
  echo "  ✓ Frontend running on :5173"
else
  echo "  ✗ Frontend not running on :5173"
fi

# Playwright webServer config auto-starts servers if not running (reuseExistingServer: true)
# So we just warn — Playwright will handle startup
if [ "$BACKEND_UP" = false ] || [ "$FRONTEND_UP" = false ]; then
  echo ""
  echo "  → Playwright will auto-start missing servers (may take ~2 min for instrument cache)"
  echo ""
fi

# --- Step 2: Verify auth state ---
echo "[2/3] Checking auth state..."

AUTH_FILE="tests/config/.auth-state.json"
AUTH_VALID=false

if [ -f "$AUTH_FILE" ]; then
  # Check if auth state file is less than 7 hours old (tokens last 8h, leave 1h buffer)
  if [ "$(find "$AUTH_FILE" -mmin -420 2>/dev/null)" ]; then
    echo "  ✓ Auth state exists and is fresh (< 7 hours old)"
    AUTH_VALID=true
  else
    echo "  ✗ Auth state is stale (> 7 hours old) — global-setup will re-login"
  fi
else
  echo "  ✗ No auth state found — global-setup will create it"
fi
echo ""

# --- Step 3: Run tests ---
echo "[3/3] Running tests (suite: $SUITE)..."
echo ""

case "$SUITE" in
  optionchain)
    echo "  Running: Option Chain tests (happy → websocket → greeks → cross-verify)"
    npx playwright test \
      tests/e2e/specs/optionchain/optionchain.happy.spec.js \
      tests/e2e/specs/optionchain/optionchain.websocket.spec.js \
      tests/e2e/specs/optionchain/optionchain.greeks.spec.js \
      tests/e2e/specs/optionchain/optionchain.crossverify.api.spec.js \
      --headed
    ;;
  strategy)
    echo "  Running: Strategy Builder tests (happy → live prices)"
    npx playwright test \
      tests/e2e/specs/strategy/strategy.happy.spec.js \
      tests/e2e/specs/strategy/strategy.liveprices.spec.js \
      --headed
    ;;
  live)
    echo "  Running: Live broker flow tests"
    npx playwright test tests/e2e/specs/live/ --headed
    ;;
  all)
    echo "  Running: Full live session (Option Chain → Strategy → Live Broker Flow)"
    echo ""
    echo "  Phase 1: Option Chain..."
    npx playwright test \
      tests/e2e/specs/optionchain/optionchain.happy.spec.js \
      tests/e2e/specs/optionchain/optionchain.websocket.spec.js \
      tests/e2e/specs/optionchain/optionchain.greeks.spec.js \
      tests/e2e/specs/optionchain/optionchain.crossverify.api.spec.js \
      --headed

    echo ""
    echo "  Phase 2: Strategy Builder..."
    npx playwright test \
      tests/e2e/specs/strategy/strategy.happy.spec.js \
      tests/e2e/specs/strategy/strategy.liveprices.spec.js \
      --headed

    echo ""
    echo "  Phase 3: Live Broker Flow..."
    npx playwright test tests/e2e/specs/live/ --headed
    ;;
  *)
    echo "  Unknown suite: $SUITE"
    echo "  Usage: bash tests/e2e/scripts/live-market-test.sh [optionchain|strategy|live|all]"
    exit 1
    ;;
esac

echo ""
echo "============================================"
echo "  Session complete — $(date '+%H:%M:%S IST')"
echo "============================================"
