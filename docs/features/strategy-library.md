# Strategy Library Feature

The Strategy Library provides pre-built option strategy templates with an AI-powered recommendation wizard, one-click deployment, and strategy comparison tools.

## Overview

The Strategy Library helps traders:
- **Discover Strategies**: Browse 20+ pre-defined option strategies by category
- **AI Recommendations**: Get personalized strategy suggestions based on market outlook
- **Educational Content**: Learn when to use each strategy, pros/cons, exit rules
- **Quick Deploy**: Deploy strategies to the Strategy Builder with live market data
- **Compare Strategies**: Side-by-side comparison of multiple strategies

## Components

### Strategy Templates

Pre-defined option strategies with full configuration:

| Category | Strategies |
|----------|-----------|
| **Bullish** | Bull Call Spread, Bull Put Spread, Long Call, Synthetic Long |
| **Bearish** | Bear Call Spread, Bear Put Spread, Long Put, Synthetic Short |
| **Neutral** | Iron Condor, Iron Butterfly, Short Straddle, Short Strangle |
| **Volatile** | Long Straddle, Long Strangle, Ratio Backspread |
| **Income** | Covered Call, Cash-Secured Put, Calendar Spread |
| **Advanced** | Jade Lizard, Broken Wing Butterfly, Double Diagonal |

Each template includes:
- **Legs Configuration**: Strike offsets, option types, positions
- **Risk Profile**: Max profit, max loss, breakeven points
- **Greeks Exposure**: Theta/Vega/Delta characteristics
- **Win Probability**: Expected success rate
- **Educational Content**: When to use, pros, cons, exit rules

### Strategy Wizard

3-step AI-powered recommendation engine:

1. **Market Outlook**: Bullish, Bearish, Neutral, or Volatile
2. **Volatility View**: High IV, Low IV, or Any
3. **Risk Tolerance**: Low, Medium, or High

**Scoring Algorithm:**
- Market outlook match: 40 points
- Volatility preference match: 25 points
- Risk tolerance match: 25 points
- Bonus (experience, capital): 10 points

Returns top 5 recommendations with match scores and reasons.

### Deploy Modal

Deploy a strategy template with live market data:
- Select underlying (NIFTY/BANKNIFTY/FINNIFTY)
- Choose expiry date
- Set number of lots
- Preview legs with live LTP
- One-click deploy to Strategy Builder

### Compare Tool

Compare up to 4 strategies side-by-side:
- Max Profit/Loss
- Win Probability
- Risk Level
- Capital Requirement
- Greeks Exposure

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/strategy-wizard/templates` | GET | List all templates with filters |
| `/api/strategy-wizard/templates/categories` | GET | Get categories with counts |
| `/api/strategy-wizard/templates/{name}` | GET | Get template details |
| `/api/strategy-wizard/wizard` | POST | Get AI recommendations |
| `/api/strategy-wizard/deploy` | POST | Deploy with live data |
| `/api/strategy-wizard/compare` | POST | Compare strategies |
| `/api/strategy-wizard/popular` | GET | Get popular strategies |

### Query Parameters for `/templates`

| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category (bullish, bearish, neutral, volatile, income, advanced) |
| `risk_level` | string | Filter by risk level (low, medium, high) |
| `difficulty` | string | Filter by difficulty (beginner, intermediate, advanced) |
| `search` | string | Search in name and description |
| `theta_positive` | boolean | Filter theta positive strategies |
| `limit` | int | Pagination limit (default 50) |
| `offset` | int | Pagination offset (default 0) |

## Database Model

**StrategyTemplate** (`app/models/strategy_templates.py`):

```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id = Column(UUID, primary_key=True)
    name = Column(String(50), unique=True)  # e.g., "iron_condor"
    display_name = Column(String(100))      # e.g., "Iron Condor"
    category = Column(String(50))           # bullish, bearish, neutral, etc.
    description = Column(Text)

    # Legs configuration (JSON)
    legs_config = Column(JSON)  # [{"type": "CE", "position": "SELL", "strike_offset": 200}]

    # Risk/reward
    max_profit = Column(String(100))   # "Limited", "Unlimited"
    max_loss = Column(String(100))
    breakeven = Column(String(200))

    # Market conditions
    market_outlook = Column(String(50))      # bullish, bearish, neutral, volatile
    volatility_preference = Column(String(50))  # high_iv, low_iv, any

    # Risk metrics
    risk_level = Column(String(20))          # low, medium, high
    capital_requirement = Column(String(20))

    # Greeks exposure
    theta_positive = Column(Boolean)
    vega_positive = Column(Boolean)
    delta_neutral = Column(Boolean)

    # Educational content
    when_to_use = Column(Text)
    pros = Column(JSON)           # Array of strings
    cons = Column(JSON)
    common_mistakes = Column(JSON)
    exit_rules = Column(JSON)

    # Metadata
    popularity_score = Column(Integer)
    difficulty_level = Column(String(20))  # beginner, intermediate, advanced
    tags = Column(JSON)
```

## Frontend Components

### StrategyLibraryView.vue

Main view at `/strategies` with:
- Category filter pills
- Search input
- Strategy cards grid
- Wizard button

### StrategyWizardModal.vue

3-step wizard for recommendations:
- Step 1: Outlook selection (4 options)
- Step 2: Volatility view (3 options)
- Step 3: Risk tolerance (3 options)
- Results: Recommendation cards with scores

### StrategyDetailsModal.vue

Full strategy details:
- Description
- When to use
- Pros and cons
- Common mistakes
- Exit rules
- Deploy button

### StrategyDeployModal.vue

Deploy configuration:
- Underlying selector
- Expiry dropdown
- Lots input
- Legs preview table
- Net premium display

### StrategyCompareModal.vue

Side-by-side comparison table:
- All metrics
- Greek badges
- Recommendation

## Pinia Store

**strategyLibrary.js** (`src/stores/strategyLibrary.js`):

```javascript
export const useStrategyLibraryStore = defineStore('strategyLibrary', {
  state: () => ({
    templates: [],
    categories: [],
    selectedCategory: null,
    searchQuery: '',
    wizardInputs: {},
    recommendations: [],
    comparison: [],
    loading: false,
    error: null
  }),

  actions: {
    async fetchTemplates(filters),
    async fetchCategories(),
    async runWizard(inputs),
    async deployTemplate(templateName, options),
    async compareStrategies(templateNames),
    addToComparison(template),
    removeFromComparison(templateName),
    clearComparison()
  }
})
```

## Seeding Templates

Run the seed script to populate templates:

```bash
cd backend
python scripts/seed_strategies.py
```

This creates 20+ pre-defined strategy templates with full educational content.

## Testing

### Backend Tests (pytest)

```bash
cd backend
pytest tests/test_strategy_templates.py -v       # Model tests
pytest tests/test_strategy_wizard_api.py -v      # API tests
pytest tests/test_strategy_validation.py -v      # Validation tests
pytest tests/test_strategy_integration.py -v     # Integration tests
```

### Frontend E2E Tests (Playwright)

```bash
npm run test:specs:strategylibrary

# Individual test types
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.happy.spec.js
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.edge.spec.js
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.visual.spec.js
npx playwright test tests/e2e/specs/strategylibrary/strategylibrary.api.spec.js
```

## data-testid Attributes

Key selectors for testing:

```
strategy-library-page
strategy-library-categories
strategy-library-category-{category}
strategy-library-search-input
strategy-library-wizard-button
strategy-library-cards-grid
strategy-card-{name}
strategy-card-{name}-view-details
strategy-card-{name}-deploy
strategy-wizard-modal
strategy-wizard-step-{n}
strategy-wizard-outlook-{value}
strategy-wizard-volatility-{value}
strategy-wizard-risk-{value}
strategy-wizard-recommendations
strategy-details-modal
strategy-deploy-modal
strategy-compare-modal
```

## Related Documentation

- [Strategy Builder](strategy-builder.md) - Build custom strategies
- [Option Chain](option-chain.md) - Select options for strategies
- [Testing Guide](../testing/README.md) - Full test documentation
