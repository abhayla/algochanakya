# AutoPilot Changelog

All notable changes to the AutoPilot feature will be documented in this file.

## [Unreleased]

## [Phase 5] - 2024-12-20

### Added
- Position leg tracking with Greeks (files: backend/app/models/autopilot.py, backend/app/api/v1/autopilot/legs.py)
- Delta monitoring per leg with alerts (file: backend/app/services/greeks_calculator.py)
- AI adjustment suggestions with confidence scoring (files: backend/app/services/suggestion_engine.py, backend/app/api/v1/autopilot/suggestions.py)
- Strike finder integration (file: backend/app/api/v1/autopilot/option_chain.py)
- Staged entry configuration (file: frontend/src/components/autopilot/builder/StagedEntryConfig.vue)
- Gamma risk monitoring and alerts (file: frontend/src/components/autopilot/monitoring/GammaRiskAlert.vue)
- IV skew analysis (file: backend/app/services/market_data.py)
- Delta band gauge visualization (file: frontend/src/components/autopilot/monitoring/DeltaBandGauge.vue)
- DTE zone indicator (file: frontend/src/components/autopilot/monitoring/DTEZoneIndicator.vue)
- Suggestion cards UI (file: frontend/src/components/autopilot/suggestions/SuggestionCard.vue)
- Leg action modals (file: frontend/src/components/autopilot/legs/LegActionModals.vue)

## [Phase 4] - 2024-12-18

### Added
- Trade journal with automatic logging (files: backend/app/models/autopilot.py, frontend/src/views/autopilot/TradeJournalView.vue)
- Analytics dashboard with performance metrics (files: backend/app/api/v1/autopilot/analytics.py, frontend/src/views/autopilot/AnalyticsView.vue)
- Daily/Weekly/Monthly/Custom reports (files: backend/app/api/v1/autopilot/router.py, frontend/src/views/autopilot/ReportsView.vue)
- PDF/Excel/CSV report export (file: backend/app/api/v1/autopilot/router.py)
- Tax reports generation (file: backend/app/api/v1/autopilot/router.py)
- Backtesting functionality (files: backend/app/api/v1/autopilot/router.py, frontend/src/views/autopilot/BacktestsView.vue)
- AutoPilot strategy templates (file: backend/app/models/autopilot.py)
- Template sharing and ratings (files: frontend/src/views/autopilot/TemplateLibraryView.vue, SharedStrategiesView.vue)
- Analytics panel component (file: frontend/src/components/autopilot/analytics/AnalyticsPanel.vue)
- Adjustment cost tracking (file: frontend/src/components/autopilot/analytics/AdjustmentCostCard.vue)

## [Phase 3] - 2024-12-16

### Added
- Kill switch for emergency stop (files: backend/app/api/v1/autopilot/router.py, frontend/src/components/autopilot/common/KillSwitchPanel.vue)
- Semi-auto mode with manual confirmations (file: backend/app/models/autopilot.py)
- Adjustment engine with 7 trigger types (file: backend/app/services/adjustment_engine.py)
- 7 adjustment action types (HEDGE_LEG, ROLL_LEG, SCALE_IN, etc.) (file: backend/app/services/adjustment_engine.py)
- Profit target and stop loss auto-exit (file: backend/app/services/strategy_monitor.py)
- DTE-based exit (file: backend/app/services/strategy_monitor.py)
- Trailing stop loss (file: backend/app/services/strategy_monitor.py)
- Re-entry conditions and cooldown (file: backend/app/models/autopilot.py)
- Adjustment logs tracking (file: backend/app/models/autopilot.py)
- Confirmation request handling via WebSocket (file: backend/app/websocket/manager.py)
- Risk overview panel (file: frontend/src/components/autopilot/dashboard/RiskOverviewPanel.vue)
- Re-entry configuration UI (file: frontend/src/components/autopilot/builder/ReentryConfig.vue)

## [Phase 2] - 2024-12-14

### Added
- WebSocket real-time updates for strategy status (file: backend/app/websocket/manager.py)
- 30+ WebSocket message types (file: backend/app/constants/websocket.py)
- Background strategy monitor service (file: backend/app/services/strategy_monitor.py)
- Order executor with retry logic (file: backend/app/services/order_executor.py)
- Condition evaluation progress tracking (file: backend/app/models/autopilot.py)
- Live P&L tracking (file: backend/app/services/strategy_monitor.py)
- Order status tracking with slippage (file: backend/app/models/autopilot.py)
- Activity timeline component (file: frontend/src/components/autopilot/dashboard/ActivityTimeline.vue)
- Market status indicator (file: frontend/src/components/autopilot/dashboard/MarketStatusIndicator.vue)
- Strategy detail view for real-time monitoring (file: frontend/src/views/autopilot/StrategyDetailView.vue)

## [Phase 1] - 2024-12-12

### Added
- AutoPilot core strategy builder (file: frontend/src/views/autopilot/StrategyBuilderView.vue)
- Entry condition builder (TIME, SPOT, VIX, PREMIUM, DELTA) (file: frontend/src/components/autopilot/builder/ConditionBuilder.vue)
- Condition engine for evaluation (file: backend/app/services/condition_engine.py)
- AutoPilot database models (file: backend/app/models/autopilot.py)
- Strategy CRUD API endpoints (file: backend/app/api/v1/autopilot/router.py)
- AutoPilot dashboard (file: frontend/src/views/autopilot/DashboardView.vue)
- Strategy list with status badges (file: frontend/src/components/autopilot/dashboard/EnhancedStrategyCard.vue)
- Activate/Pause/Exit actions (file: backend/app/api/v1/autopilot/router.py)
- Market data service (file: backend/app/services/market_data.py)
- AutoPilot store (file: frontend/src/stores/autopilot.js)
- AutoPilot legs table (file: frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue)
- Settings view for user risk limits (file: frontend/src/views/autopilot/SettingsView.vue)
