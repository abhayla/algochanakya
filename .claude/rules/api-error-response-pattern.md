---
description: >
  Routes catch domain exceptions and return HTTPException; services raise only domain exceptions,
  never HTTPException. Enforces clean separation between HTTP transport and business logic.
globs: ["backend/app/api/**/*.py", "backend/app/services/**/*.py"]
synthesized: true
private: false
---

# API Error Response Pattern

## Service Layer: Domain Exceptions Only

Services MUST raise domain-specific exceptions from `app.services.brokers.market_data.exceptions`
or standard Python exceptions. Services MUST NOT import or raise `HTTPException`.

```python
# CORRECT — service raises domain exception:
from app.services.brokers.market_data.exceptions import BrokerAPIError, InvalidSymbolError

class OptionChainService:
    async def get_chain(self, symbol: str, db: AsyncSession):
        if not self._validate_symbol(symbol):
            raise InvalidSymbolError(f"Invalid symbol: {symbol}")
        # ...

# WRONG — service raises HTTPException:
from fastapi import HTTPException
class OptionChainService:
    async def get_chain(self, symbol: str, db: AsyncSession):
        raise HTTPException(status_code=400, detail="Bad symbol")  # NEVER
```

## Route Layer: Exception Mapping

Routes MUST catch domain exceptions and map them to appropriate HTTP status codes.
Use the standard try/except pattern with re-raise for existing HTTPExceptions:

```python
@router.get("/optionchain/{symbol}")
async def get_option_chain(symbol: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await option_chain_service.get_chain(symbol, db)
        return result
    except HTTPException:
        raise  # Re-raise HTTP exceptions from dependencies
    except InvalidSymbolError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BrokerAPIError as e:
        raise HTTPException(status_code=502, detail=f"Broker error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
```

## Domain Exception Hierarchy

All market data exceptions inherit from `MarketDataError` in
`app/services/brokers/market_data/exceptions.py`:

| Exception | HTTP Status | When |
|-----------|-------------|------|
| `InvalidSymbolError` | 400 | Bad symbol format or unknown instrument |
| `AuthenticationError` | 401 | Broker credential expired/invalid |
| `RateLimitError` | 429 | Broker API rate limit hit |
| `DataNotAvailableError` | 404 | No data for requested instrument |
| `BrokerAPIError` | 502 | Upstream broker returned error |
| `ConnectionError` | 503 | Cannot reach broker API |
| `SubscriptionError` | 500 | WebSocket subscription failed |

## Why This Matters

- Services remain testable without FastAPI — no HTTP dependency in business logic
- Exception mapping is centralized in routes — consistent error responses
- New brokers can raise domain exceptions without knowing about HTTP
- Error handling is explicit and auditable per route

## MUST NOT

- MUST NOT let bare `Exception` propagate to FastAPI's default handler — always wrap in HTTPException
- MUST NOT put business logic in the exception handler — keep it to mapping only
- MUST NOT catch and swallow exceptions silently — always log before re-raising
