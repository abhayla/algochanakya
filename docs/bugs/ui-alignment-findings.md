# UI Alignment Findings

**Date logged:** 2026-04-17
**Session:** Manual UI review via Playwright (1920×1080 viewport)
**Status:** Open — not blocking, low-severity visual polish

## Context

During manual testing, visual inspection revealed layout issues on the
Dashboard and Option Chain screens. Measurements were taken via Playwright
`browser_evaluate` to get exact coordinates/widths.

---

## 1. Dashboard (`/dashboard`) — Quick Actions bar bunched left

**File:** `frontend/src/views/DashboardView.vue` (`.quick-actions` class)

### Measurements

| Element | x start | x end | width |
|---|---|---|---|
| `.quick-actions` container | 360 | 1560 | 1200 |
| "New Strategy" button | 360 | 494 | 134 |
| "View Positions" button | 504 | 644 | 140 |
| "Option Chain" button | 653 | 786 | 133 |
| **Empty trailing space** | 786 | 1560 | **~774** |

### Symptom

3 quick-action buttons consume 427px of a 1200px container, leaving ~774px
of empty whitespace to their right. Buttons look stranded top-left.

### Root cause

`.quick-actions` has `display: flex` + `gap: 10px` but
**`justify-content: normal`** (defaults to flex-start). No constraint forces
the bar to span or contents to distribute.

### Fix options (pick one)

- **(a)** `width: max-content` on `.quick-actions` — bar hugs buttons, no trailing space
- **(b)** `justify-content: space-between` — spreads 3 buttons across full 1200px
- **(c)** `justify-content: center` — centers the button group visually

---

## 2. Option Chain (`/optionchain`) — Header toolbar 775px gap

**File:** `frontend/src/views/OptionChainView.vue` (`.header-right` class)

### Measurements

| Element | x position |
|---|---|
| "Option Chain" title | x=17 |
| Underlying tabs (NIFTY/BANKNIFTY/FINNIFTY) | x=140 → 400 |
| Expiry dropdown | ends ~x=425 |
| **Gap** | ~425 → 1201 (**776px empty**) |
| `.header-right` (Market data, Spot, DTE, Greeks, Live, Find Strike, Refresh) | x=1201 → 1904 |

### Symptom

7 toolbar items float at the far right; title + tabs anchored far left.
Large dead zone between creates a "broken header" appearance.

### Root cause

Parent uses `justify-content: space-between` on a wrapper that spans the
full viewport (~1920px), so the two groups are pushed to opposite extremes.

### Fix options

- Constrain the outer header to a narrower max-width OR
- Change `space-between` → `flex-start` with controlled gap OR
- Move Greeks/Live toggles and Find Strike/Refresh buttons into a separate row
  below the title (current metric row area), pairing them with the Strikes
  dropdown

---

## 3. Option Chain — Metrics row also has large mid-gap

**File:** Same view, metrics/filters row

### Symptom

```
PCR | MAX PAIN | CE OI | PE OI | LOT SIZE ........[long gap]........ STRIKE INTERVAL (50/100) | 10 Strikes
```

Same `justify-content: space-between` pattern.

### Fix

Same approach as (2). Consider grouping left metrics + right controls closer
together or splitting into two balanced rows.

---

## 4. Option Chain — OI column is 147px wide (2× other data cols)

**File:** Option chain table columns

### Measurements

| Column | Width |
|---|---|
| OI | **147** |
| CHG | 69 |
| VOL | 66 |
| IV | 50 |
| DELTA | 83 |
| GAMMA | 100 |
| THETA | 85 |
| VEGA | 82 |
| LTP | 70 |
| CHG% | 86 |

### Symptom

OI column on both CE (leftmost data col) and PE (rightmost data col) is
~2× the width of its neighbors. With `text-align: right` on CE side, the
`-` placeholder sits flush against the CHG column, leaving ~120px of empty
left-padding per row. Mirrored behavior on PE side.

### Context

OI columns often hold 6–7 digit numbers (e.g. `1,23,45,600`) at live-market
scale, justifying the wider cell. When data is empty (`-`), the cell looks
over-sized. This is likely a design tradeoff, not a bug — but consider a
`min-width` on other numeric cols if alignment across columns feels
uneven at empty-data state.

---

## 5. Also seen (unrelated to layout)

**File:** `frontend/src/stores/watchlist.js:249`

Console error observed during option chain navigation:
```
WebSocket error: Connection is already closed @ watchlist.js:249
```

Suggests a race between unmount cleanup and a pending send/subscribe.
Non-blocking but pollutes console during navigation.

---

## Priority

Low. Purely visual. No functional impact. Fix when doing a dedicated UI
polish pass. Pair fixes 2 + 3 + 4 since they all live in
`OptionChainView.vue` CSS.

## Screenshots (session artifacts)

- `dashboard-ui-check.png` — full dashboard with Quick Actions bunched left
- `optionchain-ui-check-2.png` — full option chain showing header + metric row gaps
- `optionchain-viewport-top.png` — viewport-only crop of option chain top area
