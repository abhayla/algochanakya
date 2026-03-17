---
name: ai-service-pattern
description: >
  Add a new AI analysis service to the regime-scoring-recommendation pipeline.
  Follows the 3-stage pattern used by MarketRegimeClassifier, StressGreeksEngine,
  and StrategyRecommender. Use when adding new AI analysis capabilities.
type: workflow
allowed-tools: "Bash Read Write Edit Grep Glob"
argument-hint: "<service-name> [--stage regime|scoring|recommendation]"
version: "1.0.0"
synthesized: true
private: false
source_hash: "ai-service-v1"
---

# AI Service Pattern

Add a new AI service following the project's 3-stage analysis pipeline.

**Request:** $ARGUMENTS

---

## STEP 1: Understand the Pipeline

Read the existing pipeline to understand the data flow:

```bash
ls backend/app/services/ai/
```

The 3-stage pipeline processes market data sequentially:

```
Market Data (OHLCV, Greeks, IV)
    ↓
Stage 1: MarketRegimeClassifier (market_regime.py)
    → RegimeResult: type, confidence, reasoning
    → Types: TRENDING_BULLISH, TRENDING_BEARISH, RANGEBOUND, VOLATILE, PRE_EVENT, EVENT_DAY
    ↓
Stage 2: StressGreeksEngine (stress_greeks_engine.py)
    → StressTestResult: risk_score (0-100)
    → Weights: Delta 30%, Gamma 30%, Max Loss 25%, Volatility 15%
    → Gate: score > 75 → reject strategy
    ↓
Stage 3: StrategyRecommender (strategy_recommender.py)
    → StrategyRecommendation: confidence, reasoning, adjustments
    → Uses REGIME_STRATEGY_SCORES mapping
```

## STEP 2: Determine Where Your Service Fits

| If your service... | Stage | Pattern to follow |
|-------------------|-------|-------------------|
| Classifies market state or conditions | Stage 1 (regime) | `market_regime.py` — returns typed result with confidence |
| Scores risk or quantifies a metric | Stage 2 (scoring) | `stress_greeks_engine.py` — returns 0-100 score with weighted factors |
| Recommends actions based on analysis | Stage 3 (recommendation) | `strategy_recommender.py` — uses regime + scores to rank options |
| Adds a new parallel analysis dimension | New parallel stage | Create alongside existing stages, feed into recommender |

## STEP 3: Create the Service Class

Create `backend/app/services/ai/<service_name>.py`:

### For a Stage 1 (Classification) service:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class YourClassificationType(str, Enum):
    TYPE_A = "type_a"
    TYPE_B = "type_b"
    TYPE_C = "type_c"

@dataclass
class YourClassificationResult:
    type: YourClassificationType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    indicators: dict  # Technical indicators used

class YourClassifier:
    @staticmethod
    async def classify(market_data: dict) -> YourClassificationResult:
        """Classify based on technical indicators."""
        # Use indicators: RSI, ADX, EMA, ATR, Bollinger Bands
        # Return typed result with confidence and reasoning
        pass
```

### For a Stage 2 (Scoring) service:

```python
@dataclass
class YourScoreResult:
    score: float  # 0-100
    factor_scores: dict  # Individual factor contributions
    gate_passed: bool  # True if score is within acceptable range

class YourScoringEngine:
    WEIGHTS = {
        "factor_a": 0.30,
        "factor_b": 0.30,
        "factor_c": 0.25,
        "factor_d": 0.15,
    }

    @staticmethod
    async def score(data: dict) -> YourScoreResult:
        """Compute weighted risk/quality score."""
        # Sum weighted factors, normalize to 0-100
        pass
```

### For a Stage 3 (Recommendation) service:

```python
# Map classification types to strategy confidence scores
YOUR_STRATEGY_SCORES = {
    YourClassificationType.TYPE_A: {"strategy_x": 90, "strategy_y": 70},
    YourClassificationType.TYPE_B: {"strategy_x": 40, "strategy_y": 85},
}

@dataclass
class YourRecommendation:
    strategy: str
    confidence: float
    reasoning: str
    adjustments: list

class YourRecommender:
    @staticmethod
    async def recommend(
        classification: YourClassificationResult,
        score: YourScoreResult,
    ) -> list[YourRecommendation]:
        """Rank strategies by confidence given classification and scores."""
        pass
```

## STEP 4: Integrate into the Pipeline

1. Read the existing pipeline orchestration (look for where `MarketRegimeClassifier` is called)
2. Add your service at the appropriate stage
3. Pass data forward: each stage receives output from the previous stage

If adding a parallel analysis, feed your output into the existing `StrategyRecommender`:
```python
# In the orchestrator or route handler
regime = await MarketRegimeClassifier.classify(market_data)
stress = await StressGreeksEngine.score(position_data)
your_result = await YourService.analyze(relevant_data)  # New parallel stage
recommendation = await StrategyRecommender.recommend(regime, stress, your_result)
```

## STEP 5: Add Tests

Create `backend/tests/backend/ai/test_<service_name>.py`:

```python
import pytest
from backend.app.services.ai.<service_name> import YourClassifier, YourClassificationResult

@pytest.mark.asyncio
class TestYourClassifier:
    async def test_classifies_type_a(self):
        """Test classification with clear Type A indicators."""
        market_data = {"rsi": 75, "adx": 30, "ema_trend": "up"}
        result = await YourClassifier.classify(market_data)
        assert result.type == YourClassificationType.TYPE_A
        assert result.confidence >= 0.7

    async def test_low_confidence_ambiguous_data(self):
        """Ambiguous data should produce low confidence."""
        market_data = {"rsi": 50, "adx": 15, "ema_trend": "flat"}
        result = await YourClassifier.classify(market_data)
        assert result.confidence < 0.5
```

Run tests:
```bash
cd backend && pytest tests/backend/ai/test_<service_name>.py -v
```

## STEP 6: Verify Pipeline Integration

1. Run the full AI test suite: `cd backend && pytest tests/backend/ai/ -v`
2. Verify no regressions in existing regime/scoring/recommendation pipeline
3. Check that the new service result is properly consumed downstream

---

## CRITICAL RULES

- ALWAYS use `@dataclass` for result types — they are serializable and testable, unlike raw dicts
- ALWAYS include `confidence` (0.0-1.0) and `reasoning` (string) in classification/recommendation results — downstream consumers depend on these fields
- NEVER hardcode threshold values — use constants or config for gates (e.g., `score > 75 → reject`)
- ALWAYS use async methods — the pipeline runs in async context, blocking calls stall the event loop
- NEVER import broker libraries directly in AI services — AI services receive pre-fetched market data as input
- ALWAYS test with edge cases: ambiguous data, missing fields, extreme values
