# Dhan Authentication Flow

## Overview

Dhan uses a **simple API token** model. There is no OAuth flow, no TOTP, and no session-based
authentication. Users generate a long-lived access token from the Dhan web dashboard, and all
API requests include this token in the `access-token` HTTP header.

This is the simplest auth model among all supported brokers in AlgoChanakya.

---

## Token Lifecycle

| Property            | Value                                              |
|---------------------|----------------------------------------------------|
| Token Type          | Static API access token                            |
| Generation          | Manual, via Dhan web dashboard                     |
| Expiry              | Long-lived (typically valid until revoked or regenerated) |
| Refresh Mechanism   | None required; generate new token from dashboard   |
| Revocation          | Regenerate token from dashboard (old token invalidated) |
| Multi-token Support | One active token per application/client_id         |

---

## Obtaining the Access Token

### Step 1: Register as API User

1. Log in to [Dhan web portal](https://web.dhan.co)
2. Navigate to **Profile > API Access** (or **My Account > API & Integrations**)
3. Register for API access (one-time)
4. Note your **Client ID** (Dhan UID, numeric)

### Step 2: Generate Access Token

1. In the API section, click **Generate Token**
2. Select permissions/scopes if prompted
3. Copy the generated token immediately (shown only once)
4. Store securely -- this is equivalent to a password

### Step 3: Use in API Requests

All authenticated requests require two headers:

```
access-token: {your_access_token}
Content-Type: application/json
```

The `client-id` is sometimes required as a separate field in request bodies (not as a header).

---

## Authentication Headers

### Required Headers for All Authenticated Requests

| Header         | Value                  | Required |
|----------------|------------------------|----------|
| `access-token` | The API access token   | Yes      |
| `Content-Type` | `application/json`     | Yes (for POST/PUT) |

### Example: Authenticated Request

```python
import requests

DHAN_BASE_URL = "https://api.dhan.co/v2"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOi..."  # From dashboard

headers = {
    "access-token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}

# Get fund limits
response = requests.get(f"{DHAN_BASE_URL}/fundlimit", headers=headers)
print(response.json())
```

### Example: Using aiohttp (Async)

```python
import aiohttp

async def get_fund_limits(access_token: str) -> dict:
    headers = {
        "access-token": access_token,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.dhan.co/v2/fundlimit",
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
```

---

## AlgoChanakya Integration

### Credential Storage

Dhan credentials are stored in the `broker_credentials` table (or a dedicated `dhan_credentials` table):

| Column         | Type    | Description                              |
|----------------|---------|------------------------------------------|
| `user_id`      | Integer | FK to users table                        |
| `client_id`    | String  | Dhan numeric UID                         |
| `access_token` | String  | Encrypted API token (use `encrypt()`)    |
| `created_at`   | DateTime| When credentials were stored             |
| `updated_at`   | DateTime| Last update timestamp                    |

### Encryption

Always encrypt the access token before storing:

```python
from app.utils.encryption import encrypt, decrypt

# Store
encrypted_token = encrypt(raw_access_token)

# Retrieve
raw_token = decrypt(encrypted_token)
```

### Adapter Authentication

The `DhanAdapter` (both market data and order execution) receives credentials at construction:

```python
from app.services.brokers.factory import get_broker_adapter
from app.services.brokers.market_data.factory import get_market_data_adapter

# Order execution
order_adapter = get_broker_adapter("dhan", {
    "client_id": "1234567890",
    "access_token": "eyJ0eXAiOiJKV1Q...",
})

# Market data
data_adapter = get_market_data_adapter("dhan", {
    "client_id": "1234567890",
    "access_token": "eyJ0eXAiOiJKV1Q...",
})
```

### Token Validation

Dhan does not have a dedicated "validate token" endpoint. To verify a token is valid,
make a lightweight call to the profile or fund limit endpoint:

```python
async def validate_dhan_token(access_token: str) -> bool:
    """Validate Dhan access token by calling a lightweight endpoint."""
    headers = {"access-token": access_token}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.dhan.co/v2/fundlimit",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except Exception:
        return False
```

---

## Comparison with Other Brokers

| Feature             | Dhan              | Zerodha (Kite)       | Angel One (SmartAPI)   |
|---------------------|-------------------|----------------------|------------------------|
| Auth Type           | Static API token  | OAuth 2.0            | Client + MPIN + TOTP   |
| Token Expiry        | Long-lived        | 1 day (midnight)     | ~8 hours               |
| Refresh Required    | No                | Daily re-login       | Auto-TOTP refresh      |
| Setup Complexity    | Very simple       | Moderate (OAuth)     | Moderate (TOTP setup)  |
| Headers             | `access-token`    | `Authorization`      | `Authorization`        |
| Monthly API Cost    | FREE              | Rs 500/month (data)  | FREE                   |

---

## Error Handling for Auth

| HTTP Status | Meaning                          | Action                               |
|-------------|----------------------------------|--------------------------------------|
| 401         | Invalid or expired token         | Prompt user to regenerate token      |
| 403         | Token lacks required permissions | Check API permissions on dashboard   |
| 429         | Rate limit exceeded              | Implement backoff (see error-codes)  |

### AlgoChanakya Exception Mapping

```python
from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

def handle_dhan_auth_error(status_code: int, response_body: dict) -> None:
    if status_code == 401:
        raise AuthenticationError(
            broker="dhan",
            message="Dhan access token is invalid or expired. "
                    "Please regenerate from the Dhan dashboard.",
        )
    elif status_code == 403:
        raise PermissionDeniedError(
            broker="dhan",
            message="Dhan token lacks required permissions.",
        )
    elif status_code == 429:
        raise RateLimitError(
            broker="dhan",
            message="Dhan API rate limit exceeded.",
        )
```

---

## Security Considerations

1. **Never log the access token** -- even partially. Use `token[:8]...` for debugging at most.
2. **Always encrypt at rest** using `app.utils.encryption`.
3. **Do not embed tokens in URLs** -- Dhan uses headers, not query parameters.
4. **Rotate tokens periodically** -- even though they are long-lived, encourage users to regenerate.
5. **Single token per app** -- regenerating invalidates the previous token. Warn users in the UI.
