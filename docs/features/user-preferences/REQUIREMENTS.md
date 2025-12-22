# User Preferences Requirements

## Core Requirements
- [x] Store user-specific preferences
- [x] Get user preferences
- [x] Update preferences
- [x] Reset to defaults
- [x] Flexible JSON schema for future preferences

## P/L Grid Preferences
- [x] Show/hide ATM column
- [x] Show/hide breakeven columns
- [x] Show/hide strike columns
- [x] Custom spot price range
- [x] Number of columns configuration
- [x] Column step size

## Default Values
- [x] Default underlying (NIFTY/BANKNIFTY/FINNIFTY)
- [x] Default number of lots
- [x] Default order type
- [x] Default product type

## Notification Preferences
- [x] Order update notifications
- [x] P/L alert notifications
- [x] Position alerts
- [x] AutoPilot notifications

## Display Preferences
- [x] Theme selection (future)
- [x] Layout preferences (future)
- [x] Table density (future)

## API Requirements
- [x] GET /api/user-preferences - Get preferences
- [x] PUT /api/user-preferences - Update preferences
- [x] POST /api/user-preferences/reset - Reset to defaults

## Data Requirements
- [x] `user_preferences` table
- [x] JSON field for flexible schema
- [x] One-to-one relationship with user
- [x] Created/updated timestamps

## Default Preference Values
```json
{
  "pnl_grid": {
    "show_atm": true,
    "show_breakevens": true,
    "show_strikes": true,
    "column_count": 10
  },
  "defaults": {
    "underlying": "NIFTY",
    "lots": 1
  },
  "notifications": {
    "order_updates": true,
    "pnl_alerts": true
  }
}
```

## Integration Requirements
- [x] Used by Strategy Builder for P/L grid config
- [x] Used by Settings view for UI

---
Last updated: 2025-12-22
