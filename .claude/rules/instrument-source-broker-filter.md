---
name: instrument-source-broker-filter
description: >
  The instruments table holds duplicate rows per symbol from multiple
  source_brokers (kite + smartapi, different exchange tokens). Every instrument
  query MUST filter by source_broker via instrument_query.py — never raw selects.
globs: ["backend/app/services/brokers/market_data/instrument_query.py", "backend/app/api/routes/options.py"]
synthesized: true
version: "1.0.0"
private: false
---

# Instrument Queries — Always Filter by source_broker

The `instruments` table contains duplicate rows for the same contract: one row
per `source_broker` (kite and smartapi), each with a DIFFERENT
`instrument_token` for the same strike. An unfiltered query returns mixed-token
duplicates and crashes `scalar_one_or_none()` — this exact duplicate-row bug
was killed in commit `edc47b9`.

All instrument lookups go through
`backend/app/services/brokers/market_data/instrument_query.py`.

## Domain facts (state these, don't rediscover them)

- **SmartAPI and Upstox share NSE exchange tokens** (confirmed April 2026 —
  comment at lines 29-30). That is why both map to smartapi-sourced rows.
- **Kite has its own internal token numbering** — a kite-row token is NOT
  valid for SmartAPI/Upstox API calls, and vice versa.
- Unknown broker types cascade to the default `["kite", "smartapi"]`
  (kite-first fallback, line 43).

## The preference map — lines 31-38

```python
_SOURCE_BROKER_PREFERENCE = {
    "smartapi": ["smartapi", "kite"],
    "upstox":   ["smartapi", "kite"],   # shares NSE tokens with smartapi
    "kite":     ["kite", "smartapi"],
    "dhan":     ["smartapi", "kite"],
    "fyers":    ["smartapi", "kite"],
    "paytm":    ["smartapi", "kite"],
}
```

`preferred_source_brokers(broker_type)` (lines 41-43) resolves it,
case-insensitively, with the kite-first default for unknown brokers.

## Cascade semantics — fall through only when EMPTY

- `get_nfo_instruments()` (lines 46-93): for each source in preference order,
  run ONE filtered select (`Instrument.source_broker == source`, line 77,
  alongside name/NFO/CE-PE/expiry/strike-not-null). Return the FIRST
  non-empty result. Only an empty result moves to the next source. An
  exhausted cascade returns `[]` with a warning — never a mixed list.
- `get_single_instrument()` (lines 96-139): same cascade for one
  (underlying, expiry, strike, contract_type) row via
  `scalar_one_or_none()` — the source filter is what makes
  `scalar_one_or_none()` safe at all.
- MUST NOT merge rows from two sources in one result set. A chain built from
  mixed sources subscribes with tokens half-valid for the active broker, which
  surfaces as partially-dead chains, not as an error.

## Extending

- New query helpers (different exchange, instrument_type, etc.) MUST live in
  `instrument_query.py` and reuse `preferred_source_brokers()` + the
  empty-only cascade. NEVER write a raw `select(Instrument)` without a
  `source_broker` filter elsewhere in the codebase — `options.py` and the
  option-chain services are the consumers, not the place for bespoke selects.
  (Narrow exception: queries on columns identical across sources, e.g. the
  distinct-expiry lookup in `option_chain_prefetch.py` lines 42-59, still pin
  `source_broker == "kite"` rather than going unfiltered — follow that pattern.)
- Adding a broker: add an explicit entry to `_SOURCE_BROKER_PREFERENCE` —
  decide deliberately whether it shares NSE tokens (→ smartapi-first) or has
  its own numbering. Do not rely on the unknown-broker default.

## CRITICAL RULES

- Every query against `instruments` MUST filter by `source_broker` — no raw unfiltered selects (regression: commit `edc47b9`).
- MUST resolve source order via `preferred_source_brokers(broker_type)`; MUST NOT hardcode `"kite"` or `"smartapi"` in new call sites.
- Cascade falls through ONLY on an empty result; MUST NEVER mix rows from two source_brokers in one result.
- `get_single_instrument()` is the only sanctioned single-row lookup — bare `scalar_one_or_none()` on instruments will crash on duplicates.
- New brokers get an explicit `_SOURCE_BROKER_PREFERENCE` entry; token-sharing with SmartAPI/Upstox MUST be verified, not assumed.
- New instrument query helpers go in `instrument_query.py`, nowhere else.
