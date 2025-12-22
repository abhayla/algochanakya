# Authentication & Authorization

## Overview

Zerodha OAuth integration with JWT-based session management for secure user authentication and broker API access.

## Features

- **Zerodha OAuth Flow**: Login via Zerodha Kite Connect
- **JWT Sessions**: Token-based authentication with Redis storage
- **Broker Connections**: Store and manage broker API credentials
- **Protected Routes**: Frontend and backend route guards
- **Auto Token Refresh**: Seamless session management

## User Flow

1. Click "Login with Zerodha" button
2. Redirect to Zerodha authentication page
3. Enter credentials and authorize
4. Callback to platform with request token
5. Exchange for access token and create session
6. Redirect to dashboard

## Technical Implementation

### Backend

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/zerodha/login` | Generate Kite login URL |
| GET | `/api/auth/zerodha/callback` | Handle OAuth callback |
| POST | `/api/auth/logout` | Logout and clear session |
| GET | `/api/auth/me` | Get current user info |

**Database Models:**
- `User` - User account information
- `BrokerConnection` - Zerodha access token and metadata

**Session Management:**
- JWT tokens stored in Redis
- Tokens expire after configured hours (default: 24)
- Access tokens refreshed daily by Zerodha

### Frontend

**Components:**
- `LoginView.vue` - Login page with Zerodha button
- `AuthCallbackView.vue` - OAuth callback handler

**Store:**
- `stores/auth.js` - Authentication state management

**Router Guards:**
- Check `isAuthenticated` before allowing access to protected routes
- Redirect to login if not authenticated

### Dependencies

**Backend:**
- `get_current_user` - Dependency for protected endpoints
- `get_current_broker_connection` - Dependency for broker operations

**Frontend:**
- Axios interceptor automatically adds JWT to request headers

## Configuration

**Environment Variables (.env):**
```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
JWT_SECRET=your_jwt_secret
JWT_EXPIRY_HOURS=24
FRONTEND_URL=http://localhost:5174
```

## Testing

```bash
npm run test:specs:login
```

## Related

- [Authentication Architecture](../../architecture/authentication.md) - Detailed authentication flow
- [API Reference](../../api/README.md) - Endpoint documentation
