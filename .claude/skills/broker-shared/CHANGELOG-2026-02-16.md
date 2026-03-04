# Broker Skills Update - February 16, 2026

## Summary
All broker expert skills and the cross-broker comparison matrix have been updated with the latest API data verified from official sources as of February 16, 2026.

---

## 🔴 Critical Updates (Pricing Changes)

### 1. Upstox - PRICING CORRECTION
**Previous:** Incorrectly listed as "FREE"
**Current:** ₹499/month (₹499 + GST) for API access

**Impact:** HIGH - Users expecting free API will be surprised by charges

**Changes Made:**
- Updated pricing in API Overview table
- Updated introductory description
- Added as first gotcha in Common Gotchas section
- Updated comparison matrix pricing table

**Sources:**
- https://upstox.com/trading-api/
- https://community.upstox.com/t/developer-api-pricing/3796

---

### 2. Zerodha Kite Connect - PRICING UPDATE
**Previous:** Listed as "₹500/mo" without clarification
**Current:**
- Connect API: ₹500/month (includes market data + historical data since Feb 2025)
- Personal API: FREE (since March 2025) - orders only, NO market data

**Impact:** MEDIUM - Users need to understand the two-tier model

**Changes Made:**
- Clarified pricing in API Overview table
- Updated introductory description with both API types
- Added 3 new gotchas explaining Personal API limitations and historical data inclusion
- Updated comparison matrix with footnote

**Sources:**
- https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect
- https://kite.trade/forum/discussion/15015/revising-kite-connect-fees-from-2000-to-500-per-month
- https://www.marketcalls.in/fintech/zerodha-makes-trading-api-free-for-personal-use-bundles-historical-data-with-connect-api.html

---

### 3. Dhan - PRICING CLARIFICATION
**Previous:** "FREE (25 F&O trades/mo) or ₹499/mo unlimited" (unclear)
**Current:**
- Trading API: FREE for all users
- Data API: FREE with 25 F&O trades/month OR ₹499/month subscription

**Impact:** MEDIUM - Two-tier pricing model needed clarification

**Changes Made:**
- Restructured pricing in API Overview table to show separate Trading/Data API costs
- Updated introductory description to explain two-tier model
- Added "Two-tier pricing model" as first gotcha
- Added "Data API unlock requirement" as seventh gotcha
- Updated comparison matrix with footnote

**Sources:**
- https://www.chittorgarh.com/broker/dhan/api-for-algo-trading-review/176/
- https://dhanhq.co/docs/v2/live-market-feed/

---

## 🟡 Feature Updates

### 4. Fyers - API v3.0.0 UPDATE
**Previous:** v3 (no specific version), 200 symbols max
**Current:** v3.0.0 (released Feb 3, 2026), 5,000 symbols max

**Impact:** MEDIUM - Significant capacity increase for WebSocket

**Changes Made:**
- Updated API Version to "v3.0.0 (released Feb 3, 2026)"
- Changed max symbols from 200 to 5,000 in WebSocket Limits table
- Updated introductory description to mention 5K capacity and Position Socket
- Added v3.0.0 breaking changes as first gotcha
- Updated comparison matrix max tokens

**Sources:**
- https://fyers.in/community/api-algo-trading-bihtdkgq/post/fyers-api-v3-new-and-improved-version-of-our-trading-api-GlOwKlt3w0cVrgm
- https://support.fyers.in/portal/en/kb/articles/what-functionalities-does-the-order-websocket-in-api-v3-offer

---

## ✅ No Changes Required

### 5. SmartAPI (Angel One)
**Status:** All information verified as accurate
- Pricing: FREE ✅
- Rate limits: 1 req/sec ✅
- WebSocket: Binary V2, 3000 tokens ✅
- Auto-TOTP: Confirmed ✅

**Sources:**
- https://www.angelone.in/knowledge-center/smartapi/detailed-introduction-to-smartapi
- https://www.brandmakes.com/blogs/post/what-is-the-cost-of-using-angel-one-api

---

### 6. Paytm Money
**Status:** All information verified as accurate
- Pricing: FREE ✅
- 3-token system: Confirmed ✅
- Least mature API: Still accurate ✅

**Sources:**
- https://developer.paytmmoney.com/
- https://github.com/paytmmoney/pyPMClient

---

## 📊 Comparison Matrix Updates

### Updated Pricing Table
**Before:**
```
| Upstox | FREE | FREE | ₹0 | Extended token free |
| Kite   | ₹500/mo | FREE | ₹500 | Personal API free |
| Dhan   | FREE | FREE (25 F&O/mo) | ₹0-499 | ₹499/mo unlimited |
```

**After:**
```
| Upstox | ₹499/mo | ₹499/mo | ₹499 | API subscription required |
| Kite   | ₹500/mo* | FREE | ₹0-500 | *Personal API free (orders only, no data) |
| Dhan   | FREE† | FREE | ₹0-499 | †25 F&O trades/mo OR ₹499/mo for data |
```

### Updated WebSocket Capabilities
**Fyers max tokens:** 200 → **5,000** (v3.0.0 upgrade)

### Updated Recommendations
**Free market data:** "SmartAPI or Upstox" → "SmartAPI, Fyers, or Paytm" (Upstox no longer free)
**Highest symbol capacity:** NEW - "Fyers - 5,000 symbols/conn (v3.0.0)"

### Added Notes Section
Detailed footnotes explaining:
- Kite Connect's bundled historical data (since Feb 2025)
- Upstox's shift from free to paid model
- Dhan's two-tier pricing structure

---

## Files Modified

1. ✅ `.claude/skills/zerodha-expert/SKILL.md` (3 updates → renamed from kite-expert, v3.0)
2. ✅ `.claude/skills/upstox-expert/skill.md` (3 updates)
3. ✅ `.claude/skills/dhan-expert/skill.md` (3 updates)
4. ✅ `.claude/skills/fyers-expert/skill.md` (4 updates)
5. ✅ `.claude/skills/broker-shared/comparison-matrix.md` (4 updates)

**Total:** 17 edits across 5 files

---

## Verification Sources

All updates verified against:
- Official broker documentation (2026)
- Broker community forums
- Third-party reviews (Chittorgarh, MarketCalls)
- PyPI package documentation

**Date of verification:** February 16, 2026

---

## Impact Assessment

### High Impact (Immediate User Impact)
1. **Upstox pricing correction** - Users planning to use Upstox must budget ₹499/month
2. **Kite Personal API clarification** - Free API doesn't include market data

### Medium Impact (Architecture Planning)
1. **Dhan two-tier model** - Need to handle conditional data access based on trading volume
2. **Fyers 5K capacity** - Can support much larger watchlists now

### Low Impact (Documentation Quality)
1. **Kite historical data bundling** - Simplifies pricing structure
2. **Fyers v3.0.0 notes** - Version awareness for developers

---

## Recommended Next Steps

1. ✅ **DONE:** Update all broker skills with latest 2026 data
2. ✅ **DONE:** Update comparison matrix with verified pricing
3. 🔲 **TODO:** Update main CLAUDE.md pricing table (if exists)
4. 🔲 **TODO:** Update backend/CLAUDE.md broker references (if needed)
5. 🔲 **TODO:** Update docs/architecture/broker-abstraction.md pricing section
6. 🔲 **TODO:** Update docs/decisions/002-broker-abstraction.md if pricing impacts decisions

---

## Testing Recommendations

Before implementing adapters:
1. **Upstox:** Verify ₹499/month subscription process
2. **Kite:** Test both Personal API (free) and Connect API (₹500/mo) scenarios
3. **Dhan:** Implement 25 trades/month check for data access gating
4. **Fyers:** Test v3.0.0 SDK with 5K symbol subscriptions

---

## Documentation Maintenance

**Frequency:** Quarterly review recommended
**Next Review:** May 2026
**Trigger Events:** Broker API version changes, pricing updates, feature releases

**Monitoring:**
- Subscribe to broker API changelogs
- Monitor broker community forums
- Check PyPI package releases for SDK updates

---

**Document Created:** February 16, 2026
**Created By:** Claude Code Auto-Update Process
**Verification Status:** ✅ All sources verified and cited
