# AutoPilot AI – Prioritized Engineering Roadmap

This roadmap converts the architectural review and competitive gap analysis into a **clear, execution-ready plan**.
The priorities are aligned with:
- **Risk-adjusted returns (Sharpe, drawdown control)**
- **Decision quality & discipline**
- **HNI / serious retail users**
- **Indian regulatory realities**
- **Progressive autonomy (hard-gated)**

---

## Priority 0 – Must-Have Before Wider Launch (Stability & Trust)

### 0.1 Autonomous Drawdown Control Engine (CRITICAL)
**Why:** Most AI trading systems fail during drawdowns, not during normal markets.

**Engineering Tasks:**
- Implement drawdown-aware state machine:
  - NORMAL → DEGRADED → PAUSED
- Auto-degrade behavior:
  - Increase confidence thresholds
  - Reduce lot multipliers
  - Disable offensive adjustments
- Auto-pause conditions:
  - Sharpe < threshold over rolling window
  - Drawdown > X%
  - Consecutive decision quality < Y

**Deliverables:**
- `ai_risk_state` table
- Risk state evaluator service
- UI indicator + audit log

---

### 0.2 Strategy Kill Memory (CRITICAL)
**Why:** Prevent repeated losses from the same strategy–regime combination.

**Engineering Tasks:**
- Create `strategy_cooldown_registry`
- Track regime × strategy failures
- Apply cooldown windows (time + count based)

**Deliverables:**
- Cooling-off logic in Strategy Recommender
- Admin / debug visibility
- Explanations surfaced to user

---

### 0.3 Black Swan & Broker Failure Protocols (CRITICAL)
**Why:** HNIs expect predictable behavior during chaos.

**Engineering Tasks:**
- Define explicit behaviors for:
  - Circuit breakers
  - VIX > 30
  - Margin requirement spikes
  - Kite API outage
- Gamma-first risk reduction logic

**Deliverables:**
- `extreme_event_handler` service
- Playbook documentation
- Automated alerts + actions

---

## Priority 1 – Risk-Adjusted Performance Enhancements

### 1.1 Stress Greeks & Scenario Engine (HIGH)
**Why:** Portfolio Greeks at current spot are insufficient.

**Engineering Tasks:**
- Simulate Greeks at ±2%, ±4% spot moves
- Add stress-risk score to portfolio limits

**Deliverables:**
- Stress testing service
- Dashboard visualization
- Risk-based deployment gating

---

### 1.2 Drawdown-Aware Position Sizing (HIGH)
**Why:** Kelly alone is incomplete for live capital.

**Engineering Tasks:**
- Introduce drawdown dampener
- Volatility-of-P&L scaler
- Integrate with Tiered & Kelly modes

**Deliverables:**
- Enhanced sizing engine
- Backtest validation
- Configurable thresholds

---

### 1.3 Regime Drift Detection (HIGH)
**Why:** Rule-based regimes need drift awareness.

**Engineering Tasks:**
- Track predicted vs realized regime mismatch
- Confidence decay mechanism
- Auto-tightening thresholds on drift

**Deliverables:**
- Drift metrics
- Regime health score
- Monitoring alerts

---

## Priority 2 – ML & Learning System Maturity

### 2.1 Global → Personalized ML Blending (MEDIUM)
**Why:** Cold-start users are under-optimized.

**Engineering Tasks:**
- Train global baseline model
- Bayesian blending with user model
- Gradual personalization

**Deliverables:**
- Global model registry
- Blending coefficients logic
- Performance comparison metrics

---

### 2.2 Regime-Conditioned Decision Quality (MEDIUM)
**Why:** Decision quality should be context-aware.

**Engineering Tasks:**
- Normalize quality scores per regime
- Store regime-adjusted metrics
- Update learning reports

**Deliverables:**
- Enhanced quality scoring
- Regime attribution tables
- Improved Claude insights

---

### 2.3 Retraining Frequency Optimization (MEDIUM)
**Why:** Daily retraining can cause noise.

**Engineering Tasks:**
- User-volume based retraining cadence
- Weekly default, daily for high-volume users
- Stability vs responsiveness tuning

**Deliverables:**
- Retraining scheduler logic
- Model stability metrics

---

## Priority 3 – HNI-Grade Transparency & UX

### 3.1 Autonomy Trust Ladder UI (MEDIUM)
**Why:** Trust is built visually, not technically.

**Engineering Tasks:**
- Visualize autonomy levels:
  - Paper → Semi → Full Auto
- Show unlock criteria & status
- Show degradation / pause state

**Deliverables:**
- New dashboard section
- Real-time autonomy indicators

---

### 3.2 Regime Attribution Dashboard (MEDIUM)
**Why:** HNIs want to know *when* the system works best.

**Engineering Tasks:**
- Track P&L by regime
- Win rate & drawdown per regime

**Deliverables:**
- Analytics charts
- Downloadable reports

---

### 3.3 Capital-at-Risk Meter (MEDIUM)
**Why:** Theoretical max loss ≠ practical risk.

**Engineering Tasks:**
- Calculate worst-case daily risk
- Account for stress scenarios
- Surface prominently in UI

**Deliverables:**
- Risk meter widget
- Alerts when thresholds breached

---

## Priority 4 – Scalability & Institutional Readiness

### 4.1 WebSocket & Sync Hardening (LOW)
**Why:** Scale + broker reliability.

**Engineering Tasks:**
- WebSocket health scoring
- Auto-fallback strategies
- Sync lag prediction

---

### 4.2 Multi-Broker Abstraction (LOW)
**Why:** Strategic optionality.

**Engineering Tasks:**
- Broker adapter interface
- Unified order & position schema

---

## What NOT To Build Yet

- Stock options
- Over-aggressive ML ensembles
- Full neural networks
- Cross-asset portfolios

These will **dilute focus and increase risk**.

---

## Final Guidance

If executed in this order:
- You will surpass **all Indian platforms**
- Match or exceed **global leaders**
- Maintain **regulatory defensibility**
- Build **long-term HNI trust**

This roadmap favors **survivability over flash**, which is the defining trait of elite trading systems.
