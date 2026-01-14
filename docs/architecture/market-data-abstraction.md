# Market Data Broker Abstraction

## Executive Summary

This document provides a **comprehensive specification for the Market Data Broker Abstraction Layer** in AlgoChanakya. It covers how users select their market data source, how data flows to every screen, how option symbols are normalized across brokers, and how data types are unified.

**Goal:** User changes market data broker in Settings → ALL screens automatically use new broker with ZERO code changes.

---

## Table of Contents

1. [User Broker Selection Flow](#1-user-broker-selection-flow)
2. [Option Symbol Format by Broker](#2-option-symbol-format-by-broker)
3. [Canonical Symbol & Normalization](#3-canonical-symbol--normalization)
4. [Data Type Normalization](#4-data-type-normalization)
5. [Screen-to-Data Field Mapping](#5-screen-to-data-field-mapping)
6. [Market Data Adapter Interface](#6-market-data-adapter-interface)
7. [Complete Data Flow Diagram](#7-complete-data-flow-diagram)
8. [Data Models & Types](#8-data-models--types)
9. [Database Schema](#9-database-schema)
10. [TickerService Interface](#10-tickerservice-interface)
11. [Error Handling & Resilience](#11-error-handling--resilience)
12. [Frontend Implementation](#12-frontend-implementation)
13. [Backend API Endpoints](#13-backend-api-endpoints)
14. [Implementation Roadmap](#14-implementation-roadmap)

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

## 8. DATA MODELS & TYPES

### 8.1 Missing Dataclasses

The following dataclasses must be added to `backend/app/services/brokers/market_data_base.py`:

```python
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID


class MarketDataBrokerType(str, Enum):
    """Supported market data broker types."""
    SMARTAPI = "smartapi"
    KITE = "kite"
    UPSTOX = "upstox"
    DHAN = "dhan"
    FYERS = "fyers"
    PAYTM = "paytm"


@dataclass
class BrokerCredentials:
    """Base class for broker credentials."""
    broker_type: str
    user_id: UUID


@dataclass
class SmartAPIMarketDataCredentials(BrokerCredentials):
    """SmartAPI-specific credentials for market data."""
    client_id: str
    jwt_token: str
    feed_token: str
    broker_type: str = "smartapi"


@dataclass
class KiteMarketDataCredentials(BrokerCredentials):
    """Kite-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "kite"


@dataclass
class UpstoxMarketDataCredentials(BrokerCredentials):
    """Upstox-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "upstox"


@dataclass
class OHLCVCandle:
    """Historical OHLC+Volume candle."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: Optional[int] = None  # For F&O instruments

    # Raw response for debugging
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class Instrument:
    """Instrument definition (broker-agnostic)."""
    # Canonical identification
    canonical_symbol: str           # NIFTY25APR25000CE (Kite format)
    exchange: str                   # NSE, NFO, BSE, MCX

    # Broker-specific
    broker_symbol: str              # Broker-specific format
    instrument_token: int           # Broker token

    # Display
    tradingsymbol: str             # Human-readable name
    name: str                      # Full name (e.g., "NIFTY 24 APR 25000 CE")

    # For options
    underlying: Optional[str] = None        # NIFTY, BANKNIFTY
    expiry: Optional[date] = None          # 2025-04-24
    strike: Optional[Decimal] = None        # 25000
    option_type: Optional[str] = None       # CE, PE

    # For futures
    instrument_type: str = "EQ"    # EQ, FUT, CE, PE

    # Trading details
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    is_tradable: bool = True

    # Metadata
    segment: str = "NFO"           # CASH, NFO, BFO, MCX
    last_price: Optional[Decimal] = None
```

---

## 9. DATABASE SCHEMA

### 9.1 Token Mapping Table

**Create new table:** `broker_instrument_tokens`

```python
# backend/app/models/broker_instrument_tokens.py
"""
Broker Instrument Token Mapping

Maps canonical symbols (Kite format) to broker-specific symbols and tokens.
Populated daily via scheduled job that downloads instruments from each broker.
"""
from sqlalchemy import Column, String, BigInteger, Date, DateTime, UniqueConstraint, Index
from sqlalchemy.sql import func

from app.database import Base


class BrokerInstrumentToken(Base):
    """Maps canonical symbols to broker-specific symbols and tokens."""
    __tablename__ = "broker_instrument_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Canonical symbol (Kite format - our internal standard)
    canonical_symbol = Column(String(50), nullable=False, index=True)

    # Broker identification
    broker = Column(String(20), nullable=False, index=True)  # smartapi, kite, upstox, dhan, fyers, paytm

    # Broker-specific data
    broker_symbol = Column(String(100), nullable=False)
    broker_token = Column(BigInteger, nullable=False)

    # Instrument details
    exchange = Column(String(10), nullable=False)  # NSE, NFO, BSE, BFO, MCX
    underlying = Column(String(20), nullable=True)  # NIFTY, BANKNIFTY, etc.
    expiry = Column(Date, nullable=True)  # For cleanup of expired contracts

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Unique constraint: one mapping per symbol per broker
        UniqueConstraint('canonical_symbol', 'broker', name='uq_symbol_broker'),

        # Indexes for fast lookups
        Index('idx_broker_token', 'broker', 'broker_token'),
        Index('idx_canonical_symbol', 'canonical_symbol'),
        Index('idx_broker_symbol', 'broker', 'broker_symbol'),
        Index('idx_expiry', 'expiry'),  # For cleanup of expired contracts
    )

    def __repr__(self):
        return f"<BrokerInstrumentToken({self.canonical_symbol} -> {self.broker}:{self.broker_symbol})>"
```

**Migration steps:**
```bash
# After creating the model file:
# 1. Import in backend/app/models/__init__.py
# 2. Import in backend/alembic/env.py
# 3. Generate migration
cd backend
alembic revision --autogenerate -m "Add broker_instrument_tokens table"
alembic upgrade head
```

### 9.2 Update User Preferences

**File:** `backend/app/models/user_preferences.py`

```python
# UPDATE lines 14-19
class MarketDataSource:
    """Valid market data source values."""
    SMARTAPI = "smartapi"
    KITE = "kite"
    UPSTOX = "upstox"
    DHAN = "dhan"
    FYERS = "fyers"
    PAYTM = "paytm"

    VALID_SOURCES = [SMARTAPI, KITE, UPSTOX, DHAN, FYERS, PAYTM]

# UPDATE CheckConstraint (line 53-56)
CheckConstraint(
    "market_data_source IN ('smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm')",
    name='check_market_data_source'
),
```

### 9.3 Broker Credentials Tables

**Required:** Create credential tables for each new broker.

**Example for Upstox:**
```python
# backend/app/models/upstox_credentials.py
"""Upstox API Credentials"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


class UpstoxCredentials(Base):
    """Upstox API credentials storage."""
    __tablename__ = "upstox_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Upstox credentials
    api_key = Column(String(100), nullable=False)
    encrypted_api_secret = Column(Text, nullable=False)
    access_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_auth_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="upstox_credentials")
```

**Similar tables needed for:**
- `DhanCredentials`
- `FyersCredentials`
- `PaytmCredentials`

---

## 10. TICKERSERVICE INTERFACE

The TickerService provides a unified interface for WebSocket ticker connections across brokers.

**File:** `backend/app/services/brokers/ticker_base.py`

```python
"""
Base Ticker Service Interface

Defines the abstract interface for WebSocket ticker services.
Separate from MarketDataBrokerAdapter because WebSocket management
is a separate concern from REST API operations.
"""
from abc import ABC, abstractmethod
from typing import Callable, List, Set, Optional
from app.services.brokers.market_data_base import UnifiedQuote


class TickerService(ABC):
    """
    Abstract interface for broker WebSocket ticker services.

    All broker ticker services (SmartAPI, Kite, Upstox, etc.)
    must implement this interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish WebSocket connection to broker.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close WebSocket connection gracefully.

        Should unsubscribe from all tokens before closing.
        """
        pass

    @abstractmethod
    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to instrument tokens for live ticks.

        Args:
            tokens: List of instrument tokens (broker-specific tokens)
            mode: "ltp" (price only) or "quote" (full quote with depth)
        """
        pass

    @abstractmethod
    async def unsubscribe(self, tokens: List[int]) -> None:
        """
        Unsubscribe from instrument tokens.

        Args:
            tokens: List of instrument tokens to unsubscribe
        """
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """
        Register callback for incoming tick data.

        Callback will be invoked with list of UnifiedQuote objects.
        All prices normalized to RUPEES, all symbols in CANONICAL format.

        Args:
            callback: Function to call with tick data
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for WebSocket errors.

        Args:
            callback: Function to call with error message
        """
        pass

    @abstractmethod
    def on_close(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for connection close.

        Args:
            callback: Function to call with close reason
        """
        pass

    @abstractmethod
    async def reconnect(self, max_retries: int = 5) -> bool:
        """
        Reconnect WebSocket with exponential backoff.

        Args:
            max_retries: Maximum number of reconnection attempts

        Returns:
            True if reconnection successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        pass

    @property
    @abstractmethod
    def subscribed_tokens(self) -> Set[int]:
        """Get set of currently subscribed tokens."""
        pass

    @property
    @abstractmethod
    def reconnection_attempts(self) -> int:
        """Get number of reconnection attempts made."""
        pass


# Factory function
def get_ticker_service(broker_type: str, credentials) -> TickerService:
    """
    Factory to get ticker service based on broker type.

    Args:
        broker_type: Broker identifier (smartapi, kite, upstox, etc.)
        credentials: Broker-specific credentials object

    Returns:
        TickerService implementation for the broker

    Raises:
        ValueError: If broker type not supported
    """
    if broker_type == "smartapi":
        from app.services.smartapi_ticker import SmartAPITickerService
        return SmartAPITickerService(credentials)
    elif broker_type == "kite":
        from app.services.kite_ticker import KiteTickerService
        return KiteTickerService(credentials)
    elif broker_type == "upstox":
        from app.services.upstox_ticker import UpstoxTickerService
        return UpstoxTickerService(credentials)
    elif broker_type == "dhan":
        from app.services.dhan_ticker import DhanTickerService
        return DhanTickerService(credentials)
    elif broker_type == "fyers":
        from app.services.fyers_ticker import FyersTickerService
        return FyersTickerService(credentials)
    elif broker_type == "paytm":
        from app.services.paytm_ticker import PaytmTickerService
        return PaytmTickerService(credentials)
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")
```

---

## 11. ERROR HANDLING & RESILIENCE

### 11.1 Exception Hierarchy

```python
# backend/app/services/brokers/exceptions.py
"""Broker-related exceptions."""


class BrokerError(Exception):
    """Base exception for all broker errors."""
    pass


class BrokerAPIError(BrokerError):
    """Broker API returned an error."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class BrokerAPIDownError(BrokerAPIError):
    """Broker API is down or unreachable."""
    pass


class BrokerRateLimitError(BrokerAPIError):
    """Hit broker API rate limit."""
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after  # seconds until can retry


class BrokerAuthenticationError(BrokerAPIError):
    """Broker authentication failed (token expired/invalid)."""
    pass


class BrokerSymbolNotFoundError(BrokerError):
    """Symbol not found in broker's instrument list."""
    def __init__(self, symbol: str, broker: str):
        super().__init__(f"Symbol {symbol} not found for broker {broker}")
        self.symbol = symbol
        self.broker = broker


class BrokerWebSocketError(BrokerError):
    """WebSocket connection error."""
    pass
```

### 11.2 Rate Limiting

```python
# backend/app/services/brokers/rate_limiter.py
"""Broker API rate limiter."""
import asyncio
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BrokerRateLimiter:
    """
    Track and enforce broker API rate limits.

    Uses sliding window algorithm with Redis for distributed rate limiting.
    """

    # Rate limits per broker (requests per minute)
    RATE_LIMITS = {
        'smartapi': {
            'quotes': 100,        # LTP/quote requests
            'historical': 50,     # Historical data requests
            'instruments': 10,    # Instrument downloads
        },
        'kite': {
            'quotes': 100,
            'historical': 60,
            'instruments': 10,
        },
        'upstox': {
            'quotes': 250,
            'historical': 100,
            'instruments': 20,
        },
        'dhan': {
            'quotes': 150,
            'historical': 75,
            'instruments': 15,
        },
        'fyers': {
            'quotes': 200,
            'historical': 100,
            'instruments': 20,
        },
        'paytm': {
            'quotes': 100,
            'historical': 50,
            'instruments': 10,
        },
    }

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting
        """
        self.redis = redis_client
        self._local_counters: Dict[str, list] = {}  # Fallback to local if no Redis

    async def check_limit(self, broker: str, endpoint: str, user_id: str = None) -> bool:
        """
        Check if request is within rate limit.

        Args:
            broker: Broker name (smartapi, kite, etc.)
            endpoint: API endpoint category (quotes, historical, instruments)
            user_id: Optional user ID for per-user limiting

        Returns:
            True if request allowed, False if rate limited

        Raises:
            BrokerRateLimitError: If rate limit exceeded
        """
        limit = self.RATE_LIMITS.get(broker, {}).get(endpoint)
        if not limit:
            return True  # No limit defined

        key = f"ratelimit:{broker}:{endpoint}"
        if user_id:
            key += f":{user_id}"

        if self.redis:
            return await self._check_redis(key, limit)
        else:
            return await self._check_local(key, limit)

    async def _check_redis(self, key: str, limit: int) -> bool:
        """Check rate limit using Redis (sliding window)."""
        now = time.time()
        window = 60  # 60 seconds

        # Remove old entries
        await self.redis.zremrangebyscore(key, 0, now - window)

        # Count current requests in window
        count = await self.redis.zcard(key)

        if count >= limit:
            return False

        # Add current request
        await self.redis.zadd(key, {str(now): now})
        await self.redis.expire(key, window)

        return True

    async def _check_local(self, key: str, limit: int) -> bool:
        """Check rate limit using local memory (fallback)."""
        now = time.time()
        window = 60

        if key not in self._local_counters:
            self._local_counters[key] = []

        # Remove old entries
        self._local_counters[key] = [
            t for t in self._local_counters[key]
            if t > now - window
        ]

        if len(self._local_counters[key]) >= limit:
            return False

        self._local_counters[key].append(now)
        return True
```

### 11.3 Token Management

```python
# backend/app/services/brokers/token_manager.py
"""Broker token expiry and refresh management."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging

from app.models import User
from app.services.brokers.exceptions import BrokerAuthenticationError

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage broker token expiry and auto-refresh."""

    # Buffer time before expiry to trigger refresh (minutes)
    REFRESH_BUFFER = {
        'smartapi': 30,   # Refresh 30 min before 8-hour expiry
        'kite': 60,       # Refresh 1 hour before 24-hour expiry
        'upstox': 30,
        'dhan': 30,
        'fyers': 30,
        'paytm': 30,
    }

    async def check_token_expiry(
        self,
        broker: str,
        user_id: UUID,
        db_session
    ) -> bool:
        """
        Check if token is expired or expiring soon.

        Args:
            broker: Broker name
            user_id: User ID
            db_session: Database session

        Returns:
            True if token needs refresh, False otherwise
        """
        # Get credentials from database
        credentials = await self._get_credentials(broker, user_id, db_session)

        if not credentials or not credentials.token_expiry:
            return True  # No token or no expiry = needs refresh

        buffer = self.REFRESH_BUFFER.get(broker, 30)
        expiry_threshold = datetime.utcnow() + timedelta(minutes=buffer)

        return credentials.token_expiry <= expiry_threshold

    async def refresh_token(
        self,
        broker: str,
        user_id: UUID,
        db_session
    ) -> bool:
        """
        Refresh broker token.

        Args:
            broker: Broker name
            user_id: User ID
            db_session: Database session

        Returns:
            True if refresh successful

        Raises:
            BrokerAuthenticationError: If refresh fails
        """
        try:
            if broker == "smartapi":
                from app.services.smartapi_auth import authenticate_smartapi
                return await authenticate_smartapi(user_id, db_session)
            elif broker == "kite":
                # Kite requires OAuth - can't auto-refresh
                logger.warning(f"Kite token expired for user {user_id} - OAuth required")
                return False
            # Add other brokers
            else:
                logger.error(f"Token refresh not implemented for broker: {broker}")
                return False
        except Exception as e:
            logger.error(f"Token refresh failed for {broker}: {e}")
            raise BrokerAuthenticationError(f"Token refresh failed: {e}")

    async def _get_credentials(self, broker: str, user_id: UUID, db_session):
        """Get broker credentials from database."""
        if broker == "smartapi":
            from app.models import SmartAPICredentials
            return await db_session.get(SmartAPICredentials, user_id)
        elif broker == "upstox":
            from app.models import UpstoxCredentials
            return await db_session.get(UpstoxCredentials, user_id)
        # Add other brokers
        return None
```

---

## 12. FRONTEND IMPLEMENTATION

### 12.1 Settings UI Component

**File:** `frontend/src/views/SettingsView.vue`

Add broker selection section:

```vue
<template>
  <div class="settings-container">
    <!-- Existing settings sections -->

    <!-- Market Data Source Selection -->
    <div class="setting-section" data-testid="settings-market-data-section">
      <h3>Market Data Source</h3>
      <p class="setting-description">
        Choose which broker provides live prices, option chain data, and historical OHLCV.
        This is independent of your order execution broker.
      </p>

      <div class="setting-group">
        <label for="market-data-broker">Data Provider</label>
        <select
          id="market-data-broker"
          v-model="settings.market_data_broker"
          @change="handleBrokerChange"
          data-testid="settings-market-data-broker-select"
        >
          <option value="smartapi">Angel One (SmartAPI) - FREE [Default]</option>
          <option value="kite">Zerodha (Kite Connect) - ₹500/month</option>
          <option value="upstox">Upstox - FREE</option>
          <option value="dhan">Dhan - FREE (25 F&O trades/mo) or ₹499/mo</option>
          <option value="fyers">Fyers - FREE</option>
          <option value="paytm">Paytm Money - FREE</option>
        </select>

        <div class="broker-info" v-if="brokerInfo[settings.market_data_broker]">
          <p>{{ brokerInfo[settings.market_data_broker].description }}</p>
          <a :href="brokerInfo[settings.market_data_broker].link" target="_blank">
            Learn more →
          </a>
        </div>
      </div>

      <div class="setting-actions">
        <button
          @click="testConnection"
          :disabled="testing"
          data-testid="settings-test-connection-button"
          class="btn btn-secondary"
        >
          <span v-if="!testing">Test Connection</span>
          <span v-else>Testing...</span>
        </button>

        <button
          @click="saveSettings"
          :disabled="saving"
          data-testid="settings-save-button"
          class="btn btn-primary"
        >
          Save Changes
        </button>
      </div>

      <div
        v-if="connectionStatus"
        :class="['connection-status', connectionStatus.type]"
        data-testid="settings-connection-status"
      >
        <span class="status-icon">{{ connectionStatus.icon }}</span>
        <span>{{ connectionStatus.message }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useToast } from '@/composables/useToast'
import { brokerAPI } from '@/services/api'

const { showToast } = useToast()

const settings = reactive({
  market_data_broker: 'smartapi',
  // ... other settings
})

const testing = ref(false)
const saving = ref(false)
const connectionStatus = ref(null)

const brokerInfo = {
  smartapi: {
    description: 'Angel One SmartAPI provides free WebSocket and REST APIs with auto-TOTP authentication.',
    link: 'https://smartapi.angelbroking.com/'
  },
  kite: {
    description: 'Zerodha Kite Connect requires ₹500/month subscription but offers robust APIs.',
    link: 'https://kite.trade/docs/connect/v3/'
  },
  upstox: {
    description: 'Upstox provides free market data APIs with WebSocket support.',
    link: 'https://upstox.com/developer/'
  },
  dhan: {
    description: 'Dhan offers free data APIs if you execute 25 F&O trades/month, otherwise ₹499/mo.',
    link: 'https://dhanhq.co/docs'
  },
  fyers: {
    description: 'Fyers provides free market data APIs with good documentation.',
    link: 'https://myapi.fyers.in/docsv3'
  },
  paytm: {
    description: 'Paytm Money offers free APIs for live prices and historical data.',
    link: 'https://developer.paytmmoney.com/'
  }
}

async function testConnection() {
  testing.value = true
  connectionStatus.value = null

  try {
    const response = await brokerAPI.testConnection(settings.market_data_broker)

    connectionStatus.value = {
      type: 'success',
      icon: '✓',
      message: `Connected successfully to ${settings.market_data_broker}`
    }

    showToast('Connection test successful', 'success')
  } catch (error) {
    connectionStatus.value = {
      type: 'error',
      icon: '✗',
      message: error.response?.data?.detail || 'Connection failed'
    }

    showToast('Connection test failed', 'error')
  } finally {
    testing.value = false
  }
}

async function saveSettings() {
  saving.value = true

  try {
    await brokerAPI.updateMarketDataBroker(settings.market_data_broker)
    showToast('Settings saved successfully', 'success')

    // Refresh WebSocket connection with new broker
    window.location.reload()
  } catch (error) {
    showToast('Failed to save settings', 'error')
  } finally {
    saving.value = false
  }
}

function handleBrokerChange() {
  connectionStatus.value = null
}

onMounted(async () => {
  // Load current settings
  // ... existing code
})
</script>

<style scoped>
.setting-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.broker-info {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: var(--info-bg);
  border-radius: 4px;
  font-size: 0.9rem;
}

.connection-status {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.connection-status.success {
  background: var(--success-bg);
  color: var(--success-text);
}

.connection-status.error {
  background: var(--error-bg);
  color: var(--error-text);
}

.setting-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}
</style>
```

### 12.2 API Client Updates

**File:** `frontend/src/services/api.js`

Add broker management endpoints:

```javascript
// Market Data Broker Management
export const brokerAPI = {
  // Update user's market data broker preference
  updateMarketDataBroker: (broker) =>
    api.put('/user/preferences', { market_data_broker: broker }),

  // Test connection to broker
  testConnection: (broker) =>
    api.post('/market-data/test-connection', { broker }),

  // Get broker credentials (if stored)
  getBrokerCredentials: (broker) =>
    api.get(`/brokers/${broker}/credentials`),

  // Save broker credentials
  saveBrokerCredentials: (broker, credentials) =>
    api.post(`/brokers/${broker}/credentials`, credentials),

  // Delete broker credentials
  deleteBrokerCredentials: (broker) =>
    api.delete(`/brokers/${broker}/credentials`),
}
```

---

## 13. BACKEND API ENDPOINTS

**File:** `backend/app/api/routes/market_data.py`

```python
"""
Market Data Broker Management API

Endpoints for managing market data broker selection and configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.database import get_db
from app.models import User, UserPreferences
from app.utils.dependencies import get_current_user
from app.services.brokers.market_data_factory import get_market_data_adapter
from app.services.brokers.exceptions import BrokerAPIError, BrokerAuthenticationError

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.post("/test-connection")
async def test_connection(
    broker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Test connection to market data broker.

    Args:
        broker: Broker identifier (smartapi, kite, upstox, etc.)
        user: Current user
        db: Database session

    Returns:
        Connection status and broker info

    Raises:
        HTTPException: If connection fails
    """
    try:
        # Get adapter for broker
        adapter = await get_market_data_adapter(broker, user.id, db)

        # Test connection by fetching NIFTY 50 quote
        quotes = await adapter.get_ltp(["NIFTY 50"])

        return {
            "status": "success",
            "broker": broker,
            "message": f"Successfully connected to {broker}",
            "test_quote": {
                "symbol": "NIFTY 50",
                "ltp": str(quotes.get("NIFTY 50", 0))
            }
        }

    except BrokerAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
    except BrokerAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Broker API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


@router.put("/switch-broker")
async def switch_broker(
    new_broker: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Switch user's market data broker.

    Args:
        new_broker: New broker identifier
        user: Current user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: If broker switch fails
    """
    # Validate broker
    valid_brokers = ['smartapi', 'kite', 'upstox', 'dhan', 'fyers', 'paytm']
    if new_broker not in valid_brokers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker. Must be one of: {', '.join(valid_brokers)}"
        )

    try:
        # Get or create user preferences
        prefs = await db.get(UserPreferences, user.id)
        if not prefs:
            prefs = UserPreferences(user_id=user.id)
            db.add(prefs)

        # Update broker
        prefs.market_data_source = new_broker
        await db.commit()

        return {
            "status": "success",
            "message": f"Market data broker switched to {new_broker}",
            "broker": new_broker
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch broker: {str(e)}"
        )


@router.get("/current-broker")
async def get_current_broker(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Get user's current market data broker."""
    prefs = await db.get(UserPreferences, user.id)

    return {
        "broker": prefs.market_data_source if prefs else "smartapi",
        "default": "smartapi"
    }
```

**Register in `backend/app/main.py`:**
```python
from app.api.routes import market_data

app.include_router(market_data.router)
```

---

## 14. IMPLEMENTATION ROADMAP

### Phase 1: Core Infrastructure (Week 1)

**Goal:** Build foundation - interfaces, base classes, database schema

**Tasks:**
1. ✅ Create `market_data_base.py` with all dataclasses
   - `MarketDataBrokerType` enum
   - `BrokerCredentials` and subclasses
   - `OHLCVCandle` dataclass
   - `Instrument` dataclass

2. ✅ Create `ticker_base.py` with `TickerService` interface

3. ✅ Create `symbol_converter.py` with `CanonicalSymbol` and `SymbolConverter`
   - Implement parsers for all 6 brokers
   - Add unit tests for each broker format

4. ✅ Create database tables
   - `broker_instrument_tokens` table
   - Update `user_preferences` (add all 6 brokers to enum/constraint)
   - Create credential tables for new brokers

5. ✅ Run migrations
   ```bash
   cd backend
   alembic revision --autogenerate -m "Add market data abstraction tables"
   alembic upgrade head
   ```

6. ✅ Create error handling classes (`exceptions.py`)

7. ✅ Create `rate_limiter.py` and `token_manager.py`

**Deliverables:**
- All base interfaces defined
- Database schema complete
- Unit tests passing (symbol conversion, rate limiting)

---

### Phase 2: SmartAPI Adapter (Week 2)

**Goal:** Wrap existing SmartAPI services in new interface

**Tasks:**
1. ✅ Create `SmartAPIMarketDataAdapter` implementing `MarketDataBrokerAdapter`
   - Wrap `smartapi_market_data.py` (REST quotes)
   - Wrap `smartapi_historical.py` (OHLCV)
   - Wrap `smartapi_instruments.py` (instruments)
   - Add symbol conversion (Angel format → Canonical)
   - Add price normalization (PAISE → RUPEES for WebSocket)

2. ✅ Update `SmartAPITickerService` to implement `TickerService` interface
   - Ensure all abstract methods implemented
   - Add reconnection logic
   - Add error callbacks

3. ✅ Create `market_data_factory.py`
   ```python
   async def get_market_data_adapter(broker_type: str, user_id: UUID, db) -> MarketDataBrokerAdapter:
       """Factory to get market data adapter."""
       # Implementation
   ```

4. ✅ Test with existing screens
   - Watchlist should work with SmartAPI adapter
   - Option Chain should work with SmartAPI adapter
   - No functionality regression

**Deliverables:**
- SmartAPI fully wrapped in abstraction
- Factory pattern working
- Existing features work via adapter

---

### Phase 3: Kite Adapter (Week 2)

**Goal:** Add Kite as second broker option

**Tasks:**
1. ✅ Create `KiteMarketDataAdapter` implementing `MarketDataBrokerAdapter`
   - REST quote API
   - Historical data API
   - Instruments API
   - Symbol already in canonical format (Kite format is canonical)

2. ✅ Create `KiteTickerService` implementing `TickerService` interface
   - Wrap existing `kite_ticker.py` logic
   - Ensure interface compliance

3. ✅ Test broker switching (SmartAPI ↔ Kite)
   - Change user preference
   - Verify WebSocket switches
   - Verify REST API switches
   - All screens should work seamlessly

**Deliverables:**
- Kite adapter complete
- Broker switching functional
- E2E test for switching

---

### Phase 4: Route Refactoring (Week 3)

**Goal:** Replace hardcoded broker logic with factory pattern

**Tasks:**
1. ✅ Refactor `websocket.py`
   ```python
   # OLD:
   if market_data_source == "smartapi":
       ticker = smartapi_ticker
   else:
       ticker = kite_ticker

   # NEW:
   ticker = get_ticker_service(user.preferences.market_data_source, credentials)
   ```

2. ✅ Refactor `optionchain.py`
   - Remove conditional logic
   - Use `get_market_data_adapter()`

3. ✅ Refactor `watchlist.py` (if needed)

4. ✅ Refactor any other routes with hardcoded broker logic

**Deliverables:**
- All routes use factory pattern
- No hardcoded broker conditionals
- All E2E tests pass

---

### Phase 5: Settings UI (Week 3)

**Goal:** Add broker selection UI and credential management

**Tasks:**
1. ✅ Update `SettingsView.vue`
   - Add broker selection dropdown
   - Add test connection button
   - Add save button with WebSocket refresh

2. ✅ Create market data API routes
   - `/api/market-data/test-connection`
   - `/api/market-data/switch-broker`
   - `/api/market-data/current-broker`

3. ✅ Update `api.js` with broker endpoints

4. ✅ Add E2E tests
   - Test broker selection
   - Test connection test
   - Test switching (SmartAPI → Kite → SmartAPI)

**Deliverables:**
- Settings UI complete
- User can switch brokers via UI
- WebSocket auto-reconnects with new broker

---

### Phase 6: Additional Brokers (Week 4+)

**Goal:** Add remaining 4 brokers one by one

**For each broker (Upstox, Dhan, Fyers, Paytm):**

1. ✅ Create credentials table
2. ✅ Implement `{Broker}MarketDataAdapter`
3. ✅ Implement `{Broker}TickerService`
4. ✅ Add to factory registry
5. ✅ Test connection
6. ✅ Test with all screens
7. ✅ Add to Settings UI dropdown

**Order of implementation:**
1. **Upstox** (most similar to Kite)
2. **Dhan** (good documentation)
3. **Fyers** (robust API)
4. **Paytm** (uses security_id instead of symbols)

---

### Phase 7: Token Population (Week 5)

**Goal:** Populate `broker_instrument_tokens` table

**Tasks:**
1. ✅ Create instrument download service
   ```python
   # backend/app/services/instrument_downloader.py
   async def download_instruments(broker: str):
       """Download and store instruments for broker."""
   ```

2. ✅ Create scheduled job (daily 6 AM IST)
   ```python
   # backend/app/tasks/daily_instrument_update.py
   async def update_all_broker_instruments():
       """Download instruments from all brokers."""
   ```

3. ✅ Add cleanup job for expired contracts
   ```python
   async def cleanup_expired_instruments():
       """Delete instruments past expiry."""
   ```

**Deliverables:**
- Token mapping table populated
- Daily refresh scheduled
- Expired contracts cleaned up

---

### Testing Strategy

**Unit Tests:**
- SymbolConverter parsing/formatting (6 brokers × 2 tests = 12 tests)
- UnifiedQuote normalization
- Rate limiter logic
- Token manager expiry checks

**Integration Tests:**
- Each adapter's connect/disconnect
- Quote fetching per broker
- Historical data retrieval
- WebSocket tick normalization

**E2E Tests:**
- Broker switching flow (Settings → WebSocket reconnect → Screens update)
- Screen data display after switch
- Error handling (invalid credentials, API down)
- Rate limit handling

**Performance Tests:**
- WebSocket tick latency per broker
- Symbol conversion speed (10,000 symbols)
- Token lookup speed (with/without Redis cache)

---

### Critical Success Metrics

**Functionality:**
- ✅ All 6 brokers connect successfully
- ✅ All screens work with any broker
- ✅ Switching takes < 5 seconds
- ✅ Zero code changes when adding broker #7

**Performance:**
- ✅ Symbol conversion < 1ms per symbol
- ✅ Token lookup < 10ms (with cache < 1ms)
- ✅ WebSocket tick latency < 100ms

**Reliability:**
- ✅ Auto-reconnect on WebSocket disconnect
- ✅ Token auto-refresh before expiry
- ✅ Graceful fallback on broker API errors

---

## Related Documentation

- [Broker Abstraction Architecture](./broker-abstraction.md) - Overall multi-broker system
- [ADR-002: Multi-Broker Abstraction](../decisions/002-broker-abstraction.md) - Decision rationale
- [WebSocket Architecture](./websocket.md) - Live price streaming
- [Database Schema](./database.md) - Broker token mapping tables
- [Implementation Checklist](../IMPLEMENTATION-CHECKLIST.md) - Current implementation status
- [Developer Quick Reference](../DEVELOPER-QUICK-REFERENCE.md) - Development patterns

---

**Document Version:** 2.0
**Last Updated:** 2025-01-14
**Status:** Complete Specification - Ready for Implementation

**This document is comprehensive and includes:**
- ✅ All required interfaces and base classes
- ✅ Complete database schema
- ✅ Error handling & resilience patterns
- ✅ Frontend UI components
- ✅ Backend API endpoints
- ✅ 7-phase implementation roadmap
- ✅ Testing strategy
- ✅ Success metrics

**No gaps remaining - ready to implement!**
