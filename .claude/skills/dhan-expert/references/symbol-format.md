# Dhan Symbol Format and Instrument Identification

## Overview

Dhan uses **numeric `security_id`** values to identify instruments. Unlike Zerodha (which uses
trading symbols like `NIFTY24FEB24000CE`) or Angel One (which uses symbolic names), Dhan
requires a numeric integer for every API call.

This means **canonical symbol conversion requires a full mapping table** loaded from Dhan's
instrument CSV file.

---

## security_id

| Property          | Value                                            |
|-------------------|--------------------------------------------------|
| Type              | Integer (passed as string in some endpoints)     |
| Uniqueness        | Unique per instrument within an exchange segment |
| Stability         | May change across expiry rollovers for F&O       |
| Example (Equity)  | `1333` (HDFC Bank on NSE)                        |
| Example (F&O)     | `43854` (NIFTY option)                           |
| Example (Index)   | `13` (NIFTY 50 index)                            |

**Important:** The same underlying may have different security_ids across exchange segments.
For example, Reliance on NSE_EQ has a different security_id than Reliance on BSE_EQ.

---

## Exchange Segments

Dhan uses string identifiers for exchange segments in REST API calls and numeric bytes in
WebSocket binary frames.

| Segment String   | Byte Value | Description                     | Examples                    |
|------------------|------------|---------------------------------|-----------------------------|
| `NSE_EQ`         | 0          | NSE Equity (Cash)               | HDFCBANK, RELIANCE, TCS    |
| `NSE_FNO`        | 1          | NSE Futures & Options           | NIFTY options, stock F&O   |
| `NSE_CURRENCY`   | 2          | NSE Currency Derivatives        | USDINR futures              |
| `BSE_EQ`         | 3          | BSE Equity (Cash)               | BSE-listed equities         |
| `BSE_FNO`        | 4          | BSE Futures & Options           | SENSEX options              |
| `BSE_CURRENCY`   | 5          | BSE Currency Derivatives        | USDINR on BSE               |
| `MCX_COMM`       | 6          | MCX Commodity                   | CRUDEOIL, GOLD, SILVER     |
| `IDX_I`          | 7          | Index (non-tradable, data only) | NIFTY 50, BANKNIFTY, SENSEX|

### Segment Usage in API Calls

```python
# REST API -- use string format
payload = {
    "exchangeSegment": "NSE_FNO",
    "securityId": "43854",
}

# WebSocket subscription -- use string format in JSON
subscribe_msg = {
    "RequestCode": 21,
    "InstrumentCount": 1,
    "InstrumentList": [
        {"ExchangeSegment": "NSE_FNO", "SecurityId": "43854"}
    ]
}

# WebSocket binary response -- decode byte to segment
exchange_byte = struct.unpack('<B', data[2:3])[0]
segment = EXCHANGE_MAP[exchange_byte]  # e.g., 1 -> "NSE_FNO"
```

---

## Instrument CSV Download

Dhan provides a daily-updated CSV file with all tradable instruments. This file is the
**only way** to resolve trading symbols to security_ids.

### Download URL

```
https://images.dhan.co/api-data/api-scrip-master.csv
```

### CSV Schema

| Column              | Type    | Description                                    | Example                     |
|---------------------|---------|------------------------------------------------|-----------------------------|
| `SEM_EXM_EXCH_ID`  | String  | Exchange code                                  | `NSE`, `BSE`, `MCX`        |
| `SEM_SEGMENT`      | String  | Segment type                                   | `E` (Equity), `D` (Deriv)  |
| `SEM_SMST_SECURITY_ID` | Integer | The security_id used in API calls          | `1333`                      |
| `SEM_INSTRUMENT_NAME` | String | Instrument type                               | `EQUITY`, `OPTIDX`, `FUTIDX` |
| `SEM_TRADING_SYMBOL` | String | Exchange trading symbol                        | `HDFCBANK`, `NIFTY-Feb2026-24000-CE` |
| `SEM_LOT_UNITS`    | String  | Lot size unit                                  | `SHARES`, `LOTS`            |
| `SEM_CUSTOM_SYMBOL` | String | Dhan's formatted display symbol                | `NIFTY 26 FEB 24000 CE`    |
| `SEM_EXPIRY_DATE`  | String  | Expiry date (F&O only)                         | `2026-02-27`                |
| `SEM_STRIKE_PRICE`  | Float  | Strike price (options only)                    | `24000.0`                   |
| `SEM_OPTION_TYPE`   | String | `CE` (Call) or `PE` (Put), options only        | `CE`                        |
| `SEM_TICK_SIZE`     | Float  | Minimum price movement                         | `0.05`                      |
| `SEM_LOT_SIZE`      | Integer| Contract lot size                              | `25` (NIFTY), `15` (BANKNIFTY) |
| `SEM_EXPIRY_FLAG`   | String | Expiry type                                    | `W` (Weekly), `M` (Monthly)|

### Download and Parse Script

```python
import pandas as pd
import requests
from io import StringIO

INSTRUMENT_CSV_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"

def download_instruments() -> pd.DataFrame:
    """Download and parse Dhan instrument master CSV."""
    response = requests.get(INSTRUMENT_CSV_URL, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    return df

def filter_nse_fno(df: pd.DataFrame) -> pd.DataFrame:
    """Filter for NSE F&O instruments only."""
    return df[
        (df["SEM_EXM_EXCH_ID"] == "NSE") &
        (df["SEM_SEGMENT"] == "D") &
        (df["SEM_INSTRUMENT_NAME"].isin(["OPTIDX", "FUTIDX", "OPTSTK", "FUTSTK"]))
    ]

def filter_nse_equity(df: pd.DataFrame) -> pd.DataFrame:
    """Filter for NSE Equity instruments only."""
    return df[
        (df["SEM_EXM_EXCH_ID"] == "NSE") &
        (df["SEM_SEGMENT"] == "E") &
        (df["SEM_INSTRUMENT_NAME"] == "EQUITY")
    ]
```

### Instrument Data Refresh Schedule

| Aspect                 | Detail                                          |
|------------------------|-------------------------------------------------|
| Update Frequency       | Daily (before market open, ~8:30 AM IST)        |
| F&O Expiry Changes     | New contracts added, expired contracts removed   |
| Recommended Refresh    | Daily at startup or via scheduled cron job       |
| Cache Duration         | Until next trading day                           |
| File Size              | ~15-25 MB (all instruments across all segments)  |

---

## Canonical Symbol Conversion

AlgoChanakya uses **canonical format** (Kite-style symbols) internally. Converting between
canonical symbols and Dhan's security_ids requires the instrument mapping table.

### Canonical Format (AlgoChanakya Internal)

```
# Equity
HDFCBANK        -> security_id: 1333, segment: NSE_EQ
RELIANCE        -> security_id: 2885, segment: NSE_EQ

# Index (data only)
NIFTY 50        -> security_id: 13, segment: IDX_I
NIFTY BANK      -> security_id: 25, segment: IDX_I

# Options (Kite format: SYMBOL + YYMDD + STRIKE + TYPE)
NIFTY24FEB24000CE  -> security_id: 43854, segment: NSE_FNO
BANKNIFTY24FEB51000PE -> security_id: 44102, segment: NSE_FNO

# Futures
NIFTY24FEBFUT   -> security_id: 42001, segment: NSE_FNO
```

### SymbolConverter Implementation

```python
from app.services.brokers.market_data.symbol_converter import SymbolConverter

class DhanSymbolConverter(SymbolConverter):
    """Convert between canonical symbols and Dhan security_ids."""

    def __init__(self):
        self._canonical_to_dhan: dict[str, dict] = {}  # canonical -> {security_id, segment}
        self._dhan_to_canonical: dict[str, str] = {}   # "segment:security_id" -> canonical

    async def load_instruments(self):
        """Load instrument mapping from CSV or database."""
        # Option 1: From CSV
        df = download_instruments()

        for _, row in df.iterrows():
            canonical = self._to_canonical(row)
            if canonical:
                security_id = str(row["SEM_SMST_SECURITY_ID"])
                segment = self._map_segment(row)
                self._canonical_to_dhan[canonical] = {
                    "security_id": security_id,
                    "exchange_segment": segment,
                }
                self._dhan_to_canonical[f"{segment}:{security_id}"] = canonical

    def canonical_to_broker(self, canonical_symbol: str) -> dict:
        """Convert canonical symbol to Dhan security_id + segment."""
        result = self._canonical_to_dhan.get(canonical_symbol)
        if not result:
            raise InstrumentNotFoundError(
                broker="dhan",
                message=f"No Dhan mapping for {canonical_symbol}",
            )
        return result

    def broker_to_canonical(self, security_id: str, segment: str) -> str:
        """Convert Dhan security_id + segment to canonical symbol."""
        key = f"{segment}:{security_id}"
        result = self._dhan_to_canonical.get(key)
        if not result:
            raise InstrumentNotFoundError(
                broker="dhan",
                message=f"No canonical mapping for {key}",
            )
        return result

    def _to_canonical(self, row: pd.Series) -> str | None:
        """Convert a Dhan instrument row to canonical symbol format."""
        instrument = row["SEM_INSTRUMENT_NAME"]

        if instrument == "EQUITY":
            return row["SEM_TRADING_SYMBOL"]

        elif instrument in ("OPTIDX", "OPTSTK"):
            # Parse: NIFTY-Feb2026-24000-CE -> NIFTY26FEB24000CE
            parts = row["SEM_TRADING_SYMBOL"].split("-")
            if len(parts) >= 4:
                name = parts[0]
                expiry = self._format_expiry(row["SEM_EXPIRY_DATE"])
                strike = str(int(float(row["SEM_STRIKE_PRICE"])))
                opt_type = row["SEM_OPTION_TYPE"]
                return f"{name}{expiry}{strike}{opt_type}"

        elif instrument in ("FUTIDX", "FUTSTK"):
            # Parse: NIFTY-Feb2026 -> NIFTY26FEBFUT
            parts = row["SEM_TRADING_SYMBOL"].split("-")
            if len(parts) >= 2:
                name = parts[0]
                expiry = self._format_expiry(row["SEM_EXPIRY_DATE"])
                return f"{name}{expiry}FUT"

        return None

    def _format_expiry(self, expiry_str: str) -> str:
        """Convert 2026-02-27 to 26FEB or 260227 format."""
        from datetime import datetime
        dt = datetime.strptime(expiry_str, "%Y-%m-%d")
        return dt.strftime("%y%b").upper()  # e.g., "26FEB"

    def _map_segment(self, row: pd.Series) -> str:
        """Map CSV columns to Dhan exchange segment string."""
        exchange = row["SEM_EXM_EXCH_ID"]
        segment = row["SEM_SEGMENT"]

        if exchange == "NSE" and segment == "E":
            return "NSE_EQ"
        elif exchange == "NSE" and segment == "D":
            return "NSE_FNO"
        elif exchange == "BSE" and segment == "E":
            return "BSE_EQ"
        elif exchange == "BSE" and segment == "D":
            return "BSE_FNO"
        elif exchange == "MCX":
            return "MCX_COMM"
        return "NSE_EQ"  # default
```

---

## TokenManager Integration

### Storing Dhan Tokens in broker_instrument_tokens

```python
from app.services.brokers.market_data.token_manager import token_manager

# During instrument sync (daily job)
async def sync_dhan_instruments(db_session):
    """Sync Dhan instruments to broker_instrument_tokens table."""
    df = download_instruments()
    nse_fno = filter_nse_fno(df)

    for _, row in nse_fno.iterrows():
        canonical = converter._to_canonical(row)
        if canonical:
            await token_manager.upsert_mapping(
                db_session,
                canonical_symbol=canonical,
                broker="dhan",
                broker_symbol=row["SEM_TRADING_SYMBOL"],
                broker_token=str(row["SEM_SMST_SECURITY_ID"]),
                exchange_segment=converter._map_segment(row),
                expiry=row.get("SEM_EXPIRY_DATE"),
                strike_price=row.get("SEM_STRIKE_PRICE"),
                option_type=row.get("SEM_OPTION_TYPE"),
                lot_size=row.get("SEM_LOT_SIZE"),
            )
```

### Quick Lookup Examples

```python
# Canonical to Dhan security_id
dhan_token = await token_manager.get_broker_token("NIFTY26FEB24000CE", "dhan")
# Returns: "43854"

# Dhan security_id to canonical
canonical = await token_manager.get_canonical_symbol("43854", "dhan")
# Returns: "NIFTY26FEB24000CE"

# Batch lookup for WebSocket subscription
tokens = await token_manager.get_broker_tokens(
    ["NIFTY26FEB24000CE", "NIFTY26FEB24000PE", "HDFCBANK"],
    broker="dhan",
)
# Returns: [
#   {"canonical": "NIFTY26FEB24000CE", "security_id": "43854", "segment": "NSE_FNO"},
#   {"canonical": "NIFTY26FEB24000PE", "security_id": "43855", "segment": "NSE_FNO"},
#   {"canonical": "HDFCBANK", "security_id": "1333", "segment": "NSE_EQ"},
# ]
```

---

## Common Index security_ids

| Index           | security_id | Exchange Segment | Notes              |
|-----------------|-------------|------------------|--------------------|
| NIFTY 50        | 13          | IDX_I            | NSE benchmark      |
| NIFTY BANK      | 25          | IDX_I            | Bank NIFTY         |
| NIFTY FIN SVC   | 27          | IDX_I            | Financial services  |
| SENSEX          | 51          | IDX_I            | BSE benchmark      |
| BANKEX          | 52          | IDX_I            | BSE bank index     |
| INDIA VIX       | 26          | IDX_I            | Volatility index   |

**Note:** Index security_ids are typically stable and do not change. F&O security_ids change
with each new expiry series.

---

## Comparison: Symbol Formats Across Brokers

| Aspect              | Dhan                    | Zerodha Kite              | Angel SmartAPI            |
|---------------------|-------------------------|---------------------------|---------------------------|
| Primary ID          | `security_id` (numeric) | `instrument_token` (num)  | `symboltoken` (string)    |
| Symbol Format       | `NIFTY-Feb2026-24000-CE`| `NIFTY26FEB24000CE`       | `NIFTY26FEB2426000CE`     |
| Instrument File     | CSV (daily download)    | CSV (daily download)      | JSON API (daily download) |
| File URL            | images.dhan.co/api-data/| api.kite.trade/instruments| api.angelone.in/instruments|
| Exchange in API     | `NSE_FNO` (string)      | `NFO` (string)            | `NFO` (string)            |
| File Size           | ~15-25 MB               | ~10-15 MB                 | ~20-30 MB                 |
| Update Time         | ~8:30 AM IST            | ~8:00 AM IST              | ~8:00 AM IST              |

---

## Gotchas and Edge Cases

1. **security_id as string vs integer:** Some Dhan endpoints accept `"43854"` (string) while
   others require `43854` (integer). The subscription JSON uses strings. Always check endpoint docs.

2. **Weekly vs monthly expiry:** Both have different security_ids. Weekly options expire Thursday,
   monthly on last Thursday. Use `SEM_EXPIRY_FLAG` to distinguish (`W` vs `M`).

3. **BSE vs NSE same underlying:** The same stock (e.g., RELIANCE) has different security_ids on
   NSE_EQ vs BSE_EQ. Always pair security_id with the correct exchange segment.

4. **Instrument CSV encoding:** The CSV file uses UTF-8. Some commodity names may contain special
   characters. Use `encoding="utf-8"` when reading.

5. **security_id reuse:** Expired F&O contracts' security_ids may be reused for new contracts
   in future. Always use the latest instrument file.

6. **Index instruments are non-tradable:** `IDX_I` segment instruments are for market data only.
   You cannot place orders on index instruments -- use `NSE_FNO` for index F&O.
