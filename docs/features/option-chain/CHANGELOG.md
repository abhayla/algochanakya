# Option Chain Changelog

All notable changes to the Option Chain feature will be documented in this file.

## [Unreleased]

## [1.0.0] - 2024-12-06

### Added
- Full option chain display for NIFTY, BANKNIFTY, FINNIFTY (file: frontend/src/views/OptionChainView.vue)
- OI, IV, Greeks calculation (file: backend/app/api/routes/optionchain.py)
- Live data integration via WebSocket (file: frontend/src/stores/optionchain.js)
- Visual OI bars with color coding (file: frontend/src/components/optionchain/OptionChainTable.vue)
- ATM strike highlighting (file: frontend/src/components/optionchain/OptionChainTable.vue)
- ITM/OTM color coding (file: frontend/src/components/optionchain/OptionChainTable.vue)
- PCR and Max Pain calculations (file: backend/app/api/routes/optionchain.py)
- Strike selection for Strategy Builder (file: frontend/src/stores/optionchain.js)
- "Add to Strategy Builder" functionality (file: frontend/src/views/OptionChainView.vue)
- Strike Finder modal with ATM/Delta-based selection (file: frontend/src/components/optionchain/StrikeFinder.vue)
- Greeks toggle (file: frontend/src/views/OptionChainView.vue)
- Option Chain store (file: frontend/src/stores/optionchain.js)

### Fixed
- Breakeven accuracy in P/L calculations (file: backend/app/services/pnl_calculator.py)
