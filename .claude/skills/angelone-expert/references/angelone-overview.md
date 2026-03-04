# Angel One — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Angel One Limited (formerly Angel Broking Limited) |
| **Founded** | 1996 (Mumbai, India) |
| **Rebranded** | 2021 (Angel Broking → Angel One) |
| **Headquarters** | Mumbai, Maharashtra, India |
| **SEBI Registration** | INZ000161534 (Member: NSE, BSE, MCX, NCDEX) |
| **Market Position** | Among India's largest retail brokers (25M+ clients) |
| **Business Model** | Discount broker — flat-fee pricing, technology-driven |
| **API Brand** | SmartAPI |
| **Website** | https://www.angelone.in |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Angel One App** | Flagship mobile trading app (Android & iOS) | https://www.angelone.in/app |
| **Angel One Web** | Web-based trading platform | https://trade.angelone.in |
| **SmartAPI** | REST + binary WebSocket API for third-party apps | https://smartapi.angelbroking.com |
| **ARQ Prime** | AI-powered investment advisory engine | https://www.angelone.in/arq |
| **Smart Money** | Stock market education and content platform | https://www.angelone.in/knowledge-center |

## Brokerage Charges

| Segment | Brokerage | Notes |
|---------|-----------|-------|
| **Equity Delivery** | ₹0 (FREE) | No brokerage on delivery trades |
| **Equity Intraday** | ₹20/order or 0.25% (whichever is lower) | Flat fee |
| **F&O (Futures)** | ₹20/order or 0.25% (whichever is lower) | Per executed order |
| **F&O (Options)** | ₹20/order | Flat fee per executed order |
| **Currency** | ₹20/order or 0.25% (whichever is lower) | Per executed order |
| **Commodity** | ₹20/order or 0.25% (whichever is lower) | Per executed order |

**Other Charges:**
- Account opening: FREE (online)
- Annual Maintenance Charge (AMC): ₹240/year (demat account, first year free)
- DP charges: ₹20/scrip (on sell delivery)

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **SmartAPI** | **FREE** | REST API, WebSocket (market data + order updates), historical data, option chain with Greeks |

**Note:** SmartAPI is completely free — no subscription fees. This makes Angel One the most cost-effective API option for AlgoChanakya's platform-level market data.

## Supported Exchanges

| Exchange | Segments |
|----------|----------|
| **NSE** | Equity, F&O (Index + Stock), Currency |
| **BSE** | Equity, F&O |
| **MCX** | Commodity Futures & Options |
| **NCDEX** | Commodity (limited) |

## Account Types

| Type | Supported | Notes |
|------|-----------|-------|
| Individual | Yes | Standard demat + trading |
| Joint (Primary) | Yes | Primary holder can trade |
| HUF | Yes | Hindu Undivided Family |
| Corporate | Yes | LLP, Pvt Ltd, Partnership |
| NRI (NRE/NRO) | Yes | NRE for repatriable, NRO for non-repatriable |

## Key Differentiators

1. **Completely FREE API** — SmartAPI has zero monthly charges for market data, orders, and historical data
2. **Auto-TOTP authentication** — No manual TOTP entry; AlgoChanakya uses `pyotp` to auto-generate codes
3. **Platform default for AlgoChanakya** — SmartAPI is the default market data provider (first in failover chain)
4. **25M+ client base** — One of India's largest retail brokers with rapid digital growth
5. **Option Chain with Greeks** — Dedicated endpoint returning delta, gamma, theta, vega, IV per strike
6. **Order Update WebSocket** — Separate real-time WebSocket for order fills and rejections
7. **ARQ Prime** — AI-powered investment advisory (unique among discount brokers)
8. **3-key API system** — Separate API keys for market data, historical data, and order execution

## AlgoChanakya Usage

In AlgoChanakya, Angel One is used for:
- **Platform-default market data** — SmartAPI is the primary data source for live ticks and OHLC (FREE)
- **Order execution** via AngelOneAdapter (fully implemented)
- **First in failover chain** — Platform data failover: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
- **3 separate API keys** in `backend/.env`: `ANGEL_API_KEY` (market data), `ANGEL_HIST_API_KEY` (historical), `ANGEL_TRADE_API_KEY` (orders)

See [SKILL.md](../SKILL.md) for complete SmartAPI reference and adapter implementation details.
