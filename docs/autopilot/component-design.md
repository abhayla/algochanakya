# AutoPilot Component Design Specification

## Detailed Component Library for Auto-Execution & Adjustment System

**Version:** 1.0  
**Date:** December 2025  
**Framework:** Vue.js 3 + Pinia + TypeScript

---

## Table of Contents

1. [Component Overview](#1-component-overview)
2. [Condition Builder Components](#2-condition-builder-components)
3. [Adjustment Rule Components](#3-adjustment-rule-components)
4. [Order Execution Components](#4-order-execution-components)
5. [Risk Management Components](#5-risk-management-components)
6. [Schedule Components](#6-schedule-components)
7. [Monitoring Components](#7-monitoring-components)
8. [Action Components](#8-action-components)
9. [Shared Components](#9-shared-components)
10. [State Management](#10-state-management)

---

## 1. Component Overview

### 1.1 Component Hierarchy

```
AutoPilot/
├── pages/
│   ├── AutoPilotDashboard.vue
│   ├── AutoPilotStrategies.vue
│   ├── AutoPilotCreate.vue
│   ├── AutoPilotDetail.vue
│   ├── AutoPilotLogs.vue
│   └── AutoPilotSettings.vue
│
├── components/
│   ├── condition-builder/
│   │   ├── ConditionBuilder.vue          # Main container
│   │   ├── ConditionRow.vue              # Single condition
│   │   ├── ConditionGroup.vue            # AND/OR group
│   │   ├── VariableSelector.vue          # Variable dropdown
│   │   ├── OperatorSelector.vue          # Operator dropdown
│   │   ├── ValueInput.vue                # Value input (dynamic)
│   │   ├── ExpressionEditor.vue          # Advanced text editor
│   │   └── FlowchartBuilder.vue          # Visual node editor
│   │
│   ├── adjustment-rules/
│   │   ├── AdjustmentRuleList.vue        # List of rules
│   │   ├── AdjustmentRuleCard.vue        # Single rule card
│   │   ├── ActionSelector.vue            # Action type dropdown
│   │   ├── ActionConfigurator.vue        # Action-specific config
│   │   ├── HedgeConfigurator.vue         # Hedge action config
│   │   ├── RollConfigurator.vue          # Roll action config
│   │   ├── ShiftConfigurator.vue         # Shift strikes config
│   │   ├── ScaleConfigurator.vue         # Scale up/down config
│   │   └── ExecutionModeToggle.vue       # Auto/Semi-auto toggle
│   │
│   ├── order-execution/
│   │   ├── OrderSettings.vue             # Main order settings
│   │   ├── OrderTypeSelector.vue         # Market/Limit/SL
│   │   ├── ExecutionStyleSelector.vue    # Simultaneous/Sequential
│   │   ├── LegSequenceEditor.vue         # Drag-drop leg order
│   │   ├── SlippageSettings.vue          # Slippage protection
│   │   └── LimitOrderConfig.vue          # Limit order specifics
│   │
│   ├── risk-management/
│   │   ├── RiskSettings.vue              # Main risk panel
│   │   ├── LossLimitInput.vue            # Loss limit config
│   │   ├── TrailingStopConfig.vue        # Trailing SL config
│   │   ├── MarginLimitInput.vue          # Margin limit config
│   │   ├── TimeRestrictions.vue          # Time-based restrictions
│   │   ├── CooldownConfig.vue            # Cooldown settings
│   │   └── FailureHandling.vue           # Network/system failure
│   │
│   ├── schedule/
│   │   ├── ScheduleConfig.vue            # Main schedule panel
│   │   ├── ActivationModeSelector.vue    # Always/DateRange/etc
│   │   ├── DayPicker.vue                 # Day selection grid
│   │   ├── TimeWindowPicker.vue          # Start/end time
│   │   ├── PositionLifecycle.vue         # Intraday/Positional
│   │   └── PrioritySelector.vue          # Strategy priority
│   │
│   ├── monitoring/
│   │   ├── StrategyCard.vue              # Strategy summary card
│   │   ├── StrategyCardExpanded.vue      # Expanded view
│   │   ├── ConditionProgress.vue         # Progress to trigger
│   │   ├── ConditionMonitor.vue          # Multiple conditions
│   │   ├── ActivityFeed.vue              # Recent activity list
│   │   ├── ActivityItem.vue              # Single activity entry
│   │   ├── PositionsTable.vue            # Current positions
│   │   ├── PayoffChartMini.vue           # Mini payoff chart
│   │   └── RiskGauge.vue                 # Visual risk indicator
│   │
│   ├── actions/
│   │   ├── KillSwitch.vue                # Emergency stop
│   │   ├── KillSwitchModal.vue           # Confirmation dialog
│   │   ├── ConfirmationModal.vue         # Semi-auto confirm
│   │   ├── PauseResumeButton.vue         # Pause/Resume toggle
│   │   ├── ForceEntryButton.vue          # Manual entry trigger
│   │   └── ForceExitButton.vue           # Manual exit trigger
│   │
│   └── shared/
│       ├── StatusBadge.vue               # Status indicator
│       ├── PnLDisplay.vue                # P&L with color
│       ├── ProgressBar.vue               # Generic progress
│       ├── TooltipInfo.vue               # Info tooltip
│       ├── StepIndicator.vue             # Wizard steps
│       ├── ValidationMessage.vue         # Error/warning msg
│       └── EmptyState.vue                # No data state
```

### 1.2 Design Tokens

```typescript
// design-tokens.ts

export const colors = {
  // Status Colors
  statusActive: '#00b386',      // Green - Active/Profit
  statusWaiting: '#f1c40f',     // Yellow - Waiting
  statusPending: '#f39c12',     // Orange - Pending confirmation
  statusPaused: '#6c757d',      // Gray - Paused
  statusError: '#e74c3c',       // Red - Error/Loss
  statusCompleted: '#3498db',   // Blue - Completed
  
  // Action Colors
  actionPrimary: '#e74c3c',     // Red - Primary action
  actionSecondary: '#6c757d',   // Gray - Secondary action
  actionDanger: '#dc3545',      // Dark red - Dangerous action
  actionSuccess: '#00b386',     // Green - Success action
  
  // Background Colors
  bgPrimary: '#212529',         // Dark background
  bgSecondary: '#2d3238',       // Card background
  bgTertiary: '#343a40',        // Input background
  bgHover: '#3d4349',           // Hover state
  
  // Text Colors
  textPrimary: '#ffffff',
  textSecondary: '#adb5bd',
  textMuted: '#6c757d',
  
  // Border Colors
  borderDefault: '#495057',
  borderFocus: '#e74c3c',
};

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
};

export const typography = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  fontSize: {
    xs: '11px',
    sm: '13px',
    md: '14px',
    lg: '16px',
    xl: '20px',
    xxl: '24px',
  },
  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
};

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px rgba(0, 0, 0, 0.3)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.3)',
};
```

---

## 2. Condition Builder Components

### 2.1 ConditionBuilder.vue

**Purpose:** Main container that orchestrates condition building with three modes (Simple, Advanced, Visual).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONDITION BUILDER                                                           │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Mode: [● Simple] [○ Advanced] [○ Visual]                     [? Help]  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Condition Logic:                                                       │ │
│ │  ● All conditions must be true (AND)                                    │ │
│ │  ○ Any condition can be true (OR)                                       │ │
│ │  ○ Custom logic                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  [CONDITION ROWS RENDERED HERE]                                         │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                        [+ Add Condition]                                    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📝 PREVIEW                                                             │ │
│ │  Entry will trigger when:                                               │ │
│ │  Time is after 09:20 AND India VIX is between 13 and 18                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ConditionBuilderProps {
  // Initial conditions to load
  initialConditions?: Condition[];
  
  // Condition logic type
  logicType?: 'AND' | 'OR' | 'CUSTOM';
  
  // Available variables based on context
  availableVariables?: VariableDefinition[];
  
  // Mode: simple dropdown, advanced expression, visual flowchart
  defaultMode?: 'simple' | 'advanced' | 'visual';
  
  // Whether to show preview
  showPreview?: boolean;
  
  // Context: entry conditions vs adjustment conditions
  context?: 'entry' | 'adjustment';
  
  // Maximum conditions allowed
  maxConditions?: number;
  
  // Disabled state
  disabled?: boolean;
}

interface Condition {
  id: string;
  variable: string;
  operator: OperatorType;
  value: ConditionValue;
  enabled: boolean;
}

type OperatorType = 
  | 'equals' 
  | 'not_equals' 
  | 'greater_than' 
  | 'less_than'
  | 'greater_equals' 
  | 'less_equals'
  | 'between'
  | 'not_between'
  | 'crosses_above'
  | 'crosses_below';

type ConditionValue = number | string | [number, number] | boolean;

interface VariableDefinition {
  key: string;
  label: string;
  category: 'price' | 'time' | 'indicator' | 'volatility' | 'oi' | 'event';
  valueType: 'number' | 'time' | 'percentage' | 'boolean';
  operators: OperatorType[];
  defaultValue?: ConditionValue;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
}
```

**Emits:**

```typescript
interface ConditionBuilderEmits {
  (e: 'update:conditions', conditions: Condition[]): void;
  (e: 'update:logicType', logicType: 'AND' | 'OR' | 'CUSTOM'): void;
  (e: 'update:customExpression', expression: string): void;
  (e: 'validation-change', isValid: boolean, errors: string[]): void;
}
```

**Component State:**

```typescript
interface ConditionBuilderState {
  conditions: Condition[];
  logicType: 'AND' | 'OR' | 'CUSTOM';
  customExpression: string;
  mode: 'simple' | 'advanced' | 'visual';
  validationErrors: Map<string, string>;
  previewText: string;
}
```

**Methods:**

```typescript
// Add new condition with defaults
addCondition(): void

// Remove condition by ID
removeCondition(id: string): void

// Update single condition
updateCondition(id: string, updates: Partial<Condition>): void

// Reorder conditions (for drag-drop)
reorderConditions(fromIndex: number, toIndex: number): void

// Validate all conditions
validateConditions(): { isValid: boolean; errors: string[] }

// Generate human-readable preview
generatePreview(): string

// Convert conditions to expression (for backend)
toExpression(): string

// Parse expression to conditions (for loading)
fromExpression(expression: string): void
```

---

### 2.2 ConditionRow.vue

**Purpose:** Single condition row with variable, operator, and value inputs.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONDITION ROW                                                               │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ☰  [▼ NIFTY Spot Price  ]  [▼ is greater than ]  [ 26000      ]  [🗑️] │ │
│ │  │                                                                      │ │
│ │  │  Drag handle                                                         │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ BETWEEN OPERATOR VARIANT:                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ☰  [▼ India VIX         ]  [▼ is between      ]  [ 13 ] and [ 18 ] [🗑️]│ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ TIME VARIANT:                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ☰  [▼ Time              ]  [▼ is after        ]  [ 09:20 ⏰ ]     [🗑️] │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ DISABLED STATE:                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                    ░░░░ │ │
│ │  ☰  [▼ NIFTY Spot Price  ]  [▼ is greater than ]  [ 26000      ]  [🗑️] │ │
│ │     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░       │ │
│ │  [○] Disabled - click to enable                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ VALIDATION ERROR STATE:                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                         ┌─────────────┐ │ │
│ │  ☰  [▼ NIFTY Spot Price  ]  [▼ is greater than ]  [    ⚠️    ]  [🗑️] │ │
│ │                                                         └─────────────┘ │ │
│ │  ⚠️ Value is required                                                   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ConditionRowProps {
  condition: Condition;
  index: number;
  availableVariables: VariableDefinition[];
  disabled?: boolean;
  showDragHandle?: boolean;
  showDeleteButton?: boolean;
  validationError?: string;
}
```

**Emits:**

```typescript
interface ConditionRowEmits {
  (e: 'update', updates: Partial<Condition>): void;
  (e: 'delete'): void;
  (e: 'toggle-enabled'): void;
}
```

**Interaction States:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INTERACTION STATES                                                          │
│                                                                             │
│ DEFAULT:                                                                    │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ Background: #2d3238  Border: #495057  Opacity: 100%                 │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ HOVER:                                                                      │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ Background: #343a40  Border: #495057  Drag handle visible           │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ DRAGGING:                                                                   │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ Background: #3d4349  Border: #e74c3c  Shadow: lg  Opacity: 90%      │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ DISABLED:                                                                   │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ Background: #2d3238  Border: #495057  Opacity: 50%  Strikethrough   │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│ ERROR:                                                                      │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ Background: #2d3238  Border: #e74c3c  Error message below           │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.3 VariableSelector.vue

**Purpose:** Categorized dropdown for selecting condition variables.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ VARIABLE SELECTOR                                                           │
│                                                                             │
│ CLOSED STATE:                                                               │
│ ┌─────────────────────────────┐                                            │
│ │ 📊 NIFTY Spot Price      ▼ │                                            │
│ └─────────────────────────────┘                                            │
│                                                                             │
│ OPEN STATE (with categories):                                               │
│ ┌─────────────────────────────┐                                            │
│ │ 🔍 Search variables...      │                                            │
│ ├─────────────────────────────┤                                            │
│ │ 📊 PRICE-BASED              │                                            │
│ │   ├─ NIFTY Spot Price       │                                            │
│ │   ├─ NIFTY Change %         │                                            │
│ │   ├─ NIFTY Day High         │                                            │
│ │   ├─ NIFTY Day Low          │                                            │
│ │   ├─ BANKNIFTY Spot Price   │                                            │
│ │   └─ Premium (any leg)      │                                            │
│ │                             │                                            │
│ │ 📅 TIME-BASED               │                                            │
│ │   ├─ Current Time           │                                            │
│ │   ├─ Minutes Since Open     │                                            │
│ │   └─ Minutes To Close       │                                            │
│ │                             │                                            │
│ │ 📈 INDICATOR-BASED          │                                            │
│ │   ├─ RSI (14)               │                                            │
│ │   ├─ VWAP                   │                                            │
│ │   └─ Moving Average (20)    │                                            │
│ │                             │                                            │
│ │ 🌊 VOLATILITY               │                                            │
│ │   ├─ India VIX              │                                            │
│ │   ├─ IV Percentile          │                                            │
│ │   └─ IV Rank                │                                            │
│ │                             │                                            │
│ │ 📊 OI-BASED                 │                                            │
│ │   ├─ PCR (Put-Call Ratio)   │                                            │
│ │   ├─ Max Pain               │                                            │
│ │   ├─ OI Change % (CE)       │                                            │
│ │   └─ OI Change % (PE)       │                                            │
│ │                             │                                            │
│ │ 📅 EVENT-BASED              │                                            │
│ │   ├─ Is Expiry Day          │                                            │
│ │   ├─ Is Monthly Expiry      │                                            │
│ │   └─ Days to Expiry         │                                            │
│ └─────────────────────────────┘                                            │
│                                                                             │
│ SEARCH FILTERED:                                                            │
│ ┌─────────────────────────────┐                                            │
│ │ 🔍 vix                      │                                            │
│ ├─────────────────────────────┤                                            │
│ │ 🌊 VOLATILITY               │                                            │
│ │   └─ India VIX    ✓ Match   │                                            │
│ └─────────────────────────────┘                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface VariableSelectorProps {
  modelValue: string;
  variables: VariableDefinition[];
  placeholder?: string;
  disabled?: boolean;
  showSearch?: boolean;
  showCategories?: boolean;
}
```

**Variable Definitions (Complete List):**

```typescript
const CONDITION_VARIABLES: VariableDefinition[] = [
  // Price-Based
  {
    key: 'NIFTY.SPOT',
    label: 'NIFTY Spot Price',
    category: 'price',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than', 'greater_equals', 'less_equals', 'between', 'crosses_above', 'crosses_below'],
    min: 0,
    max: 100000,
    step: 50,
    unit: '₹'
  },
  {
    key: 'NIFTY.CHANGE_PCT',
    label: 'NIFTY Change %',
    category: 'price',
    valueType: 'percentage',
    operators: ['equals', 'greater_than', 'less_than', 'between'],
    min: -10,
    max: 10,
    step: 0.1,
    unit: '%'
  },
  {
    key: 'NIFTY.HIGH',
    label: 'NIFTY Day High',
    category: 'price',
    valueType: 'number',
    operators: ['crosses_above', 'crosses_below', 'greater_than', 'less_than'],
  },
  {
    key: 'NIFTY.LOW',
    label: 'NIFTY Day Low',
    category: 'price',
    valueType: 'number',
    operators: ['crosses_above', 'crosses_below', 'greater_than', 'less_than'],
  },
  {
    key: 'BANKNIFTY.SPOT',
    label: 'BANKNIFTY Spot Price',
    category: 'price',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than', 'greater_equals', 'less_equals', 'between', 'crosses_above', 'crosses_below'],
    step: 100,
  },
  {
    key: 'PREMIUM.ANY',
    label: 'Premium (any leg)',
    category: 'price',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'between'],
    min: 0,
  },
  {
    key: 'PREMIUM.SOLD_CE',
    label: 'Sold CE Premium',
    category: 'price',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'doubles', 'halves'],
  },
  {
    key: 'PREMIUM.SOLD_PE',
    label: 'Sold PE Premium',
    category: 'price',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'doubles', 'halves'],
  },
  
  // Time-Based
  {
    key: 'TIME.CURRENT',
    label: 'Current Time',
    category: 'time',
    valueType: 'time',
    operators: ['equals', 'greater_than', 'less_than', 'between'],
    defaultValue: '09:20',
  },
  {
    key: 'TIME.MINUTES_SINCE_OPEN',
    label: 'Minutes Since Open',
    category: 'time',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than'],
    min: 0,
    max: 375,
    unit: 'mins'
  },
  {
    key: 'TIME.MINUTES_TO_CLOSE',
    label: 'Minutes To Close',
    category: 'time',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than'],
    min: 0,
    max: 375,
    unit: 'mins'
  },
  
  // Indicator-Based
  {
    key: 'INDICATOR.RSI_14',
    label: 'RSI (14)',
    category: 'indicator',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'between', 'crosses_above', 'crosses_below'],
    min: 0,
    max: 100,
  },
  {
    key: 'INDICATOR.VWAP',
    label: 'VWAP',
    category: 'indicator',
    valueType: 'number',
    operators: ['crosses_above', 'crosses_below', 'greater_than', 'less_than'],
  },
  {
    key: 'INDICATOR.SMA_20',
    label: 'SMA (20)',
    category: 'indicator',
    valueType: 'number',
    operators: ['crosses_above', 'crosses_below', 'greater_than', 'less_than'],
  },
  
  // Volatility
  {
    key: 'VOLATILITY.VIX',
    label: 'India VIX',
    category: 'volatility',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than', 'between', 'crosses_above', 'crosses_below'],
    min: 8,
    max: 50,
    step: 0.5,
  },
  {
    key: 'VOLATILITY.IV_PERCENTILE',
    label: 'IV Percentile',
    category: 'volatility',
    valueType: 'percentage',
    operators: ['greater_than', 'less_than', 'between'],
    min: 0,
    max: 100,
    unit: '%'
  },
  {
    key: 'VOLATILITY.IV_RANK',
    label: 'IV Rank',
    category: 'volatility',
    valueType: 'percentage',
    operators: ['greater_than', 'less_than', 'between'],
    min: 0,
    max: 100,
    unit: '%'
  },
  
  // OI-Based
  {
    key: 'OI.PCR',
    label: 'PCR (Put-Call Ratio)',
    category: 'oi',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'between', 'crosses_above', 'crosses_below'],
    min: 0,
    max: 3,
    step: 0.1,
  },
  {
    key: 'OI.MAX_PAIN',
    label: 'Max Pain',
    category: 'oi',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than'],
  },
  {
    key: 'OI.CHANGE_PCT_CE',
    label: 'OI Change % (CE)',
    category: 'oi',
    valueType: 'percentage',
    operators: ['greater_than', 'less_than', 'between'],
    min: -100,
    max: 100,
    unit: '%'
  },
  {
    key: 'OI.CHANGE_PCT_PE',
    label: 'OI Change % (PE)',
    category: 'oi',
    valueType: 'percentage',
    operators: ['greater_than', 'less_than', 'between'],
    min: -100,
    max: 100,
    unit: '%'
  },
  
  // Event-Based
  {
    key: 'EVENT.IS_EXPIRY',
    label: 'Is Expiry Day',
    category: 'event',
    valueType: 'boolean',
    operators: ['equals'],
    defaultValue: true,
  },
  {
    key: 'EVENT.IS_MONTHLY_EXPIRY',
    label: 'Is Monthly Expiry',
    category: 'event',
    valueType: 'boolean',
    operators: ['equals'],
    defaultValue: true,
  },
  {
    key: 'EVENT.DTE',
    label: 'Days to Expiry',
    category: 'event',
    valueType: 'number',
    operators: ['equals', 'greater_than', 'less_than', 'less_equals'],
    min: 0,
    max: 60,
    unit: 'days'
  },
  
  // Strategy-Specific (for adjustments)
  {
    key: 'STRATEGY.PNL',
    label: 'Strategy P&L',
    category: 'price',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'between'],
    unit: '₹'
  },
  {
    key: 'STRATEGY.PNL_PCT',
    label: 'Strategy P&L %',
    category: 'price',
    valueType: 'percentage',
    operators: ['greater_than', 'less_than', 'between'],
    unit: '%'
  },
  {
    key: 'STRATEGY.DELTA',
    label: 'Strategy Delta',
    category: 'indicator',
    valueType: 'number',
    operators: ['greater_than', 'less_than', 'between'],
    min: -1,
    max: 1,
    step: 0.1,
  },
  {
    key: 'STRATEGY.THETA',
    label: 'Strategy Theta',
    category: 'indicator',
    valueType: 'number',
    operators: ['greater_than', 'less_than'],
  },
  {
    key: 'SPOT.VS_SOLD_CE',
    label: 'Spot vs Sold CE Strike',
    category: 'price',
    valueType: 'number',
    operators: ['breaches', 'approaches'],
    unit: 'pts'
  },
  {
    key: 'SPOT.VS_SOLD_PE',
    label: 'Spot vs Sold PE Strike',
    category: 'price',
    valueType: 'number',
    operators: ['breaches', 'approaches'],
    unit: 'pts'
  },
];
```

---

### 2.4 OperatorSelector.vue

**Purpose:** Dropdown for selecting comparison operator based on variable type.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPERATOR SELECTOR                                                           │
│                                                                             │
│ NUMBER OPERATORS:                                                           │
│ ┌─────────────────────────┐                                                │
│ │ is greater than      ▼ │                                                │
│ ├─────────────────────────┤                                                │
│ │   is equal to           │                                                │
│ │   is not equal to       │                                                │
│ │ ✓ is greater than       │                                                │
│ │   is less than          │                                                │
│ │   is greater or equal   │                                                │
│ │   is less or equal      │                                                │
│ │   is between            │                                                │
│ │   is not between        │                                                │
│ │   crosses above         │                                                │
│ │   crosses below         │                                                │
│ └─────────────────────────┘                                                │
│                                                                             │
│ TIME OPERATORS:                                                             │
│ ┌─────────────────────────┐                                                │
│ │ is after             ▼ │                                                │
│ ├─────────────────────────┤                                                │
│ │   is exactly            │                                                │
│ │   is before             │                                                │
│ │ ✓ is after              │                                                │
│ │   is between            │                                                │
│ └─────────────────────────┘                                                │
│                                                                             │
│ BOOLEAN OPERATORS:                                                          │
│ ┌─────────────────────────┐                                                │
│ │ is true              ▼ │                                                │
│ ├─────────────────────────┤                                                │
│ │ ✓ is true               │                                                │
│ │   is false              │                                                │
│ └─────────────────────────┘                                                │
│                                                                             │
│ PREMIUM-SPECIFIC:                                                           │
│ ┌─────────────────────────┐                                                │
│ │ doubles              ▼ │                                                │
│ ├─────────────────────────┤                                                │
│ │ ✓ doubles (2x entry)    │                                                │
│ │   halves (0.5x entry)   │                                                │
│ │   increases by %        │                                                │
│ │   decreases by %        │                                                │
│ └─────────────────────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface OperatorSelectorProps {
  modelValue: OperatorType;
  allowedOperators: OperatorType[];
  disabled?: boolean;
}

const OPERATOR_LABELS: Record<OperatorType, string> = {
  equals: 'is equal to',
  not_equals: 'is not equal to',
  greater_than: 'is greater than',
  less_than: 'is less than',
  greater_equals: 'is greater or equal to',
  less_equals: 'is less or equal to',
  between: 'is between',
  not_between: 'is not between',
  crosses_above: 'crosses above',
  crosses_below: 'crosses below',
  breaches: 'breaches',
  approaches: 'approaches (within)',
  doubles: 'doubles (2x entry)',
  halves: 'halves (0.5x entry)',
};
```

---

### 2.5 ValueInput.vue

**Purpose:** Dynamic value input that adapts to the variable type.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ VALUE INPUT VARIANTS                                                        │
│                                                                             │
│ NUMBER INPUT:                                                               │
│ ┌───────────────────────┐                                                  │
│ │ [ 26000         ] ₹   │ ← With unit suffix                               │
│ └───────────────────────┘                                                  │
│ ┌───────────────────────┐                                                  │
│ │ [−] [ 26000     ] [+] │ ← With increment buttons                         │
│ └───────────────────────┘                                                  │
│                                                                             │
│ BETWEEN INPUT (two values):                                                 │
│ ┌───────────────────────────────────────┐                                  │
│ │ [ 13      ] and [ 18      ]           │                                  │
│ └───────────────────────────────────────┘                                  │
│                                                                             │
│ TIME INPUT:                                                                 │
│ ┌───────────────────────┐                                                  │
│ │ [ 09:20       ] ⏰     │ ← Time picker                                    │
│ └───────────────────────┘                                                  │
│                                                                             │
│ TIME BETWEEN:                                                               │
│ ┌───────────────────────────────────────┐                                  │
│ │ [ 09:20 ⏰ ] and [ 15:15 ⏰ ]          │                                  │
│ └───────────────────────────────────────┘                                  │
│                                                                             │
│ PERCENTAGE INPUT:                                                           │
│ ┌───────────────────────┐                                                  │
│ │ [ 2.5           ] %   │                                                  │
│ └───────────────────────┘                                                  │
│                                                                             │
│ BOOLEAN INPUT:                                                              │
│ ┌───────────────────────┐                                                  │
│ │ [▼ Yes               ]│                                                  │
│ └───────────────────────┘                                                  │
│                                                                             │
│ STRIKE REFERENCE INPUT (for adjustment context):                            │
│ ┌─────────────────────────────────────────┐                                │
│ │ [▼ Sold CE Strike    ] + [ 100    ] pts │                                │
│ └─────────────────────────────────────────┘                                │
│                                                                             │
│ VALIDATION STATES:                                                          │
│ ┌───────────────────────┐                                                  │
│ │ [ -5          ] ⚠️    │ ← Error: Below minimum (0)                       │
│ └───────────────────────┘                                                  │
│ ┌───────────────────────┐                                                  │
│ │ [             ] ⚠️    │ ← Error: Required                                │
│ └───────────────────────┘                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ValueInputProps {
  modelValue: ConditionValue;
  valueType: 'number' | 'time' | 'percentage' | 'boolean';
  operator: OperatorType;
  min?: number;
  max?: number;
  step?: number;
  unit?: string;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
}
```

**Component Logic:**

```typescript
// Computed: Determines if two inputs needed
const needsTwoInputs = computed(() => {
  return ['between', 'not_between'].includes(props.operator);
});

// Computed: Input type based on valueType
const inputType = computed(() => {
  switch (props.valueType) {
    case 'time': return 'time';
    case 'boolean': return 'select';
    default: return 'number';
  }
});

// Validation
const validate = (value: ConditionValue): string | null => {
  if (value === null || value === undefined || value === '') {
    return 'Value is required';
  }
  
  if (props.valueType === 'number' || props.valueType === 'percentage') {
    const num = Number(value);
    if (isNaN(num)) return 'Must be a number';
    if (props.min !== undefined && num < props.min) {
      return `Minimum value is ${props.min}`;
    }
    if (props.max !== undefined && num > props.max) {
      return `Maximum value is ${props.max}`;
    }
  }
  
  if (props.operator === 'between' && Array.isArray(value)) {
    if (value[0] >= value[1]) {
      return 'First value must be less than second';
    }
  }
  
  return null;
};
```

---

### 2.6 ExpressionEditor.vue

**Purpose:** Advanced text-based expression editor with syntax highlighting and validation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXPRESSION EDITOR                                                           │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  EDITOR TOOLBAR                                                         │ │
│ │  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐                      │ │
│ │  │ AND │ OR  │  (  │  )  │  >  │  <  │  =  │ != │  [Format] [Validate] │ │
│ │  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘                      │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CODE EDITOR (with syntax highlighting)                                 │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │ 1 │ (                                                               │ │ │
│ │ │ 2 │   TIME.CURRENT > "09:20"                                        │ │ │
│ │ │ 3 │   AND VOLATILITY.VIX >= 13                                      │ │ │
│ │ │ 4 │   AND VOLATILITY.VIX <= 18                                      │ │ │
│ │ │ 5 │ )                                                               │ │ │
│ │ │ 6 │ OR                                                              │ │ │
│ │ │ 7 │ (                                                               │ │ │
│ │ │ 8 │   TIME.CURRENT > "10:00"                                        │ │ │
│ │ │ 9 │   AND NIFTY.CHANGE_PCT < -1.0                                   │ │ │
│ │ │10 │ )                                                               │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  AVAILABLE VARIABLES (click to insert)                                  │ │
│ │                                                                         │ │
│ │  ┌─────────────┬─────────────┬─────────────┬─────────────┐             │ │
│ │  │ TIME.CURRENT│ NIFTY.SPOT  │ VIX         │ PCR         │             │ │
│ │  ├─────────────┼─────────────┼─────────────┼─────────────┤             │ │
│ │  │ NIFTY.HIGH  │ NIFTY.LOW   │ IV_PERCENTILE│ OI.CHANGE% │             │ │
│ │  └─────────────┴─────────────┴─────────────┴─────────────┘             │ │
│ │                                                      [Show All →]       │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  VALIDATION RESULT                                                      │ │
│ │                                                                         │ │
│ │  ✅ Expression is valid                                                  │ │
│ │                                                                         │ │
│ │  Parsed as:                                                             │ │
│ │  • Group 1 (OR):                                                        │ │
│ │    - Time is after 09:20                                                │ │
│ │    - India VIX is between 13 and 18                                     │ │
│ │  • Group 2 (OR):                                                        │ │
│ │    - Time is after 10:00                                                │ │
│ │    - NIFTY change is less than -1%                                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ERROR STATE:                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ❌ Expression has errors                                                │ │
│ │                                                                         │ │
│ │  Line 3: Unknown variable "VIXX" - did you mean "VIX"?                  │ │
│ │  Line 5: Unclosed parenthesis                                           │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ExpressionEditorProps {
  modelValue: string;
  availableVariables: VariableDefinition[];
  disabled?: boolean;
  height?: string;
  showToolbar?: boolean;
  showVariables?: boolean;
  showValidation?: boolean;
}
```

**Syntax Highlighting Rules:**

```typescript
const syntaxRules = {
  keywords: {
    pattern: /\b(AND|OR|NOT)\b/gi,
    className: 'keyword', // color: #e74c3c
  },
  variables: {
    pattern: /\b(TIME|NIFTY|BANKNIFTY|VOLATILITY|VIX|OI|PCR|STRATEGY|SPOT|PREMIUM|INDICATOR)\.[A-Z_]+\b/g,
    className: 'variable', // color: #3498db
  },
  operators: {
    pattern: /(>=|<=|!=|>|<|=)/g,
    className: 'operator', // color: #f39c12
  },
  numbers: {
    pattern: /\b\d+\.?\d*\b/g,
    className: 'number', // color: #00b386
  },
  strings: {
    pattern: /"[^"]*"/g,
    className: 'string', // color: #9b59b6
  },
  parentheses: {
    pattern: /[()]/g,
    className: 'paren', // color: #95a5a6
  },
};
```

**Expression Parser:**

```typescript
interface ParseResult {
  isValid: boolean;
  errors: ParseError[];
  ast?: ExpressionAST;
  preview?: string;
}

interface ParseError {
  line: number;
  column: number;
  message: string;
  suggestion?: string;
}

interface ExpressionAST {
  type: 'AND' | 'OR' | 'CONDITION';
  children?: ExpressionAST[];
  condition?: {
    variable: string;
    operator: OperatorType;
    value: ConditionValue;
  };
}

function parseExpression(expression: string): ParseResult {
  // Tokenize
  // Build AST
  // Validate variables exist
  // Validate operator compatibility
  // Generate preview text
}
```

---

### 2.7 FlowchartBuilder.vue

**Purpose:** Visual node-based condition builder with drag-and-drop.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FLOWCHART BUILDER                                                           │
│                                                                             │
│ ┌──────────────┐  ┌─────────────────────────────────────────────────────┐  │
│ │  TOOLBOX     │  │  CANVAS                                             │  │
│ │  ───────────  │  │                                                     │  │
│ │              │  │                    ┌─────────────┐                   │  │
│ │  ┌────────┐  │  │                    │   START     │                   │  │
│ │  │◇ IF    │  │  │                    └──────┬──────┘                   │  │
│ │  └────────┘  │  │                           │                          │  │
│ │              │  │                           ▼                          │  │
│ │  ┌────────┐  │  │              ┌────────────────────────┐              │  │
│ │  │◆ AND   │  │  │              │   Time > 09:20?        │──── No ───┐  │  │
│ │  └────────┘  │  │              │   ◇ Condition          │           │  │  │
│ │              │  │              └───────────┬────────────┘           │  │  │
│ │  ┌────────┐  │  │                    Yes   │                        │  │  │
│ │  │◇ OR    │  │  │                          ▼                        │  │  │
│ │  └────────┘  │  │              ┌────────────────────────┐           │  │  │
│ │              │  │              │   VIX between 13-18?   │── No ──┐  │  │  │
│ │  ┌────────┐  │  │              │   ◇ Condition          │        │  │  │  │
│ │  │→ THEN  │  │  │              └───────────┬────────────┘        │  │  │  │
│ │  └────────┘  │  │                    Yes   │                     │  │  │  │
│ │              │  │                          ▼                     │  │  │  │
│ │  ┌────────┐  │  │              ┌────────────────────────┐        │  │  │  │
│ │  │● ACTION│  │  │              │   ✅ TRIGGER ENTRY     │        │  │  │  │
│ │  └────────┘  │  │              │   ● Action             │        │  │  │  │
│ │              │  │              └────────────────────────┘        │  │  │  │
│ │              │  │                                                │  │  │  │
│ │              │  │                          ┌────────────────────┬┘  │  │  │
│ │              │  │                          │                    │   │  │  │
│ │              │  │                          ▼                    ▼   │  │  │
│ │              │  │              ┌────────────────────────────────────┴──┐│  │
│ │              │  │              │   ⏸ WAIT (continue monitoring)       ││  │
│ │              │  │              └───────────────────────────────────────┘│  │
│ │              │  │                                                       │  │
│ │              │  └───────────────────────────────────────────────────────┘  │
│ └──────────────┘                                                            │
│                                                                             │
│ NODE EDITOR PANEL (when node selected):                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  EDIT CONDITION NODE                                                    │ │
│ │                                                                         │ │
│ │  Variable: [▼ India VIX           ]                                     │ │
│ │  Operator: [▼ is between          ]                                     │ │
│ │  Value:    [ 13      ] and [ 18      ]                                  │ │
│ │                                                                         │ │
│ │  [Delete Node]                                     [Apply Changes]      │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface FlowchartBuilderProps {
  modelValue: FlowchartData;
  availableVariables: VariableDefinition[];
  disabled?: boolean;
  canvasHeight?: string;
}

interface FlowchartData {
  nodes: FlowchartNode[];
  edges: FlowchartEdge[];
}

interface FlowchartNode {
  id: string;
  type: 'start' | 'condition' | 'and' | 'or' | 'action' | 'wait';
  position: { x: number; y: number };
  data: {
    condition?: Condition;
    action?: 'trigger' | 'wait';
    label?: string;
  };
}

interface FlowchartEdge {
  id: string;
  source: string;
  target: string;
  label?: 'yes' | 'no';
}
```

**Node Types:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ NODE TYPES                                                                  │
│                                                                             │
│ START NODE:                                                                 │
│ ┌─────────────────┐                                                        │
│ │ ○   START       │  Rounded rectangle, green border                       │
│ │     ──┬──       │  Single output connector                               │
│ └───────┼─────────┘                                                        │
│         ▼                                                                   │
│                                                                             │
│ CONDITION NODE:                                                             │
│ ┌─────────────────────────┐                                                │
│ │ ◇   Time > 09:20?       │  Diamond shape, blue border                    │
│ │     ────┬────           │  One input, two outputs (Yes/No)               │
│ └─────Yes─┼───No──────────┘                                                │
│           ▼     ▼                                                           │
│                                                                             │
│ AND GATE:                                                                   │
│ ┌─────────────────┐                                                        │
│ │ ◆   AND         │  Rectangle, purple border                              │
│ │   ──┬── ──┬──   │  Multiple inputs, one output                           │
│ └─────┼─────┼─────┘  All inputs must be true                               │
│       ▼     ▼                                                               │
│                                                                             │
│ OR GATE:                                                                    │
│ ┌─────────────────┐                                                        │
│ │ ◇   OR          │  Rectangle, orange border                              │
│ │   ──┬── ──┬──   │  Multiple inputs, one output                           │
│ └─────┼─────┼─────┘  Any input can be true                                 │
│       ▼     ▼                                                               │
│                                                                             │
│ ACTION NODE:                                                                │
│ ┌─────────────────┐                                                        │
│ │ ●  TRIGGER      │  Rounded rectangle, green fill                         │
│ │    ENTRY        │  One input, no output (terminal)                       │
│ └─────────────────┘                                                        │
│                                                                             │
│ WAIT NODE:                                                                  │
│ ┌─────────────────┐                                                        │
│ │ ⏸  WAIT         │  Rounded rectangle, gray border                        │
│ │    (continue)   │  One input, no output (loops back to start)            │
│ └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Adjustment Rule Components

### 3.1 AdjustmentRuleList.vue

**Purpose:** Container for multiple adjustment rules with drag-drop reordering.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ADJUSTMENT RULE LIST                                                        │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ADJUSTMENT RULES                                          [+ Add Rule] │ │
│ │  Define how the strategy should react to market changes                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📋 Rules are evaluated in order. First matching rule triggers.         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ☰ RULE 1 - Stop Loss                              [✓ Enabled]  [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │  IF: Strategy P&L loss exceeds ₹5,000                                   │ │
│ │  THEN: Add Hedge (Buy PE 200 pts below + Buy CE 200 pts above)          │ │
│ │  MODE: Semi-Automatic (requires confirmation)                           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ☰ RULE 2 - Strike Breach                          [✓ Enabled]  [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │  IF: Spot price breaches sold CE strike                                 │ │
│ │  THEN: Shift strikes (move CE side +100 pts)                            │ │
│ │  MODE: Fully Automatic                                                  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ☰ RULE 3 - Profit Target / Time Exit              [✓ Enabled]  [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │  IF: P&L profit reaches ₹8,000 OR Time is 15:15                         │ │
│ │  THEN: Exit Entire Strategy                                             │ │
│ │  MODE: Fully Automatic                                                  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│ │  ☰ RULE 4 - Theta Decay Target                     [○ Disabled] [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │  IF: Strategy Theta reaches ₹2,000                                      │ │
│ │  THEN: Alert Only                                                       │ │
│ │  MODE: Alert Only (no action)                                           │ │
│ │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                        [+ Add Adjustment Rule]                              │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  💡 TIP: Add at least one exit rule (profit target or time-based)       │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface AdjustmentRuleListProps {
  modelValue: AdjustmentRule[];
  strategyLegs: StrategyLeg[];  // Current strategy legs for context
  maxRules?: number;
  disabled?: boolean;
}

interface AdjustmentRule {
  id: string;
  name: string;
  enabled: boolean;
  trigger: {
    conditions: Condition[];
    logic: 'AND' | 'OR';
  };
  action: AdjustmentAction;
  executionMode: 'auto' | 'semi-auto';
  priority: number;
}

interface AdjustmentAction {
  type: 'exit_all' | 'exit_partial' | 'roll' | 'shift' | 'add_hedge' | 'scale_up' | 'scale_down' | 'convert' | 'alert_only';
  config: ActionConfig;
}

type ActionConfig = 
  | ExitConfig 
  | RollConfig 
  | ShiftConfig 
  | HedgeConfig 
  | ScaleConfig 
  | AlertConfig;
```

---

### 3.2 AdjustmentRuleCard.vue

**Purpose:** Single adjustment rule card with expandable details.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ADJUSTMENT RULE CARD                                                        │
│                                                                             │
│ COLLAPSED STATE:                                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ☰ RULE 1 - Stop Loss                              [✓ Enabled]  [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │  IF: Strategy P&L loss exceeds ₹5,000                                   │ │
│ │  THEN: Add Hedge                                                        │ │
│ │  MODE: 🔔 Semi-Auto                                            [▼]     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ EXPANDED STATE:                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ☰ RULE 1 - Stop Loss                              [✓ Enabled]  [⋮]    │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │                                                                         │ │
│ │  📍 TRIGGER CONDITION                                                   │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ [CONDITION BUILDER - embedded]                                   │   │ │
│ │  │                                                                  │   │ │
│ │  │ [▼ Strategy P&L ] [▼ loss exceeds ] [₹ 5000        ]       [🗑️] │   │ │
│ │  │                                                                  │   │ │
│ │  │                    [+ Add Condition]                             │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  🎯 ACTION                                                              │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ Action Type: [▼ Add Hedge                                  ]    │   │ │
│ │  │                                                                  │   │ │
│ │  │ ┌─ Hedge Configuration ──────────────────────────────────────┐  │   │ │
│ │  │ │                                                             │  │   │ │
│ │  │ │ Hedge Type: [▼ Both sides (PE + CE)    ]                   │  │   │ │
│ │  │ │                                                             │  │   │ │
│ │  │ │ PE Strike: [▼ 200 pts below spot       ]                   │  │   │ │
│ │  │ │ CE Strike: [▼ 200 pts above spot       ]                   │  │   │ │
│ │  │ │                                                             │  │   │ │
│ │  │ │ Quantity:  [▼ Same as position (1 lot) ]                   │  │   │ │
│ │  │ │                                                             │  │   │ │
│ │  │ └─────────────────────────────────────────────────────────────┘  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ⚡ EXECUTION MODE                                                      │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ ○ Fully Automatic                                                │   │ │
│ │  │   Execute immediately when condition triggers                    │   │ │
│ │  │                                                                  │   │ │
│ │  │ ● Semi-Automatic                                                 │   │ │
│ │  │   Show confirmation modal, wait for approval                     │   │ │
│ │  │   Timeout: [▼ 60 seconds ] then [▼ Skip this adjustment ]       │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │                                                                  [▲]   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ CONTEXT MENU (⋮):                                                           │
│ ┌─────────────────┐                                                        │
│ │ ✏️ Rename        │                                                        │
│ │ 📋 Duplicate     │                                                        │
│ │ ↑ Move Up       │                                                        │
│ │ ↓ Move Down     │                                                        │
│ │ ───────────────  │                                                        │
│ │ 🗑️ Delete        │                                                        │
│ └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.3 ActionConfigurator.vue

**Purpose:** Dynamic action configuration based on selected action type.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTION CONFIGURATOR                                                         │
│                                                                             │
│ ACTION TYPE SELECTOR:                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ [▼ Select Action Type                                              ]    │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │  📤 EXIT ACTIONS                                                        │ │
│ │     Exit Entire Strategy       Close all legs at market/limit          │ │
│ │     Exit Partial              Close only selected legs                  │ │
│ │                                                                         │ │
│ │  🔄 ADJUSTMENT ACTIONS                                                  │ │
│ │     Roll Position             Move to next expiry                       │ │
│ │     Shift Strikes             Move strikes further OTM                  │ │
│ │     Add Hedge                 Add protective legs                       │ │
│ │                                                                         │ │
│ │  📊 SCALING ACTIONS                                                     │ │
│ │     Scale Up                  Add more lots                             │ │
│ │     Scale Down                Reduce position size                      │ │
│ │                                                                         │ │
│ │  🔀 OTHER                                                               │ │
│ │     Convert Strategy          Change strategy type                      │ │
│ │     Alert Only                No action, just notify                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ EXIT ENTIRE STRATEGY CONFIG:                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Exit Entire Strategy                                                   │ │
│ │                                                                         │ │
│ │  Order Type: [▼ MARKET                    ]                             │ │
│ │                                                                         │ │
│ │  ☐ Use limit orders with price improvement                              │ │
│ │     Try limit for [ 15 ] seconds, then convert to MARKET                │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ EXIT PARTIAL CONFIG:                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Exit Partial                                                           │ │
│ │                                                                         │ │
│ │  Exit which legs:                                                       │ │
│ │  ○ All losing legs (negative P&L)                                       │ │
│ │  ○ All profitable legs (positive P&L)                                   │ │
│ │  ○ Specific legs:                                                       │ │
│ │     ☑️ SELL PE 25800                                                     │ │
│ │     ☐ BUY PE 25600                                                      │ │
│ │     ☑️ SELL CE 26200                                                     │ │
│ │     ☐ BUY CE 26400                                                      │ │
│ │                                                                         │ │
│ │  Order Type: [▼ MARKET                    ]                             │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ ROLL POSITION CONFIG:                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Roll Position                                                          │ │
│ │                                                                         │ │
│ │  Roll to:        [▼ Next Week Expiry      ]                             │ │
│ │                                                                         │ │
│ │  Strike selection:                                                      │ │
│ │  ○ Same strike (maintain current strikes)                               │ │
│ │  ○ ATM (recalculate based on spot at roll time)                         │ │
│ │  ○ Same moneyness (maintain delta distance)                             │ │
│ │                                                                         │ │
│ │  Roll which legs:                                                       │ │
│ │  ● All legs                                                             │ │
│ │  ○ Only sold legs                                                       │ │
│ │  ○ Only bought legs                                                     │ │
│ │                                                                         │ │
│ │  Execution: [▼ Close current, then open new (sequential) ]              │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ SHIFT STRIKES CONFIG:                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Shift Strikes                                                          │ │
│ │                                                                         │ │
│ │  Shift direction:                                                       │ │
│ │  ● Away from spot (move OTM)                                            │ │
│ │  ○ Toward spot (move ITM)                                               │ │
│ │  ○ Custom                                                               │ │
│ │                                                                         │ │
│ │  Shift amount:   [ 100        ] points                                  │ │
│ │                                                                         │ │
│ │  Shift which side:                                                      │ │
│ │  ○ CE side only                                                         │ │
│ │  ○ PE side only                                                         │ │
│ │  ● Both sides (maintain spread width)                                   │ │
│ │                                                                         │ │
│ │  ┌─ Preview ─────────────────────────────────────────────────────────┐ │ │
│ │  │ Current:  SELL PE 25800 / BUY PE 25600 / SELL CE 26200 / BUY CE 26400│ │
│ │  │ After:    SELL PE 25700 / BUY PE 25500 / SELL CE 26300 / BUY CE 26500│ │
│ │  └───────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ ADD HEDGE CONFIG:                                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Add Hedge                                                              │ │
│ │                                                                         │ │
│ │  Hedge Type:                                                            │ │
│ │  ○ PE only (downside protection)                                        │ │
│ │  ○ CE only (upside protection)                                          │ │
│ │  ● Both sides                                                           │ │
│ │                                                                         │ │
│ │  ┌─ PE Hedge ─────────────────────────────────────────────────────────┐ │ │
│ │  │ Strike: [▼ 200 pts below spot          ]  or  [ 25500      ] fixed │ │ │
│ │  │ Qty:    [▼ Same as sold PE (1 lot)     ]                           │ │ │
│ │  └───────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ CE Hedge ─────────────────────────────────────────────────────────┐ │ │
│ │  │ Strike: [▼ 200 pts above spot          ]  or  [ 26500      ] fixed │ │ │
│ │  │ Qty:    [▼ Same as sold CE (1 lot)     ]                           │ │ │
│ │  └───────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  Max hedge cost: ₹ [ 3000      ] (skip if premium exceeds)              │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ SCALE UP CONFIG:                                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Scale Up (Add Lots)                                                    │ │
│ │                                                                         │ │
│ │  Add:  [ 1 ] lot(s)                                                     │ │
│ │                                                                         │ │
│ │  Entry price:                                                           │ │
│ │  ● Current market price                                                 │ │
│ │  ○ Limit at [ 2 ] % better than market                                  │ │
│ │                                                                         │ │
│ │  Max total lots: [ 3 ] (won't scale beyond this)                        │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ SCALE DOWN CONFIG:                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Scale Down (Reduce Lots)                                               │ │
│ │                                                                         │ │
│ │  Reduce by:                                                             │ │
│ │  ○ [ 1 ] lot(s)                                                         │ │
│ │  ● [ 50 ] % of position                                                 │ │
│ │                                                                         │ │
│ │  Min remaining lots: [ 1 ] (won't reduce below this)                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ ALERT ONLY CONFIG:                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Alert Only (No Trading Action)                                         │ │
│ │                                                                         │ │
│ │  Alert message: [ P&L reached ₹{value}. Consider adjusting position. ] │ │
│ │                                                                         │ │
│ │  Alert priority:                                                        │ │
│ │  ○ Normal (regular notification)                                        │ │
│ │  ● Urgent (prominent alert with sound)                                  │ │
│ │                                                                         │ │
│ │  Repeat alert every [ 5 ] minutes until acknowledged                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Order Execution Components

### 4.1 LegSequenceEditor.vue

**Purpose:** Drag-and-drop editor for defining leg execution order.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LEG SEQUENCE EDITOR                                                         │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  LEG EXECUTION ORDER                                                    │ │
│ │  Drag to reorder. Legs will execute from top to bottom.                 │ │
│ │                                                                         │ │
│ │  ┌─ Execution Queue ───────────────────────────────────────────────┐   │ │
│ │  │                                                                  │   │ │
│ │  │  ┌───────────────────────────────────────────────────────────┐  │   │ │
│ │  │  │ ☰  1. SELL PE 25800   │  75 qty  │  Credit leg  │  First │  │   │ │
│ │  │  └───────────────────────────────────────────────────────────┘  │   │ │
│ │  │                              │                                   │   │ │
│ │  │                              ▼ [ 2 ] seconds delay               │   │ │
│ │  │                              │                                   │   │ │
│ │  │  ┌───────────────────────────────────────────────────────────┐  │   │ │
│ │  │  │ ☰  2. SELL CE 26200   │  75 qty  │  Credit leg  │         │  │   │ │
│ │  │  └───────────────────────────────────────────────────────────┘  │   │ │
│ │  │                              │                                   │   │ │
│ │  │                              ▼ [ 2 ] seconds delay               │   │ │
│ │  │                              │                                   │   │ │
│ │  │  ┌───────────────────────────────────────────────────────────┐  │   │ │
│ │  │  │ ☰  3. BUY PE 25600    │  75 qty  │  Debit leg   │         │  │   │ │
│ │  │  └───────────────────────────────────────────────────────────┘  │   │ │
│ │  │                              │                                   │   │ │
│ │  │                              ▼ [ 2 ] seconds delay               │   │ │
│ │  │                              │                                   │   │ │
│ │  │  ┌───────────────────────────────────────────────────────────┐  │   │ │
│ │  │  │ ☰  4. BUY CE 26400    │  75 qty  │  Debit leg   │  Last  │  │   │ │
│ │  │  └───────────────────────────────────────────────────────────┘  │   │ │
│ │  │                                                                  │   │ │
│ │  └──────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  Delay between legs: [ 2 ] seconds                                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  QUICK PRESETS                                                          │ │
│ │                                                                         │ │
│ │  [Sell legs first]  [Buy legs first]  [By premium (high→low)]  [Reset] │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  IF ANY LEG FAILS                                                       │ │
│ │                                                                         │ │
│ │  ○ Continue with remaining legs (partial position)                      │ │
│ │  ● Stop and alert (no further orders)                                   │ │
│ │  ○ Reverse already executed legs (unwind position)                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  💡 TIP: Executing sell (credit) legs first reduces margin requirement │ │
│ │  and ensures you receive premium before paying for hedges.              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface LegSequenceEditorProps {
  legs: StrategyLeg[];
  delayBetweenLegs: number;
  failureAction: 'continue' | 'stop' | 'reverse';
  disabled?: boolean;
}

interface StrategyLeg {
  id: string;
  instrument: string;
  contractType: 'CE' | 'PE';
  transactionType: 'BUY' | 'SELL';
  strike: number;
  quantity: number;
  executionOrder: number;
}
```

---

### 4.2 SlippageSettings.vue

**Purpose:** Configure slippage protection settings.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SLIPPAGE SETTINGS                                                           │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  SLIPPAGE PROTECTION                                                    │ │
│ │                                                                         │ │
│ │  ☑️ Enable slippage protection                                           │ │
│ │                                                                         │ │
│ │  ┌─ Protection Settings ────────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  Maximum slippage allowed:                                        │  │ │
│ │  │  ┌─────────────────────────────────────────────────────────────┐ │  │ │
│ │  │  │ Per leg:    [ 2.0   ] %   OR   ₹[ 5      ] per qty          │ │  │ │
│ │  │  │ Total:      [ 5.0   ] %   OR   ₹[ 500    ] for strategy     │ │  │ │
│ │  │  └─────────────────────────────────────────────────────────────┘ │  │ │
│ │  │                                                                   │  │ │
│ │  │  When slippage limit exceeded:                                    │  │ │
│ │  │  ○ Skip this leg and alert                                        │  │ │
│ │  │  ● Retry with adjusted price (max [ 3 ] attempts)                 │  │ │
│ │  │  ○ Execute anyway (override protection)                           │  │ │
│ │  │                                                                   │  │ │
│ │  │  Retry settings:                                                  │  │ │
│ │  │  Wait [ 5 ] seconds between retries                               │  │ │
│ │  │  Increase price by [ 0.5 ] % each retry                           │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  PRICE IMPROVEMENT                                                      │ │
│ │                                                                         │ │
│ │  ☑️ Try for better price before market order                             │ │
│ │                                                                         │ │
│ │  For BUY orders: Try [ 0.5 ] % below LTP for [ 10 ] seconds             │ │
│ │  For SELL orders: Try [ 0.5 ] % above LTP for [ 10 ] seconds            │ │
│ │                                                                         │ │
│ │  If not filled, convert to: [▼ MARKET order         ]                   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📊 ESTIMATED SLIPPAGE (based on current market)                        │ │
│ │                                                                         │ │
│ │  Leg                    Bid-Ask Spread    Est. Slippage                 │ │
│ │  SELL PE 25800          ₹45.10 - ₹45.30   ~₹0.20 (0.4%)                 │ │
│ │  BUY PE 25600           ₹28.40 - ₹28.60   ~₹0.20 (0.7%)                 │ │
│ │  SELL CE 26200          ₹52.20 - ₹52.50   ~₹0.30 (0.6%)                 │ │
│ │  BUY CE 26400           ₹31.70 - ₹31.90   ~₹0.20 (0.6%)                 │ │
│ │  ────────────────────────────────────────────────────────────────────── │ │
│ │  Total estimated slippage: ~₹67 (0.5% of premium)                       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Risk Management Components

### 5.1 RiskGauge.vue

**Purpose:** Visual gauge showing current risk level vs limit.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ RISK GAUGE                                                                  │
│                                                                             │
│ HORIZONTAL BAR VARIANT:                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Daily Loss Limit                                                       │ │
│ │                                                                         │ │
│ │  ██████████████████████████████░░░░░░░░░░░░░░░░░░░░  ₹8,200 / ₹20,000  │ │
│ │  └─────────── 41% used ───────────┘                                     │ │
│ │                                                                         │ │
│ │  🟢 Safe                                                                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ WARNING STATE (> 70%):                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Daily Loss Limit                                                       │ │
│ │                                                                         │ │
│ │  ████████████████████████████████████████████░░░░░░  ₹15,200 / ₹20,000 │ │
│ │  └─────────────────── 76% used ───────────────┘                         │ │
│ │                                                                         │ │
│ │  🟡 Warning - Approaching limit                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ CRITICAL STATE (> 90%):                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Daily Loss Limit                                                       │ │
│ │                                                                         │ │
│ │  ████████████████████████████████████████████████░░  ₹18,500 / ₹20,000 │ │
│ │  └──────────────────────── 92% used ─────────────┘                      │ │
│ │                                                                         │ │
│ │  🔴 Critical - Near limit, auto-pause imminent                          │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ═══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│ CIRCULAR GAUGE VARIANT (for dashboard):                                     │
│                                                                             │
│         ┌─────────────────┐                                                │
│         │    ╭───────╮    │                                                │
│         │  ╭─┘       └─╮  │                                                │
│         │ ╱    41%     ╲ │                                                │
│         │ │   USED      │ │                                                │
│         │ ╲  ₹8.2K     ╱ │                                                │
│         │  ╰─┐       ┌─╯  │                                                │
│         │    ╰───────╯    │                                                │
│         │   Daily Loss    │                                                │
│         │   ₹20K limit    │                                                │
│         └─────────────────┘                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface RiskGaugeProps {
  label: string;
  currentValue: number;
  maxValue: number;
  unit?: string;
  format?: 'currency' | 'percentage' | 'number';
  variant?: 'horizontal' | 'circular';
  showStatus?: boolean;
  thresholds?: {
    warning: number;   // default 70
    critical: number;  // default 90
  };
}
```

---

## 6. Monitoring Components

### 6.1 ConditionProgress.vue

**Purpose:** Shows how close a condition is to triggering.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONDITION PROGRESS                                                          │
│                                                                             │
│ SIMPLE VARIANT:                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  NIFTY > 26,000                                                         │ │
│ │  Current: 25,850 ────────────────────────────────── Target: 26,000      │ │
│ │  ████████████████████████████████████░░░░░░░░░░░░░  85%                 │ │
│ │  150 points away                                                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ DETAILED VARIANT:                                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ┌── Entry Condition 1 ──────────────────────────────────────────────┐ │ │
│ │  │  Time > 09:20                                                      │ │ │
│ │  │  Current: 09:25  ✅ SATISFIED                                      │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌── Entry Condition 2 ──────────────────────────────────────────────┐ │ │
│ │  │  VIX between 13 and 18                                             │ │ │
│ │  │  Current: 14.2  ✅ SATISFIED (within range)                        │ │ │
│ │  │  ░░░░░░░░░░░░░░██████████████████████░░░░░░░░░░░░░░░░░░             │ │ │
│ │  │              13 ──────────▲─────────── 18                          │ │ │
│ │  │                         14.2                                       │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌── Entry Condition 3 ──────────────────────────────────────────────┐ │ │
│ │  │  PCR > 0.8                                                         │ │ │
│ │  │  Current: 0.72  ⏳ PENDING                                         │ │ │
│ │  │  ████████████████████████████████████░░░░░░░░░░░░░░░░░░  90%       │ │ │
│ │  │  0.08 away from trigger                                            │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  Overall: 2/3 conditions met                                            │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ BETWEEN RANGE VISUALIZATION:                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  VIX between 13 and 18                                                  │ │
│ │                                                                         │ │
│ │  8    10    12   [13═══════14.2═══════18]   20    22    24              │ │
│ │  ├────┼────┼────┼░░░░░░░░░░░▲░░░░░░░░░░┼────┼────┼────┤              │ │
│ │                  └─────── VALID ───────┘                                │ │
│ │                         Current                                         │ │
│ │                                                                         │ │
│ │  ✅ Within range - 1.2 from lower bound, 3.8 from upper bound          │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ CROSSES ABOVE/BELOW VISUALIZATION:                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  NIFTY crosses above 26,000                                             │ │
│ │                                                                         │ │
│ │  Previous: 25,920 ──────────────────────────────────── Trigger: 26,000  │ │
│ │  Current:  25,985 ─────────────────────────────────▲                    │ │
│ │                                                    │                    │ │
│ │  ████████████████████████████████████████████████░░│░░  99.4%           │ │
│ │                                                    │                    │ │
│ │  ⏳ 15 points away from trigger                     │                    │ │
│ │                                                    └── Must cross this  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface ConditionProgressProps {
  condition: Condition;
  currentValue: number | string | boolean;
  variant?: 'simple' | 'detailed';
  showAnimation?: boolean;
}

// Computed properties
interface ConditionProgressComputed {
  progressPercentage: number;      // 0-100
  status: 'satisfied' | 'pending' | 'far';
  distanceToTrigger: string;       // "150 points away"
  isWithinRange: boolean;          // for between operators
}
```

---

### 6.2 ActivityFeed.vue

**Purpose:** Real-time feed of all automated actions and events.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ACTIVITY FEED                                                               │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RECENT ACTIVITY                                    [Filter ▼] [⏸ Pause]│ │
│ │                                                                         │ │
│ │  ┌─ 11:23:48 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🟢 ORDER EXECUTED                                                   │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ Action: Exit All - Profit target reached                            │ │ │
│ │  │                                                                     │ │ │
│ │  │ Orders:                                                             │ │ │
│ │  │ • BUY PE 25800 @ ₹32.15 (75 qty) ✓                                 │ │ │
│ │  │ • SELL PE 25600 @ ₹18.15 (75 qty) ✓                                │ │ │
│ │  │ • BUY CE 26200 @ ₹41.10 (75 qty) ✓                                 │ │ │
│ │  │ • SELL CE 26400 @ ₹22.45 (75 qty) ✓                                │ │ │
│ │  │                                                                     │ │ │
│ │  │ P&L Realized: +₹8,155                                               │ │ │
│ │  │ Execution time: 2.3s | Slippage: ₹45 (0.18%)                        │ │ │
│ │  │                                                           [Details →]│ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ 11:23:45 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🔔 CONDITION TRIGGERED                                              │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ Rule: Profit Target Exit                                            │ │ │
│ │  │                                                                     │ │ │
│ │  │ Condition: P&L profit > ₹8,000                                      │ │ │
│ │  │ Actual: ₹8,200                                                      │ │ │
│ │  │                                                                     │ │ │
│ │  │ Proceeding with: Fully Automatic execution                          │ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ 10:45:32 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🟢 ADJUSTMENT EXECUTED                                              │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ Rule: Stop Loss Hedge                                               │ │ │
│ │  │                                                                     │ │ │
│ │  │ Added:                                                              │ │ │
│ │  │ • BUY PE 25500 @ ₹15.00 (75 qty) ✓                                 │ │ │
│ │  │ • BUY CE 26500 @ ₹18.20 (75 qty) ✓                                 │ │ │
│ │  │                                                                     │ │ │
│ │  │ Hedge cost: ₹2,490                                                  │ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ 10:45:30 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🟠 CONFIRMATION REQUESTED                                           │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ Rule: Stop Loss Hedge (Semi-Automatic)                              │ │ │
│ │  │                                                                     │ │ │
│ │  │ Waiting for user confirmation...                                    │ │ │
│ │  │ Confirmed by user at 10:45:31 (1.2s response)                       │ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ 10:30:00 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🔵 CONDITION EVALUATED                                              │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ Condition: P&L > ₹8,000                                             │ │ │
│ │  │ Current: ₹6,850 (85% to trigger)                                    │ │ │
│ │  │ Result: Not yet triggered                                           │ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌─ 09:20:08 ─────────────────────────────────────────────────────────┐ │ │
│ │  │ 🟢 ENTRY EXECUTED                                                   │ │ │
│ │  │                                                                     │ │ │
│ │  │ Strategy: Iron Condor Weekly                                        │ │ │
│ │  │ All entry conditions met at 09:20:05                                │ │ │
│ │  │                                                                     │ │ │
│ │  │ 4 legs executed:                                                    │ │ │
│ │  │ • SELL PE 25800 @ ₹45.20 ✓                                         │ │ │
│ │  │ • BUY PE 25600 @ ₹28.50 ✓                                          │ │ │
│ │  │ • SELL CE 26200 @ ₹52.30 ✓                                         │ │ │
│ │  │ • BUY CE 26400 @ ₹31.80 ✓                                          │ │ │
│ │  │                                                                     │ │ │
│ │  │ Net Credit: ₹4,200 | Margin: ₹1,24,000                              │ │ │
│ │  └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │                            [Load More ↓]                                │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ FILTER DROPDOWN:                                                            │
│ ┌─────────────────────┐                                                    │
│ │ ☑️ All Events        │                                                    │
│ │ ──────────────────── │                                                    │
│ │ ☑️ Order Executed    │                                                    │
│ │ ☑️ Condition Trigger │                                                    │
│ │ ☑️ Confirmation Req  │                                                    │
│ │ ☑️ Evaluation        │                                                    │
│ │ ☑️ Errors            │                                                    │
│ └─────────────────────┘                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Activity Item Types:**

```typescript
type ActivityType = 
  | 'entry_triggered'
  | 'entry_executed'
  | 'adjustment_triggered'
  | 'adjustment_executed'
  | 'confirmation_requested'
  | 'confirmation_received'
  | 'confirmation_timeout'
  | 'exit_executed'
  | 'condition_evaluated'
  | 'order_placed'
  | 'order_filled'
  | 'order_rejected'
  | 'error'
  | 'warning';

interface ActivityItem {
  id: string;
  timestamp: Date;
  type: ActivityType;
  strategyId: string;
  strategyName: string;
  ruleName?: string;
  data: ActivityData;
  severity: 'success' | 'info' | 'warning' | 'error';
}

// Icon and color mapping
const activityStyles: Record<ActivityType, { icon: string; color: string }> = {
  entry_executed: { icon: '🟢', color: '#00b386' },
  adjustment_executed: { icon: '🟢', color: '#00b386' },
  exit_executed: { icon: '🟢', color: '#00b386' },
  condition_triggered: { icon: '🔔', color: '#f39c12' },
  confirmation_requested: { icon: '🟠', color: '#f39c12' },
  condition_evaluated: { icon: '🔵', color: '#3498db' },
  order_rejected: { icon: '🔴', color: '#e74c3c' },
  error: { icon: '❌', color: '#e74c3c' },
  // ...
};
```

---

## 7. Action Components

### 7.1 KillSwitch.vue

**Purpose:** Emergency stop all button with confirmation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KILL SWITCH                                                                 │
│                                                                             │
│ NORMAL STATE (on dashboard):                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ┌───────────────────────────────────────────┐                          │ │
│ │  │                                           │                          │ │
│ │  │   🔴 KILL SWITCH                          │                          │ │
│ │  │                                           │                          │ │
│ │  │   [     STOP ALL      ]                   │                          │ │
│ │  │                                           │                          │ │
│ │  │   Exit all & Cancel pending               │                          │ │
│ │  │                                           │                          │ │
│ │  └───────────────────────────────────────────┘                          │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ HOVER STATE:                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ┌───────────────────────────────────────────┐                          │ │
│ │  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                          │ │
│ │  │  ░░ 🔴 KILL SWITCH                     ░░ │  ← Pulsing border        │ │
│ │  │  ░░                                    ░░ │                          │ │
│ │  │  ░░ [     STOP ALL      ]              ░░ │                          │ │
│ │  │  ░░                                    ░░ │                          │ │
│ │  │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │                          │ │
│ │  └───────────────────────────────────────────┘                          │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ CONFIRMATION MODAL:                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ⚠️ EMERGENCY STOP - CONFIRM ACTION                                     │ │
│ │  ═══════════════════════════════════════════════════════════════════   │ │
│ │                                                                         │ │
│ │  This will immediately:                                                 │ │
│ │                                                                         │ │
│ │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│ │  │  1. PAUSE all active AutoPilot strategies                         │ │ │
│ │  │  2. CANCEL all pending orders                                      │ │ │
│ │  │  3. EXIT all open positions at MARKET price                        │ │ │
│ │  └───────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  CURRENT POSITIONS (will be closed):                                    │ │
│ │  ┌───────────────────────────────────────────────────────────────────┐ │ │
│ │  │  Strategy              │ Legs │ Current P&L │ Est. Exit P&L       │ │ │
│ │  ├───────────────────────────────────────────────────────────────────┤ │ │
│ │  │  Iron Condor Weekly    │  6   │  +₹8,200    │  ~+₹8,100          │ │ │
│ │  │  Bull Put Spread       │  2   │  -₹1,200    │  ~-₹1,350          │ │ │
│ │  ├───────────────────────────────────────────────────────────────────┤ │ │
│ │  │  TOTAL                 │  8   │  +₹7,000    │  ~+₹6,750          │ │ │
│ │  └───────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ⚠️ Estimated slippage: ~₹250 (market orders during exit)              │ │
│ │                                                                         │ │
│ │  Type "STOP" to confirm: [ _____________ ]                              │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │                                                                  │   │ │
│ │  │  [Cancel]                    [🛑 CONFIRM EMERGENCY STOP]        │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ EXECUTING STATE:                                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  🔄 EXECUTING EMERGENCY STOP...                                         │ │
│ │                                                                         │ │
│ │  ✓ Paused 2 strategies                                                  │ │
│ │  ✓ Cancelled 0 pending orders                                           │ │
│ │  🔄 Exiting positions... (4/8 completed)                                │ │
│ │                                                                         │ │
│ │  ████████████████████████████████░░░░░░░░░░░░░░░░░░░░  50%              │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ COMPLETED STATE:                                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ✅ EMERGENCY STOP COMPLETED                                            │ │
│ │                                                                         │ │
│ │  Summary:                                                               │ │
│ │  • 2 strategies paused                                                  │ │
│ │  • 0 orders cancelled                                                   │ │
│ │  • 8 positions closed                                                   │ │
│ │  • Realized P&L: +₹6,820                                                │ │
│ │  • Execution time: 3.2 seconds                                          │ │
│ │                                                                         │ │
│ │  [View Detailed Log]                              [Close]               │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 7.2 ConfirmationModal.vue

**Purpose:** Semi-automatic adjustment confirmation with timeout.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONFIRMATION MODAL                                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  ⚠️ ADJUSTMENT CONFIRMATION REQUIRED                                    │ │
│ │  ═══════════════════════════════════════════════════════════════════   │ │
│ │                                                                         │ │
│ │  Strategy: Iron Condor Weekly - Auto                                    │ │
│ │  Rule: Stop Loss Hedge                                                  │ │
│ │                                                                         │ │
│ │  ┌─ TRIGGER REASON ─────────────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  Condition: Strategy P&L loss exceeds ₹5,000                      │  │ │
│ │  │  Current P&L: -₹5,120                                             │  │ │
│ │  │  Triggered at: 10:45:30                                           │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌─ PROPOSED ACTION ────────────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  Add Hedge:                                                       │  │ │
│ │  │  ┌─────────────────────────────────────────────────────────────┐ │  │ │
│ │  │  │ BUY  │ NIFTY 25500 PE │ 75 qty │ LTP: ₹15.00 │ Cost: ₹1,125│ │  │ │
│ │  │  │ BUY  │ NIFTY 26500 CE │ 75 qty │ LTP: ₹18.20 │ Cost: ₹1,365│ │  │ │
│ │  │  └─────────────────────────────────────────────────────────────┘ │  │ │
│ │  │                                                                   │  │ │
│ │  │  Total Hedge Cost: ₹2,490                                         │  │ │
│ │  │  Margin Impact: ₹0 (hedges reduce margin)                         │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌─ CURRENT MARKET ─────────────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  NIFTY Spot: 25,920 (▼ 0.3%)                                      │  │ │
│ │  │  VIX: 15.2                                                        │  │ │
│ │  │  Prices last updated: 10:45:28 (2 seconds ago)                    │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌─ AUTO-TIMEOUT ───────────────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  If no response in: 60 seconds                                    │  │ │
│ │  │  Action: Skip this adjustment                                     │  │ │
│ │  │                                                                   │  │ │
│ │  │  Time remaining: 0:45                                             │  │ │
│ │  │  ████████████████████████████████░░░░░░░░░░░░░░░░░░░░             │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │                                                                  │   │ │
│ │  │  [Skip This Time]   [Modify Action ↗]   [✅ CONFIRM & EXECUTE]  │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ MODIFY ACTION EXPANDED:                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ┌─ MODIFY PROPOSED ACTION ─────────────────────────────────────────┐  │ │
│ │  │                                                                   │  │ │
│ │  │  PE Strike: [ 25500    ] → [ 25400    ]  ← User changed          │  │ │
│ │  │  CE Strike: [ 26500    ] → [ 26500    ]                          │  │ │
│ │  │  Quantity:  [ 75       ] (1 lot)                                  │  │ │
│ │  │                                                                   │  │ │
│ │  │  Updated Cost: ₹2,650 (was ₹2,490)                                │  │ │
│ │  │                                                                   │  │ │
│ │  │  [Reset to Original]                      [Apply Modifications]   │  │ │
│ │  │                                                                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ URGENT VARIANT (pulsing border, sound):                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│ │  ░░                                                                 ░░  │ │
│ │  ░░  🚨 URGENT: CONFIRMATION REQUIRED                              ░░  │ │
│ │  ░░                                                                 ░░  │ │
│ │  ░░  Time remaining: 0:15                                          ░░  │ │
│ │  ░░                                                                 ░░  │ │
│ │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Shared Components

### 8.1 StatusBadge.vue

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STATUS BADGE                                                                │
│                                                                             │
│ VARIANTS:                                                                   │
│                                                                             │
│ ┌───────────────┐  Active - Green background, white text, pulsing dot      │
│ │ 🟢 ACTIVE     │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Waiting - Yellow background, dark text                  │
│ │ 🟡 WAITING    │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Pending - Orange background, white text, pulsing        │
│ │ 🟠 PENDING    │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Paused - Gray background, white text                    │
│ │ ⏸️ PAUSED     │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Error - Red background, white text                      │
│ │ 🔴 ERROR      │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Completed - Blue background, white text                 │
│ │ ✅ COMPLETED  │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
│ ┌───────────────┐  Draft - Dashed border, muted text                       │
│ │ 📝 DRAFT      │                                                          │
│ └───────────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Props Interface:**

```typescript
interface StatusBadgeProps {
  status: 'active' | 'waiting' | 'pending' | 'paused' | 'error' | 'completed' | 'draft';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showPulse?: boolean;
  customLabel?: string;
}
```

---

### 8.2 StepIndicator.vue

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STEP INDICATOR                                                              │
│                                                                             │
│ HORIZONTAL (default):                                                       │
│                                                                             │
│  ●───────○───────○───────○───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│  ✓                                                                          │
│                                                                             │
│ CURRENT STEP HIGHLIGHTED:                                                   │
│                                                                             │
│  ●───────●───────◉───────○───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│  ✓       ✓       ●                                                          │
│                                                                             │
│ STEP STATES:                                                                │
│ ● Completed (solid fill, check mark)                                        │
│ ◉ Current (solid fill, number, larger)                                      │
│ ○ Upcoming (outline only, number)                                           │
│ ⊘ Error (red, warning icon)                                                 │
│                                                                             │
│ VERTICAL VARIANT:                                                           │
│                                                                             │
│  ● Base Strategy                                                            │
│  │ Select or create base strategy                                          │
│  │                                                                          │
│  ● Entry Conditions                                                         │
│  │ Define when to enter                                                     │
│  │                                                                          │
│  ◉ Adjustment Rules  ← Current                                             │
│  │ Define position adjustments                                              │
│  │                                                                          │
│  ○ Order Execution                                                          │
│  │ Configure order settings                                                 │
│  │                                                                          │
│  ○ Risk Management                                                          │
│     Set safety limits                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. State Management

### 9.1 AutoPilot Pinia Store

```typescript
// stores/autopilot.ts

import { defineStore } from 'pinia';

interface AutoPilotState {
  // Strategies
  strategies: AutoPilotStrategy[];
  activeStrategy: AutoPilotStrategy | null;
  
  // Creation wizard
  wizardStep: number;
  wizardData: Partial<AutoPilotStrategy>;
  wizardValidation: Map<number, boolean>;
  
  // Real-time monitoring
  conditionStates: Map<string, ConditionState>;
  activityFeed: ActivityItem[];
  
  // Global settings
  globalSettings: GlobalSettings;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  confirmationModal: ConfirmationModalState | null;
}

interface AutoPilotStrategy {
  id: string;
  name: string;
  status: StrategyStatus;
  
  // Configuration
  underlying: string;
  expiry: string;
  lots: number;
  positionType: 'intraday' | 'positional';
  legs: StrategyLeg[];
  
  // Conditions
  entryConditions: ConditionGroup;
  adjustmentRules: AdjustmentRule[];
  
  // Execution settings
  orderSettings: OrderSettings;
  legSequence: string[]; // leg IDs in order
  
  // Risk settings
  riskSettings: RiskSettings;
  
  // Schedule
  schedule: ScheduleConfig;
  priority: number;
  
  // Runtime state
  runtimeState: RuntimeState | null;
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

export const useAutoPilotStore = defineStore('autopilot', {
  state: (): AutoPilotState => ({
    strategies: [],
    activeStrategy: null,
    wizardStep: 1,
    wizardData: {},
    wizardValidation: new Map(),
    conditionStates: new Map(),
    activityFeed: [],
    globalSettings: getDefaultGlobalSettings(),
    isLoading: false,
    error: null,
    confirmationModal: null,
  }),
  
  getters: {
    activeStrategies: (state) => 
      state.strategies.filter(s => s.status === 'active'),
    
    waitingStrategies: (state) =>
      state.strategies.filter(s => s.status === 'waiting'),
    
    canCreateStrategy: (state) =>
      state.activeStrategies.length < state.globalSettings.maxActiveStrategies,
    
    totalPnL: (state) =>
      state.activeStrategies.reduce((sum, s) => 
        sum + (s.runtimeState?.currentPnL || 0), 0),
    
    totalMarginUsed: (state) =>
      state.activeStrategies.reduce((sum, s) =>
        sum + (s.runtimeState?.marginUsed || 0), 0),
    
    dailyLossUsed: (state) =>
      state.activityFeed
        .filter(a => a.type === 'exit_executed' && isToday(a.timestamp))
        .reduce((sum, a) => sum + (a.data.realizedPnL || 0), 0),
    
    isWizardStepValid: (state) => (step: number) =>
      state.wizardValidation.get(step) ?? false,
  },
  
  actions: {
    // Strategy CRUD
    async fetchStrategies() { /* ... */ },
    async createStrategy(data: Partial<AutoPilotStrategy>) { /* ... */ },
    async updateStrategy(id: string, updates: Partial<AutoPilotStrategy>) { /* ... */ },
    async deleteStrategy(id: string) { /* ... */ },
    
    // Strategy control
    async activateStrategy(id: string) { /* ... */ },
    async pauseStrategy(id: string) { /* ... */ },
    async resumeStrategy(id: string) { /* ... */ },
    async forceEntry(id: string) { /* ... */ },
    async forceExit(id: string) { /* ... */ },
    
    // Kill switch
    async executeKillSwitch() { /* ... */ },
    
    // Wizard
    setWizardStep(step: number) { /* ... */ },
    updateWizardData(data: Partial<AutoPilotStrategy>) { /* ... */ },
    validateWizardStep(step: number): boolean { /* ... */ },
    resetWizard() { /* ... */ },
    
    // Confirmation modal
    showConfirmation(data: ConfirmationModalState) { /* ... */ },
    handleConfirmation(action: 'confirm' | 'skip' | 'modify') { /* ... */ },
    
    // Real-time updates (WebSocket)
    handleConditionUpdate(update: ConditionUpdate) { /* ... */ },
    handleActivityEvent(event: ActivityItem) { /* ... */ },
    handleStrategyStateChange(strategyId: string, state: RuntimeState) { /* ... */ },
    
    // Settings
    async updateGlobalSettings(settings: Partial<GlobalSettings>) { /* ... */ },
  },
});
```

---

## 10. Implementation Notes

### 10.1 Component Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ COMPONENT DEPENDENCIES                                                      │
│                                                                             │
│ ConditionBuilder                                                            │
│ ├── ConditionRow (multiple)                                                 │
│ │   ├── VariableSelector                                                   │
│ │   ├── OperatorSelector                                                   │
│ │   └── ValueInput                                                         │
│ ├── ConditionGroup (for nested AND/OR)                                     │
│ ├── ExpressionEditor (advanced mode)                                       │
│ └── FlowchartBuilder (visual mode)                                         │
│                                                                             │
│ AdjustmentRuleCard                                                          │
│ ├── ConditionBuilder (embedded)                                            │
│ ├── ActionConfigurator                                                     │
│ │   ├── HedgeConfigurator                                                  │
│ │   ├── RollConfigurator                                                   │
│ │   ├── ShiftConfigurator                                                  │
│ │   └── ScaleConfigurator                                                  │
│ └── ExecutionModeToggle                                                    │
│                                                                             │
│ OrderSettings                                                               │
│ ├── OrderTypeSelector                                                      │
│ ├── ExecutionStyleSelector                                                 │
│ ├── LegSequenceEditor                                                      │
│ │   └── LegItem (draggable)                                                │
│ └── SlippageSettings                                                       │
│                                                                             │
│ StrategyCard                                                                │
│ ├── StatusBadge                                                            │
│ ├── PnLDisplay                                                             │
│ ├── ConditionProgress (multiple)                                           │
│ └── ActionButtons (Pause/Resume/Exit)                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 External Libraries Needed

```json
{
  "dependencies": {
    "@vueuse/core": "^10.x",          // Composables
    "vue-draggable-plus": "^0.3.x",   // Drag-drop
    "monaco-editor": "^0.45.x",       // Expression editor
    "@vue-flow/core": "^1.x",         // Flowchart builder
    "chart.js": "^4.x",               // Progress charts
    "date-fns": "^3.x"                // Date formatting
  }
}
```

### 10.3 Testing Checklist

```
[ ] ConditionBuilder - all modes work
[ ] ConditionRow - all variable types
[ ] ValueInput - all input types
[ ] ExpressionEditor - syntax validation
[ ] FlowchartBuilder - drag-drop, connections
[ ] AdjustmentRuleCard - expand/collapse
[ ] ActionConfigurator - all action types
[ ] LegSequenceEditor - reorder, presets
[ ] KillSwitch - confirmation, execution
[ ] ConfirmationModal - timeout, modify
[ ] StatusBadge - all states
[ ] ConditionProgress - all operators
[ ] ActivityFeed - filtering, real-time
[ ] RiskGauge - thresholds, colors
```

---

**End of Component Design Document**
