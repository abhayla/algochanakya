# Testing Scenarios Reference

Screen-specific testing scenarios for comprehensive AlgoChanakya testing using Claude Chrome.

---

## Strategy Builder (`/strategy`) - 15 Scenarios

### Scenario 1: Basic Strategy Creation
```
1. Navigate to localhost:5173/strategy
2. Click strategy-add-row-button
3. Select NIFTY underlying
4. Select Buy action
5. Select CE option type
6. Enter strike price
7. Enter quantity
8. Click recalculate
9. Verify P/L grid populates
10. Check for console errors
```

### Scenario 2: Iron Condor Creation
```
1. Add 4 legs:
   - Sell CE at ATM+100
   - Buy CE at ATM+200
   - Sell PE at ATM-100
   - Buy PE at ATM-200
2. Click recalculate
3. Verify breakeven columns appear
4. Verify max profit/loss cards show values
5. Verify payoff chart renders
```

### Scenario 3: Save Strategy
```
1. Create a 2-leg strategy
2. Click strategy-save-button
3. Verify save modal opens
4. Enter strategy name
5. Click save
6. Check for success message
7. Verify no console errors
```

### Scenario 4: Live CMP Update
```
1. Create a strategy with NIFTY options
2. Monitor the CMP column
3. Wait 5 seconds
4. Verify CMP values update in real-time
5. Check WebSocket connection in console
```

### Scenario 5: P/L Grid Column Verification
```
1. Create a strategy
2. Click recalculate
3. Verify these columns exist:
   - Strike prices from legs
   - Breakeven points
   - Current spot (highlighted)
4. Verify values in each column
```

### Scenario 6: Payoff Chart
```
1. Create a Bull Call Spread
2. Click recalculate
3. Verify payoff chart renders
4. Check profit zone is green
5. Check loss zone is red
6. Verify breakeven line exists
```

### Scenario 7: Exit P/L Calculation
```
1. Create a strategy
2. Verify Exit P/L column
3. Click on a cell in Exit P/L
4. Verify manual override modal opens
5. Enter custom value
6. Verify calculation updates
```

### Scenario 8: Strategy Type Auto-Population
```
1. Create an Iron Condor manually
2. Verify strategy type label updates to "Iron Condor"
3. Try other patterns (Bull Call Spread, etc.)
4. Verify auto-detection works
```

### Scenario 9: Delete Leg
```
1. Create a 3-leg strategy
2. Click delete button on second leg
3. Verify leg is removed
4. Click recalculate
5. Verify P/L updates correctly
```

### Scenario 10: Underlying Tab Switching
```
1. Create NIFTY strategy
2. Switch to BANKNIFTY tab
3. Verify table clears
4. Create BANKNIFTY strategy
5. Switch back to NIFTY
6. Verify NIFTY strategy is still there
```

### Scenario 11: Share Strategy
```
1. Create and save a strategy
2. Click share button
3. Verify share modal opens
4. Check share link is generated
5. Copy link
6. Verify toast notification appears
```

### Scenario 12: Basket Order Modal
```
1. Create a 2-leg strategy
2. Click "Place Order" button
3. Verify basket order modal opens
4. Check leg details are correct
5. Verify total margin is shown
6. Verify order type selection works
```

### Scenario 13: P/L Mode Toggle
```
1. Create a strategy
2. Toggle between "At Expiry" and "Current"
3. Verify P/L grid values update
4. Verify payoff chart updates
5. Check for calculation errors in console
```

### Scenario 14: Validation Errors
```
1. Try to save without name
2. Verify validation error appears
3. Try to calculate without legs
4. Verify error message shows
5. Try duplicate strikes
6. Verify warning appears
```

### Scenario 15: Responsive Table
```
1. Create strategy with 6+ legs
2. Verify horizontal scroll works
3. Verify column headers stay visible
4. Check for overflow issues
5. Test at different viewport sizes
```

---

## Positions View (`/positions`) - 10 Scenarios

### Scenario 1: Load Positions
```
1. Navigate to localhost:5173/positions
2. Verify positions-table loads
3. Check for console errors
4. Verify WebSocket connection
5. Verify live P/L updates
```

### Scenario 2: Day/Net Toggle
```
1. Click positions-type-toggle
2. Switch to Net positions
3. Verify table data updates
4. Switch back to Day
5. Verify data changes back
```

### Scenario 3: Exit Position Modal
```
1. Click exit button on first position
2. Verify positions-exit-modal opens
3. Check quantity is pre-filled
4. Check instrument symbol is correct
5. Verify order type buttons work
6. Close modal without exiting
```

### Scenario 4: Add to Position Modal
```
1. Click "Add" button on a position
2. Verify positions-add-modal opens
3. Toggle Buy/Sell
4. Enter quantity
5. Enter limit price
6. Verify validation works
```

### Scenario 5: Exit All Positions
```
1. Click positions-exit-all-button
2. Verify confirmation modal opens
3. Check position count is shown
4. Cancel the action
5. Verify modal closes
```

### Scenario 6: P&L Summary Box
```
1. Verify positions-pnl-box exists
2. Check total P&L value
3. Verify color coding (green/red)
4. Check realized/unrealized split
5. Verify values update in real-time
```

### Scenario 7: Auto-Refresh Toggle
```
1. Verify auto-refresh is ON by default
2. Watch positions update automatically
3. Toggle auto-refresh OFF
4. Verify updates stop
5. Toggle back ON
6. Verify updates resume
```

### Scenario 8: Empty State
```
1. If no positions exist:
2. Verify empty state message
3. Check "Go to Option Chain" link exists
4. Click link
5. Verify navigation to /optionchain
```

### Scenario 9: Position Row Details
```
1. Verify each row shows:
   - Instrument symbol
   - Quantity (with +/- indicator)
   - Avg price
   - LTP (live update)
   - Day change
   - P&L (with color coding)
2. Click on a row
3. Verify row details expand (if implemented)
```

### Scenario 10: Grouped Positions
```
1. If grouping feature exists
2. Toggle grouping by underlying/expiry
3. Verify positions are grouped correctly
4. Verify group headers show totals
5. Test expand/collapse functionality
```

---

## Option Chain (`/optionchain`) - 12 Scenarios

### Scenario 1: Load Option Chain
```
1. Navigate to localhost:5173/optionchain
2. Select NIFTY underlying
3. Select expiry date
4. Verify chain table loads
5. Check for CE and PE columns
6. Verify spot price displays
```

### Scenario 2: Live Price Updates
```
1. Load option chain
2. Monitor LTP values for 10 seconds
3. Verify prices update in real-time
4. Check WebSocket messages in console
5. Verify no update lag
```

### Scenario 3: Greeks Toggle
```
1. Click Greeks toggle button
2. Verify Delta, Gamma, Theta, Vega columns appear
3. Verify values are populated
4. Toggle OFF
5. Verify columns hide
```

### Scenario 4: OI Bars Visualization
```
1. Verify OI bars display for CE and PE
2. Check bar widths represent OI values
3. Verify color coding (green/red)
4. Hover over bars
5. Check tooltip shows exact OI value
```

### Scenario 5: ITM Highlighting
```
1. Identify ATM strike
2. Verify CE strikes below ATM are highlighted green (ITM)
3. Verify PE strikes above ATM are highlighted red (ITM)
4. Check color intensity
```

### Scenario 6: Strike Finder
```
1. Click optionchain-strike-finder-btn
2. Verify strike finder modal opens
3. Select "ATM-based" mode
4. Enter range (+/- 5 strikes)
5. Verify strikes are filtered
6. Try "Delta-based" mode
7. Enter target delta (0.3)
8. Verify matching strikes are shown
```

### Scenario 7: Add to Strategy Builder
```
1. Click "Add CE" button on a strike
2. Verify navigation to /strategy
3. Check leg is added with correct details
4. Go back to option chain
5. Add PE option
6. Verify both legs exist in strategy
```

### Scenario 8: Max Pain Calculation
```
1. Verify Max Pain value displays
2. Check if Max Pain strike is highlighted
3. Verify calculation is correct
4. Compare with manual calculation
```

### Scenario 9: PCR (Put-Call Ratio)
```
1. Verify PCR value displays
2. Check if PCR > 1 or < 1
3. Verify color coding based on value
4. Check tooltip explanation
```

### Scenario 10: Expiry Selection
```
1. Open expiry dropdown
2. Verify all expiries are listed
3. Select weekly expiry
4. Verify chain updates
5. Select monthly expiry
6. Verify data changes
```

### Scenario 11: Underlying Tab Switching
```
1. Switch between NIFTY, BANKNIFTY, FINNIFTY
2. Verify spot price updates
3. Verify chain data loads for each
4. Check for console errors
5. Verify WebSocket re-subscribes
```

### Scenario 12: Scrolling and Performance
```
1. Load full chain (100+ strikes)
2. Scroll up and down
3. Verify smooth scrolling
4. Check for rendering lag
5. Verify no memory leaks
```

---

## AutoPilot Dashboard (`/autopilot`) - 20 Scenarios

### Scenario 1: Load Dashboard
```
1. Navigate to localhost:5173/autopilot
2. Verify autopilot-dashboard loads
3. Check WebSocket connection status
4. Verify autopilot-connection-status shows "Connected"
5. Check for [AutoPilot WS] logs in console
```

### Scenario 2: WebSocket Connection
```
1. Monitor console for WebSocket connection
2. Verify connection message
3. Check connection status indicator
4. If disconnected, verify reconnection attempts
5. Verify reconnection success
```

### Scenario 3: Strategy List
```
1. Verify autopilot-strategy-list loads
2. Check if strategies are displayed
3. Verify each strategy card shows:
   - Name
   - Status badge
   - Current P&L
   - Entry conditions
4. Click on a strategy
5. Verify navigation to detail view
```

### Scenario 4: Kill Switch
```
1. Locate autopilot-kill-switch-btn
2. Verify button is visible and accessible
3. Click kill switch
4. Verify confirmation modal opens
5. Cancel action
6. Verify modal closes
```

### Scenario 5: Summary P&L
```
1. Verify autopilot-summary-pnl displays
2. Check total P&L value
3. Verify color coding (green/red)
4. Check realized/unrealized breakdown
5. Verify values update in real-time
```

### Scenario 6: Activity Feed
```
1. Verify activity feed exists
2. Check for recent log entries
3. Verify log severity colors (info/warning/error)
4. Scroll through logs
5. Check for real-time log updates
```

### Scenario 7: Create New Strategy
```
1. Click "New Strategy" button
2. Verify navigation to /autopilot/strategies/new
3. Verify wizard loads
4. Check step indicator shows step 1/5
```

### Scenario 8: Filter Strategies
```
1. If filter exists
2. Filter by status (Active/Paused/Waiting)
3. Verify strategy list updates
4. Clear filter
5. Verify all strategies show
```

### Scenario 9: Real-Time Strategy Update
```
1. Monitor a strategy with status "Active"
2. Wait for WebSocket message
3. Verify P&L updates
4. Verify status badge updates if changed
5. Check for smooth UI updates
```

### Scenario 10: Empty State
```
1. If no strategies exist
2. Verify empty state message
3. Check "Create Strategy" CTA button
4. Click button
5. Verify navigation to builder
```

### Scenario 11: Pause Strategy
```
1. Click pause button on an active strategy
2. Verify confirmation modal
3. Confirm pause
4. Verify status changes to "Paused"
5. Check for success notification
```

### Scenario 12: Resume Strategy
```
1. Click resume on a paused strategy
2. Verify status changes to "Active"
3. Check WebSocket message sent
4. Verify UI updates
```

### Scenario 13: Exit Strategy
```
1. Click exit button on a strategy
2. Verify confirmation modal with P&L
3. Confirm exit
4. Verify status changes to "Exited"
5. Check if exit orders are placed
```

### Scenario 14: Risk Alerts
```
1. Monitor for risk alert notifications
2. If alert appears, verify:
   - Alert message is clear
   - Severity is indicated (warning/critical)
   - Action buttons are available
3. Dismiss alert
4. Verify it disappears
```

### Scenario 15: Confirmation Requests (Semi-Auto)
```
1. If semi-auto mode enabled
2. Wait for confirmation request
3. Verify modal shows:
   - Adjustment details
   - Reason for adjustment
   - Approve/Reject buttons
4. Approve or reject
5. Verify WebSocket message sent
```

### Scenario 16: Greeks Update
```
1. Monitor strategies with position legs
2. Check if Greeks values update
3. Verify Delta, Gamma display
4. Check update frequency
```

### Scenario 17: Dashboard Statistics
```
1. Verify total strategies count
2. Check active/paused/waiting counts
3. Verify today's P&L
4. Check win rate percentage
5. Verify all metrics update
```

### Scenario 18: Network Resilience
```
1. Monitor WebSocket connection
2. Simulate network interruption (if possible)
3. Verify reconnection attempts
4. Check if data syncs after reconnection
5. Verify no data loss
```

### Scenario 19: Multiple Tab Workflow
```
1. Open dashboard in tab 1
2. Open strategy detail in tab 2
3. Make changes in tab 2
4. Switch to tab 1
5. Verify dashboard reflects changes
```

### Scenario 20: Performance with Many Strategies
```
1. Load dashboard with 10+ strategies
2. Monitor CPU/memory usage
3. Verify smooth scrolling
4. Check for rendering lag
5. Verify WebSocket efficiency
```

---

## AutoPilot Strategy Builder (`/autopilot/strategies/new`) - 20+ Scenarios

### Scenario 1: Step 1 - Basic Info
```
1. Navigate to /autopilot/strategies/new
2. Verify autopilot-builder-step-1 loads
3. Enter strategy name
4. Select trading mode (Live/Paper)
5. Click Next
6. Verify validation works
```

### Scenario 2: Step 1 - Add Legs
```
1. In step 1, click "Add Leg"
2. Select NIFTY
3. Select CE option type
4. Choose strike selection mode (ATM offset/Absolute/Delta-based)
5. Enter quantity
6. Verify leg is added to table
```

### Scenario 3: Step 2 - Entry Conditions
```
1. Navigate to step 2
2. Click autopilot-add-condition-button
3. Verify condition builder opens
4. Select variable (TIME/SPOT/VIX/PREMIUM)
5. Select operator (>, <, ==, between)
6. Enter value
7. Verify condition is added
```

### Scenario 4: Step 2 - Complex Conditions
```
1. Add multiple conditions with AND/OR logic
2. Verify parentheses grouping works
3. Test nested conditions
4. Verify condition preview displays correctly
```

### Scenario 5: Step 3 - Risk Management
```
1. Navigate to step 3
2. Enable trailing stop
3. Set stop loss percentage
4. Set target profit percentage
5. Verify risk preview calculates correctly
```

### Scenario 6: Step 4 - Adjustments
```
1. Navigate to step 4
2. Add adjustment rule
3. Select trigger type (Delta breach, P&L threshold, etc.)
4. Select action (Roll strike, Add leg, Exit, etc.)
5. Verify rule configuration
```

### Scenario 7: Step 5 - Schedule
```
1. Navigate to step 5
2. Select entry time window
3. Set exit time
4. Select trading days
5. Verify schedule preview
```

### Scenario 8: Step 5 - Review & Create
```
1. In step 5, review all settings
2. Click autopilot-builder-save
3. Verify strategy is created
4. Check for success notification
5. Verify navigation to dashboard
```

### Scenario 9: Validation Errors
```
1. Try to proceed without filling required fields
2. Verify autopilot-validation-error-{index} displays
3. Fix errors
4. Verify errors clear
5. Proceed successfully
```

### Scenario 10: Back Navigation
```
1. Proceed to step 3
2. Click "Back" to step 2
3. Verify data is retained
4. Make changes
5. Proceed forward
6. Verify changes persist
```

### Scenario 11: Live CMP in Legs Table
```
1. Add legs in step 1
2. Verify CMP column shows live prices
3. Monitor for updates
4. Check WebSocket connection
```

### Scenario 12: Template Loading
```
1. If templates exist
2. Click "Load Template"
3. Select a template
4. Verify all steps populate with template data
5. Modify and save as new strategy
```

### Scenario 13: Save as Template
```
1. Configure a strategy
2. Click "Save as Template"
3. Enter template name
4. Verify template is saved
5. Load it again to verify
```

### Scenario 14: Step Navigation via Stepper
```
1. Click on step 3 directly from step 1
2. Verify navigation is prevented (if validation required)
3. Complete step 1
4. Verify step 2 is accessible
5. Test all step combinations
```

### Scenario 15: Condition Variable Types
```
Test each variable type:
1. TIME: Set entry between 9:15 AM - 10:00 AM
2. SPOT: Set NIFTY spot > 25000
3. VIX: Set VIX < 15
4. PREMIUM: Set premium collected > 100
5. DELTA: Set portfolio delta between -0.5 and 0.5
Verify all work correctly
```

### Scenario 16: Discard Changes
```
1. Fill wizard partially
2. Click "Cancel" or "Discard"
3. Verify confirmation modal
4. Confirm discard
5. Verify navigation to dashboard
6. Verify strategy not saved
```

### Scenario 17: Semi-Auto vs Full-Auto
```
1. Toggle between semi-auto and full-auto modes
2. Verify UI shows correct options for each
3. In semi-auto, verify confirmation settings
4. In full-auto, verify auto-execution settings
```

### Scenario 18: Greeks Monitoring Settings
```
1. Enable Greeks monitoring
2. Set Delta alert threshold
3. Set Gamma risk threshold
4. Verify settings are saved
```

### Scenario 19: Re-Entry Settings
```
1. Enable re-entry
2. Set re-entry conditions
3. Set maximum re-entry count
4. Verify configuration
```

### Scenario 20: Complex Strategy Creation
```
End-to-end test:
1. Create Iron Condor AutoPilot strategy
2. Set entry: TIME = 9:30 AM AND SPOT between 25000-26000
3. Add legs with ATM offsets
4. Set stop loss: 50% of premium
5. Set trailing stop: 20%
6. Add adjustment: If Delta > 0.5, roll strike
7. Schedule: Monday-Friday, 9:30 AM - 3:15 PM
8. Save and activate
9. Verify all settings persist
10. Check dashboard shows new strategy
```

---

## Watchlist (`/watchlist`) - 8 Scenarios

### Scenario 1: Load Watchlist
```
1. Navigate to localhost:5173/watchlist
2. Verify watchlist-page loads
3. Check instrument list displays
4. Verify WebSocket connection
5. Verify live prices update
```

### Scenario 2: Search Instruments
```
1. Type "NIFTY" in watchlist-search-input
2. Verify filtered results
3. Clear search
4. Verify all instruments show
```

### Scenario 3: Add Instrument
```
1. Search for an instrument
2. Click "Add" button
3. Verify instrument added to watchlist
4. Check if persisted (refresh page)
```

### Scenario 4: Remove Instrument
```
1. Click remove button on an instrument
2. Verify confirmation (if any)
3. Confirm removal
4. Verify instrument disappears
```

### Scenario 5: Tab Management
```
1. Create new watchlist tab
2. Name the tab
3. Add instruments to new tab
4. Switch between tabs
5. Verify each tab shows correct instruments
```

### Scenario 6: Live Price Updates
```
1. Monitor watchlist for 10 seconds
2. Verify LTP updates
3. Check change percentage updates
4. Verify color coding (green/red)
```

### Scenario 7: Navigate to Option Chain
```
1. Click on an index instrument (NIFTY)
2. Verify navigation to /optionchain
3. Verify underlying is pre-selected
```

### Scenario 8: Empty Watchlist
```
1. If watchlist is empty
2. Verify empty state message
3. Check "Add Instruments" CTA
4. Click CTA
5. Verify search opens
```

---

## Dashboard (`/dashboard`) - 5 Scenarios

### Scenario 1: Load Dashboard
```
1. Navigate to localhost:5173/dashboard
2. Verify all navigation cards display
3. Check for layout issues
4. Verify no console errors
```

### Scenario 2: Navigation Cards
```
1. Verify these cards exist:
   - Watchlist
   - Positions
   - Option Chain
   - Strategy Builder
   - Strategy Library
   - AutoPilot
2. Click each card
3. Verify navigation works
```

### Scenario 3: Quick Stats (if implemented)
```
1. Check if dashboard shows summary stats
2. Verify P&L displays
3. Check positions count
4. Verify active strategies count
```

### Scenario 4: Responsive Layout
```
1. Test dashboard at different viewport sizes
2. Verify cards reflow correctly
3. Check mobile layout
4. Verify no overflow issues
```

### Scenario 5: Authentication Check
```
1. Access /dashboard without auth
2. Verify redirect to login
3. Log in
4. Verify redirect back to dashboard
```

---

## Strategy Library (`/strategies`) - 8 Scenarios

### Scenario 1: Browse Templates
```
1. Navigate to localhost:5173/strategies
2. Verify strategy template cards display
3. Check category filters work
4. Search for "Iron Condor"
5. Verify search results
```

### Scenario 2: Strategy Wizard
```
1. Click "Strategy Wizard" button
2. Answer 3 questions (outlook, volatility, risk)
3. Verify AI recommendation
4. Check recommended strategies display
```

### Scenario 3: Deploy Template
```
1. Select a template (e.g., Bull Call Spread)
2. Click "Deploy"
3. Verify navigation to /strategy
4. Check legs are pre-populated
5. Verify live prices are fetched
```

### Scenario 4: View Template Details
```
1. Click "View Details" on a template
2. Verify details modal opens
3. Check educational content displays:
   - When to use
   - Pros/cons
   - Max profit/loss
   - Greeks exposure
4. Close modal
```

### Scenario 5: Compare Strategies
```
1. Select 2-3 templates
2. Click "Compare"
3. Verify comparison modal shows side-by-side
4. Check risk/reward comparison
5. Verify visual comparison charts
```

### Scenario 6: Category Filtering
```
1. Filter by "Bullish"
2. Verify only bullish strategies show
3. Filter by "Neutral"
4. Verify results update
5. Clear filters
```

### Scenario 7: Popular Strategies
```
1. Click "Popular" tab
2. Verify most-used strategies display
3. Check popularity ranking
4. Deploy a popular strategy
```

### Scenario 8: Save Custom Strategy
```
1. Create a custom strategy in Strategy Builder
2. Save it
3. Navigate to /strategies
4. Verify "My Strategies" tab exists
5. Check custom strategy appears
```

---

## General Testing Scenarios

### Cross-Screen WebSocket Testing
```
1. Open /watchlist in tab 1
2. Open /optionchain in tab 2
3. Open /strategy in tab 3
4. Monitor WebSocket connections
5. Verify separate connections for ticks and autopilot
6. Check for connection leaks
```

### Authentication Flow
```
1. Clear localStorage
2. Navigate to any protected route
3. Verify redirect to login
4. Complete OAuth flow
5. Verify redirect back to original route
```

### Error Boundary Testing
```
1. Trigger React error (if possible)
2. Verify error boundary catches it
3. Check if fallback UI displays
4. Verify console error is logged
```

### Performance Testing
```
1. Open all screens in separate tabs
2. Monitor CPU/memory usage
3. Check for memory leaks
4. Verify smooth operation across tabs
```
