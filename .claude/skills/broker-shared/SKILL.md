---
name: broker-shared
description: Cross-broker comparison, shared gotchas, and broker selection guidance.
  Use for questions spanning multiple brokers or common integration patterns.
version: "1.0.0"
last_verified: "2026-03-18"
---

# Broker Shared Knowledge

Cross-broker reference skill for questions that span multiple brokers, common integration gotchas, and broker selection guidance.

## When to Use

- Comparing features, pricing, or capabilities across brokers
- Debugging issues that could affect multiple broker integrations
- Deciding which broker to use for a specific feature (market data, orders, historical)
- Understanding shared gotchas (token expiry, symbol formats, rate limits)
- Questions about the platform-level failover chain
- Adding a new broker adapter (need to understand existing patterns)

## When NOT to Use

- **Broker-specific API questions** → Delegate to the relevant expert skill:
  - `/zerodha-expert` — Kite Connect API, OAuth flow, Kite Ticker
  - `/angelone-expert` — SmartAPI, TOTP auth, 3-key model
  - `/upstox-expert` — Upstox API v2, OAuth, WebSocket
  - `/dhan-expert` — DhanHQ API, static token auth
  - `/fyers-expert` — Fyers API v3, OAuth, data API
  - `/paytm-expert` — Paytm Money API, 3-JWT model
- **Implementation details** for a single broker's adapter
- **Debugging a single broker** connection issue (use that broker's expert)

## Steps

### 1. Identify Question Type

Classify the user's question:

| Type | Example | Action |
|------|---------|--------|
| **Comparison** | "Which broker has the best WebSocket?" | Reference comparison-matrix.md |
| **Shared gotcha** | "Why do tokens expire?" | Reference common-gotchas.md |
| **Broker selection** | "Which broker for historical data?" | Use decision matrix below |
| **Cross-broker pattern** | "How do symbol formats differ?" | Reference comparison-matrix.md + gotchas |
| **Broker-specific** | "How does SmartAPI TOTP work?" | Delegate to `/angelone-expert` |

### 2. Reference Comparison Matrix

For comparison questions, consult `comparison-matrix.md` (same directory). Key sections:

| Section | Content |
|---------|---------|
| 1 | Authentication methods per broker |
| 2 | Market data capabilities (WebSocket, REST, historical) |
| 3 | Rate limits and throttling |
| 4 | Order types and execution |
| 5 | Symbol format and instrument mapping |
| 6 | Pricing and costs |
| 7 | WebSocket architecture |
| 8 | Historical data access |
| 9 | Error handling patterns |
| 10 | Platform failover chain |
| 11 | Implementation status |

### 3. Reference Common Gotchas

For integration issues, consult `references/common-gotchas.md`. Categories:
- Token expiry and refresh patterns
- Symbol format conversion
- Rate limiting strategies
- WebSocket reconnection
- Price unit differences
- Order status mapping
- Market hours handling
- Multi-key confusion (AngelOne)

### 4. Broker Selection Decision Matrix

| Need | Recommended Broker | Why |
|------|-------------------|-----|
| **Free market data** | SmartAPI (AngelOne) | FREE, 9K token capacity |
| **Free historical data** | SmartAPI or Fyers | Both free, SmartAPI faster |
| **Reliable WebSocket** | Kite Connect | Most stable, but ₹500/mo |
| **Cheapest orders** | Dhan | ₹0 delivery, ₹20 F&O |
| **Longest token life** | Upstox | ~1 year OAuth token |
| **Static auth (no OAuth)** | Dhan | Static token, no expiry flow |
| **Platform default** | SmartAPI | First in failover chain |

### 5. Delegate if Broker-Specific

If the question is about a single broker's internals, respond with:
```
This is a broker-specific question. Use `/[broker]-expert` for detailed guidance.
```

## Platform Failover Chain

```
SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
(FREE)    (FREE)  (FREE)  (FREE)   (₹499)   (₹500, last resort)
```

Platform-level credentials serve ALL users by default. User-level (own API key) is an optional upgrade.

## Version Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-03-18 | Frontmatter aligned with broker-expert pattern (top-level version + last_verified, removed nested metadata). Added Version Changelog section. No content changes. |

## Cross-References

- **Comparison Matrix:** `comparison-matrix.md` (same directory) — detailed feature-by-feature comparison
- **Common Gotchas:** `references/common-gotchas.md` — shared integration pitfalls
- **Architecture:** `docs/architecture/broker-abstraction.md` — adapter pattern design
- **Working Doc:** `docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md`
- **Individual experts:** `/zerodha-expert`, `/angelone-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert`
