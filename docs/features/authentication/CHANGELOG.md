# Authentication Changelog

All notable changes to the Authentication feature will be documented in this file.

## [Unreleased]

## [1.1.0] - 2024-12-07

### Changed
- Redesigned login screen with light theme (file: frontend/src/views/LoginView.vue)
- Added broker logos to login page (file: frontend/src/views/LoginView.vue)
- Dashboard-style header on login page (file: frontend/src/views/LoginView.vue)

## [1.0.0] - 2024-12-03

### Added
- Initial Zerodha OAuth integration (file: backend/app/api/routes/auth.py)
- JWT-based session management (file: backend/app/utils/dependencies.py)
- Redis session storage (file: backend/app/database.py)
- User and BrokerConnection models (files: backend/app/models/users.py, broker_connections.py)
- Login view with Zerodha button (file: frontend/src/views/LoginView.vue)
- OAuth callback handler (file: frontend/src/views/AuthCallbackView.vue)
- Auth store for state management (file: frontend/src/stores/auth.js)
- Axios interceptor for auth headers (file: frontend/src/services/api.js)
- Router guards for protected routes (file: frontend/src/router/index.js)
