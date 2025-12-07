# API Reference

AlgoChanakya exposes a RESTful API built with FastAPI. All endpoints are prefixed with `/api/`.

## Interactive Documentation

When the backend is running, access interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

### Getting a Token

1. Redirect user to: `GET /api/auth/zerodha/login`
2. After OAuth, callback provides JWT token
3. Store token in localStorage/cookies

## API Endpoints

### Health

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | No | Health check (DB + Redis) |

### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/zerodha/login` | GET | No | Get Zerodha OAuth URL |
| `/api/auth/zerodha/callback` | GET | No | OAuth callback handler |
| `/api/auth/me` | GET | Yes | Get current user |
| `/api/auth/logout` | POST | Yes | Logout (invalidate session) |

### Watchlist

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/watchlist` | GET | Yes | List user's watchlists |
| `/api/watchlist` | POST | Yes | Create watchlist |
| `/api/watchlist/{id}` | GET | Yes | Get watchlist by ID |
| `/api/watchlist/{id}` | PUT | Yes | Update watchlist |
| `/api/watchlist/{id}` | DELETE | Yes | Delete watchlist |
| `/api/watchlist/{id}/instruments` | POST | Yes | Add instrument |
| `/api/watchlist/{id}/instruments/{token}` | DELETE | Yes | Remove instrument |

### Instruments

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/instruments/search` | GET | Yes | Search instruments |

**Query Parameters:**
- `q` - Search query (symbol or name)
- `limit` - Max results (default: 20)

### Option Chain

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/optionchain/chain` | GET | Yes | Full option chain with OI, IV, Greeks |
| `/api/optionchain/oi-analysis` | GET | Yes | OI data for charts |

**Query Parameters:**
- `underlying` - NIFTY, BANKNIFTY, or FINNIFTY
- `expiry` - Expiry date (YYYY-MM-DD)

### Options

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/options/expiries` | GET | Yes | Available expiry dates |
| `/api/options/strikes` | GET | Yes | Strike prices for expiry |
| `/api/options/chain` | GET | Yes | Option chain data |
| `/api/options/instrument` | GET | Yes | Get instrument by params |

**Query Parameters:**
- `underlying` - NIFTY, BANKNIFTY, or FINNIFTY
- `expiry` - Expiry date

### Strategies

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/strategies` | GET | Yes | List user's strategies |
| `/api/strategies` | POST | Yes | Create strategy |
| `/api/strategies/{id}` | GET | Yes | Get strategy by ID |
| `/api/strategies/{id}` | PUT | Yes | Update strategy |
| `/api/strategies/{id}` | DELETE | Yes | Delete strategy |
| `/api/strategies/calculate` | POST | Yes | Calculate P/L grid |
| `/api/strategies/{id}/share` | POST | Yes | Generate share link |
| `/api/strategies/shared/{code}` | GET | No | Get shared strategy (public) |

### Orders

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/orders/basket` | POST | Yes | Place basket order via Kite |
| `/api/orders/positions` | GET | Yes | Get broker positions |
| `/api/orders/import-positions` | POST | Yes | Import positions as strategy |
| `/api/orders/ltp` | GET | Yes | Get LTP for instruments |

### Positions

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/positions` | GET | Yes | Get F&O positions with P&L |
| `/api/positions/exit` | POST | Yes | Exit a position |
| `/api/positions/add` | POST | Yes | Add to position |
| `/api/positions/exit-all` | POST | Yes | Exit all positions |
| `/api/positions/grouped` | GET | Yes | Positions grouped by underlying |

**Query Parameters for GET:**
- `type` - `day` or `net` (default: day)

### WebSocket

| Endpoint | Protocol | Auth | Description |
|----------|----------|------|-------------|
| `/ws/ticks` | WebSocket | Yes (query param) | Live price streaming |

**Connection:** `ws://localhost:8000/ws/ticks?token=<jwt>`

## Request/Response Examples

### Create Strategy

```http
POST /api/strategies
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Iron Condor",
  "underlying": "NIFTY",
  "legs": [
    {
      "strike": 24500,
      "expiry": "2024-12-26",
      "contract_type": "CE",
      "transaction_type": "SELL",
      "lots": 1,
      "entry_price": 150.50
    }
  ]
}
```

**Response:**
```json
{
  "id": 123,
  "name": "Iron Condor",
  "underlying": "NIFTY",
  "status": "open",
  "legs": [...]
}
```

### Calculate P/L

```http
POST /api/strategies/calculate
Authorization: Bearer <token>
Content-Type: application/json

{
  "underlying": "NIFTY",
  "mode": "expiry",
  "legs": [...]
}
```

**Response:**
```json
{
  "spot_prices": [24000, 24100, ...],
  "pnl_values": [-5000, -4000, ...],
  "max_profit": 7500,
  "max_loss": -12500,
  "breakevens": [24150, 24850]
}
```

## Error Responses

```json
{
  "detail": "Error message here"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid/expired token |
| 403 | Forbidden - No broker connection |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

## Rate Limits

Currently no rate limiting is enforced. Kite Connect API has its own limits:
- 3 requests/second for most endpoints
- 1 request/second for order placement

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- JSON: http://localhost:8000/openapi.json
- YAML: [openapi.yaml](openapi.yaml) (when exported)

To export OpenAPI spec:
```bash
curl http://localhost:8000/openapi.json > docs/api/openapi.json
```

## Related Documentation

- [Authentication](../architecture/authentication.md) - OAuth flow
- [WebSocket](../architecture/websocket.md) - Live price streaming
- [Troubleshooting](../guides/troubleshooting.md) - Common issues
