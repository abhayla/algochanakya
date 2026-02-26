# Dhan Trader's Control Reference

> Source: Dhan API v2 Docs (https://dhanhq.co/docs/v2/traders-control/) | Last verified: 2026-02-26

## Overview

Trader's Control provides two risk management APIs:

1. **Kill Switch** — Disables ALL trading for the remainder of the current trading day
2. **P&L Exit** — Automatically exits all positions when a profit or loss threshold is hit

Both are session-scoped (reset at end of trading day).

---

## 1. Kill Switch

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/killswitch?killSwitchStatus=ACTIVATE` | Disable all trading |
| POST | `/v2/killswitch?killSwitchStatus=DEACTIVATE` | Re-enable trading |
| GET | `/v2/killswitch` | Check current status |

No request body needed. The status is a **query parameter**.

### Activate Kill Switch

```
POST https://api.dhan.co/v2/killswitch?killSwitchStatus=ACTIVATE
```

**CRITICAL PREREQUISITE:** All positions must be closed AND no pending orders before calling ACTIVATE.

If there are open positions/orders, the API will fail. Required sequence:
1. `DELETE /v2/orders/{id}` for all pending orders
2. Wait for confirmations (or use `GET /v2/orders` to verify)
3. Exit all open positions (place opposite orders)
4. Wait for positions to close
5. `POST /v2/killswitch?killSwitchStatus=ACTIVATE`

**Response on success:**
```json
{
  "dhanClientId": "1000000003",
  "killSwitchStatus": "Kill Switch has been successfully activated"
}
```

### Deactivate Kill Switch

```
POST https://api.dhan.co/v2/killswitch?killSwitchStatus=DEACTIVATE
```

**Response:**
```json
{
  "dhanClientId": "1000000003",
  "killSwitchStatus": "Kill Switch has been successfully deactivated"
}
```

### Get Kill Switch Status

```
GET https://api.dhan.co/v2/killswitch
```

**Response:**
```json
{
  "dhanClientId": "1000000003",
  "killSwitchStatus": "ACTIVATE"
}
```

**Status values:** `ACTIVATE` or `DEACTIVATE`

---

## 2. P&L Based Exit

Automatically exits all open positions when either a profit or loss threshold is reached.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/pnlExit` | Configure thresholds and activate |
| DELETE | `/v2/pnlExit` | Stop P&L exit |
| GET | `/v2/pnlExit` | Get current configuration |

### Configure P&L Exit

**POST** `/v2/pnlExit`

```json
{
  "profitValue": 5000.00,
  "lossValue": 2000.00,
  "productType": ["INTRADAY", "DELIVERY"],
  "enableKillSwitch": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `profitValue` | float | Profit threshold (positions exit when P&L ≥ this value) |
| `lossValue` | float | Loss threshold (positions exit when P&L ≤ negative of this value) |
| `productType` | string[] | Which product types to monitor: `"INTRADAY"`, `"DELIVERY"` |
| `enableKillSwitch` | boolean | If `true`, also activates Kill Switch after P&L exit completes |

**WARNING:** If `profitValue` is set below the current unrealized P&L at the time of the API call, **exit triggers immediately**. Always verify current P&L before setting thresholds.

**Response on success:**
```json
{
  "pnlExitStatus": "ACTIVE",
  "profitValue": 5000.00,
  "lossValue": 2000.00,
  "productType": ["INTRADAY", "DELIVERY"],
  "enableKillSwitch": true
}
```

### Stop P&L Exit

**DELETE** `/v2/pnlExit`

```json
{
  "pnlExitStatus": "DISABLED",
  "message": "P&L based exit stopped successfully"
}
```

### Get P&L Exit Status

**GET** `/v2/pnlExit`

```json
{
  "pnlExitStatus": "ACTIVE",
  "profit": 5000.00,
  "loss": 2000.00,
  "productType": ["INTRADAY"],
  "enable_kill_switch": true
}
```

**Note:** Response field is `enable_kill_switch` (snake_case) vs request field `enableKillSwitch` (camelCase). Handle both.

---

## Combined Usage: Kill Switch + P&L Exit

The most common pattern is to chain P&L Exit → Kill Switch:

```python
# Set P&L exit with auto kill switch
payload = {
    "profitValue": 10000.00,   # Exit all positions if profit >= 10k
    "lossValue": 5000.00,      # Exit all positions if loss >= 5k
    "productType": ["INTRADAY"],
    "enableKillSwitch": True   # Also activate kill switch after exit
}
response = await dhan.post("/v2/pnlExit", json=payload)
```

With `enableKillSwitch: true`, when the threshold is hit:
1. All matching positions are automatically exited
2. Kill switch activates, preventing further order placement

---

## AlgoChanakya Integration

- Trader's Control APIs are **NOT yet integrated** into AlgoChanakya
- Planned integration: AutoPilot risk management module
- Kill Switch would be mapped to AutoPilot's existing kill switch concept (`backend/app/services/autopilot/kill_switch.py`)
- P&L Exit could enhance AutoPilot's daily loss limit feature

### Proposed Implementation

```python
# backend/app/services/brokers/dhan_order_adapter.py (future)

async def activate_kill_switch(self) -> dict:
    """Activate Dhan kill switch. Requires all positions closed first."""
    response = await self._client.post(
        "/killswitch",
        params={"killSwitchStatus": "ACTIVATE"},
        headers=self._auth_headers,
    )
    response.raise_for_status()
    return response.json()

async def set_pnl_exit(
    self,
    profit_target: float,
    loss_limit: float,
    product_types: list[str],
    activate_kill_switch: bool = True,
) -> dict:
    """Configure Dhan P&L-based auto-exit."""
    # Safety check: warn if profitValue < current unrealized P&L
    payload = {
        "profitValue": profit_target,
        "lossValue": loss_limit,
        "productType": product_types,
        "enableKillSwitch": activate_kill_switch,
    }
    response = await self._client.post("/pnlExit", json=payload, headers=self._auth_headers)
    response.raise_for_status()
    return response.json()
```

---

## Important Notes

1. **Session-scoped**: Both Kill Switch and P&L Exit reset at end of trading day (midnight IST).
2. **No body on Kill Switch POST**: Pass only the query parameter `killSwitchStatus`.
3. **P&L Exit is for all positions**: You cannot target individual instruments — it exits all positions matching the product types.
4. **P&L Exit immediate trigger**: Setting `profitValue` below current P&L triggers exit on the API call itself. This is not a bug.
5. **Kill Switch prerequisite**: No pending orders + no open positions before calling ACTIVATE.
6. **Broker-level, not app-level**: The kill switch operates at the broker level — even if AlgoChanakya is down, the kill switch remains active at Dhan.
