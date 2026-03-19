"""
Broker availability constants.

ORG_ACTIVE_BROKERS defines which brokers have active org-level API access
(platform-wide market data, failover chain, live tests).

Rules for adding a broker here:
- Must have a free or paid org-level API (not just a personal user account)
- Credentials must be configured in backend/.env
- Must be verified working for live market data

Current status:
- angelone  ✅ Active (free org API, primary)
- upstox    ✅ Active (free org API, secondary — verified 2026-03-19)
- kite      ❌ Paid API — not active at org level
- dhan      ❌ Paid API — not active at org level
- fyers     ❌ Not working
- paytm     ❌ Not working
"""

# Brokers with active org-level market data API access.
# This is the single source of truth used by:
#   - FailoverController (primary/secondary broker selection)
#   - Live integration tests (parametrize scope)
#   - Any service that needs to know which brokers are org-active
ORG_ACTIVE_BROKERS = ["angelone", "upstox"]

# All brokers with adapter implementations (including user-level / paid)
ALL_BROKERS = ["angelone", "kite", "upstox", "dhan", "fyers", "paytm"]
