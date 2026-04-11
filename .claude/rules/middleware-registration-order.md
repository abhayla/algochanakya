---
description: >
  Enforces correct middleware registration order in the FastAPI application.
  CORS middleware MUST be registered before any routers to prevent blocking legitimate cross-origin requests.
globs: ["backend/app/main.py"]
synthesized: true
private: false
version: "1.0.0"
---

# Middleware Registration Order

In `backend/app/main.py`, middleware MUST be registered in a specific order relative to router includes. FastAPI/Starlette processes middleware in LIFO order (last registered = first executed), and routers are matched after all middleware runs.

## Required Order

```python
# 1. Create FastAPI app
app = FastAPI(lifespan=lifespan)

# 2. Register ALL middleware BEFORE any router includes
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Include routers AFTER middleware
app.include_router(auth_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
# ... all other routers
```

## Why This Order Matters

- CORS middleware registered AFTER routers causes preflight `OPTIONS` requests to hit route handlers that may return 405 Method Not Allowed instead of the correct CORS headers
- Auth middleware (if added later) registered BEFORE CORS would reject preflight requests that carry no authentication token
- Middleware order affects error response formatting — the outermost middleware sees the final response

## MUST Rules

- MUST register `CORSMiddleware` BEFORE any `app.include_router()` calls
- MUST NOT add auth middleware that runs before CORS — preflight requests carry no auth token by design
- MUST keep the `allow_origin_regex=r"http://localhost:\d+"` pattern for local development — do NOT hardcode a single port (frontend uses 5173, tests use various ports)
- When adding new middleware, place it AFTER CORS but BEFORE router includes
- If adding rate-limiting middleware, it MUST run AFTER CORS (so preflight requests aren't rate-limited) and AFTER auth (so rate limits can be per-user)

## Current CORS Configuration

The project uses regex-based origin matching (`localhost:\d+`) rather than a fixed origin list. This supports:
- Frontend dev server (port 5173)
- Backend dev server (port 8001)
- Test runners on dynamic ports
- Production uses a separate CORS config — MUST NOT change the dev regex to a production domain
