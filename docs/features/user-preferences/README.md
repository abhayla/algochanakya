# User Preferences

## Overview

User-specific settings and preferences for customizing the platform experience.

## Features

- **P/L Grid Configuration**: Customize spot price columns in Strategy Builder
- **Display Settings**: Theme, layout preferences
- **Notification Settings**: Alert preferences
- **Default Values**: Default underlying, expiry, lots

## Preference Types

### P/L Grid Preferences

Controls which spot price columns appear in Strategy Builder P/L grid:

- **Default Columns**: ATM, Breakevens, Strike prices
- **Custom Range**: Define custom spot price range
- **Column Count**: Number of columns to display
- **Step Size**: Increment between columns

### Other Preferences

- Default underlying (NIFTY, BANKNIFTY, FINNIFTY)
- Default number of lots
- Auto-refresh intervals
- Notification preferences

## Technical Implementation

### Backend

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/user-preferences` | Get user preferences |
| PUT | `/api/user-preferences` | Update preferences |
| POST | `/api/user-preferences/reset` | Reset to defaults |

**Database Model:**
- `UserPreferences` - User settings (JSON field for flexible schema)

**Preferences Schema:**
```json
{
  "pnl_grid": {
    "show_atm": true,
    "show_breakevens": true,
    "show_strikes": true,
    "custom_range": [-500, 500],
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

### Frontend

**Store:**
- `stores/userPreferences.js` - Preferences state management

**Views:**
- `SettingsView.vue` - Preferences configuration UI

**Usage in Strategy Builder:**
```javascript
import { useUserPreferencesStore } from '@/stores/userPreferences'

const preferencesStore = useUserPreferencesStore()
const showBreakevens = preferencesStore.pnlGrid.show_breakevens
```

## Default Values

```javascript
{
  pnl_grid: {
    show_atm: true,
    show_breakevens: true,
    show_strikes: true,
    column_count: 10
  },
  defaults: {
    underlying: 'NIFTY',
    lots: 1
  }
}
```

## Testing

```bash
# Test preferences API
curl -X GET http://localhost:8000/api/user-preferences \
  -H "Authorization: Bearer $TOKEN"
```

## Related

- [Strategy Builder](../strategy-builder/) - P/L grid customization
- [Settings View](../dashboard/) - Preferences UI
