# Dhan — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Dhan (Raise Financial Services Pvt. Ltd.) |
| **Founded** | 2021 (Mumbai, India) |
| **Founder** | Pravin Jadhav (ex-PayPal, ex-Paytm Money) |
| **Headquarters** | Mumbai, Maharashtra, India |
| **SEBI Registration** | INZ000313632 (Member: NSE, BSE, MCX) |
| **Market Position** | Fast-growing fintech broker, focused on active traders and F&O |
| **Business Model** | Discount broker — flat-fee pricing, built for derivatives traders |
| **API Brand** | DhanHQ API (v2) |
| **Website** | https://dhan.co |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Dhan App** | Mobile trading app (Android & iOS) | https://dhan.co/app |
| **Dhan Web** | Web-based trading platform | https://web.dhan.co |
| **Options Trader** | Dedicated options trading interface | https://dhan.co/options-trader |
| **DhanHQ API** | REST + binary WebSocket API for developers | https://dhanhq.co |
| **Dhan TV** | Market analysis and education content | https://dhan.co/tv |

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
- AMC: ₹0 (no annual charges for trading account)
- DP charges: Standard CDSL charges

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **Trading API** | **FREE** | REST API for orders, positions, holdings, portfolio |
| **Data API** | **FREE** (with 25 F&O trades/month) OR **₹499/month** | Market data WebSocket, historical data, option chain |

**Note:** Two-tier pricing is Dhan's unique model. Trading APIs are always free. Data APIs (WebSocket, historical, option chain) require either 25 F&O trades/month or a ₹499/month subscription.

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

1. **200-level market depth** — Unique in India; only broker offering 200 bid/ask levels (1 instrument per WS connection)
2. **Little Endian binary WebSocket** — Only Indian broker using Little Endian byte order
3. **Super Order** — Bracket order combining entry + target + stop-loss + trailing in a single API call
4. **Kill Switch API** — Programmatically disable all trading for risk management
5. **P&L-based auto-exit** — Auto-exit all positions when profit/loss threshold is hit
6. **Forever Orders (GTT)** — Persistent orders valid up to 365 days with OCO support
7. **Static token** — Long-lived API token (until manually revoked), no daily re-auth needed
8. **Postback webhook** — HTTP webhook for order updates (configure in web portal)
9. **Built for derivatives** — Options Trader interface and F&O-focused features

## AlgoChanakya Usage

In AlgoChanakya, Dhan is used for:
- **Order execution** via DhanOrderAdapter (fully implemented) — Trading API is always FREE
- **Market data** via DhanMarketDataAdapter — **user-level only**, NOT platform-level
- **WebSocket ticks** via Little Endian binary ticker adapter — **user-level only**, NOT platform-level
- **Failover chain note** — Dhan is listed second in the platform data failover chain (SmartAPI → **Dhan** → Fyers → Paytm → Upstox → Kite), BUT it can only serve as a failover for users with an active paid Data API subscription (₹499/month or 25 F&O trades/month per account). It is NOT a universal platform-level fallback.
- **Platform market data** = SmartAPI (`.env` credentials, free for all users). Dhan data = per-user opt-in via Settings page.

### Data API Subscription Flow (User Level)

1. User logs in with Dhan credentials
2. User goes to Settings → Dhan → enters Client ID + Access Token
3. If their Dhan account has paid Data API subscription → market data works
4. If not subscribed → API returns HTTP 401 with `{"data":{"806":"Data APIs not Subscribed"}}`
5. Backend raises `DataNotAvailableError` (not `AuthenticationError`) — this is NOT an auth failure
6. User must subscribe at: `web.dhan.co` → Profile → DhanHQ Trading APIs → Data API subscription (₹499/month)

See [SKILL.md](../SKILL.md) for complete DhanHQ API reference and adapter implementation details.
