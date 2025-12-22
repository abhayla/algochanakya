# AutoPilot Requirements

## Core Requirements (Phase 1-2)
- [x] Create AutoPilot strategies with conditional entry
- [x] Entry conditions: TIME, SPOT, VIX, PREMIUM, DELTA
- [x] Entry schedule configuration
- [x] Multi-leg strategy configuration
- [x] Strategy activation/pause/exit
- [x] Real-time position monitoring
- [x] Live P&L tracking
- [x] WebSocket updates for strategy status

## Condition Engine (Phase 1-2)
- [x] Evaluate TIME conditions (before/after/between)
- [x] Evaluate SPOT conditions (above/below/between)
- [x] Evaluate VIX conditions
- [x] Evaluate PREMIUM conditions
- [x] Evaluate DELTA conditions
- [x] Combine conditions with AND/OR logic
- [x] Real-time condition evaluation progress

## Order Execution (Phase 1-2)
- [x] Place orders via Kite Connect
- [x] Sequential order execution
- [x] Simultaneous order execution
- [x] Retry logic for failed orders
- [x] Order status tracking
- [x] Slippage tracking

## Background Monitoring (Phase 1-2)
- [x] Strategy monitor service (5s polling interval)
- [x] Evaluate entry conditions
- [x] Execute entries when conditions met
- [x] Execute exits when requested
- [x] Update strategy status

## WebSocket Updates (Phase 1-2)
- [x] STRATEGY_UPDATE messages
- [x] PNL_UPDATE messages
- [x] CONDITION_EVALUATED messages
- [x] ORDER_PLACED messages
- [x] ORDER_FILLED messages
- [x] RISK_ALERT messages
- [x] Per-user connection management

## Risk Management (Phase 3)
- [x] Kill switch - Emergency stop all strategies
- [x] Daily loss limit
- [x] Max positions limit
- [x] Semi-auto mode with manual confirmations
- [x] Confirmation requests via WebSocket

## Adjustment Engine (Phase 3)
- [x] 7 adjustment trigger types (DELTA_BREACH, SPOT_DISTANCE, etc.)
- [x] 7 adjustment action types (HEDGE_LEG, ROLL_LEG, SCALE_IN, etc.)
- [x] Adjustment rule configuration
- [x] Automatic adjustment execution
- [x] Adjustment logging

## Auto-Exit & Re-entry (Phase 3)
- [x] Profit target exit
- [x] Stop loss exit
- [x] DTE-based exit
- [x] Trailing stop loss
- [x] Re-entry conditions
- [x] Re-entry cooldown period

## Analytics & Reports (Phase 4)
- [x] Trade journal (automatic logging)
- [x] Analytics dashboard
- [x] Performance metrics
- [x] Daily/Weekly/Monthly/Custom reports
- [x] Tax reports
- [x] PDF/Excel/CSV export

## Backtesting (Phase 4)
- [x] Historical strategy testing
- [x] Backtest configuration
- [x] Backtest results storage
- [x] Performance metrics from backtest

## Templates (Phase 4)
- [x] AutoPilot strategy templates
- [x] Template sharing
- [x] Template ratings
- [x] Community templates

## Advanced Adjustments (Phase 5)
- [x] Position leg tracking with Greeks
- [x] Delta monitoring per leg
- [x] Delta alerts
- [x] AI adjustment suggestions
- [x] Confidence scoring for suggestions
- [x] Strike finder integration
- [x] Staged entry configuration
- [x] Gamma risk monitoring
- [x] IV skew analysis

## API Requirements
- [x] GET /api/v1/autopilot/strategies - List strategies
- [x] POST /api/v1/autopilot/strategies - Create strategy
- [x] PUT /api/v1/autopilot/strategies/{id} - Update strategy
- [x] DELETE /api/v1/autopilot/strategies/{id} - Delete strategy
- [x] POST /api/v1/autopilot/strategies/{id}/activate - Activate strategy
- [x] POST /api/v1/autopilot/strategies/{id}/pause - Pause strategy
- [x] POST /api/v1/autopilot/strategies/{id}/exit - Exit strategy
- [x] GET /api/v1/autopilot/dashboard/summary - Dashboard summary
- [x] GET /api/v1/autopilot/orders - Order history
- [x] GET /api/v1/autopilot/logs - Activity logs
- [x] POST /api/v1/autopilot/kill-switch - Kill switch
- [x] POST /api/v1/autopilot/confirmations/{id}/respond - Confirmation response
- [x] GET /api/v1/autopilot/templates - Templates
- [x] GET /api/v1/autopilot/analytics/* - Analytics endpoints
- [x] GET/POST /api/v1/autopilot/reports - Reports endpoints
- [x] GET/POST /api/v1/autopilot/backtests - Backtest endpoints
- [x] GET/POST /api/v1/autopilot/suggestions - Suggestion endpoints

## UI Requirements
- [x] Dashboard view with active strategies
- [x] Strategy Builder view for creating strategies
- [x] Strategy Detail view for monitoring
- [x] Settings view for user preferences
- [x] Analytics view for performance insights
- [x] Reports view for report generation
- [x] Trade Journal view
- [x] Backtests view
- [x] Order History view
- [x] Template Library view
- [x] Shared Strategies view

## Data Requirements (16 tables)
- [x] autopilot_strategies
- [x] autopilot_orders
- [x] autopilot_logs
- [x] autopilot_templates
- [x] autopilot_user_settings
- [x] autopilot_daily_summary
- [x] autopilot_condition_eval
- [x] autopilot_adjustment_logs
- [x] autopilot_pending_confirmations
- [x] autopilot_position_legs
- [x] autopilot_adjustment_suggestions
- [x] autopilot_trade_journal
- [x] autopilot_backtests
- [x] autopilot_reports
- [x] autopilot_template_ratings
- [x] autopilot_shared_strategies

## Testing Requirements
- [x] ~100+ E2E tests for AutoPilot
- [x] Phase-specific test suites
- [x] Integration tests
- [x] API tests

---
Last updated: 2025-12-22
