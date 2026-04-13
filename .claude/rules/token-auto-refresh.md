# Token Auto-Refresh Rule

## When Adding a New Broker Adapter

1. MUST add an entry to `backend/app/services/brokers/market_data/ticker/token_policy.py`
2. MUST classify ALL known error codes for the broker in `_BROKER_ERRORS` tables
3. MUST specify whether broker can auto-refresh (add to `_AUTO_REFRESHABLE_BROKERS` if yes)
4. MUST add frontend notification message in `get_frontend_notification()` if NOT_REFRESHABLE

## Error Classification Categories

| Category | Meaning | Action |
|----------|---------|--------|
| `RETRYABLE` | Transient failure, 3x exponential backoff | Pool retries automatically |
| `RETRYABLE_ONCE` | TOTP wait + 1 retry | 30s delay then single retry |
| `NOT_RETRYABLE` | Config error (wrong API key) | Instant failover |
| `NOT_REFRESHABLE` | Can't auto-refresh (OAuth/static token) | Instant failover + frontend notification |

## Auto-Refreshable Brokers

| Broker | Mechanism | Key File |
|--------|-----------|----------|
| AngelOne (smartapi) | pyotp TOTP + refresh_token | `platform_token_refresh.py` |
| Upstox | upstox-totp library | `platform_token_refresh.py` |

## NOT_REFRESHABLE Brokers

| Broker | Why | User Action |
|--------|-----|-------------|
| Kite (zerodha) | OAuth flow requires browser | Re-login via Kite OAuth |
| Dhan | Static token from portal | Regenerate from Dhan portal |
| Fyers | OAuth flow requires browser | Re-login via Fyers OAuth |
| Paytm | Portal authentication broken | Re-login from Paytm Money portal |

## MUST NOT

- MUST NOT add a broker adapter without classifying its error codes in `token_policy.py`
- MUST NOT mark a broker as auto-refreshable unless the refresh flow is implemented and tested
- MUST NOT skip the `NOT_REFRESHABLE` frontend notification — users need to know why data stopped
