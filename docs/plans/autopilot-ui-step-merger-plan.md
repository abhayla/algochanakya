# AutoPilot UI/UX Consistency & Step Merger Implementation Plan

## Summary
Two main tasks:
1. **Step Merger**: Combine Step 1 (Basic Info) and Step 2 (Strategy Legs) into a single Step 1, reducing wizard from 6 steps to 5 steps
2. **UI Consistency**: Apply Kite theme styling across all AutoPilot screens to match the main Strategy Builder

---

## Part 1: Step Merger Requirements

### What We're Doing
- Merge Step 1 (Basic Info) + Step 2 (Strategy Legs) into a **single new Step 1**
- Reduce wizard from **6 steps to 5 steps**

### New Step Structure
| New Step | Content | Old Step |
|----------|---------|----------|
| Step 1 | Strategy Legs + Basic Info (merged) | Steps 1+2 |
| Step 2 | Entry Conditions | Step 3 |
| Step 3 | Adjustment Rules | Step 4 |
| Step 4 | Risk Settings | Step 5 |
| Step 5 | Review | Step 6 |

### Merged Step 1 Layout
```
┌─────────────────────────────────────────────────────────────┐
│ Create Strategy                          Step 1 of 5  Cancel│
│ Configure your automated trading strategy                   │
│ [1] [2] [3] [4] [5]                                         │
├─────────────────────────────────────────────────────────────┤
│ ▼ Basic Information (collapsible, expanded by default)      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Strategy Name*: [_______________]                       │ │
│ │ Description:    [_______________]                       │ │
│ │ Underlying*: [NIFTY ▼]    Expiry Type: [Current Week ▼] │ │
│ │ Lots*: [1]                Position Type: [Intraday ▼]   │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Strategy Legs                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ □ │ACTION│EXPIRY│STRIKE│TYPE│LOTS│ENTRY│CMP│EXIT P/L...│ │
│ │ ─────────────────────────────────────────────────────── │ │
│ │     No legs added. Click "+ Add Row" to start...        │ │
│ └─────────────────────────────────────────────────────────┘ │
│ [Delete Selected] [+ Add Row]           0 leg(s) | Total: 0 │
├─────────────────────────────────────────────────────────────┤
│ [Previous]                                           [Next] │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions
1. **Collapsible section**: Basic Info in collapsible panel above legs table
2. **Expanded by default**: Section starts expanded so user sees fields first
3. **Remove info text**: No "Underlying: NIFTY | Lot Size: 75" text (redundant)
4. **Step indicator**: Update to show 5 steps instead of 6

### Files to Modify for Step Merger
- `frontend/src/views/autopilot/StrategyBuilderView.vue` - Main wizard component
- `frontend/src/stores/autopilot.js` - Update step logic if needed

---

## Part 2: UI/UX Consistency (Kite Theme)

### Analysis: Styling Comparison

### Reference Standard: Strategy Builder (StrategyBuilderView.vue)
The original Strategy Builder uses:
- **Shared CSS imports**: `@/assets/css/strategy-table.css`, `kite-theme.css`
- **CSS Classes**: `.strategy-table-wrapper`, `.strategy-table`, `.strategy-btn`, `.strategy-select`, `.tag-select`, `.tag-buy`, `.tag-sell`
- **CSS Variables**: `--kite-blue`, `--kite-green`, `--kite-red`, `--kite-border`, etc.
- **Form styling**: `.strategy-input.compact`, `.strategy-select.compact`
- **Action bar**: `.action-bar`, `.action-left`, `.action-right`
- **Summary cards**: `.strategy-summary-card`

### Current AutoPilot Screens Issues

#### 1. DashboardView.vue (528 lines)
**Issue**: Uses **only Tailwind CSS classes** - no Kite theme integration
- Uses: `bg-white rounded-lg shadow p-4`, `text-gray-500`, `bg-blue-600`, etc.
- Should use: Kite CSS variables and button classes
- Missing: Card styling from `.strategy-summary-card`, button styling from `.strategy-btn`

#### 2. SettingsView.vue (289 lines)
**Issue**: Uses **only Tailwind CSS classes**
- Input styling: `border border-gray-300 rounded-lg` instead of `.strategy-input`
- Button styling: `bg-blue-600 text-white rounded-lg` instead of `.strategy-btn-primary`
- Card containers use Tailwind instead of `.kite-card` or `.strategy-summary-card`

#### 3. StrategyDetailView.vue (424 lines)
**Issue**: Uses **only Tailwind CSS classes**
- Table uses: `min-w-full divide-y divide-gray-200`, `bg-gray-50`
- Should use: `.strategy-table`, `.kite-table` patterns
- Status badges inline instead of reusable classes

#### 4. StrategyBuilderView.vue (AutoPilot) (601 lines)
**Status**: **Partially compliant** - Step 2 uses correct imports
- Step 2 (Legs Table): Correctly uses `AutoPilotLegsTable` which imports `strategy-table.css`
- Steps 1, 3, 4, 5, 6: Use Tailwind utility classes instead of Kite theme

---

## Visual Evidence from Screenshots

### Step 1 (Basic Info)
- Form labels use plain text styling
- Inputs appear as basic browser defaults with thin borders
- No Kite theme styling applied

### Step 2 (Strategy Legs) - GOOD
- Uses `strategy-table.css` correctly
- Table header has proper uppercase, gray background
- BUY/SELL tags have proper colored badges
- Action bar matches Strategy Builder

### Step 3 (Entry Conditions)
- Dropdown and inputs lack Kite styling
- Remove button lacks proper button styling
- Condition rows lack `.strategy-summary-card` or bordered styling

### Steps 4, 5, 6
- All use basic Tailwind classes
- Forms/inputs lack consistent Kite theme styling
- Review step lacks card styling for summary sections

---

## Root Cause
The AutoPilot views were built with **Tailwind CSS utility classes** for speed, but the existing codebase uses a **custom Kite theme system** with CSS variables and reusable classes. Only the `AutoPilotLegsTable` component properly imported and used the shared styles.

---

## Implementation Plan

### Phase 1: Add CSS Import to All AutoPilot Views
Add to each view's `<script setup>` or as `<style>` import:
```javascript
import '@/assets/css/strategy-table.css'
```

Files to modify:
- `frontend/src/views/autopilot/DashboardView.vue`
- `frontend/src/views/autopilot/SettingsView.vue`
- `frontend/src/views/autopilot/StrategyDetailView.vue`
- `frontend/src/views/autopilot/StrategyBuilderView.vue`

### Phase 2: Replace Tailwind Classes with Kite Theme Classes

#### 2.1 Buttons
Replace:
```html
<!-- Tailwind -->
class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
<!-- Kite Theme -->
class="strategy-btn strategy-btn-primary"
```

Button mappings:
| Tailwind Pattern | Kite Theme Class |
|-----------------|------------------|
| `bg-blue-600 text-white` | `strategy-btn strategy-btn-primary` |
| `bg-green-600 text-white` | `strategy-btn strategy-btn-success` |
| `bg-red-600 text-white` | `strategy-btn strategy-btn-danger` |
| `border border-gray-300` | `strategy-btn strategy-btn-outline` |

#### 2.2 Form Inputs
Replace:
```html
<!-- Tailwind -->
class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500"
<!-- Kite Theme -->
class="strategy-input w-full"
```

#### 2.3 Select Dropdowns
Replace:
```html
<!-- Tailwind -->
class="text-sm border border-gray-300 rounded px-2 py-1"
<!-- Kite Theme -->
class="strategy-select compact"
```

#### 2.4 Cards/Panels
Replace:
```html
<!-- Tailwind -->
class="bg-white rounded-lg shadow p-4"
<!-- Kite Theme -->
class="strategy-summary-card" OR class="kite-card p-4"
```

#### 2.5 Tables
Replace:
```html
<!-- Tailwind -->
class="min-w-full divide-y divide-gray-200"
<!-- Kite Theme -->
class="strategy-table" (within .strategy-table-wrapper)
```

### Phase 3: File-by-File Changes

#### DashboardView.vue
- [ ] Add CSS import
- [ ] Replace button classes (Kill Switch, Settings, New Strategy, Refresh)
- [ ] Replace summary cards with `.strategy-summary-card`
- [ ] Replace filters with `.strategy-select.compact`
- [ ] Replace strategy list cards styling

#### SettingsView.vue
- [ ] Add CSS import
- [ ] Replace all input classes with `.strategy-input`
- [ ] Replace button classes
- [ ] Replace card containers with `.kite-card`

#### StrategyDetailView.vue
- [ ] Add CSS import
- [ ] Replace button classes
- [ ] Replace summary cards
- [ ] Replace table with `.strategy-table` pattern
- [ ] Replace status badges with shared utility classes

#### StrategyBuilderView.vue (Steps 1, 3, 4, 5, 6)
- [ ] Step 1: Replace form inputs with `.strategy-input`
- [ ] Step 3: Replace condition row styling, use `.strategy-select`
- [ ] Step 4: Already placeholder - minimal changes
- [ ] Step 5: Replace risk settings inputs with `.strategy-input`
- [ ] Step 6: Replace review sections with `.strategy-summary-card` or `.kite-card`
- [ ] Navigation buttons: Replace with `.strategy-btn` classes

---

## Critical Files to Modify

1. `frontend/src/views/autopilot/DashboardView.vue`
2. `frontend/src/views/autopilot/SettingsView.vue`
3. `frontend/src/views/autopilot/StrategyDetailView.vue`
4. `frontend/src/views/autopilot/StrategyBuilderView.vue`

## Reference Files (Do Not Modify)
- `frontend/src/assets/css/strategy-table.css` - Shared table styles
- `frontend/src/assets/styles/kite-theme.css` - Theme variables
- `frontend/src/views/StrategyBuilderView.vue` - Reference implementation

---

## Estimated Changes
- ~50-80 class replacements per file
- No functional changes - purely CSS class swaps
- May need to add a few wrapper divs for proper container styling

---

## Implementation Order

### Phase A: Step Merger (Do First)
1. Modify `StrategyBuilderView.vue`:
   - Change `totalSteps` from 6 to 5
   - Merge Step 1 content into Step 2 template
   - Add collapsible section for Basic Info fields
   - Remove old Step 1 case from switch/v-if
   - Update all step number references (step 3→2, step 4→3, etc.)
   - Remove "Underlying: NIFTY | Lot Size: 75" info text from legs section
   - Update step indicator to show 5 circles instead of 6

2. Update `autopilot.js` store (if needed):
   - Check if step validation logic needs updating
   - Ensure form data structure still works

3. Update E2E tests in `tests/e2e/specs/autopilot/`:
   - Update step navigation tests
   - Update step indicator assertions

### Phase B: Kite Theme Styling (Do Second)
1. Add CSS imports to all AutoPilot views
2. Replace Tailwind classes with Kite theme classes
3. Test visual consistency across all screens

---

## Critical Files

### Must Modify
- `frontend/src/views/autopilot/StrategyBuilderView.vue` - Step merger + styling
- `frontend/src/views/autopilot/DashboardView.vue` - Styling only
- `frontend/src/views/autopilot/SettingsView.vue` - Styling only
- `frontend/src/views/autopilot/StrategyDetailView.vue` - Styling only
- `frontend/src/components/autopilot/builder/AutoPilotLegsTable.vue` - Minor adjustments

### May Need Updates
- `frontend/src/stores/autopilot.js` - Step logic
- `tests/e2e/specs/autopilot/*.spec.js` - Test updates

### Reference Only (Do Not Modify)
- `frontend/src/assets/css/strategy-table.css`
- `frontend/src/assets/styles/kite-theme.css`
- `frontend/src/views/StrategyBuilderView.vue` - Reference for styling patterns
