# Zerodha — Broker Overview

## Company Profile

| Property | Value |
|----------|-------|
| **Full Name** | Zerodha Broking Limited |
| **Founded** | 2010 (Bengaluru, India) |
| **Founders** | Nithin Kamath, Nikhil Kamath |
| **Headquarters** | Bengaluru, Karnataka, India |
| **SEBI Registration** | INZ000031633 (Member: NSE, BSE, MCX) |
| **Market Position** | Largest retail stockbroker in India by active clients (~14M+) |
| **Business Model** | Discount broker — flat-fee pricing, technology-first |
| **Website** | https://zerodha.com |

## Products & Platforms

| Product | Description | URL |
|---------|-------------|-----|
| **Kite** | Flagship web & mobile trading platform | https://kite.zerodha.com |
| **Console** | Back-office: reports, P&L, tax statements, corporate actions | https://console.zerodha.com |
| **Coin** | Direct mutual fund platform (zero commission) | https://coin.zerodha.com |
| **Varsity** | Free stock market education (modules, videos) | https://zerodha.com/varsity |
| **Sentinel** | Price alerts (free, no login needed for basic) | https://sentinel.zerodha.com |
| **Kite Connect** | REST + WebSocket API for third-party apps | https://kite.trade |
| **Streak** | Algo/strategy builder (no-code, backtesting) | https://streak.zerodha.com |
| **Smallcase** | Thematic investment portfolios (via partner) | https://smallcase.zerodha.com |

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
- Annual Maintenance Charge (AMC): ₹300/year (demat account)
- DP charges: ₹15.93/scrip (on sell delivery)
- Pledge/unpledge: ₹30 + GST per request

## API Costs

| API Product | Cost | Includes |
|-------------|------|----------|
| **Kite Connect** | ₹500/month | REST API, WebSocket, live market data, historical data (since Feb 2025) |
| **Personal API** | FREE | Order execution only — NO market data, NO historical data (since March 2025) |
| **Publisher** | FREE (with Connect) | Postback URLs for order updates |

**Note:** Personal API is free but severely limited — suitable only for personal order automation. For any app that needs quotes, ticks, or OHLC data, Kite Connect (₹500/month) is required.

## Supported Exchanges

| Exchange | Segments |
|----------|----------|
| **NSE** | Equity, F&O (Index + Stock), Currency |
| **BSE** | Equity, F&O (limited), Currency |
| **MCX** | Commodity Futures & Options |
| **CDS** | Currency Derivatives (NSE CDS segment) |

## Account Types

| Type | Supported | Notes |
|------|-----------|-------|
| Individual | Yes | Standard demat + trading |
| Joint (Primary) | Yes | Primary holder can trade |
| HUF | Yes | Hindu Undivided Family |
| Corporate | Yes | LLP, Pvt Ltd, Partnership |
| NRI (NRE/NRO) | Yes | NRE for repatriable, NRO for non-repatriable |

## Key Differentiators

1. **Largest broker by active clients** — 14M+ active accounts, dominant market share
2. **Technology-first** — In-house built platforms (Kite, Console, Coin), open-source contributions
3. **Flat-fee pricing** — ₹20/order cap across all segments (pioneered discount broking in India)
4. **Free equity delivery** — Zero brokerage on equity delivery trades
5. **Kite Connect API** — Well-documented, stable REST + binary WebSocket API
6. **Canonical symbol format** — Kite's symbol format is used as the canonical standard in AlgoChanakya
7. **Education focus** — Varsity is the most popular free stock market education platform in India
8. **No advisory/tips** — Execution-only model, no research recommendations

## AlgoChanakya Usage

In AlgoChanakya, Zerodha is used for:
- **Order execution** via Kite Connect REST API (fully implemented)
- **Symbol format standard** — Kite format IS the canonical format, no conversion needed
- **NOT used for market data** by default — SmartAPI (Angel One) is the platform default for live ticks and OHLC (free vs ₹500/month)
- **Last in failover chain** — Platform data failover: SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect (most expensive)

See [SKILL.md](../SKILL.md) for complete Kite Connect API reference and adapter implementation details.
