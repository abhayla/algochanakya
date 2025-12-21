# AutoPilot Condition Variables

Complete list of variables available in entry conditions and adjustment rules.

## Core Variables (Available Now)

### TIME Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `TIME.CURRENT` | string | Current time (HH:MM) | "09:25" |
| `TIME.MINUTES_SINCE_OPEN` | integer | Minutes since 9:15 AM | 10 |

**Operators:** `equals`, `not_equals`, `greater_than`, `less_than`, `greater_equal`, `less_equal`

**Example:**
```json
{
  "variable": "TIME.CURRENT",
  "operator": "greater_equal",
  "value": "09:20"
}
```

### SPOT Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `SPOT.{UNDERLYING}` | decimal | Spot price | `SPOT.NIFTY` → 24567.8 |
| `SPOT.{UNDERLYING}.CHANGE_PCT` | decimal | Spot change % | `SPOT.NIFTY.CHANGE_PCT` → 1.25 |

**Operators:** All numeric operators, `between`, `not_between`

**Example:**
```json
{
  "variable": "SPOT.NIFTY",
  "operator": "between",
  "value": [24000, 25000]
}
```

### VIX Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `VIX.VALUE` | decimal | India VIX value | 15.25 |

**Example:**
```json
{
  "variable": "VIX.VALUE",
  "operator": "less_than",
  "value": 20.0
}
```

### WEEKDAY Variable

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `WEEKDAY` | string | Current weekday | "MON", "TUE", "WED", "THU", "FRI" |

**Operators:** `equals`, `not_equals`

**Example:**
```json
{
  "variable": "WEEKDAY",
  "operator": "equals",
  "value": "MON"
}
```

### PREMIUM Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `PREMIUM.{LEG_ID}` | decimal | Premium for leg | `PREMIUM.leg_1` → 125.50 |

**Example:**
```json
{
  "variable": "PREMIUM.leg_1",
  "operator": "greater_than",
  "value": 100.0
}
```

---

## Phase 5A Variables (Greeks)

### STRATEGY Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `STRATEGY.DELTA` | decimal | Net portfolio delta | 0.15 |
| `STRATEGY.GAMMA` | decimal | Net portfolio gamma | 0.02 |
| `STRATEGY.THETA` | decimal | Net portfolio theta | -50.25 |
| `STRATEGY.VEGA` | decimal | Net portfolio vega | 25.50 |

**Example:**
```json
{
  "variable": "STRATEGY.DELTA",
  "operator": "greater_than",
  "value": 0.5
}
```

---

## Phase 5B Variables (Spot Distance & Premium)

### SPOT.DISTANCE_TO Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `SPOT.DISTANCE_TO.BREAKEVEN` | decimal | Distance to breakeven % | 2.5 (means 2.5% away) |
| `SPOT.DISTANCE_TO.{LEG_ID}` | decimal | Distance to leg strike % | `SPOT.DISTANCE_TO.leg_1` → 3.2 |

**Example:**
```json
{
  "variable": "SPOT.DISTANCE_TO.BREAKEVEN",
  "operator": "less_than",
  "value": 1.0
}
```

### PREMIUM.CAPTURED_PCT Variable

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `PREMIUM.CAPTURED_PCT` | decimal | Premium captured % | 75.0 (75% of max premium) |

**Example:**
```json
{
  "variable": "PREMIUM.CAPTURED_PCT",
  "operator": "greater_equal",
  "value": 70.0
}
```

### IV Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `IV.RANK` | decimal | IV Rank (0-100) | 65.5 |
| `IV.PERCENTILE` | decimal | IV Percentile (0-100) | 72.3 |

**Example:**
```json
{
  "variable": "IV.RANK",
  "operator": "greater_than",
  "value": 50.0
}
```

---

## Phase 5C Variables (OI & Probability)

### OI Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `OI.PCR` | decimal | Put-Call Ratio | 1.25 |
| `OI.MAX_PAIN` | decimal | Max pain strike | 24500.0 |
| `OI.CHANGE` | decimal | OI change % | 15.5 |

**Example:**
```json
{
  "variable": "OI.PCR",
  "operator": "between",
  "value": [0.8, 1.2]
}
```

### PROBABILITY Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `PROBABILITY.OTM` | decimal | Probability OTM (%) | 65.0 |

**Example:**
```json
{
  "variable": "PROBABILITY.OTM",
  "operator": "greater_than",
  "value": 60.0
}
```

### STRATEGY.DTE Variable

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `STRATEGY.DTE` | integer | Days to expiry | 5 |

**Example:**
```json
{
  "variable": "STRATEGY.DTE",
  "operator": "less_equal",
  "value": 3
}
```

---

## Available Operators

| Operator | Works With | Description |
|----------|------------|-------------|
| `equals` | All types | Exact match |
| `not_equals` | All types | Not equal |
| `greater_than` | Numeric | Strictly greater |
| `less_than` | Numeric | Strictly less |
| `greater_equal` | Numeric | Greater or equal |
| `less_equal` | Numeric | Less or equal |
| `between` | Numeric | Within range (inclusive) |
| `not_between` | Numeric | Outside range |
| `crosses_above` | Numeric | Value crosses above threshold |
| `crosses_below` | Numeric | Value crosses below threshold |

---

## Condition Logic

Combine conditions with AND/OR logic:

**AND Logic (all must be true):**
```json
{
  "logic": "AND",
  "conditions": [...]
}
```

**OR Logic (at least one must be true):**
```json
{
  "logic": "OR",
  "conditions": [...]
}
```

---

## Examples

### Example 1: Time-Based Entry
Enter at 9:20 AM on Monday-Wednesday:
```json
{
  "logic": "AND",
  "conditions": [
    {
      "variable": "TIME.CURRENT",
      "operator": "greater_equal",
      "value": "09:20"
    },
    {
      "variable": "WEEKDAY",
      "operator": "not_equals",
      "value": "FRI"
    }
  ]
}
```

### Example 2: Range-Bound Entry
Enter if NIFTY between 24,000-25,000 and VIX < 20:
```json
{
  "logic": "AND",
  "conditions": [
    {
      "variable": "SPOT.NIFTY",
      "operator": "between",
      "value": [24000, 25000]
    },
    {
      "variable": "VIX.VALUE",
      "operator": "less_than",
      "value": 20.0
    }
  ]
}
```

### Example 3: Premium-Based Entry
Enter when premium >= 100:
```json
{
  "logic": "AND",
  "conditions": [
    {
      "variable": "TIME.CURRENT",
      "operator": "greater_equal",
      "value": "09:20"
    },
    {
      "variable": "PREMIUM.leg_1",
      "operator": "greater_equal",
      "value": 100.0
    }
  ]
}
```
