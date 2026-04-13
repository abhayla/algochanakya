---
name: broker-shared
description: >
  Cross-broker comparison, shared gotchas, instrument token architecture, and broker selection guidance.
  INVOKE when: discussing multiple brokers, comparing brokers, broker failover, broker selection,
  auto-refresh across brokers, platform_token_refresh, token expiry patterns, NOT_REFRESHABLE brokers,
  failover chain order, token_policy.py, refresh_broker_token.
  Also triggers on instrument token, instrument_token, exchange token, exchange_token,
  symbol token, symboltoken, instrument key, instrument_key, tradingsymbol,
  trading_symbol, token mapping, token_to_symbol, instrument master, broker token,
  NSE token, cross-broker token, token mismatch, duplicate instrument, source_broker.
version: "2.0.0"
last_verified: "2026-04-12"
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

### 6. Auto-Capture New Findings

When new cross-broker instrument or token knowledge is discovered during debugging or research,
append it to `references/instrument-token-architecture.md` without waiting for user prompting.

Format for new entries:
```markdown
## New Finding: {title}

**Date:** YYYY-MM-DD
**Source:** {how this was discovered — debugging session, API testing, documentation review}

{content}
```

This ensures the reference stays current as the platform evolves and new broker behaviors are discovered.

## Platform Failover Chain

```
SmartAPI → Dhan → Fyers → Paytm → Upstox → Kite Connect
(FREE)    (FREE)  (FREE)  (FREE)   (₹499)   (₹500, last resort)
```

Platform-level credentials serve ALL users by default. User-level (own API key) is an optional upgrade.

## Token Auto-Refresh & Error Classification

All broker auth errors are classified by `token_policy.py` into 4 categories:

| Category | Action | Brokers |
|----------|--------|---------|
| RETRYABLE | 3x exponential backoff | All (network errors, rate limits) |
| RETRYABLE_ONCE | 30s TOTP wait + 1 retry | SmartAPI (TOTP timing) |
| NOT_RETRYABLE | Instant failover | All (config errors like wrong API key) |
| NOT_REFRESHABLE | Instant failover + frontend notification | Kite, Dhan, Fyers, Paytm |

**Auto-refreshable**: SmartAPI (pyotp TOTP), Upstox (upstox-totp library)
**Manual refresh required**: Kite (OAuth), Dhan (portal), Fyers (OAuth), Paytm (portal)

Key files: `token_policy.py` (classification), `platform_token_refresh.py` (refresh logic), `health.py` (scoring), `failover.py` (switching)

## Version Changelog

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-03-18 | Frontmatter aligned with broker-expert pattern (top-level version + last_verified, removed nested metadata). Added Version Changelog section. No content changes. |
| 2.0.0 | 2026-04-12 | Added instrument-token-architecture reference, trigger words for auto-discovery, auto-capture workflow for new findings. |

## Cross-References

- **Comparison Matrix:** `comparison-matrix.md` (same directory) — detailed feature-by-feature comparison
- **Common Gotchas:** `references/common-gotchas.md` — shared integration pitfalls
- **Instrument Token Architecture:** `references/instrument-token-architecture.md` — Cross-broker instrument token architecture, NSE exchange token equivalence, tradingsymbol formats
- **Architecture:** `docs/architecture/broker-abstraction.md` — adapter pattern design
- **Working Doc:** `docs/architecture/Working-Doc-AlgoChanakya-Multi-Broker-Architecture-Platform-Level.md`
- **Individual experts:** `/zerodha-expert`, `/angelone-expert`, `/upstox-expert`, `/dhan-expert`, `/fyers-expert`, `/paytm-expert`
