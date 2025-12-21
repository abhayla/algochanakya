# data-testid Naming Conventions

Format: `[screen]-[component]-[element]`

## Rules

1. **Lowercase with hyphens** - No camelCase or underscores
2. **Screen prefix** - Always start with screen name
3. **Specific and descriptive** - Clearly identify the element
4. **Dynamic IDs** - Use template literals for list items, rows, etc.

## Examples by Screen

### Login Screen

```vue
<button data-testid="login-zerodha-button">Login with Zerodha</button>
<div data-testid="login-error-message">{{ errorMessage }}</div>
<input data-testid="login-totp-input" v-model="totp" />
```

### Dashboard Screen

```vue
<div data-testid="dashboard-page">
  <div data-testid="dashboard-summary-cards">
    <div data-testid="dashboard-card-positions">Positions</div>
    <div data-testid="dashboard-card-strategies">Strategies</div>
  </div>
</div>
```

### Positions Screen

```vue
<!-- Page container -->
<div data-testid="positions-page">

  <!-- Toggle buttons -->
  <button data-testid="positions-day-button">Day</button>
  <button data-testid="positions-net-button">Net</button>

  <!-- Summary -->
  <div data-testid="positions-pnl-box">
    <span data-testid="positions-pnl-total">₹5,250</span>
  </div>

  <!-- Table -->
  <table data-testid="positions-table">
    <!-- Dynamic rows -->
    <tr :data-testid="`positions-row-${pos.tradingsymbol}`">
      <button :data-testid="`positions-exit-button-${pos.tradingsymbol}`">Exit</button>
      <button :data-testid="`positions-add-button-${pos.tradingsymbol}`">Add</button>
    </tr>
  </table>

  <!-- Modals -->
  <div data-testid="positions-exit-modal-overlay">
    <div data-testid="positions-exit-modal">
      <select data-testid="positions-exit-order-type">
        <option>Market</option>
        <option>Limit</option>
      </select>
      <button data-testid="positions-exit-confirm-button">Confirm</button>
    </div>
  </div>

  <!-- Empty state -->
  <div data-testid="positions-empty-state">No positions</div>
</div>
```

### Option Chain Screen

```vue
<!-- Page -->
<div data-testid="optionchain-page">

  <!-- Controls -->
  <select data-testid="optionchain-expiry-select" v-model="expiry">
    <option>2024-01-25</option>
  </select>

  <button data-testid="optionchain-greeks-toggle">Show Greeks</button>

  <!-- Strike rows (dynamic) -->
  <div :data-testid="`optionchain-strike-row-${strike}`">
    <!-- CE side -->
    <div :data-testid="`optionchain-ce-oi-${strike}`">{{ ceOI }}</div>
    <div :data-testid="`optionchain-ce-ltp-${strike}`">{{ ceLTP }}</div>
    <div :data-testid="`optionchain-ce-iv-${strike}`">{{ ceIV }}</div>

    <!-- Strike price -->
    <div :data-testid="`optionchain-strike-${strike}`">{{ strike }}</div>

    <!-- PE side -->
    <div :data-testid="`optionchain-pe-oi-${strike}`">{{ peOI }}</div>
    <div :data-testid="`optionchain-pe-ltp-${strike}`">{{ peLTP }}</div>
    <div :data-testid="`optionchain-pe-iv-${strike}`">{{ peIV }}</div>
  </div>
</div>
```

### Strategy Builder Screen

```vue
<!-- Page -->
<div data-testid="strategy-page">

  <!-- Header -->
  <input data-testid="strategy-name-input" v-model="strategyName" />
  <button data-testid="strategy-save-button">Save</button>
  <button data-testid="strategy-calculate-button">Calculate P/L</button>

  <!-- Legs table -->
  <table data-testid="strategy-legs-table">
    <!-- Dynamic leg rows -->
    <tr :data-testid="`strategy-leg-row-${index}`">
      <select :data-testid="`strategy-leg-type-${index}`">
        <option>CE</option>
        <option>PE</option>
      </select>
      <select :data-testid="`strategy-leg-action-${index}`">
        <option>BUY</option>
        <option>SELL</option>
      </select>
      <input :data-testid="`strategy-leg-strike-${index}`" />
      <input :data-testid="`strategy-leg-qty-${index}`" />
      <button :data-testid="`strategy-leg-remove-${index}`">Remove</button>
    </tr>
  </table>

  <button data-testid="strategy-add-row-button">Add Leg</button>

  <!-- P/L Chart -->
  <div data-testid="strategy-pnl-chart">
    <canvas data-testid="strategy-pnl-chart-canvas"></canvas>
  </div>

  <!-- Summary -->
  <div data-testid="strategy-summary-section">
    <div data-testid="strategy-max-profit">Max Profit: ₹10,000</div>
    <div data-testid="strategy-max-loss">Max Loss: ₹5,000</div>
    <div data-testid="strategy-breakeven">Breakeven: 24,500</div>
  </div>
</div>
```

### Strategy Library Screen

```vue
<!-- Page -->
<div data-testid="strategy-library-page">

  <!-- Wizard button -->
  <button data-testid="strategy-library-wizard-button">Find Strategy</button>

  <!-- Category tabs -->
  <button data-testid="strategy-library-tab-bullish">Bullish</button>
  <button data-testid="strategy-library-tab-bearish">Bearish</button>
  <button data-testid="strategy-library-tab-neutral">Neutral</button>

  <!-- Strategy cards (dynamic) -->
  <div :data-testid="`strategy-card-${strategy.id}`">
    <h3 data-testid="`strategy-card-title-${strategy.id}`">{{ strategy.name }}</h3>
    <button :data-testid="`strategy-card-deploy-${strategy.id}`">Deploy</button>
    <button :data-testid="`strategy-card-view-${strategy.id}`">View</button>
  </div>

  <!-- Wizard Modal -->
  <div data-testid="strategy-wizard-modal">
    <!-- Question 1: Outlook -->
    <button data-testid="strategy-wizard-outlook-bullish">Bullish</button>
    <button data-testid="strategy-wizard-outlook-bearish">Bearish</button>
    <button data-testid="strategy-wizard-outlook-neutral">Neutral</button>

    <!-- Question 2: Volatility -->
    <button data-testid="strategy-wizard-volatility-low">Low</button>
    <button data-testid="strategy-wizard-volatility-medium">Medium</button>
    <button data-testid="strategy-wizard-volatility-high">High</button>

    <!-- Recommendations -->
    <div :data-testid="`strategy-wizard-recommendation-${index}`">
      <button :data-testid="`strategy-wizard-recommendation-deploy-${index}`">Deploy</button>
    </div>
  </div>

  <!-- Deploy Modal -->
  <div data-testid="strategy-deploy-modal">
    <input data-testid="strategy-deploy-lots-input" />
    <button data-testid="strategy-deploy-lots-plus">+</button>
    <button data-testid="strategy-deploy-lots-minus">-</button>
    <button data-testid="strategy-deploy-confirm-button">Deploy</button>
  </div>
</div>
```

### AutoPilot Screen

```vue
<!-- Dashboard -->
<div data-testid="autopilot-dashboard-page">

  <!-- Summary cards -->
  <div data-testid="autopilot-summary-section">
    <div data-testid="autopilot-active-count">5</div>
    <div data-testid="autopilot-waiting-count">2</div>
    <div data-testid="autopilot-pnl-total">₹15,250</div>
  </div>

  <!-- Strategy cards -->
  <div :data-testid="`autopilot-strategy-card-${strategy.id}`">
    <button :data-testid="`autopilot-strategy-pause-${strategy.id}`">Pause</button>
    <button :data-testid="`autopilot-strategy-exit-${strategy.id}`">Exit</button>
  </div>

  <!-- Kill switch -->
  <button data-testid="autopilot-kill-switch-btn">Emergency Stop</button>
</div>

<!-- Strategy Builder -->
<div data-testid="autopilot-builder-page">
  <!-- Steps -->
  <button data-testid="autopilot-builder-strategy-tab">Strategy</button>
  <button data-testid="autopilot-builder-conditions-tab">Conditions</button>
  <button data-testid="autopilot-builder-monitoring-tab">Monitoring</button>

  <!-- Condition builder -->
  <button data-testid="autopilot-add-condition-button">Add Condition</button>
  <div :data-testid="`condition-group-${groupIndex}`">
    <select :data-testid="`condition-${groupIndex}-${condIndex}-variable`">
      <option>TIME.CURRENT</option>
      <option>SPOT.NIFTY</option>
    </select>
  </div>
</div>
```

## Common Patterns

### Modals

```vue
<!-- Modal overlay -->
<div data-testid="myscreen-modal-overlay" @click.self="closeModal">
  <!-- Modal container -->
  <div data-testid="myscreen-modal">
    <h2 data-testid="myscreen-modal-title">Title</h2>
    <button data-testid="myscreen-modal-close">Close</button>
    <button data-testid="myscreen-modal-confirm">Confirm</button>
  </div>
</div>
```

### Forms

```vue
<form data-testid="myscreen-form">
  <input data-testid="myscreen-form-name" v-model="name" />
  <input data-testid="myscreen-form-email" v-model="email" />
  <button data-testid="myscreen-form-submit">Submit</button>
</form>
```

### Lists

```vue
<div data-testid="myscreen-list">
  <div v-for="item in items" :key="item.id" :data-testid="`myscreen-item-${item.id}`">
    <span :data-testid="`myscreen-item-name-${item.id}`">{{ item.name }}</span>
    <button :data-testid="`myscreen-item-edit-${item.id}`">Edit</button>
    <button :data-testid="`myscreen-item-delete-${item.id}`">Delete</button>
  </div>
</div>
```

### Empty States

```vue
<div v-if="items.length === 0" data-testid="myscreen-empty-state">
  No items found
</div>
```

### Loading States

```vue
<div v-if="isLoading" data-testid="myscreen-loading-spinner">
  Loading...
</div>
```

### Error States

```vue
<div v-if="error" data-testid="myscreen-error-message">
  {{ error }}
</div>
```

## Anti-Patterns

### ❌ Wrong

```vue
<!-- Too generic -->
<button data-testid="button">Submit</button>

<!-- CamelCase -->
<div data-testid="myScreenContainer">...</div>

<!-- Underscores -->
<div data-testid="my_screen_container">...</div>

<!-- Missing screen prefix -->
<button data-testid="submit-button">Submit</button>

<!-- Using indices instead of IDs -->
<div :data-testid="`item-${index}`">...</div>
```

### ✅ Correct

```vue
<!-- Specific with screen prefix -->
<button data-testid="myscreen-submit-button">Submit</button>

<!-- Lowercase with hyphens -->
<div data-testid="myscreen-container">...</div>

<!-- Using item IDs -->
<div :data-testid="`myscreen-item-${item.id}`">...</div>
```
