# Paytm Money — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Paytm Money Limited (subsidiary of One97 Communications Ltd.) |
| **Founded** | 2019 (Bengaluru, India) |
| **Parent Company** | One97 Communications (Paytm) |
| **Headquarters** | Bengaluru, Karnataka, India |
| **SEBI Registration** | INZ000240032 (Member: NSE, BSE) |
| **Market Position** | Fintech-backed broker leveraging Paytm's massive user base |
| **Business Model** | Discount broker — flat-fee pricing, digital-first |
| **API Brand** | Paytm Money API |
| **Website** | https://www.paytmmoney.com |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Paytm Money App** | Mobile trading app (Android & iOS) | https://www.paytmmoney.com/stocks |
| **Paytm Money Web** | Web-based trading platform | https://wealth.paytmmoney.com |
| **Paytm Money API** | REST + JSON WebSocket API for developers | https://developer.paytmmoney.com |
| **Paytm Money MF** | Mutual fund investment platform | https://www.paytmmoney.com/mutual-funds |

## Brokerage Charges

| Segment | Brokerage | Notes |
|---------|-----------|-------|
| **Equity Delivery** | ₹0 (FREE) | No brokerage on delivery trades |
| **Equity Intraday** | ₹20/order or 0.05% (whichever is lower) | Flat fee |
| **F&O (Futures)** | ₹20/order or 0.05% (whichever is lower) | Per executed order |
| **F&O (Options)** | ₹20/order | Flat fee per executed order |
| **Currency** | Not available | Paytm Money does not support currency segment |

**Other Charges:**
- Account opening: FREE (online)
- AMC: ₹0 (no annual charges)
- DP charges: Standard CDSL charges on sell delivery

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **Paytm Money API** | **FREE** | REST API, JSON WebSocket, market data, historical data |

**Note:** Paytm Money API is free. However, the SDK (`pyPMClient`) was last updated in Jul 2024 and has limited maintenance.

## Supported Exchanges

| Exchange | Segments |
|----------|----------|
| **NSE** | Equity, F&O (Index + Stock) |
| **BSE** | Equity, F&O (added in 2025: SENSEX, BANKEX options) |

**Note:** No MCX commodity support. No currency derivatives.

## Account Types

| Type | Supported | Notes |
|------|-----------|-------|
| Individual | Yes | Standard demat + trading |
| Joint (Primary) | Yes | Primary holder can trade |
| HUF | Yes | Hindu Undivided Family |
| Corporate | Limited | Check availability |
| NRI | Limited | Check availability |

## Key Differentiators

1. **3-token JWT system** — Unique authentication with `access_token`, `public_access_token` (WebSocket), `read_access_token` (read-only)
2. **Heckyl-powered Greeks** — Option chain data with Greeks sourced from Heckyl Technologies
3. **Paytm ecosystem integration** — Leverages Paytm's massive user base for user acquisition
4. **FREE API** — No subscription charges for API access
5. **Custom auth header** — Uses `x-jwt-token` header (not standard `Authorization: Bearer`)

## Maturity Warning

**Paytm Money API is the least mature among the 6 supported brokers in AlgoChanakya.** Expect:
- Limited documentation with sparse examples
- Occasional breaking changes without deprecation notices
- Lower SDK quality (`pyPMClient` last updated Jul 2024)
- Less community support compared to Zerodha, Upstox, or Angel One
- Limited F&O coverage (no MCX, no currency)
- No HTTP webhooks and no order update WebSocket — REST polling only

## AlgoChanakya Usage

In AlgoChanakya, Paytm Money is used for:
- **Order execution** via PaytmOrderAdapter (fully implemented)
- **Market data** via PaytmMarketDataAdapter (fully implemented)
- **WebSocket ticks** via JSON-based ticker adapter (fully implemented)
- **Fourth in failover chain** — Platform data failover: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
- **Least mature adapter** — Extra defensive error handling recommended

See [SKILL.md](../SKILL.md) for complete Paytm Money API reference and adapter implementation details.
