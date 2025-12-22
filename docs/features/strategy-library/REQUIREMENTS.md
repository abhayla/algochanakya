# Strategy Library Requirements

## Core Requirements
- [x] Browse 20+ pre-built strategy templates
- [x] Filter by category (bullish, bearish, neutral, volatile, income, advanced)
- [x] Search templates by name/description
- [x] View template details
- [x] Deploy template to Strategy Builder
- [x] Compare multiple templates side-by-side

## Strategy Templates Database
- [x] Store templates in database (`strategy_templates` table)
- [x] Legs configuration as JSON
- [x] Risk/reward metrics
- [x] Market condition matching
- [x] Greeks exposure (theta/vega/delta)
- [x] Educational content (when to use, pros, cons, exit rules)

## Template Categories
- [x] Bullish strategies (4+)
- [x] Bearish strategies (4+)
- [x] Neutral strategies (4+)
- [x] Volatile strategies (3+)
- [x] Income strategies (3+)
- [x] Advanced strategies (3+)

## Strategy Wizard (AI Recommendations)
- [x] 3-step wizard flow
- [x] Step 1: Market outlook (Bullish/Bearish/Neutral/Volatile)
- [x] Step 2: Volatility view (High IV/Low IV/Any)
- [x] Step 3: Risk tolerance (Low/Medium/High)
- [x] Scoring algorithm (100 points total)
- [x] Return top 5 recommendations with scores
- [x] Show match reasons for each recommendation

## Deploy Modal
- [x] Select underlying (NIFTY/BANKNIFTY/FINNIFTY/SENSEX)
- [x] Select expiry date
- [x] Set number of lots
- [x] Preview legs with live LTP
- [x] Show net premium
- [x] One-click deploy to Strategy Builder

## Compare Tool
- [x] Select up to 4 strategies to compare
- [x] Side-by-side comparison table
- [x] Compare max profit/loss
- [x] Compare win probability
- [x] Compare risk level
- [x] Compare capital requirement
- [x] Compare Greeks exposure

## Template Details
- [x] Strategy name and description
- [x] Legs configuration
- [x] Max profit/loss
- [x] Breakeven points
- [x] When to use
- [x] Pros and cons lists
- [x] Common mistakes
- [x] Exit rules
- [x] Difficulty level
- [x] Popularity score

## API Requirements
- [x] GET /api/strategy-wizard/templates - List templates
- [x] GET /api/strategy-wizard/templates/categories - Category counts
- [x] GET /api/strategy-wizard/templates/{name} - Template details
- [x] POST /api/strategy-wizard/wizard - AI recommendations
- [x] POST /api/strategy-wizard/deploy - Deploy with live data
- [x] POST /api/strategy-wizard/compare - Compare strategies
- [x] GET /api/strategy-wizard/popular - Popular strategies

## UI Requirements
- [x] Category filter pills
- [x] Search input with debounce
- [x] Strategy cards grid
- [x] "Strategy Wizard" button
- [x] Template details modal
- [x] Deploy modal
- [x] Compare modal
- [x] "View Details" and "Deploy" buttons on cards

## Data Requirements
- [x] `strategy_templates` table with full schema
- [x] JSON fields for legs_config, pros, cons, tags
- [x] Indexed on category, difficulty, popularity
- [x] Seed script to populate templates

## Seeding Requirements
- [x] Python seed script at `backend/scripts/seed_strategies.py`
- [x] Create 20+ templates with full data
- [x] Include all categories
- [x] Include educational content for each

## Performance Requirements
- [x] Load templates within 500ms
- [x] Search results within 200ms
- [x] Wizard scoring within 100ms
- [x] Deploy preview within 1 second

## Integration Requirements
- [x] Integration with Strategy Builder for deployment
- [x] Live LTP fetching for deploy preview
- [x] Trading constants for lot sizes

---
Last updated: 2025-12-22
