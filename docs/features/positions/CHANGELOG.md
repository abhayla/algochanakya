# Positions Changelog

All notable changes to the Positions feature will be documented in this file.

## [Unreleased]

## [1.0.0] - 2024-12-05

### Added
- F&O Positions view with real-time P&L (file: frontend/src/views/PositionsView.vue)
- Day/Net position toggle (file: frontend/src/views/PositionsView.vue)
- Live P&L calculation using WebSocket prices (file: frontend/src/stores/positions.js)
- Total P&L summary box with color coding (file: frontend/src/views/PositionsView.vue)
- Summary bar with positions count, quantity, realized/unrealized P&L (file: frontend/src/views/PositionsView.vue)
- Exit modal for closing positions (file: frontend/src/components/positions/ExitModal.vue)
- Add modal for increasing position size (file: frontend/src/components/positions/AddModal.vue)
- Exit All functionality with confirmation (file: frontend/src/views/PositionsView.vue)
- Auto-refresh toggle (5 second interval) (file: frontend/src/stores/positions.js)
- Empty state with link to Option Chain (file: frontend/src/views/PositionsView.vue)
- Positions API routes (file: backend/app/api/routes/positions.py)
- Positions store (file: frontend/src/stores/positions.js)
