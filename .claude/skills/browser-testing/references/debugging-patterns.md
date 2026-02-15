# Debugging Patterns Reference

Detailed debugging strategies for AlgoChanakya using Claude Chrome.

---

## Console Log Filtering

### Log Prefixes in AlgoChanakya

| Prefix | Location | Purpose |
|--------|----------|---------|
| `[AutoPilot WS]` | `frontend/src/composables/autopilot/useWebSocket.js` | WebSocket connection, messages, errors, reconnection |
| `[OptionChain]` | `frontend/src/stores/optionchain.js` | Option chain subscriptions and price updates |
| `[Strategy]` | `frontend/src/stores/strategy.js` | P/L calculation errors, instrument token fetch failures |

### Filtering Commands

```
// Show only WebSocket logs
Filter console for logs containing "[AutoPilot WS]"

// Show only errors
Show me console.error messages

// Show API errors
Filter for logs containing "API" or "fetch"

// Exclude noise
Show console errors but exclude React warnings
```

### Common Console Patterns

**WebSocket Connection Success:**
```
[AutoPilot WS] Connecting to: ws://localhost:8000/ws/autopilot?token=...
[AutoPilot WS] Connection opened
[AutoPilot WS] Connection established
```

**WebSocket Connection Failure:**
```
[AutoPilot WS] Error: WebSocket connection failed
[AutoPilot WS] WebSocket closed: 1006
[AutoPilot WS] Reconnecting in 3s...
```

**API Errors:**
```
Error fetching positions: TypeError: Failed to fetch
API request failed: 401 Unauthorized
CORS error: No 'Access-Control-Allow-Origin' header
```

---

## Network Request Inspection

### API Endpoints to Monitor

| Endpoint | Screen | Expected Response |
|----------|--------|-------------------|
| `GET /api/positions/` | Positions | 200, array of positions |
| `GET /api/optionchain/chain` | Option Chain | 200, chain data with CE/PE |
| `POST /api/strategies/calculate` | Strategy Builder | 200, P/L grid data |
| `GET /api/autopilot/strategies` | AutoPilot | 200, array of strategies |
| `WS /ws/ticks` | All screens | WebSocket connection |
| `WS /ws/autopilot` | AutoPilot | WebSocket connection |

### Network Debugging Commands

```
// Check for failed requests
Open Network tab and filter for status codes 4xx and 5xx

// Check WebSocket
Open Network -> WS tab and verify connection to localhost:8000/ws/ticks

// Check slow requests
Show me requests that took longer than 2 seconds

// Check CORS errors
Filter Network tab for CORS-related failures
```

### Common Network Issues

**401 Unauthorized:**
- **Cause:** Auth token expired or missing
- **Fix:** Re-authenticate or inject fresh token

**CORS Error:**
- **Cause:** Backend CORS settings
- **Fix:** Verify backend is running and CORS is configured

**WebSocket 1006 Error:**
- **Cause:** Connection closed abnormally
- **Fix:** Check if backend WebSocket server is running

---

## DOM State Inspection

### data-testid Verification

AlgoChanakya uses **only** data-testid selectors for testing.

**Convention:** `[screen]-[component]-[element]`

### Verification Commands

```
// Check if element exists
Check if document.querySelector('[data-testid="strategy-table"]') exists

// Verify visibility
Check if positions-exit-modal is visible

// Count elements
How many elements with data-testid starting with "optionchain-strike-row-" exist?

// Get text content
What is the text of strategy-max-profit-card?
```

### Common DOM Issues

**Element Not Found:**
```
Debugging steps:
1. Check if page loaded completely
2. Verify component is mounted (check console for errors)
3. Check if data-testid attribute exists in DOM
4. Verify no typos in data-testid value
```

**Element Not Visible:**
```
Debugging steps:
1. Check CSS display/visibility properties
2. Check if parent container is visible
3. Verify no overlapping elements
4. Check z-index stacking
```

---

## WebSocket Message Monitoring

### Message Types

**Price Ticks (Watchlist, Option Chain, Strategy Builder):**
```json
{
  "type": "ticks",
  "data": [
    {
      "token": 256265,
      "ltp": 25800.50,
      "change": 150.25,
      "change_percent": 0.58
    }
  ]
}
```

**AutoPilot Updates:**
```json
{
  "type": "strategy_update",
  "data": {
    "strategy_id": 123,
    "status": "active",
    "pnl": 1500.50
  }
}
```

### Monitoring Commands

```
// Monitor for specific message type
Show me WebSocket messages with type "ticks"

// Monitor for duration
Monitor WebSocket for 10 seconds and report all message types received

// Check message frequency
Count how many "ticks" messages are received in 5 seconds

// Inspect payload
Show me the payload of the first "strategy_update" message
```

### Common WebSocket Issues

**No Messages Received:**
```
Debugging steps:
1. Verify WebSocket connection established
2. Check if subscription message was sent
3. Verify backend is sending messages
4. Check for console errors
```

**Incorrect Message Format:**
```
Debugging steps:
1. Log the raw message payload
2. Verify message structure matches expected format
3. Check for parsing errors in console
```

---

## data-testid Element Verification

### Critical Elements by Screen

**Strategy Builder (`/strategy`):**
```
strategy-page
strategy-toolbar
strategy-underlying-tabs
strategy-table
strategy-add-row-button
strategy-recalculate-button
strategy-save-button
strategy-max-profit-card
strategy-max-loss-card
strategy-breakeven-card
strategy-payoff-section
```

**Positions (`/positions`):**
```
positions-page
positions-type-toggle
positions-day-button
positions-net-button
positions-pnl-box
positions-table
positions-exit-modal
positions-add-modal
positions-exit-all-button
```

**AutoPilot Dashboard (`/autopilot`):**
```
autopilot-dashboard
autopilot-connection-status
autopilot-strategy-list
autopilot-kill-switch-btn
autopilot-summary-pnl
```

**AutoPilot Builder (`/autopilot/strategies/new`):**
```
autopilot-builder-step-1
autopilot-builder-step-2
autopilot-builder-step-3
autopilot-builder-step-4
autopilot-builder-step-5
autopilot-builder-name
autopilot-add-condition-button
autopilot-builder-save
```

### Verification Workflow

```
1. Navigate to the screen
2. Wait for page to load
3. For each critical element:
   - Check if it exists
   - Verify it's visible
   - Check if it's interactive (clickable/typeable)
4. Report missing elements
```

---

## Error Pattern Recognition

### React Errors

**Hydration Errors:**
```
Warning: Text content did not match. Server: "X" Client: "Y"
```
- **Cause:** Server/client rendering mismatch
- **Impact:** May cause visual glitches

**Key Warnings:**
```
Warning: Cannot update a component while rendering a different component
```
- **Cause:** State update during render
- **Impact:** Infinite loops or performance issues

### API Error Patterns

**Authentication Errors:**
```
401 Unauthorized
403 Forbidden
```
- **Action:** Check token validity, re-authenticate

**Not Found Errors:**
```
404 Not Found at /api/positions/
```
- **Action:** Verify backend route exists, check URL

**Server Errors:**
```
500 Internal Server Error
502 Bad Gateway
```
- **Action:** Check backend logs, verify backend is running

### WebSocket Error Patterns

**Connection Errors:**
```
WebSocket connection to 'ws://localhost:8000/ws/ticks' failed
```
- **Action:** Verify backend WebSocket server running

**Close Codes:**
- `1000` - Normal closure
- `1006` - Abnormal closure (no close frame)
- `1008` - Policy violation
- `1011` - Server error

---

## Performance Debugging

### Slow Page Loads

```
Debugging checklist:
1. Check Network tab for slow API requests
2. Verify no unnecessary re-renders (React DevTools)
3. Check for memory leaks
4. Verify images/assets are optimized
```

### High Memory Usage

```
Debugging steps:
1. Open Performance tab
2. Take heap snapshot
3. Check for detached DOM nodes
4. Verify WebSocket connections are cleaned up
```

### Slow Calculations

```
Strategy Builder P/L calculation slow:
1. Check P/L grid size (too many columns?)
2. Verify no console errors during calculation
3. Check API response time for /api/strategies/calculate
```

---

## Common Debugging Workflows

### Workflow 1: Page Won't Load

```
1. Check console for errors
2. Check Network tab for failed requests
3. Verify auth token is valid
4. Check if backend is running
5. Verify correct URL and route exists
```

### Workflow 2: WebSocket Not Connecting

```
1. Check console for [AutoPilot WS] or WebSocket errors
2. Open Network -> WS tab
3. Verify connection attempt is made
4. Check backend WebSocket server is running
5. Verify auth token is included in connection URL
```

### Workflow 3: Data Not Updating

```
1. Check if WebSocket messages are being received
2. Verify store is updating (Vue DevTools)
3. Check if component is reactive to store changes
4. Look for console errors during update
```

### Workflow 4: Button/Modal Not Working

```
1. Check if element with correct data-testid exists
2. Verify element is not disabled
3. Check for console errors when clicked
4. Verify event handlers are attached
5. Check for overlapping elements blocking clicks
```

### Workflow 5: Visual Regression

```
1. Navigate to the screen
2. Take full page screenshot
3. Compare with baseline screenshot
4. Identify differences (color, layout, missing elements)
5. Report specific discrepancies
```

---

## Debugging Tools

### Chrome DevTools Shortcuts

| Tool | Shortcut | Use Case |
|------|----------|----------|
| Console | `Ctrl+Shift+J` | View logs and errors |
| Network | `Ctrl+Shift+E` | Monitor API/WebSocket |
| Elements | `Ctrl+Shift+C` | Inspect DOM structure |
| Performance | `Ctrl+Shift+P` | Profile performance |

### Vue DevTools

- Install Vue DevTools Chrome extension
- Inspect component state
- Track Pinia store updates
- Monitor events

### Useful Console Commands

```javascript
// Get auth token
localStorage.getItem('token')

// Check if element exists
document.querySelector('[data-testid="strategy-table"]')

// Get all data-testid elements
document.querySelectorAll('[data-testid]')

// Check store state (if exposed)
// (Vue DevTools preferred)
```

---

## Reporting Template

When debugging issues, report using this template:

```
**Screen:** /strategy
**Issue:** P/L grid not updating after clicking recalculate

**Console Errors:**
[List any console errors]

**Network Issues:**
[List failed requests or slow responses]

**DOM State:**
[Report on element existence/visibility]

**WebSocket:**
[Report connection status and messages]

**Steps to Reproduce:**
1. Navigate to /strategy
2. Add 2 legs
3. Click recalculate
4. P/L grid remains empty

**Expected Behavior:**
P/L grid should populate with values

**Actual Behavior:**
Grid remains empty, no console errors
```
