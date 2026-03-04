# Fyers — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Fyers Securities Pvt. Ltd. |
| **Founded** | 2015 (Bengaluru, India) |
| **Founder** | Tejas Khoday |
| **Headquarters** | Bengaluru, Karnataka, India |
| **SEBI Registration** | INZ000197436 (Member: NSE, BSE, MCX) |
| **Market Position** | Tech-focused discount broker targeting active traders |
| **Business Model** | Discount broker — flat-fee pricing, API-first approach |
| **API Brand** | Fyers API v3 |
| **Website** | https://fyers.in |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Fyers Web** | Web-based trading platform | https://trade.fyers.in |
| **Fyers App** | Mobile trading app (Android & iOS) | https://fyers.in/app |
| **Fyers One** | Desktop trading terminal | https://fyers.in/fyers-one |
| **Fyers API v3** | REST + multi-socket WebSocket API | https://myapi.fyers.in |
| **Fyers Community** | Trader community and education | https://community.fyers.in |

## Brokerage Charges

| Segment | Brokerage | Notes |
|---------|-----------|-------|
| **Equity Delivery** | ₹0 (FREE) | No brokerage on delivery trades |
| **Equity Intraday** | ₹20/order or 0.03% (whichever is lower) | Flat fee |
| **F&O (Futures)** | ₹20/order or 0.03% (whichever is lower) | Per executed order |
| **F&O (Options)** | ₹20/order | Flat fee per executed order |
| **Currency** | ₹20/order or 0.03% (whichever is lower) | Per executed order |
| **Commodity** | ₹20/order or 0.03% (whichever is lower) | Per executed order |

**Other Charges:**
- Account opening: FREE (online)
- AMC: ₹0 (no annual charges)
- DP charges: Standard CDSL charges on sell delivery

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **Fyers API v3** | **FREE** | REST API, 5-socket WebSocket system, market data, historical data, option chain with Greeks |

**Note:** Fyers API is completely free with no subscription charges. Daily limit of 100,000 REST requests.

## Supported Exchanges

| Exchange | Segments |
|----------|----------|
| **NSE** | Equity, F&O (Index + Stock), Currency |
| **BSE** | Equity, F&O |
| **MCX** | Commodity Futures & Options |

## Account Types

| Type | Supported | Notes |
|------|-----------|-------|
| Individual | Yes | Standard demat + trading |
| Joint (Primary) | Yes | Primary holder can trade |
| HUF | Yes | Hindu Undivided Family |
| Corporate | Yes | LLP, Pvt Ltd |
| NRI | Yes | NRE/NRO accounts |

## Key Differentiators

1. **5 WebSocket socket types** — Most extensive WebSocket system among Indian brokers (Data, Order, Position, Trade, General)
2. **5,000 symbols per Data WS** — Massive upgrade from 200 in v2; highest among comparable brokers
3. **Virtual Trading** — Built-in paper trading mode via API (same endpoints, different mode)
4. **Rich option chain** — Greeks include delta, theta, gamma, vega, rho, vanna, charm
5. **Exchange-prefixed symbols** — `NSE:SYMBOL` format closely mirrors Kite canonical (easy conversion)
6. **JSON WebSocket** — Human-readable WebSocket messages (easier debugging vs binary)
7. **100K daily request limit** — Generous daily REST quota for active algorithmic trading
8. **API-first philosophy** — Tech-focused broker with strong API documentation

## AlgoChanakya Usage

In AlgoChanakya, Fyers is used for:
- **Order execution** via FyersOrderAdapter (fully implemented)
- **Market data** via FyersMarketDataAdapter (fully implemented)
- **WebSocket ticks** via FyersDataSocket adapter (fully implemented)
- **Third in failover chain** — Platform data failover: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
- **Easy symbol conversion** — Fyers symbols are Kite canonical with `NSE:` prefix

See [SKILL.md](../SKILL.md) for complete Fyers API reference and adapter implementation details.
