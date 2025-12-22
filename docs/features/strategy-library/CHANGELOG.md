# Strategy Library Changelog

All notable changes to the Strategy Library feature will be documented in this file.

## [Unreleased]

## [1.0.0] - 2024-12-08

### Added
- Strategy Library with 20+ pre-built templates (file: frontend/src/views/StrategyLibraryView.vue)
- Strategy templates database model (file: backend/app/models/strategy_templates.py)
- Category-based browsing (bullish, bearish, neutral, volatile, income, advanced) (file: frontend/src/views/StrategyLibraryView.vue)
- AI-powered Strategy Wizard with 3-step flow (file: frontend/src/components/strategyLibrary/WizardModal.vue)
- Recommendation scoring algorithm (file: backend/app/api/routes/strategy_wizard.py)
- One-click template deployment to Strategy Builder (file: backend/app/api/routes/strategy_wizard.py)
- Strategy comparison tool (compare up to 4 strategies) (file: frontend/src/components/strategyLibrary/CompareModal.vue)
- Template details modal with educational content (file: frontend/src/components/strategyLibrary/DetailsModal.vue)
- Seed script for populating templates (file: backend/scripts/seed_strategies.py)
- Strategy Library store (file: frontend/src/stores/strategyLibrary.js)
- Strategy Wizard API routes (file: backend/app/api/routes/strategy_wizard.py)
- Template card component (file: frontend/src/components/strategyLibrary/TemplateCard.vue)
