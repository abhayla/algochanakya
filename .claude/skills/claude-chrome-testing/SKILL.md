# Claude Chrome Testing Skill

**IMPORTANT:** Use this skill for browser-based testing, debugging, and visual verification of the AlgoChanakya application.

## Slash Command

Users can invoke this skill with `/chrome-test` to trigger Chrome testing workflows.

## When to Use

### Proactive Use (Automatic)
Claude should automatically use this skill when:
- Debugging failing Playwright tests
- Verifying visual changes after code modifications
- Testing WebSocket real-time updates
- Checking console errors in the browser
- Validating complex user flows

### User-Invoked Use
Users can explicitly request Chrome testing with:
```
/chrome-test
```

## Prerequisites

1. **Claude Chrome extension** v1.0.36+ installed
2. **Claude Code CLI** v2.0.73+ installed
3. **Chrome browser** running
4. Start session with: `claude --chrome`
5. Backend running on `localhost:8000`
6. Frontend running on `localhost:5173`

## Quick Setup

```bash
# Update Claude Code
claude update

# Start with Chrome enabled
claude --chrome

# Verify connection
/chrome
```

---

## Key Screens to Test

| Screen | URL | Key Test Areas |
|--------|-----|----------------|
| Dashboard | /dashboard | Navigation cards, layout |
| Watchlist | /watchlist | Live price updates, WebSocket connection |
| Positions | /positions | Exit/Add modals, P&L updates, Day/Net toggle |
| Option Chain | /optionchain | Greeks toggle, OI bars, strike finder, live prices |
| Strategy Builder | /strategy | P/L grid, live CMP, breakeven columns, payoff chart |
| Strategy Library | /strategies | Template cards, wizard modal, deploy functionality |
| AutoPilot Dashboard | /autopilot | WebSocket status, strategy list, P&L summary |
| AutoPilot Builder | /autopilot/strategies/new | 5-step wizard validation, condition builder |

---

## Common Testing Commands

### 1. Test WebSocket Connection
```
Go to localhost:5173/autopilot, open the console, and check for
WebSocket connection messages starting with [AutoPilot WS].
Tell me if the connection succeeds.
```

### 2. Verify P/L Calculations
```
Go to localhost:5173/strategy, add a NIFTY iron condor with:
- Sell CE at +100 from ATM
- Buy CE at +200 from ATM
- Sell PE at -100 from ATM
- Buy PE at -200 from ATM

Then verify:
1. Breakeven columns appear in the P/L grid
2. Max profit/loss cards show correct values
3. Payoff chart renders correctly
```

### 3. Debug Console Errors
```
Navigate to localhost:5173/positions, open DevTools console,
and report any errors or warnings. Focus on WebSocket and API errors.
```

### 4. Test Modal Interactions
```
Go to localhost:5173/positions, click the exit button on the first position,
and verify:
1. Exit modal opens
2. Market/Limit order type buttons work
3. Quantity is pre-filled
4. Exit button is clickable
```

### 5. Verify Live Price Updates
```
Go to localhost:5173/optionchain, monitor for 10 seconds, and verify:
1. LTP values update in real-time
2. Spot price updates
3. No console errors during price updates
```

### 6. Test 5-Step Wizard
```
Go to localhost:5173/autopilot/strategies/new and test the wizard:
1. Fill step 1 (name and legs)
2. Click Next - verify validation works
3. Continue through all 5 steps
4. Report any validation errors or console errors
```

### 7. Check data-testid Elements
```
Go to localhost:5173/strategy and verify these data-testid elements exist:
- strategy-page
- strategy-table
- strategy-add-row-button
- strategy-save-button
- strategy-max-profit-card
```

### 8. Record Demo GIF
```
Record a GIF showing the complete workflow for creating a strategy:
1. Navigate to /strategy
2. Add 2 legs (Buy Call + Sell Call)
3. Click recalculate
4. Show the P/L grid and payoff chart
Save the GIF as docs/assets/screenshots/strategy-builder-demo.gif
```

---

## Authentication Workflow

### Using Existing Token (Default)
```
1. Read token from tests/config/.auth-token
2. Go to localhost:5173/dashboard
3. Execute: localStorage.setItem('token', '<token>')
4. Refresh the page
5. Verify authentication succeeded
```

### Token Expired or Missing
```
If token is expired or missing:
1. Ask user for TOTP
2. Navigate to localhost:8000/api/auth/zerodha/login
3. Complete OAuth flow
4. Extract token from redirect
5. Save to tests/config/.auth-token
```

---

## Debugging Patterns

### Console Log Prefixes
Filter console logs by these prefixes:
- `[AutoPilot WS]` - WebSocket connection, messages, errors
- `[OptionChain]` - Option chain subscriptions and updates
- `[Strategy]` - P/L calculation logs

### Network Tab
Check Network tab for:
- Failed API requests (4xx, 5xx)
- Slow responses (>2s)
- WebSocket connection status
- CORS errors

### DOM State
Verify elements exist:
```
Check if document.querySelector('[data-testid="strategy-table"]') exists
```

### WebSocket Messages
Monitor WebSocket frames:
```
Open DevTools -> Network -> WS tab
Filter for localhost:8000/ws/ticks
Check message payloads
```

---

## Integration with auto-verify Skill

When `auto-verify` skill runs Playwright tests and failures occur, this skill should:

1. **Read test failure** from Playwright output
2. **Navigate to failing URL** in Chrome
3. **Check console** for errors
4. **Verify data-testid** elements exist
5. **Capture screenshot** or GIF of the issue
6. **Report findings** to help diagnose the problem

### Example Integration Workflow
```
Auto-verify ran positions.happy.spec.js and it failed at line 45.
The test expected the exit modal to appear but it didn't.

Use Chrome to:
1. Go to localhost:5173/positions
2. Click the exit button
3. Check if positions-exit-modal element exists
4. Look for console errors
5. Report what you find
```

---

## Best Practices

### 1. Handle Modal Dialogs
JavaScript alerts, confirms, and prompts block browser events.
If you encounter one, dismiss it manually and tell Claude to continue.

### 2. Use Fresh Tabs
If a tab becomes unresponsive, create a new tab:
```
Open a new tab and go to localhost:5173/strategy
```

### 3. Filter Console Output
Instead of requesting ALL logs, specify patterns:
```
Show me console errors containing "WebSocket" or "API"
```

### 4. Verify Before Acting
Before clicking/filling forms, verify elements exist:
```
Check if the strategy-add-row-button exists before clicking it
```

---

## Limitations

### Browser Support
- ✅ **Google Chrome** - Fully supported
- ❌ **Brave, Arc, other Chromium browsers** - Not supported
- ❌ **Firefox, Safari, Edge** - Not supported
- ❌ **WSL (Windows Subsystem for Linux)** - Not supported

### Browser State
- **Visible browser required** - No headless mode
- **Login handling** - Pauses on login pages/CAPTCHAs for manual intervention
- **Modal blocking** - JavaScript alerts/confirms block automation

---

## Reference Files

See `references/` folder for:
- `browser-commands.md` - Complete command reference
- `debugging-patterns.md` - Detailed debugging strategies
- `testing-scenarios.md` - Screen-specific testing scenarios
