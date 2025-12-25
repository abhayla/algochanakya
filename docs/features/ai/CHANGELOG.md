# Changelog - AI Configuration & Settings

All notable changes to the AI Configuration feature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Confidence tier boundary validation gaps by adjusting max values from 59/74/84 to 60/75/85 (file: backend/app/models/ai.py)

### Planned
- Advanced confidence tier editor with visual builder
- Strategy universe selector UI component
- Kelly Criterion position sizing implementation (Week 9)
- AI-powered strategy explanations with Claude integration
- Risk profile templates (Conservative/Moderate/Aggressive)
- Configuration import/export (JSON format)
- Real-time paper trading metrics dashboard

## [1.0.0] - 2025-12-24

### Added - Week 2 Complete Implementation

#### Database & Models
- Database migration 010_ai_week2_user_config.py creating `ai_user_config` table (file: backend/alembic/versions/010_ai_week2_user_config.py)
- AIUserConfig SQLAlchemy model with 20+ configuration fields (file: backend/app/models/ai.py)
- One-to-one relationship with User model (file: backend/app/models/users.py)
- JSONB storage for confidence_tiers and allowed_strategies
- PostgreSQL ARRAY for deploy_days
- CHECK constraints for data validation
- Default confidence tiers: SKIP (0-60, 0x), LOW (60-75, 1.0x), MEDIUM (75-85, 1.5x), HIGH (85-100, 2.0x)

#### Pydantic Schemas
- AIUserConfigResponse schema with all fields (file: backend/app/schemas/ai.py)
- AIUserConfigUpdate schema for partial updates (file: backend/app/schemas/ai.py)
- AIConfigDefaults schema for default configuration template (file: backend/app/schemas/ai.py)
- PositionSizingConfig schema with tier validation (file: backend/app/schemas/ai.py)
- DeploymentScheduleConfig schema (file: backend/app/schemas/ai.py)
- AILimitsConfig schema (file: backend/app/schemas/ai.py)
- ConfidenceTier schema with range validation (file: backend/app/schemas/ai.py)
- PaperTradingStatus schema for graduation tracking (file: backend/app/schemas/ai.py)
- ClaudeKeyValidationRequest/Response schemas (file: backend/app/schemas/ai.py)
- Model validators for tier gap/overlap checking
- Field validators for confidence range (0-100) and positive values

#### Service Layer
- AIConfigService with configuration management logic (file: backend/app/services/ai/config_service.py)
- get_or_create_config() method - Auto-creates defaults for new users (file: backend/app/services/ai/config_service.py)
- update_config() method with partial update support (file: backend/app/services/ai/config_service.py)
- calculate_lots_for_confidence() - Tier-based lot size calculation (file: backend/app/services/ai/config_service.py)
- should_deploy_today() - Deployment day validation with event checking (file: backend/app/services/ai/config_service.py)
- is_within_limits() - Multi-constraint limit enforcement (file: backend/app/services/ai/config_service.py)
- validate_claude_api_key() - Anthropic API key validation (file: backend/app/services/ai/config_service.py)
- get_paper_trading_status() - Graduation status tracking (file: backend/app/services/ai/config_service.py)
- can_graduate_to_live() - Graduation criteria checking (file: backend/app/services/ai/config_service.py)

#### API Endpoints
- GET /api/v1/ai/config - Get user configuration with auto-creation (file: backend/app/api/v1/ai/config.py)
- PUT /api/v1/ai/config - Update configuration with validation (file: backend/app/api/v1/ai/config.py)
- GET /api/v1/ai/config/defaults - Get default configuration template (file: backend/app/api/v1/ai/config.py)
- GET /api/v1/ai/config/strategies - Get allowed strategy templates (file: backend/app/api/v1/ai/config.py)
- PUT /api/v1/ai/config/strategies - Update allowed strategies (file: backend/app/api/v1/ai/config.py)
- GET /api/v1/ai/config/sizing - Get position sizing configuration (file: backend/app/api/v1/ai/config.py)
- PUT /api/v1/ai/config/sizing - Update position sizing (file: backend/app/api/v1/ai/config.py)
- POST /api/v1/ai/config/validate-claude - Validate Claude API key (file: backend/app/api/v1/ai/config.py)
- GET /api/v1/ai/config/paper-trading/status - Get graduation status (file: backend/app/api/v1/ai/config.py)
- Config router registration (file: backend/app/api/v1/ai/router.py)

#### Frontend Store
- useAIConfigStore Pinia store with state management (file: frontend/src/stores/aiConfig.js)
- fetchConfig() action - Loads user configuration (file: frontend/src/stores/aiConfig.js)
- saveConfig() action - Saves configuration updates (file: frontend/src/stores/aiConfig.js)
- resetToDefaults() action - Resets to default configuration (file: frontend/src/stores/aiConfig.js)
- validateClaudeKey() action - Validates API key (file: frontend/src/stores/aiConfig.js)
- isAIEnabled getter - Quick access to AI toggle state (file: frontend/src/stores/aiConfig.js)
- canGraduateToLive getter - Graduation eligibility check (file: frontend/src/stores/aiConfig.js)
- lotsForConfidence getter - Lot size calculation (file: frontend/src/stores/aiConfig.js)
- confidenceTierForScore getter - Find tier for confidence score (file: frontend/src/stores/aiConfig.js)
- graduationProgress getter - Graduation progress percentage (file: frontend/src/stores/aiConfig.js)

#### Frontend UI
- AISettingsView.vue - Main configuration page (file: frontend/src/views/ai/AISettingsView.vue)
- Autonomy Settings Panel with AI toggle and mode selection (file: frontend/src/views/ai/AISettingsView.vue)
- Deployment Schedule Panel with time, days, and skip options (file: frontend/src/views/ai/AISettingsView.vue)
- Position Sizing Panel with mode selection and base lots (file: frontend/src/views/ai/AISettingsView.vue)
- Trading Limits Panel with 6 limit inputs in 2-column grid (file: frontend/src/views/ai/AISettingsView.vue)
- Auto-save with 2-second debounce on configuration changes (file: frontend/src/views/ai/AISettingsView.vue)
- Manual Save Configuration button with loading state (file: frontend/src/views/ai/AISettingsView.vue)
- Reset to Defaults button with confirmation dialog (file: frontend/src/views/ai/AISettingsView.vue)
- Live trading mode disabled until graduation requirements met (file: frontend/src/views/ai/AISettingsView.vue)
- Tailwind CSS styled toggle switch for AI enabled (file: frontend/src/views/ai/AISettingsView.vue)
- Loading and error states (file: frontend/src/views/ai/AISettingsView.vue)
- All inputs have data-testid attributes for E2E testing (file: frontend/src/views/ai/AISettingsView.vue)

#### Navigation & Routing
- AI Settings route at /ai/settings with auth requirement (file: frontend/src/router/index.js)
- Navigation link in KiteHeader with brain icon (file: frontend/src/components/layout/KiteHeader.vue)
- Active route highlighting support (file: frontend/src/components/layout/KiteHeader.vue)

#### Documentation
- Feature README.md with comprehensive overview (file: docs/features/ai/README.md)
- Feature REQUIREMENTS.md with implementation checklist (file: docs/features/ai/REQUIREMENTS.md)
- Feature CHANGELOG.md with version history (file: docs/features/ai/CHANGELOG.md)
- Feature registry entry with auto-detect patterns (file: docs/feature-registry.yaml)

### Changed
- Updated User model with ai_config relationship (file: backend/app/models/users.py)
- Updated models __init__.py to export AIUserConfig (file: backend/app/models/__init__.py)
- Extended AI router to include config endpoints (file: backend/app/api/v1/ai/router.py)
- Extended feature registry with AI configuration patterns (file: docs/feature-registry.yaml)
- Updated frontend router with AI settings route (file: frontend/src/router/index.js)
- Updated KiteHeader navigation with AI Settings link (file: frontend/src/components/layout/KiteHeader.vue)

### Technical Details

**Position Sizing Modes:**
- **Fixed:** All trades use base_lots
- **Tiered:** Confidence-based multipliers applied to base_lots
- **Kelly:** Placeholder for future implementation (Week 9)

**Graduation Criteria:**
- 25 completed paper trades
- 55% or higher win rate
- 15 days of paper trading experience
- Manual admin approval

**Default Limits:**
- Max 2 lots per strategy
- Max 6 lots per day
- Max 5 strategies per day
- Min 60% confidence to trade
- Max VIX 25.0
- Weekly loss limit ₹50,000

**Auto-Deploy Logic:**
- Checks deploy_days (e.g., ["MON", "TUE", "WED", "THU", "FRI"])
- Skips event days (Budget, RBI policy) if enabled
- Skips weekly expiry (Thursday) if enabled
- Uses deploy_time for scheduling (e.g., "09:20")

## [0.1.0] - Planning Phase

### Designed
- Database schema for ai_user_config table
- API endpoint structure
- Frontend component architecture
- Position sizing strategy with confidence tiers
- Paper trading graduation system
- Integration points with AutoPilot

---

**Migration Guide:**
- Run database migration: `alembic upgrade head` (applies migration 010)
- No breaking changes, backward compatible
- Existing users will have config auto-created on first API call
- Default configuration safe for immediate use

**Next Steps (Week 3):**
- Integrate with AutoPilot strategy deployment
- Add strategy universe selector UI
- Implement real-time graduation tracking
- Add configuration export/import
