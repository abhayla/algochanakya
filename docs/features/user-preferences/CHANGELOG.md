# User Preferences Changelog

All notable changes to the User Preferences feature will be documented in this file.

## [Unreleased]

### Added
- `order_broker` column to `user_preferences` table for order execution broker selection (file: backend/app/models/user_preferences.py)
- `OrderBroker` class with valid broker values: kite, angel, upstox, dhan, fyers, paytm (file: backend/app/models/user_preferences.py)
- `platform` as a valid `market_data_source` value (platform-default data with SmartAPI→Dhan→Fyers→Paytm→Upstox→Kite failover) (file: backend/app/models/user_preferences.py)
- Alembic migration for new `order_broker` column and updated constraint (file: backend/alembic/versions/a1b2c3d4e5f6_add_order_broker_and_platform_source.py)
- `brokerPreferences.js` Pinia store with `isUsingPlatformDefault`, `activeSourceLabel`, `marketDataSourceOptions`, `orderBrokerOptions` getters (file: frontend/src/stores/brokerPreferences.js)
- `BrokerUpgradeBanner.vue` persistent upgrade banner shown on all data screens (file: frontend/src/components/common/BrokerUpgradeBanner.vue)
- `DataSourceBadge.vue` live data source indicator badge (file: frontend/src/components/common/DataSourceBadge.vue)
- `BrokerSettings.vue` settings component with market data source dropdown and order broker dropdown (file: frontend/src/components/settings/BrokerSettings.vue)
- Broker upgrade banner wired into Dashboard, Watchlist, Option Chain, and Positions views

### Changed
- `UserPreferencesUpdateRequest` schema pattern updated to accept all 7 market_data_source values (file: backend/app/schemas/user_preferences.py)
- `UserPreferencesResponse` schema now includes `order_broker` field (file: backend/app/schemas/user_preferences.py)
- `user_preferences` route updated to validate and persist `order_broker` field (file: backend/app/api/routes/user_preferences.py)
- Default `market_data_source` changed from `smartapi` to `platform` (file: backend/app/models/user_preferences.py)
- Settings view extended with Broker Selection section (file: frontend/src/views/SettingsView.vue)

## [1.0.0] - 2024-12-15

### Added
- User preferences API endpoints (file: backend/app/api/routes/user_preferences.py)
- User preferences database model (file: backend/app/models/user_preferences.py)
- P/L grid configuration preferences (file: backend/app/models/user_preferences.py)
- Default values for underlying, lots (file: backend/app/models/user_preferences.py)
- Notification preferences (file: backend/app/models/user_preferences.py)
- User preferences store (file: frontend/src/stores/userPreferences.js)
- Settings view for preferences management (file: frontend/src/views/SettingsView.vue)
- Reset to defaults functionality (file: backend/app/api/routes/user_preferences.py)
