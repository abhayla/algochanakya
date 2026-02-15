# Browser Commands Reference

Complete reference for Claude Chrome browser automation commands used in AlgoChanakya testing.

---

## Navigation Commands

### Basic Navigation
```
Go to localhost:5173/dashboard
Navigate to localhost:5173/autopilot/strategies/new
Open localhost:5173/positions in a new tab
```

### With Authentication
```
Go to localhost:5173/strategy and inject auth token from tests/config/.auth-token into localStorage as 'token'
```

### Refresh Page
```
Refresh the page
Reload localhost:5173/optionchain
```

---

## Element Interaction

### Click Actions
```
Click the element with data-testid="strategy-add-row-button"
Click the exit button (data-testid="positions-exit-{symbol}")
Click Next button in the wizard
```

### Form Filling
```
Type "Iron Condor" into the input with data-testid="strategy-name-input"
Select "NIFTY" from the underlying dropdown
Fill the quantity field with "1"
```

### Checkbox/Toggle
```
Toggle the Day/Net switch (data-testid="positions-type-toggle")
Check the "Enable trailing stop" checkbox
```

---

## Debugging Commands

### Console Inspection
```
Open DevTools console and show me all errors
Check the console for errors containing "WebSocket"
Show me warnings in the console
Filter console logs for "[AutoPilot WS]" prefix
```

### Network Inspection
```
Open Network tab and show me failed requests
Check if WebSocket connection to localhost:8000/ws/ticks is established
Show me API requests to /api/positions
Report slow responses (>2 seconds)
```

### DOM Inspection
```
Check if element with data-testid="strategy-table" exists
Verify that positions-exit-modal is visible
Count how many rows are in the positions table
Show me the text content of strategy-max-profit-card
```

### Element Properties
```
Get the value of the input with data-testid="autopilot-builder-name"
Check if strategy-save-button is disabled
Report the background color of positions-pnl-box
```

---

## Screenshot & Recording

### Screenshots
```
Take a screenshot of the current page
Screenshot just the strategy-payoff-section element
Capture full page screenshot and save to docs/assets/screenshots/positions-view.png
```

### GIF Recording
```
Record a GIF of the following workflow:
1. Navigate to /strategy
2. Add 2 legs
3. Click recalculate
4. Show the payoff chart
Save as docs/assets/screenshots/strategy-demo.gif
```

---

## Multi-Tab Workflows

### Creating Tabs
```
Open localhost:5173/positions in a new tab
Create a second tab for /optionchain
```

### Switching Tabs
```
Switch to the tab with /autopilot
Go back to the positions tab
```

### Grouping Tabs
```
Group the tabs for /strategy, /positions, and /optionchain together
```

---

## Waiting & Timing

### Wait for Elements
```
Wait for data-testid="positions-table" to appear
Wait up to 5 seconds for the exit modal to open
```

### Wait for Conditions
```
Wait for the page to finish loading
Wait for WebSocket connection to establish
Monitor for 10 seconds and report any console errors
```

---

## WebSocket-Specific Commands

### Connection Monitoring
```
Open /autopilot and check if WebSocket connects successfully
Monitor WebSocket messages for 15 seconds
Report the connection status of ws://localhost:8000/ws/autopilot
```

### Message Inspection
```
Show me the first 5 WebSocket messages received
Check if "ticks" messages are being received
Report the structure of the latest WebSocket message
```

---

## AlgoChanakya-Specific Commands

### Strategy Builder
```
Add a NIFTY Call option at 25000 strike
Set the quantity to 2 lots
Click recalculate and verify P/L grid updates
Check if breakeven columns appear
```

### Positions View
```
Click exit on the first position
Verify the exit modal opens with correct data
Check if P&L is calculated correctly
```

### Option Chain
```
Toggle Greeks view on
Verify IV values are displayed
Click strike finder button
```

### AutoPilot
```
Navigate to AutoPilot builder step 2
Add a condition: SPOT > 25000
Verify condition validation works
```

---

## Verification Commands

### Visual Verification
```
Verify the payoff chart is rendered
Check if all table columns are visible
Confirm the modal is centered on screen
```

### Data Verification
```
Verify the P&L value matches the calculation
Check if live prices are updating
Confirm the strategy name is saved correctly
```

### Error Checking
```
Verify there are no console errors
Check for any React warnings
Confirm no 404 API errors in Network tab
```

---

## Advanced Commands

### Resize Window
```
Resize window to 1920x1080
Test responsive design at 768px width
```

### Scroll Actions
```
Scroll to the bottom of the option chain table
Scroll the P/L grid horizontally to see breakeven columns
```

### Hover Actions
```
Hover over the max profit card
Hover over a P/L grid cell to see tooltip
```

---

## Error Handling

### When Elements Don't Exist
```
If the element doesn't exist, check the DOM structure and report what you find
If the button is not clickable, check if it's disabled or hidden
```

### When Pages Don't Load
```
If the page doesn't load, check console for errors and Network tab for failed requests
If authentication fails, verify the token is valid
```

### When WebSocket Fails
```
If WebSocket doesn't connect, check:
1. Backend is running on localhost:8000
2. No CORS errors in console
3. Token is valid
```

---

## Command Templates

### Full Test Workflow
```
1. Go to localhost:5173/strategy
2. Inject auth token: localStorage.setItem('token', '<token>')
3. Refresh the page
4. Wait for page to load
5. Click data-testid="strategy-add-row-button"
6. Fill in leg details
7. Click recalculate
8. Verify P/L grid updates
9. Take screenshot
10. Report findings
```

### Debug Workflow
```
1. Navigate to {url}
2. Open DevTools console
3. Check for errors
4. Open Network tab
5. Check for failed requests
6. Report all findings
```

### Visual Regression Workflow
```
1. Navigate to {url}
2. Wait for page to load
3. Take full page screenshot
4. Compare with baseline in docs/assets/screenshots/
5. Report any differences
```
