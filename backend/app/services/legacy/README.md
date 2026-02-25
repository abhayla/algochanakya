# Legacy Services (ARCHIVED)

These services are superseded by the broker abstraction layer and should NOT be used directly.

| File | Superseded By | Status |
|------|--------------|--------|
| `smartapi_auth.py` | Broker auth routes (`auth.py`) | Still used for auto-TOTP credential lookup |
| `smartapi_historical.py` | `brokers/market_data/smartapi_adapter.py` | May still be referenced by AI module |
| `smartapi_market_data.py` | `brokers/market_data/smartapi_adapter.py` | Deprecated |
| `smartapi_instruments.py` | `brokers/market_data/token_manager.py` | Deprecated |
| `kite_orders.py` | `brokers/kite_adapter.py` | Deprecated |
| `market_data.py` | `brokers/market_data/factory.py` | Deprecated |

**Do NOT add new code here.** Use broker adapters via factories instead.

**Cleanup plan:** Remove these files once all references are migrated to the abstraction layer. Check for imports before deletion.
