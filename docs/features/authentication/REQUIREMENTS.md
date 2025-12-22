# Authentication Requirements

## Core Requirements
- [x] Zerodha OAuth 2.0 integration
- [x] JWT-based session management
- [x] Session storage in Redis
- [x] Broker access token storage
- [x] User profile management
- [x] Logout functionality

## OAuth Flow
- [x] Generate Kite login URL with API key
- [x] Redirect to Zerodha authentication
- [x] Handle OAuth callback with request token
- [x] Exchange request token for access token
- [x] Store access token in database
- [x] Generate JWT session token
- [x] Store JWT in Redis with expiry

## Session Management
- [x] JWT token generation
- [x] JWT token validation
- [x] Redis session storage
- [x] Configurable session expiry (default 24 hours)
- [x] Session cleanup on logout
- [x] Auto token refresh handling

## User Management
- [x] Create user on first login
- [x] Update user on subsequent logins
- [x] Store broker connection metadata
- [x] Track last login timestamp

## API Requirements
- [x] GET /api/auth/zerodha/login - Generate login URL
- [x] GET /api/auth/zerodha/callback - Handle OAuth callback
- [x] POST /api/auth/logout - Logout user
- [x] GET /api/auth/me - Get current user info

## Security Requirements
- [x] Secure JWT secret (env variable)
- [x] HTTPS for production
- [x] CORS configuration
- [x] No password storage (OAuth only)
- [x] Access token encryption in database

## Frontend Requirements
- [x] Login page with Zerodha button
- [x] OAuth callback handler
- [x] JWT storage in localStorage
- [x] Axios interceptor for auth headers
- [x] Router guards for protected routes
- [x] Auto-redirect to login if unauthenticated

## Backend Dependencies
- [x] `get_current_user` dependency for protected endpoints
- [x] `get_current_broker_connection` dependency for broker operations
- [x] FastAPI security utilities

## Data Requirements
- [x] `users` table - User account info
- [x] `broker_connections` table - Broker credentials
- [x] Redis for JWT storage
- [x] Index on user email

## Integration Requirements
- [x] Kite Connect OAuth endpoints
- [x] Redis connection for sessions
- [x] Frontend-backend CORS config

---
Last updated: 2025-12-22
