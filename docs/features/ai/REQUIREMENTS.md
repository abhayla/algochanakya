# AI Configuration Requirements

This document tracks the implementation status of AI Configuration & Settings feature requirements.

## Database Requirements

- [x] `ai_user_config` table with user relationship
- [x] JSONB storage for confidence_tiers and allowed_strategies
- [x] PostgreSQL ARRAY for deploy_days and preferred_underlyings
- [x] Unique constraint on user_id (one config per user)
- [x] CHECK constraints for validation (confidence 0-100, lots > 0, VIX > 0)
- [x] Migration 010_ai_week2_user_config.py with up/downgrade
- [x] Default values for all configuration fields
- [x] Encrypted Claude API key storage (column exists, encryption TBD)

## API Requirements

### Configuration Management
- [x] GET /api/v1/ai/config - Get user configuration
- [x] PUT /api/v1/ai/config - Update configuration
- [x] GET /api/v1/ai/config/defaults - Get default configuration template

### Strategy Management
- [x] GET /api/v1/ai/config/strategies - Get allowed strategy templates
- [x] PUT /api/v1/ai/config/strategies - Update allowed strategies

### Position Sizing
- [x] GET /api/v1/ai/config/sizing - Get position sizing configuration
- [x] PUT /api/v1/ai/config/sizing - Update position sizing

### Validation & Status
- [x] POST /api/v1/ai/config/validate-claude - Validate Claude API key
- [x] GET /api/v1/ai/config/paper-trading/status - Get graduation status

## Data Models

- [x] AIUserConfig SQLAlchemy model with all fields
- [x] User model relationship (back_populates)
- [x] Pydantic schema: AIUserConfigResponse
- [x] Pydantic schema: AIUserConfigUpdate (partial updates)
- [x] Pydantic schema: AIConfigDefaults
- [x] Pydantic schema: PositionSizingConfig with validation
- [x] Pydantic schema: DeploymentScheduleConfig
- [x] Pydantic schema: AILimitsConfig
- [x] Pydantic schema: ConfidenceTier
- [x] Pydantic schema: PaperTradingStatus
- [x] Pydantic schema: ClaudeKeyValidationRequest
- [x] Pydantic schema: ClaudeKeyValidationResponse

## Service Layer

- [x] AIConfigService class with static methods
- [x] get_or_create_config() - Create defaults if missing
- [x] update_config() - Partial updates support
- [x] validate_allowed_strategies() - Strategy ID validation
- [x] get_confidence_tier() - Find tier for confidence score
- [x] calculate_lots_for_confidence() - Lot size calculation
- [x] should_deploy_today() - Deployment day checking
- [x] is_within_limits() - Limit validation
- [x] validate_claude_api_key() - API key testing with Anthropic client
- [x] get_paper_trading_status() - Graduation status
- [x] can_graduate_to_live() - Graduation criteria checking

## Frontend Store

- [x] Pinia store: useAIConfigStore
- [x] State: config, loading, saving, error, validationErrors
- [x] State: claudeKeyValid, claudeKeyValidating
- [x] State: paperTradingStatus, defaultConfig, availableStrategies
- [x] Getter: isAIEnabled
- [x] Getter: autonomyMode
- [x] Getter: canGraduateToLive (graduation criteria check)
- [x] Getter: confidenceTierForScore
- [x] Getter: lotsForConfidence (with tier calculation)
- [x] Getter: shouldDeployToday
- [x] Getter: graduationProgress
- [x] Action: fetchConfig()
- [x] Action: saveConfig()
- [x] Action: fetchDefaults()
- [x] Action: fetchAvailableStrategies()
- [x] Action: updateStrategies()
- [x] Action: updateSizing()
- [x] Action: validateClaudeKey()
- [x] Action: fetchPaperTradingStatus()
- [x] Action: resetToDefaults()
- [x] Action: clearError()

## UI Components

### Main View
- [x] AISettingsView.vue - Main configuration page
- [x] Header with title and description
- [x] Loading state display
- [x] Error state display
- [x] Save/Reset action buttons

### Autonomy Settings Panel
- [x] AI Enabled toggle switch (Tailwind styled)
- [x] Paper/Live mode radio buttons
- [x] Live mode disabled until graduation
- [x] Graduation requirement message

### Deployment Schedule Panel
- [x] Auto-deploy toggle checkbox
- [x] Deploy time input (HH:MM format)
- [x] Deploy days checkboxes (Mon-Fri)
- [x] Skip event days checkbox
- [x] Skip weekly expiry checkbox

### Position Sizing Panel
- [x] Sizing mode dropdown (Fixed/Tiered/Kelly)
- [x] Base lots number input
- [x] Confidence tiers display (simplified for Week 2)
- [ ] Advanced tier editor (Phase 3 - deferred)

### Trading Limits Panel
- [x] Max lots per strategy input
- [x] Max lots per day input
- [x] Max strategies per day input
- [x] Min confidence percentage input
- [x] Max VIX input
- [x] Weekly loss limit input (currency)
- [x] 2-column grid layout

## UI/UX Features

- [x] Auto-save with 2-second debounce
- [x] Manual save button
- [x] Reset to defaults with confirmation
- [x] Form validation (min/max constraints)
- [x] Responsive grid layouts
- [x] All inputs have data-testid attributes
- [x] Loading spinner during fetch
- [x] Error message display
- [x] Success feedback (via store state)

## Validation

### Frontend Validation
- [x] Number inputs with min/max constraints
- [x] Time format validation (HH:MM)
- [x] At least one deploy day selected
- [x] Confidence range 0-100
- [x] Positive values for limits

### Backend Validation
- [x] Pydantic field validators for ranges
- [x] Confidence tier gap/overlap checking
- [x] Tier range validation (must cover 0-100)
- [x] Strategy ID existence checking
- [x] Deploy days enum validation
- [x] Database CHECK constraints

## Navigation & Routing

- [x] Route registered at /ai/settings
- [x] Route requires authentication
- [x] Navigation link in KiteHeader
- [x] Brain icon for AI Settings
- [x] data-testid on nav link
- [x] Active route highlighting

## Business Logic

### Position Sizing
- [x] Fixed sizing mode - Returns base_lots
- [x] Tiered sizing mode - Multiplier-based calculation
- [x] Confidence threshold checking
- [ ] Kelly Criterion mode (Placeholder for Week 9)

### Deployment Rules
- [x] Day of week checking
- [x] Event day detection (via MarketRegimeClassifier)
- [x] Weekly expiry skip (Thursday)
- [x] Auto-deploy enabled check

### Limit Enforcement
- [x] Daily lots limit checking
- [x] Daily strategies limit checking
- [x] VIX limit checking
- [x] Weekly loss limit checking
- [x] Returns list of violations

### Paper Trading Graduation
- [x] 25 trades requirement
- [x] 55% win rate requirement
- [x] 15 days requirement
- [x] Manual approval flag
- [x] Progress calculation
- [ ] Automated trade tracking (Week 4 - trade journal integration)

## Integration

- [x] Router integration (frontend/src/router/index.js)
- [x] Header navigation integration
- [x] API router registration (backend/app/api/v1/ai/router.py)
- [x] Model __init__.py imports
- [x] User model relationship added
- [ ] AutoPilot integration (Week 3 - strategy deployment)
- [ ] Strategy Builder integration (Week 3 - position sizing)

## Testing

- [x] Backend API manually tested
- [ ] E2E tests for AI Settings view
- [ ] E2E tests for configuration CRUD
- [ ] E2E tests for validation errors
- [ ] E2E tests for reset to defaults
- [ ] E2E tests for graduation status
- [ ] Backend unit tests for AIConfigService
- [ ] Frontend unit tests for aiConfig store

## Documentation

- [x] Feature README.md
- [x] Feature REQUIREMENTS.md
- [x] Feature CHANGELOG.md
- [x] Feature registry updated
- [x] Auto-detect patterns added
- [ ] API documentation updated
- [ ] Architecture docs updated
- [ ] CLAUDE.md updated (if needed)

## Future Enhancements (Post-Week 2)

- [ ] Advanced tier editor with visual builder
- [ ] Strategy universe selector UI
- [ ] Kelly Criterion implementation (Week 9)
- [ ] AI-powered explanations with Claude
- [ ] Risk profile templates (Conservative/Moderate/Aggressive)
- [ ] Backtesting configuration integration
- [ ] Configuration versioning and rollback
- [ ] Configuration import/export (JSON)
- [ ] Real-time graduation progress tracking
- [ ] Notification preferences

## Known Limitations (Week 2)

- **Tier editing:** Simplified display only, advanced editor deferred to Phase 3
- **Kelly sizing:** Placeholder only, implementation deferred to Week 9
- **Strategy selection:** API exists but UI deferred to Week 3
- **API key encryption:** Column exists but encryption not yet implemented
- **Trade tracking:** Paper trading metrics manually managed, automated tracking in Week 4

---

**Last updated:** 2025-12-24
**Completion:** Week 2 - Backend & Frontend Complete (91% of planned Week 2 features)
