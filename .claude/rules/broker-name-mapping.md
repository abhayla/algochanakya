---
description: >
  DB stores zerodha/angelone but BrokerType enum uses kite/angel.
  Always use the broker name mapping utility when converting between formats.
globs: ["backend/**/*.py"]
synthesized: true
private: false
---

# Broker Name Mapping

## The Mismatch

| Context | Zerodha | Angel One |
|---------|---------|-----------|
| `BrokerConnection.broker` (DB) | `"zerodha"` | `"angelone"` |
| `BrokerType` enum | `"kite"` | `"angel"` |
| Frontend display | `"Zerodha"` | `"Angel One"` |

## Why This Exists

The `broker_connections` table stores human-readable broker names (`zerodha`, `angelone`).
The `BrokerType` enum uses SDK names (`kite` for KiteConnect, `angel` for SmartAPI).
These were designed at different times and cannot be changed without a data migration.

## MUST Use Mapping When Converting

When going from DB broker name to adapter:
```python
# Do NOT do: BrokerType(connection.broker)  # ValueError!
# Instead use the mapping utility or explicit conversion
BROKER_NAME_MAP = {
    "zerodha": BrokerType.KITE,
    "angelone": BrokerType.ANGEL,
    "upstox": BrokerType.UPSTOX,
    "dhan": BrokerType.DHAN,
    "fyers": BrokerType.FYERS,
    "paytm": BrokerType.PAYTM,
}
broker_type = BROKER_NAME_MAP[connection.broker]
```

## Common Bug Pattern

This mismatch has caused bugs when:
- Passing `connection.broker` directly to `get_broker_adapter()` — fails with ValueError
- Comparing BrokerType enum values against DB strings — never matches
- Frontend sends display name instead of DB name to API

