# Strategy Builder Changelog

All notable changes to the Strategy Builder feature will be documented in this file.

## [Unreleased]

### Added
- User preferences for P/L grid configuration (file: backend/app/api/routes/user_preferences.py)

## [1.2.0] - 2026-01-02

### Changed
- P/L grid column range now uses both current spot AND strikes (file: backend/app/services/pnl_calculator.py)
  - New formula: Min = min(floor(current_spot/100)*100, lowest_strike) - 200
  - New formula: Max = max(ceil(current_spot/100)*100, highest_strike) + 200
  - Generates all 100-point interval columns between Min and Max
- Frontend now sends live current_spot to backend for accurate range calculation (file: frontend/src/stores/strategy.js)

## [1.1.0] - 2024-12-06

### Changed
- Redesigned Strategy Builder UI with full-width layout (file: frontend/src/views/StrategyBuilderView.vue)
- Enhanced P/L grid with dynamic columns (file: frontend/src/components/strategy/PnLGrid.vue)

### Added
- Breakeven columns in P/L grid (file: frontend/src/components/strategy/PnLGrid.vue)
- Linear interpolation for breakeven/strike P&L values (file: frontend/src/stores/strategy.js)
- Live CMP (Current Market Price) display via WebSocket (file: frontend/src/stores/strategy.js)
- Exit P/L calculation per leg (file: frontend/src/components/strategy/StrategyLegRow.vue)
- Manual override for Exit P/L (file: frontend/src/components/strategy/StrategyLegRow.vue)

## [1.0.0] - 2024-12-05

### Added
- Multi-leg strategy builder (file: frontend/src/views/StrategyBuilderView.vue)
- P/L calculator with Black-Scholes pricing (file: backend/app/services/pnl_calculator.py)
- Payoff chart visualization (file: frontend/src/components/strategy/PayoffChart.vue)
- Summary cards (Max Profit, Max Loss, Breakeven, Risk/Reward) (file: frontend/src/views/StrategyBuilderView.vue)
- P/L grid with dynamic spot price columns (file: frontend/src/components/strategy/PnLGrid.vue)
- "At Expiry" and "Current" P/L modes (file: frontend/src/stores/strategy.js)
- Save/Load strategy functionality (file: backend/app/api/routes/strategy.py)
- Share strategy via public links (file: backend/app/api/routes/strategy.py)
- Import positions from broker (file: backend/app/api/routes/orders.py)
- Basket order execution via Kite (file: backend/app/api/routes/orders.py)
- Strategy database models (files: backend/app/models/strategies.py)
- Strategy store (file: frontend/src/stores/strategy.js)
- Strategy components (files: frontend/src/components/strategy/*.vue)
