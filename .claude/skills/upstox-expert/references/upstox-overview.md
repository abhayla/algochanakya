# Upstox — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Upstox (RKSV Securities India Pvt. Ltd.) |
| **Founded** | 2012 (Mumbai, India) |
| **Founders** | Ravi Kumar, Shrini Viswanath, Kavitha Subramanian |
| **Headquarters** | Mumbai, Maharashtra, India |
| **SEBI Registration** | INZ000185137 (Member: NSE, BSE, MCX) |
| **Market Position** | Among India's top discount brokers (10M+ users), backed by Ratan Tata & Tiger Global |
| **Business Model** | Discount broker — flat-fee pricing, technology-first |
| **API Brand** | Upstox API (v2/v3) |
| **Website** | https://upstox.com |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Upstox Pro App** | Mobile trading app (Android & iOS) | https://upstox.com/app |
| **Upstox Pro Web** | Web-based trading platform | https://pro.upstox.com |
| **Upstox API** | REST + Protobuf WebSocket API (v2/v3) | https://upstox.com/developer/api-documentation |
| **Upstox MF** | Mutual fund investment platform | https://upstox.com/mutual-funds |

## Brokerage Charges

| Segment | Brokerage | Notes |
|---------|-----------|-------|
| **Equity Delivery** | ₹0 (FREE) | No brokerage on delivery trades |
| **Equity Intraday** | ₹20/order or 0.05% (whichever is lower) | Flat fee |
| **F&O (Futures)** | ₹20/order | Per executed order |
| **F&O (Options)** | ₹20/order | Flat fee per executed order |
| **Currency** | ₹20/order | Per executed order |
| **Commodity** | ₹20/order | Per executed order |

**Other Charges:**
- Account opening: FREE (online)
- AMC: ₹0 (no annual charges)
- DP charges: Standard CDSL charges on sell delivery
- API brokerage: ₹10/order (promotional rate till Mar 2026)

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **Upstox API** | **FREE** | REST API, Protobuf WebSocket, market data, historical data, option chain with Greeks |

**Note:** Upstox API pricing changed from ₹499/month to FREE in 2025. All trading and data APIs are now free.

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

1. **Protobuf WebSocket** — Only Indian broker using Protocol Buffers for WebSocket (efficient binary serialization)
2. **Real-time Greeks via WebSocket** — Unique `option_greeks` mode streams delta, gamma, theta, vega, IV in real-time
3. **Extended token** — 1-year read-only token for market data (no daily re-auth for data access)
4. **FREE API** — Zero cost for all trading and data APIs (changed from ₹499/month in 2025)
5. **Multi-order APIs** — Batch place, cancel, and exit positions in single API calls
6. **MCP integration** — Supports Claude Desktop / VS Code MCP for read-only portfolio access
7. **Sandbox environment** — Test order flows without real money (available since Jan 2025)
8. **6 SDK languages** — Python, JavaScript, .NET, Java, C#, PHP

## AlgoChanakya Usage

In AlgoChanakya, Upstox is used for:
- **Order execution** via UpstoxOrderAdapter (fully implemented)
- **Market data** via UpstoxMarketDataAdapter (fully implemented)
- **WebSocket ticks** via Protobuf-based ticker adapter (fully implemented)
- **Fifth in failover chain** — Platform data failover: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
- **Extended token advantage** — Can maintain market data access for 1 year without daily re-auth

See [SKILL.md](../SKILL.md) for complete Upstox API reference and adapter implementation details.
