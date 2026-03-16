---
description: >
  Backend services MUST live in subdirectories (autopilot/, ai/, brokers/, options/, legacy/).
  Only 4 named files allowed at services/ root. Enforced by CI and hooks.
globs: ["backend/app/services/**/*.py"]
synthesized: true
private: false
---

# Backend Services Subdirectory Rule

## Enforcement

This rule is enforced by:
- `guard_folder_structure.py` hook (PreToolUse)
- `.github/scripts/validate-structure.py` (CI)

## Allowed at `backend/app/services/` Root

Only these 4 files are permitted at the services root:
- `__init__.py`
- `instruments.py` (legacy)
- `ofo_calculator.py` (legacy)
- `option_chain_service.py` (legacy)

## All Other Services MUST Be in Subdirectories

| Directory | Purpose |
|-----------|---------|
| `autopilot/` | Strategy engine, conditions, adjustments, kill switch, suggestions |
| `ai/` | Regime detection, risk scoring, recommendations, ML pipeline |
| `brokers/` | Order execution adapters, market data adapters, ticker system |
| `options/` | Greeks, P&L, payoff, IV metrics, theta curves |
| `legacy/` | Legacy services pending refactor |
| `deprecated/` | Deprecated services (old ticker singletons) |

## Examples

```
backend/app/services/new_service.py          # BLOCKED by hook
backend/app/services/strategy_builder.py     # BLOCKED — must be in autopilot/
backend/app/services/autopilot/strategy_builder.py  # CORRECT
backend/app/services/options/strike_selector.py      # CORRECT
```

