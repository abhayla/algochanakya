# AutoPilot AI - Grok Review Implementation Prompt

**Use this prompt to continue implementation in a new Claude session.**

---

## Context

I'm implementing recommendations from an external code review (ChatGPT/Grok) for the AlgoChanakya AutoPilot AI module. The review is at:
- `docs/external/ChatGPT-AutoPilot_AI_Prioritized_Engineering_Roadmap.md`

A detailed gap analysis and implementation plan has been created at:
- `C:\Users\itsab\.claude\plans\wondrous-honking-wolf.md`

---

## What Was Done

1. ✅ Created external review document: `docs/external/AI-AutoPilot-Architecture-Review.md`
2. ✅ Received feedback from Grok/ChatGPT with prioritized roadmap
3. ✅ Completed gap analysis comparing review recommendations vs current implementation
4. ✅ Created detailed implementation plan with files to create/modify

---

## Gap Analysis Summary

| Priority | Item | Status | Effort |
|----------|------|--------|--------|
| **P0** | 0.1 Drawdown Control Engine | ❌ Missing | HIGH |
| **P0** | 0.2 Strategy Kill Memory | ⚠️ Partial | MEDIUM |
| **P0** | 0.3 Black Swan Protocols | ⚠️ Partial | MEDIUM |
| **P1** | 1.1 Stress Greeks Engine | ❌ Missing | HIGH |
| **P1** | 1.2 Drawdown-Aware Sizing | ⚠️ Partial | MEDIUM |
| **P1** | 1.3 Regime Drift Detection | ⚠️ Partial | MEDIUM |
| **P2** | 2.1 Global→Personal ML | ❌ Missing | HIGH |
| **P2** | 2.2 Regime-Conditioned Quality | ⚠️ Partial | LOW |
| **P2** | 2.3 Retraining Optimization | ⚠️ Partial | LOW |
| **P3** | 3.1 Trust Ladder UI | ⚠️ Partial | MEDIUM |
| **P3** | 3.2 Regime Attribution | ✅ Exists | MINOR |
| **P3** | 3.3 Capital-at-Risk Meter | ⚠️ Partial | MEDIUM |

---

## Implementation Order

### Phase 1 (Priority 0 - CRITICAL)
Start here. These are must-haves before production launch.

1. **0.1 Drawdown Control Engine**
   - Create: `backend/app/services/ai/risk_state_engine.py`
   - Create: `backend/app/models/ai_risk_state.py`
   - Create: `frontend/src/components/ai/RiskStateIndicator.vue`
   - Modify: `backend/app/services/ai/ai_monitor.py`
   - Migration: `ai_risk_state` table

2. **0.2 Strategy Kill Memory**
   - Create: `backend/app/services/ai/strategy_cooldown.py`
   - Create: `backend/app/models/ai_strategy_cooldown.py`
   - Modify: `backend/app/services/ai/strategy_recommender.py`
   - Modify: `backend/app/services/ai/feedback_scorer.py`
   - Migration: `ai_strategy_cooldown` table

3. **0.3 Black Swan Protocols**
   - Create: `backend/app/services/ai/extreme_event_handler.py`
   - Modify: `backend/app/services/ai/market_regime.py`
   - Modify: `backend/app/services/ai/ai_monitor.py`

### Phase 2 (Priority 1 - HIGH)
4. **1.1 Stress Greeks Engine**
5. **1.2 Drawdown-Aware Sizing**
6. **1.3 Regime Drift Detection**

### Phase 3 (Priority 2 - MEDIUM)
7. **2.1 Global→Personal ML**
8. **2.2 Regime-Conditioned Quality**
9. **2.3 Retraining Optimization**

### Phase 4 (Priority 3 - UI)
10. **3.1 Trust Ladder UI**
11. **3.3 Capital-at-Risk Meter**

---

## Prompt to Continue

Copy and paste this prompt to continue implementation:

```
Continue implementing the Grok review recommendations for AutoPilot AI.

Reference documents:
1. Implementation plan: Read the plan file at `C:\Users\itsab\.claude\plans\wondrous-honking-wolf.md`
2. Original review: `docs/external/ChatGPT-AutoPilot_AI_Prioritized_Engineering_Roadmap.md`
3. Context prompt: `docs/plans/GROK-REVIEW-IMPLEMENTATION-PROMPT.md`

Current status: [UPDATE THIS]
- Phase 1 (P0): Not started / In progress / Complete
- Phase 2 (P1): Not started
- Phase 3 (P2): Not started
- Phase 4 (P3): Not started

Next task: Implement [ITEM NUMBER AND NAME]

Requirements:
- Follow the implementation details in the plan file
- Create database migrations using Alembic
- Add appropriate error handling and logging
- Follow existing code patterns in the AI module
- Add data-testid attributes to Vue components
- Run tests after implementation
```

---

## Key Files to Reference

**Existing AI Services (patterns to follow):**
- `backend/app/services/ai/market_regime.py` - Example service structure
- `backend/app/services/ai/kelly_calculator.py` - Example calculator service
- `backend/app/services/ai/feedback_scorer.py` - Example scoring service
- `backend/app/models/ai.py` - Example model structure

**Existing Frontend Components:**
- `frontend/src/components/ai/GraduationProgress.vue` - Example AI component
- `frontend/src/views/ai/AnalyticsView.vue` - Example analytics view

---

## Notes

- All new services should follow async/await patterns
- Use dependency injection via FastAPI's Depends()
- Frontend components should use Composition API with `<script setup>`
- Add WebSocket message types for real-time updates where needed
- Update `docs/ai/README.md` after implementation

---

*Created: December 2025*
*Last Updated: December 2025*
