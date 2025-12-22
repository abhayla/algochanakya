# Dashboard

## Overview

Main dashboard view providing navigation to all platform features with quick stats and shortcuts.

## Features

- **Navigation Cards**: Quick access to all features
- **Welcome Message**: Personalized greeting
- **Feature Grid**: Visual card layout for all modules
- **Responsive Design**: Mobile and desktop optimized

## Feature Cards

| Feature | Route | Description |
|---------|-------|-------------|
| Watchlist | `/watchlist` | Real-time instrument prices |
| Positions | `/positions` | F&O positions with P&L |
| Option Chain | `/optionchain` | Full option chain with Greeks |
| Strategy Builder | `/strategy/new` | Build multi-leg strategies |
| Strategy Library | `/strategies` | Pre-built templates |
| AutoPilot | `/autopilot` | Automated execution |

## Technical Implementation

### Frontend

**Component:**
- `DashboardView.vue` - Main dashboard view

**Route:**
- `/dashboard` - Dashboard page
- Redirect from `/` to `/watchlist` (bypasses dashboard for quick access)

**Layout:**
```vue
<template>
  <div class="dashboard">
    <h1>Welcome to AlgoChanakya</h1>
    <div class="feature-grid">
      <router-link
        v-for="feature in features"
        :to="feature.route"
        class="feature-card"
      >
        <h3>{{ feature.name }}</h3>
        <p>{{ feature.description }}</p>
      </router-link>
    </div>
  </div>
</template>
```

## Navigation Flow

```
Login
  ↓
Dashboard (or direct to Watchlist)
  ↓
Feature Selection
  ↓
Feature Page
```

## Testing

```bash
npm run test:specs:dashboard
```

## Related

- [Navigation Tests](../../testing/) - Navigation flow tests
- [Router Configuration](../../architecture/) - Route definitions
