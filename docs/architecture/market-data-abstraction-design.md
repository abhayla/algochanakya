# Market Data Broker Abstraction - Part 1: Design & Specification

**Document:** Part 1 of 3 - Design & Architecture
**Version:** 2.0
**Last Updated:** 2025-01-14

---

## Overview

This document provides the **design specification** for the Market Data Broker Abstraction Layer in AlgoChanakya. It covers how users select their market data source, how data flows to every screen, how option symbols are normalized across brokers, and how data types are unified.

**Goal:** User changes market data broker in Settings → ALL screens automatically use new broker with ZERO code changes.

**Related Documents:**
- [Part 2: Code Specifications](./market-data-abstraction-code-specs.md) - Data models, database schema, interfaces
- [Part 3: Implementation Guide](./market-data-abstraction-implementation.md) - Frontend/backend code, roadmap
- [Broker Abstraction Architecture](./broker-abstraction.md) - Overall multi-broker system
- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) - Decision rationale

---

## Table of Contents

1. [User Broker Selection Flow](#1-user-broker-selection-flow)
2. [Option Symbol Format by Broker](#2-option-symbol-format-by-broker)
3. [Canonical Symbol & Normalization](#3-canonical-symbol--normalization)
4. [Data Type Normalization](#4-data-type-normalization)
5. [Screen-to-Data Field Mapping](#5-screen-to-data-field-mapping)
6. [Market Data Adapter Interface](#6-market-data-adapter-interface)
7. [Complete Data Flow Diagram](#7-complete-data-flow-diagram)

---

## 1. USER BROKER SELECTION FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         USER SELECTS MARKET DATA BROKER                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  SETTINGS PAGE (frontend/src/views/SettingsView.vue)                                    │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  Market Data Source                                                                 │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │  ○ Angel One (SmartAPI) - FREE                        [DEFAULT]             │   │ │
│  │  │  ○ Zerodha (Kite Connect) - ₹500/month                                      │   │ │
│  │  │  ○ Upstox - FREE                                                            │   │ │
│  │  │  ○ Dhan - FREE (25 F&O trades/mo) or ₹499/mo                               │   │ │
│  │  │  ○ Paytm Money - FREE                                                       │   │ │
│  │  │  ○ Fyers - FREE                                                             │   │ │
│  │  └─────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                     │ │
│  │  [Save] [Test Connection]                                                           │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  DATABASE: users table                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │  id  │  email              │  market_data_broker  │  order_broker  │  ...          │ │
│  │──────┼─────────────────────┼──────────────────────┼────────────────┼───────────────│ │
│  │  1   │  user@example.com   │  "angel"             │  "zerodha"     │  ...          │ │
│  │  2   │  trader@gmail.com   │  "upstox"            │  "dhan"        │  ...          │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  BACKEND: Factory reads user preference and returns correct adapter                     │
│                                                                                          │
│  async def get_market_data_adapter(user: User) -> MarketDataBrokerAdapter:              │
│      broker_type = user.market_data_broker  # "angel", "upstox", "dhan", etc.           │
│      credentials = await get_broker_credentials(user.id, broker_type)                   │
│      return _MARKET_DATA_ADAPTERS[broker_type](credentials)                             │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. OPTION SYMBOL FORMAT BY BROKER

### 2.1 Symbol Format Comparison Table

For **NIFTY 25000 CE expiring April 24, 2025**:

| Broker | Symbol Format | Example |
|--------|---------------|---------|
| **Zerodha (Monthly)** | `{UNDERLYING}{YY}{MMM}{STRIKE}{CE\|PE}` | `NIFTY25APR25000CE` |
| **Zerodha (Weekly)** | `{UNDERLYING}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NIFTY2542425000CE` |
| **Angel One** | `{UNDERLYING}{DD}{MMM}{YY}{STRIKE}{CE\|PE}` | `NIFTY24APR2525000CE` |
| **Upstox** | `{UNDERLYING} {STRIKE} {CE\|PE} {DD} {MMM} {YY}` | `NIFTY 25000 CE 24 APR 25` |
| **Dhan** | `{UNDERLYING} {DD} {MMM} {STRIKE} {CALL\|PUT}` | `NIFTY 24 APR 25000 CALL` |
| **Fyers** | `{EXCHANGE}:{UNDERLYING}{YY}{M}{DD}{STRIKE}{CE\|PE}` | `NSE:NIFTY2542425000CE` |
| **Paytm Money** | Uses `security_id` (numeric) | `123456789` |

### 2.2 Visual Symbol Breakdown

```
═══════════════════════════════════════════════════════════════════════════════════════════
                    OPTION SYMBOL FORMAT BREAKDOWN BY BROKER
═══════════════════════════════════════════════════════════════════════════════════════════

ZERODHA KITE (Monthly Expiry):
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N I F T Y 2 5 A P R 2 5 0 0 0 C E                                                     │
│   ├─────┤ ├───┤ ├─────┤ ├───────┤ ├───┤                                                 │
│   Under-  Year   Month   Strike   Option                                                │
│   lying   (25)   (APR)   Price    Type                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

ZERODHA KITE (Weekly Expiry):
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N I F T Y 2 5 4 2 4 2 5 0 0 0 C E                                                     │
│   ├─────┤ ├───┤ │ ├───┤ ├───────┤ ├───┤                                                 │
│   Under-  Year  M  Day   Strike   Option                                                │
│   lying   (25) (4) (24)  Price    Type                                                  │
│                 └── Month code: 1-9, O(Oct), N(Nov), D(Dec)                             │
└─────────────────────────────────────────────────────────────────────────────────────────┘

ANGEL ONE SMARTAPI:
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N I F T Y 2 4 A P R 2 5 2 5 0 0 0 C E                                                 │
│   ├─────┤ ├───┤ ├─────┤ ├───┤ ├───────┤ ├───┤                                           │
│   Under-  Day   Month   Year   Strike   Option                                          │
│   lying   (24)  (APR)   (25)   Price    Type                                            │
│                                                                                          │
│   KEY DIFFERENCE: Day comes FIRST (DD-MON-YY vs YY-MON for Kite)                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘

UPSTOX:
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N I F T Y   2 5 0 0 0   C E   2 4   A P R   2 5                                       │
│   ├─────┤     ├───────┤   ├───┤ ├───┤ ├─────┤ ├───┤                                     │
│   Under-      Strike      Option Day   Month   Year                                     │
│   lying       Price       Type  (24)  (APR)   (25)                                      │
│                                                                                          │
│   KEY DIFFERENCE: Has SPACES, Strike before Option Type, Date at END                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

DHAN:
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N I F T Y   2 4   A P R   2 5 0 0 0   C A L L                                         │
│   ├─────┤     ├───┤ ├─────┤ ├───────┤   ├──────┤                                        │
│   Under-      Day   Month   Strike      Option                                          │
│   lying       (24)  (APR)   Price       Type                                            │
│                                                                                          │
│   KEY DIFFERENCE: Uses "CALL"/"PUT" instead of "CE"/"PE"                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘

FYERS:
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│   N S E : N I F T Y 2 5 4 2 4 2 5 0 0 0 C E                                             │
│   ├─────┤ ├─────┤ ├───┤ │ ├───┤ ├───────┤ ├───┤                                         │
│   Exchange Under-  Year M  Day   Strike   Option                                        │
│   Prefix   lying   (25)(4) (24)  Price    Type                                          │
│                                                                                          │
│   KEY DIFFERENCE: Has EXCHANGE PREFIX (NSE:, BSE:, etc.)                                │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Month Code Reference (Weekly Options)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  MONTH CODES FOR WEEKLY OPTIONS (Zerodha/Fyers)                            │
├────────────────────────────────────────────────────────────────────────────┤
│  January   = 1    April     = 4    July       = 7    October  = O         │
│  February  = 2    May       = 5    August     = 8    November = N         │
│  March     = 3    June      = 6    September  = 9    December = D         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CANONICAL SYMBOL & NORMALIZATION

### 3.1 Canonical (Internal) Format

AlgoChanakya uses **Zerodha Kite format** as the internal canonical format:

```python
# Canonical Symbol Structure
@dataclass
class CanonicalSymbol:
    underlying: str          # "NIFTY", "BANKNIFTY", "FINNIFTY"
    expiry: date            # 2025-04-24
    strike: Decimal         # 25000
    option_type: str        # "CE" or "PE"

    def to_kite_symbol(self) -> str:
        """Convert to Kite format (our canonical string format)"""
        if self.is_monthly_expiry():
            return f"{self.underlying}{self.expiry.strftime('%y%b').upper()}{int(self.strike)}{self.option_type}"
        else:
            month_code = self._get_month_code(self.expiry.month)
            return f"{self.underlying}{self.expiry.strftime('%y')}{month_code}{self.expiry.day:02d}{int(self.strike)}{self.option_type}"
```

### 3.2 Symbol Converter Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           SYMBOL NORMALIZATION LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              CANONICAL SYMBOL
                         (Underlying, Expiry, Strike, Type)
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
            ▼                         ▼                         ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  to_kite_symbol() │     │ to_angel_symbol() │     │to_upstox_symbol() │
│                   │     │                   │     │                   │
│ NIFTY25APR25000CE │     │NIFTY24APR2525000CE│     │NIFTY 25000 CE ... │
└───────────────────┘     └───────────────────┘     └───────────────────┘
            │                         │                         │
            ▼                         ▼                         ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ from_kite_symbol()│     │from_angel_symbol()│     │from_upstox_symbol│
│                   │     │                   │     │                   │
│    Parse string   │     │    Parse string   │     │    Parse string   │
│    → Canonical    │     │    → Canonical    │     │    → Canonical    │
└───────────────────┘     └───────────────────┘     └───────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              SYMBOL CONVERTER CLASS                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  class SymbolConverter:                                                                 │
│      """Converts symbols between broker formats and canonical representation."""        │
│                                                                                         │
│      # Parse broker-specific symbol to canonical                                        │
│      def parse(self, symbol: str, broker: BrokerType) -> CanonicalSymbol               │
│                                                                                         │
│      # Format canonical to broker-specific symbol                                       │
│      def format(self, canonical: CanonicalSymbol, broker: BrokerType) -> str           │
│                                                                                         │
│      # Convert directly between brokers                                                 │
│      def convert(self, symbol: str, from_broker: BrokerType,                           │
│                  to_broker: BrokerType) -> str                                         │
│                                                                                         │
│      # Get all possible symbol variations for a canonical                              │
│      def get_all_formats(self, canonical: CanonicalSymbol) -> Dict[BrokerType, str]    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Token Mapping Database

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  DATABASE: broker_instrument_tokens                                                     │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐ │
│  │  canonical_symbol  │  broker  │  broker_symbol          │  broker_token  │  expiry │ │
│  ├────────────────────┼──────────┼─────────────────────────┼────────────────┼─────────┤ │
│  │  NIFTY25APR25000CE │  kite    │  NIFTY25APR25000CE      │  12345678      │  Apr 24 │ │
│  │  NIFTY25APR25000CE │  angel   │  NIFTY24APR2525000CE    │  87654321      │  Apr 24 │ │
│  │  NIFTY25APR25000CE │  upstox  │  NIFTY 25000 CE 24...   │  11223344      │  Apr 24 │ │
│  │  NIFTY25APR25000CE │  dhan    │  NIFTY 24 APR 25000 CALL│  55667788      │  Apr 24 │ │
│  │  NIFTY25APR25000CE │  fyers   │  NSE:NIFTY254242500...  │  99887766      │  Apr 24 │ │
│  └───────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                         │
│  INDEX: (canonical_symbol, broker) → UNIQUE                                            │
│  POPULATED: Daily instrument download from each broker                                 │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. DATA TYPE NORMALIZATION

### 4.1 Raw Data Differences by Broker

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                       DATA TYPE DIFFERENCES BY BROKER                                   │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┬──────────────────┬──────────────────┬──────────────────┬─────────────┐
│     FIELD        │   SMARTAPI WS    │   SMARTAPI REST  │   KITE           │   UNIFIED   │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┼─────────────┤
│                  │                  │                  │                  │             │
│  Price Unit      │  PAISE (÷100)    │  RUPEES          │  RUPEES          │  Decimal    │
│                  │                  │                  │                  │  (RUPEES)   │
│                  │                  │                  │                  │             │
│  Token           │  int             │  string          │  int             │  int        │
│                  │                  │                  │                  │             │
│  LTP Field       │ last_traded_price│  ltp             │  last_price      │  last_price │
│                  │                  │                  │                  │             │
│  Volume Field    │volume_trade_for_ │  tradeVolume     │  volume          │  volume     │
│                  │  the_day         │                  │                  │             │
│                  │                  │                  │                  │             │
│  OI Field        │  open_interest   │  opnInterest     │  oi              │  oi         │
│                  │                  │                  │                  │             │
│  Timestamp       │  int (ms epoch)  │  string (ISO)    │  datetime obj    │  datetime   │
│                  │                  │                  │                  │             │
│  Price Type      │  float           │  float           │  float           │  Decimal    │
│                  │                  │                  │                  │             │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┴─────────────┘

⚠️  CRITICAL: SmartAPI WebSocket returns prices in PAISE - must divide by 100!
```

### 4.2 Field Name Mapping Table

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           FIELD NAME MAPPING BY BROKER                                  │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┬─────────────────────┬─────────────────────┬─────────────────┬──────────┐
│   UNIFIED       │   SMARTAPI WS       │   SMARTAPI REST     │   KITE          │  UPSTOX  │
├─────────────────┼─────────────────────┼─────────────────────┼─────────────────┼──────────┤
│  last_price     │  last_traded_price  │  ltp                │  last_price     │  ltp     │
│  open           │  open_price_of_day  │  open               │  ohlc.open      │  open    │
│  high           │  high_price_of_day  │  high               │  ohlc.high      │  high    │
│  low            │  low_price_of_day   │  low                │  ohlc.low       │  low     │
│  close          │  closed_price       │  close              │  ohlc.close     │  close   │
│  volume         │  volume_trade_for_  │  tradeVolume        │  volume         │  volume  │
│                 │    the_day          │                     │                 │          │
│  oi             │  open_interest      │  opnInterest        │  oi             │  oi      │
│  oi_change      │  -                  │  opnInterestChange  │  oi_day_change  │  -       │
│  change         │  (calculated)       │  (calculated)       │  net_change     │  change  │
│  bid_price      │  best_bid_price     │  depth.buy[0].price │  depth.buy[0]   │  bid     │
│  ask_price      │  best_ask_price     │  depth.sell[0].price│  depth.sell[0]  │  ask     │
│  last_trade_time│ last_traded_time    │  exchTradeTime      │ last_trade_time │  ltt     │
│  exchange_time  │  exchange_timestamp │  exchFeedTime       │exchange_timestamp│  -      │
└─────────────────┴─────────────────────┴─────────────────────┴─────────────────┴──────────┘
```

### 4.3 Unified Quote Model

```python
@dataclass
class UnifiedQuote:
    """
    Unified market data quote - ALL adapters MUST normalize to this format.

    PRICE RULES:
    - All prices in RUPEES (not paise)
    - All prices as Decimal for precision

    TOKEN RULES:
    - instrument_token as int
    - tradingsymbol in CANONICAL format (Kite format)

    TIMESTAMP RULES:
    - All timestamps as Python datetime objects
    - Timezone: IST (Asia/Kolkata)
    """

    # Identification
    tradingsymbol: str = ""           # Canonical format (Kite)
    exchange: str = ""                # NSE, NFO, BSE, MCX
    instrument_token: int = 0         # Numeric token

    # Prices (ALL IN RUPEES, ALL AS DECIMAL)
    last_price: Decimal = Decimal("0")
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    close: Decimal = Decimal("0")     # Previous day close

    # Change (calculated)
    change: Decimal = Decimal("0")           # last_price - close
    change_percent: Decimal = Decimal("0")   # (change / close) * 100

    # Volume & Open Interest
    volume: int = 0
    oi: int = 0
    oi_change: int = 0

    # Bid/Ask (Level 1)
    bid_price: Decimal = Decimal("0")
    bid_quantity: int = 0
    ask_price: Decimal = Decimal("0")
    ask_quantity: int = 0

    # Timestamps (Python datetime, IST timezone)
    last_trade_time: Optional[datetime] = None
    exchange_timestamp: Optional[datetime] = None

    # Greeks (calculated, for options)
    iv: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    gamma: Optional[Decimal] = None
    theta: Optional[Decimal] = None
    vega: Optional[Decimal] = None

    # Raw response for debugging
    raw_response: Optional[Dict[str, Any]] = None
```

---

## 5. SCREEN-TO-DATA FIELD MAPPING

### 5.1 Complete Field Requirements by Screen

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        SCREEN → DATA FIELD REQUIREMENTS                                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  HEADER (Index Prices Bar)                                                              │
│  ══════════════════════════                                                             │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  NIFTY 50: 24,521.65 ▲ +156.30 (+0.64%)                                             ││
│  │            ├────────┤   ├──────┤ ├──────┤                                           ││
│  │            ltp         change   change_percent                                       ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: WebSocket (TickerService)                                                 │
│  Tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265                   │
│  Fields: ltp, change, change_percent                                                    │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  WATCHLIST                                                                              │
│  ═════════                                                                              │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  Symbol              LTP        Change      %Change     Volume      OI              ││
│  │  ─────────────────────────────────────────────────────────────────────────────────  ││
│  │  NIFTY25APR25000CE   156.50     +12.30      +8.53%      1,234,567   45,678          ││
│  │  ├────────────────┤  ├─────┤    ├──────┤    ├──────┤    ├─────────┤ ├──────┤        ││
│  │  tradingsymbol       ltp        change      change_%    volume      oi              ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: WebSocket (TickerService)                                                 │
│  Fields: ltp, change, change_percent, volume, oi, high, low, open, close              │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  OPTION CHAIN                                                                           │
│  ════════════                                                                           │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │         CALLS                    STRIKE           PUTS                              ││
│  │  OI    Vol   IV    LTP   Chg%   ──────   Chg%   LTP   IV    Vol   OI               ││
│  │  ─────────────────────────────────────────────────────────────────────────────────  ││
│  │  45K   12K  18.5  156.5  +8.5   25000   -5.2   89.5  19.2  8.5K  32K               ││
│  │  ├──┤ ├───┤├────┤├────┤ ├───┤          ├───┤ ├────┤├────┤├───┤ ├──┤               ││
│  │  oi   vol   iv    ltp  change%         change% ltp   iv   vol   oi                 ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: REST API + WebSocket for live updates                                     │
│  Fields per strike: ltp, change, change_percent, oi, oi_change, volume, iv,            │
│                     delta, gamma, theta, vega, bid_price, ask_price                    │
│  Calculated: iv (Newton-Raphson), Greeks (Black-Scholes), Max Pain, PCR                │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  STRATEGY BUILDER                                                                       │
│  ════════════════                                                                       │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  Leg    Symbol              Qty   Entry   LTP     P&L                               ││
│  │  ─────────────────────────────────────────────────────────────────────────────────  ││
│  │  BUY    NIFTY25APR25000CE   25    150.0   156.5   +₹16,250                          ││
│  │         ├────────────────┤       ├─────┤ ├─────┤                                    ││
│  │         tradingsymbol            entry   ltp (for P&L calc)                         ││
│  │                                                                                      ││
│  │  Spot Price: 24,521.65  ◄── From index WebSocket (ltp)                             ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: WebSocket for spot + leg LTP, REST for strategy load                     │
│  Fields: ltp (for spot and each leg), change, change_percent                           │
│  For P&L: Current mode uses ltp, At-Expiry mode uses intrinsic value                   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  POSITIONS                                                                              │
│  ═════════                                                                              │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  Symbol              Qty    Avg     LTP     P&L       Day Chg                       ││
│  │  ─────────────────────────────────────────────────────────────────────────────────  ││
│  │  NIFTY25APR25000CE   +50   145.0   156.5   +₹28,750   +₹6,150                       ││
│  │  ├────────────────┤ ├───┤ ├─────┤ ├─────┤ ├────────┤  ├───────┤                     ││
│  │  tradingsymbol      qty   avg_price ltp   pnl        day_change                     ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: Broker Order API (positions), WebSocket for live P&L updates            │
│  Fields: quantity, average_price, ltp, pnl, realized_pnl, unrealized_pnl              │
│  Note: Positions come from ORDER EXECUTION broker, LTP from MARKET DATA broker        │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  AUTOPILOT                                                                              │
│  ═════════                                                                              │
│                                                                                          │
│  Entry Condition: "Spot crosses above 24,500"                                           │
│                    └── Needs: index ltp from WebSocket                                 │
│                                                                                          │
│  Adjustment: "If leg LTP drops 20%"                                                     │
│              └── Needs: leg ltp from WebSocket                                         │
│                                                                                          │
│  Exit: "At 3:15 PM or if MTM > ₹5,000"                                                  │
│        └── Needs: all leg ltp for MTM calculation                                      │
│                                                                                          │
│  Data Source: WebSocket for all condition monitoring                                    │
│  Fields: ltp (spot index + all legs), change, change_percent                           │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  OFO CALCULATOR                                                                         │
│  ══════════════                                                                         │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  Option: NIFTY25APR25000CE    LTP: ₹156.50    Qty Recommended: 50 lots             ││
│  │                               ├──────────┤                                          ││
│  │                               Uses ltp for position sizing                          ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: REST API for quote                                                        │
│  Fields: ltp, bid_price, ask_price (for slippage estimation)                           │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  BACKTESTING / AI MODULE                                                                │
│  ═══════════════════════                                                                │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐│
│  │  Date        Open      High      Low       Close     Volume                         ││
│  │  ─────────────────────────────────────────────────────────────────────────────────  ││
│  │  2025-01-14  24,450    24,600    24,400    24,521    1.2B                           ││
│  └─────────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                          │
│  Data Source: REST API (Historical OHLCV)                                              │
│  Fields: timestamp, open, high, low, close, volume                                     │
│  Intervals: 1min, 5min, 15min, 1hour, 1day                                             │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. MARKET DATA ADAPTER INTERFACE

### 6.1 Abstract Base Class

```python
class MarketDataBrokerAdapter(ABC):
    """
    Abstract interface for all market data broker adapters.

    EVERY adapter MUST:
    1. Normalize all prices to RUPEES
    2. Normalize all symbols to CANONICAL format
    3. Normalize all tokens to int
    4. Normalize all timestamps to datetime (IST)
    5. Return UnifiedQuote for all quote methods
    """

    def __init__(self, credentials: BrokerCredentials):
        self.credentials = credentials
        self._symbol_converter = SymbolConverter()

    @property
    @abstractmethod
    def broker_type(self) -> MarketDataBrokerType:
        """Return the broker type identifier."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for symbols.

        Args:
            symbols: List of CANONICAL symbols (Kite format)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote
        """
        pass

    @abstractmethod
    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only (lightweight).

        Args:
            symbols: List of CANONICAL symbols

        Returns:
            Dict mapping canonical symbol to LTP (Decimal, in RUPEES)
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to live ticks via WebSocket.

        Args:
            tokens: List of instrument tokens (internal/canonical tokens)
            mode: "ltp" (price only) or "quote" (full quote with depth)
        """
        pass

    @abstractmethod
    async def unsubscribe(self, tokens: List[int]) -> None:
        """Unsubscribe from live ticks."""
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """
        Register callback for incoming ticks.

        Callback receives list of UnifiedQuote (normalized).
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # HISTORICAL DATA
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        interval: str = "day"  # "1min", "5min", "15min", "hour", "day"
    ) -> List[OHLCVCandle]:
        """
        Get historical OHLCV data.

        Args:
            symbol: CANONICAL symbol
            from_date: Start date
            to_date: End date
            interval: Candle interval

        Returns:
            List of OHLCV candles (prices in RUPEES, Decimal)
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUMENTS
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """Get all instruments for exchange."""
        pass

    @abstractmethod
    async def search_instruments(self, query: str) -> List[Instrument]:
        """Search instruments by name/symbol."""
        pass

    @abstractmethod
    async def get_token(self, symbol: str) -> int:
        """
        Get broker token for canonical symbol.
        Uses internal mapping table.
        """
        pass

    @abstractmethod
    async def get_symbol(self, token: int) -> str:
        """Get canonical symbol for broker token."""
        pass
```

---

## 7. COMPLETE DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE MARKET DATA FLOW: BROKER → SCREEN                           │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                  USER SETTINGS
                            market_data_broker: "angel"
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND SCREENS                                           │
│                                                                                         │
│   Header    Watchlist   OptionChain   Strategy   Positions   AutoPilot   Backtesting   │
│     │           │            │            │           │           │           │         │
│     └───────────┴────────────┴────────────┴───────────┴───────────┴───────────┘         │
│                                      │                                                   │
│                          watchlistStore.ticks                                           │
│                          watchlistStore.indexTicks                                      │
└──────────────────────────────────────┼───────────────────────────────────────────────────┘
                                       │
                    WebSocket: ws://api/ws/ticks?token=JWT
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND WEBSOCKET HANDLER                                  │
│                              (websocket.py)                                             │
│                                                                                         │
│   1. Get user from JWT                                                                  │
│   2. Get user.market_data_broker → "angel"                                             │
│   3. Get ticker service via factory:                                                    │
│      ticker = get_ticker_service(user.market_data_broker)                              │
│                                                                                         │
└──────────────────────────────────────┼───────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              TICKER SERVICE FACTORY                                     │
│                                                                                         │
│   def get_ticker_service(broker_type: str) -> TickerService:                           │
│       if broker_type == "angel":                                                        │
│           return SmartAPITickerService(credentials)                                     │
│       elif broker_type == "kite":                                                       │
│           return KiteTickerService(credentials)                                         │
│       elif broker_type == "upstox":                                                     │
│           return UpstoxTickerService(credentials)                                       │
│       ...                                                                               │
│                                                                                         │
└──────────────────────────────────────┼───────────────────────────────────────────────────┘
                                       │
                        ┌──────────────┼──────────────┐
                        │              │              │
                        ▼              ▼              ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│  SmartAPITickerService  │ │   KiteTickerService     │ │  UpstoxTickerService    │
│                         │ │                         │ │                         │
│  _normalize_tick():     │ │  _normalize_tick():     │ │  _normalize_tick():     │
│  • ltp /= 100 (paise)   │ │  • ltp as-is (rupees)   │ │  • ltp as-is (rupees)   │
│  • field name mapping   │ │  • field name mapping   │ │  • field name mapping   │
│  • token to canonical   │ │  • token to canonical   │ │  • token to canonical   │
│                         │ │                         │ │                         │
│  Returns: UnifiedQuote  │ │  Returns: UnifiedQuote  │ │  Returns: UnifiedQuote  │
└────────────┬────────────┘ └────────────┬────────────┘ └────────────┬────────────┘
             │                           │                           │
             ▼                           ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│  SmartAPI WebSocket V2  │ │  Kite WebSocket         │ │  Upstox WebSocket       │
│                         │ │                         │ │                         │
│  wss://smartapi...      │ │  wss://kite...          │ │  wss://upstox...        │
└────────────┬────────────┘ └────────────┬────────────┘ └────────────┬────────────┘
             │                           │                           │
             ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              BROKER APIS (External)                                     │
│                                                                                         │
│  Angel One SmartAPI    Zerodha Kite Connect    Upstox    Dhan    Fyers    Paytm        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │    EXCHANGES     │
                              │    NSE / BSE     │
                              └──────────────────┘


═══════════════════════════════════════════════════════════════════════════════════════════
                    WHAT HAPPENS WHEN USER SWITCHES BROKER
═══════════════════════════════════════════════════════════════════════════════════════════

  1. User goes to Settings, changes "Market Data Source" from Angel to Upstox

  2. Frontend calls: PUT /api/user/settings { market_data_broker: "upstox" }

  3. Backend updates users table: market_data_broker = "upstox"

  4. Frontend refreshes WebSocket connection

  5. Backend WebSocket handler:
     - Reads user.market_data_broker → "upstox"
     - Factory returns UpstoxTickerService
     - Subscribes to same tokens via Upstox WebSocket

  6. All screens automatically receive data from Upstox
     - UnifiedQuote format is identical
     - No frontend code changes needed
     - No backend route changes needed

  🎯 SEAMLESS SWITCH - Zero code changes, just configuration!

```

---

## Related Documentation

- **[Part 2: Code Specifications →](./market-data-abstraction-code-specs.md)** - Data models, database schema, interfaces, error handling
- **[Part 3: Implementation Guide →](./market-data-abstraction-implementation.md)** - Frontend/backend code, API endpoints, roadmap
- [Broker Abstraction Architecture](./broker-abstraction.md) - Overall multi-broker system
- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) - Decision rationale

---

**Document Version:** 2.0
**Part:** 1 of 3
**Status:** Complete Design Specification
