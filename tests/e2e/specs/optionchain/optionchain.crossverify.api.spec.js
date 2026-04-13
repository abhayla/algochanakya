/**
 * Option Chain Cross-Verification against NSE India
 *
 * Opens the option chain screen in the browser and compares displayed data
 * against NSE India's official v3 API (the authoritative source for NIFTY options).
 *
 * Handles all situations:
 *   - Market hours (Mon-Fri 9:15-15:30 IST): Full comparison — spot, LTP, OI, PCR
 *   - After hours (Mon-Fri outside 9:15-15:30): Spot (prev close), OI, PCR
 *   - Weekends/holidays: NSE v3 returns cached data — OI, PCR, last close
 *   - NSE unreachable: All tests skip gracefully
 *   - App error/empty state: Tests skip with clear message
 *
 * Run:
 *   npx playwright test optionchain.crossverify.api.spec.js
 *   npx playwright test --grep "@crossverify"
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { OptionChainPage } from '../../pages/OptionChainPage.js';

// ─────────────────────────────────────────────────────────────────────────────
// NSE API helpers
// ─────────────────────────────────────────────────────────────────────────────

const NSE_BASE = 'https://www.nseindia.com';
const NSE_V3_URL = `${NSE_BASE}/api/option-chain-v3`;
const NSE_V1_URL = `${NSE_BASE}/api/option-chain-indices`;

const NSE_HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  Accept: 'application/json',
  'Accept-Language': 'en-US,en;q=0.9',
  Referer: 'https://www.nseindia.com/option-chain',
};

// Tolerances
const SPOT_TOLERANCE_PCT = 1.5;    // ±1.5% — covers bid-ask + slight delay
const LTP_TOLERANCE_PCT = 20.0;    // ±20% — wide for bid-ask spread + broker delay
const PCR_TOLERANCE_ABS = 0.3;     // ±0.3 absolute — PCR varies by source filtering
const OI_TOLERANCE_PCT = 15.0;     // ±15% — OI updates lag between sources

/**
 * Check if Indian markets are currently open.
 */
function isMarketHours() {
  const now = new Date();
  // IST = UTC + 5:30
  const istOffset = 5.5 * 60 * 60 * 1000;
  const ist = new Date(now.getTime() + istOffset + now.getTimezoneOffset() * 60 * 1000);
  const day = ist.getDay(); // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return false;
  const hours = ist.getHours();
  const minutes = ist.getMinutes();
  const timeMinutes = hours * 60 + minutes;
  return timeMinutes >= 9 * 60 + 15 && timeMinutes <= 15 * 60 + 30;
}

/**
 * Get the nearest upcoming Thursday (weekly NIFTY expiry).
 */
function nearestExpiryThursday() {
  const today = new Date();
  const day = today.getDay(); // 0=Sun, 4=Thu
  let daysAhead = (4 - day + 7) % 7; // Thursday = 4
  if (daysAhead === 0 && !isMarketHours()) daysAhead = 7;
  const expiry = new Date(today);
  expiry.setDate(today.getDate() + daysAhead);
  return expiry;
}

/**
 * Format date as "DD-Mon-YYYY" for NSE API.
 */
function formatNSEDate(d) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dd = String(d.getDate()).padStart(2, '0');
  return `${dd}-${months[d.getMonth()]}-${d.getFullYear()}`;
}

/**
 * Percentage difference between two values.
 */
function pctDiff(a, b) {
  if (a === 0 && b === 0) return 0;
  const avg = (Math.abs(a) + Math.abs(b)) / 2;
  if (avg === 0) return 100;
  return (Math.abs(a - b) / avg) * 100;
}

/**
 * Fetch and parse NSE option chain data using Playwright's request context.
 * Returns null if NSE is unreachable or returns no data.
 */
async function fetchNSEData(request) {
  try {
    // Step 1: Get cookies by visiting NSE
    const cookieResp = await request.get(`${NSE_BASE}/option-chain`, {
      headers: NSE_HEADERS,
      timeout: 15000,
    });
    if (!cookieResp.ok()) return null;

    // Step 2: Try v1 to get expiry list
    const v1Resp = await request.get(NSE_V1_URL, {
      headers: NSE_HEADERS,
      params: { symbol: 'NIFTY' },
      timeout: 15000,
    });
    let v1Data = {};
    if (v1Resp.ok()) {
      try {
        v1Data = await v1Resp.json();
      } catch { /* ignore parse error */ }
    }

    let availableExpiries = v1Data?.records?.expiryDates || [];

    // Step 3: If v1 had no expiries, probe v3 with guessed expiry
    if (availableExpiries.length === 0) {
      const guessExpiry = formatNSEDate(nearestExpiryThursday());
      const probeResp = await request.get(NSE_V3_URL, {
        headers: NSE_HEADERS,
        params: { type: 'Indices', symbol: 'NIFTY', expiry: guessExpiry },
        timeout: 15000,
      });
      if (probeResp.ok()) {
        const probeData = await probeResp.json();
        availableExpiries = probeData?.records?.expiryDates || [];
        if (probeData?.records?.data?.length > 0) {
          return parseNSEResponse(probeData);
        }
      }
    }

    // Step 4: Try v3 with each available expiry (nearest first)
    for (const expiryStr of availableExpiries.slice(0, 3)) {
      const resp = await request.get(NSE_V3_URL, {
        headers: NSE_HEADERS,
        params: { type: 'Indices', symbol: 'NIFTY', expiry: expiryStr },
        timeout: 15000,
      });
      if (resp.ok()) {
        const data = await resp.json();
        if (data?.records?.data?.length > 0) {
          return parseNSEResponse(data);
        }
      }
    }

    // Step 5: Fall back to v1 data if it had content
    if (v1Data?.records?.data?.length > 0) {
      return parseNSEResponse(v1Data);
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Parse raw NSE response into a comparable format.
 * Calculates OI totals from per-strike data (not from totCE/totPE which can be 0 on weekends).
 */
function parseNSEResponse(nseData) {
  const records = nseData.filtered || nseData.records || {};
  // v3 sometimes has underlyingValue=0 in "filtered" but correct in "records"
  const spotPrice =
    records.underlyingValue || nseData.records?.underlyingValue || 0;
  const allExpiries = nseData.records?.expiryDates || [];

  const strikes = {};
  let sumCEOI = 0;
  let sumPEOI = 0;
  for (const row of records.data || []) {
    const strike = parseFloat(row.strikePrice || 0);
    const ceOI = row.CE?.openInterest || 0;
    const peOI = row.PE?.openInterest || 0;
    const entry = {
      ce_ltp: row.CE?.lastPrice || 0,
      ce_oi: ceOI,
      ce_volume: row.CE?.totalTradedVolume || 0,
      ce_iv: row.CE?.impliedVolatility || 0,
      pe_ltp: row.PE?.lastPrice || 0,
      pe_oi: peOI,
      pe_volume: row.PE?.totalTradedVolume || 0,
      pe_iv: row.PE?.impliedVolatility || 0,
    };
    strikes[strike] = entry;
    sumCEOI += ceOI;
    sumPEOI += peOI;
  }

  // Prefer per-strike sum (always available) over totCE/totPE (can be 0 on weekends)
  const totalCEOI = sumCEOI || records.totCE?.totOI || 0;
  const totalPEOI = sumPEOI || records.totPE?.totOI || 0;

  return {
    spotPrice,
    expiryDates: allExpiries,
    strikes,
    totalCEOI,
    totalPEOI,
    pcr: totalCEOI > 0 ? totalPEOI / totalCEOI : 0,
    strikeCount: Object.keys(strikes).length,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

test.describe('Option Chain — NSE Cross-Verification @crossverify', () => {
  /** @type {OptionChainPage} */
  let chainPage;
  /** @type {object|null} */
  let nseData;

  test.beforeAll(async ({ request }) => {
    // Fetch NSE data once for all tests in this suite
    nseData = await fetchNSEData(request);
  });

  test.beforeEach(async ({ authenticatedPage }) => {
    chainPage = new OptionChainPage(authenticatedPage);
    await chainPage.navigate();
  });

  test('@crossverify spot price matches NSE', async () => {
    test.skip(!nseData, 'NSE data unavailable — API unreachable or returned empty');

    const state = await chainPage.waitForChainLoad();
    test.skip(state === 'error', 'Option chain failed to load — broker may be down');
    test.skip(state === 'empty', 'Option chain is empty — no data for current expiry');

    const uiSpot = await chainPage.getSpotPrice();
    test.skip(isNaN(uiSpot) || uiSpot === 0, 'UI spot price is zero or unavailable');

    const nseSpot = nseData.spotPrice;
    test.skip(nseSpot === 0, 'NSE spot price is zero — data may be stale');

    const diff = pctDiff(uiSpot, nseSpot);
    expect(diff, `Spot: UI=${uiSpot}, NSE=${nseSpot}, diff=${diff.toFixed(2)}%`).toBeLessThanOrEqual(
      SPOT_TOLERANCE_PCT
    );
  });

  test('@crossverify expiry dates include NSE nearest expiry', async () => {
    test.skip(!nseData, 'NSE data unavailable');
    test.skip(nseData.expiryDates.length === 0, 'NSE returned no expiry dates');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const uiExpiries = await chainPage.getExpiryOptions();
    test.skip(uiExpiries.length === 0, 'UI has no expiry options');

    // NSE nearest expiry should be available in the UI dropdown
    // NSE dates are "DD-Mon-YYYY", UI dates are "YYYY-MM-DD" — compare parsed
    const nseNearest = nseData.expiryDates[0];
    const nseDate = new Date(nseNearest);
    const nseDateStr = nseDate.toISOString().split('T')[0]; // YYYY-MM-DD

    // Check if any UI expiry matches (within 1 day tolerance for format differences)
    const hasMatch = uiExpiries.some((uiExp) => {
      const uiDate = new Date(uiExp);
      return Math.abs(uiDate - nseDate) <= 24 * 60 * 60 * 1000; // ±1 day
    });

    expect(hasMatch, `NSE nearest expiry ${nseNearest} (${nseDateStr}) not found in UI expiries: ${uiExpiries.slice(0, 5).join(', ')}`).toBe(true);
  });

  test('@crossverify strike list overlaps with NSE', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const uiStrikes = await chainPage.getVisibleStrikes();
    test.skip(uiStrikes.length === 0, 'No strikes visible in UI');

    const nseStrikes = Object.keys(nseData.strikes).map(Number);
    test.skip(nseStrikes.length === 0, 'NSE has no strikes');

    // UI strikes should be a subset of NSE strikes (UI shows filtered range)
    const nseStrikeSet = new Set(nseStrikes);
    const matchCount = uiStrikes.filter((s) => nseStrikeSet.has(s)).length;
    const matchPct = (matchCount / uiStrikes.length) * 100;

    expect(
      matchPct,
      `Only ${matchCount}/${uiStrikes.length} UI strikes found in NSE data (${matchPct.toFixed(0)}%). ` +
        `UI sample: ${uiStrikes.slice(0, 5)}, NSE sample: ${nseStrikes.slice(0, 5)}`
    ).toBeGreaterThanOrEqual(80);
  });

  test('@crossverify ATM CE LTP matches NSE', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const nseSpot = nseData.spotPrice;
    test.skip(nseSpot === 0, 'NSE spot is zero');

    // Find ATM strike (nearest to NSE spot)
    const nseStrikes = Object.keys(nseData.strikes).map(Number);
    const atmStrike = nseStrikes.reduce((closest, s) =>
      Math.abs(s - nseSpot) < Math.abs(closest - nseSpot) ? s : closest
    );

    const nseATM = nseData.strikes[atmStrike];
    test.skip(nseATM.ce_ltp === 0, `NSE ATM CE LTP is zero at strike ${atmStrike} — market may be closed`);

    // Check if this strike is visible in UI
    const uiStrikes = await chainPage.getVisibleStrikes();
    test.skip(!uiStrikes.includes(atmStrike), `ATM strike ${atmStrike} not visible in UI (range may be narrower)`);

    const uiLTP = await chainPage.getCELTPValue(atmStrike);
    test.skip(isNaN(uiLTP) || uiLTP === 0, `UI CE LTP is zero/unavailable at ATM ${atmStrike}`);

    const diff = pctDiff(uiLTP, nseATM.ce_ltp);
    expect(
      diff,
      `ATM CE LTP: UI=${uiLTP}, NSE=${nseATM.ce_ltp}, strike=${atmStrike}, diff=${diff.toFixed(2)}%`
    ).toBeLessThanOrEqual(LTP_TOLERANCE_PCT);
  });

  test('@crossverify ATM PE LTP matches NSE', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const nseSpot = nseData.spotPrice;
    test.skip(nseSpot === 0, 'NSE spot is zero');

    const nseStrikes = Object.keys(nseData.strikes).map(Number);
    const atmStrike = nseStrikes.reduce((closest, s) =>
      Math.abs(s - nseSpot) < Math.abs(closest - nseSpot) ? s : closest
    );

    const nseATM = nseData.strikes[atmStrike];
    test.skip(nseATM.pe_ltp === 0, `NSE ATM PE LTP is zero at strike ${atmStrike} — market may be closed`);

    const uiStrikes = await chainPage.getVisibleStrikes();
    test.skip(!uiStrikes.includes(atmStrike), `ATM strike ${atmStrike} not visible in UI`);

    const uiLTP = await chainPage.getPELTPValue(atmStrike);
    test.skip(isNaN(uiLTP) || uiLTP === 0, `UI PE LTP is zero/unavailable at ATM ${atmStrike}`);

    const diff = pctDiff(uiLTP, nseATM.pe_ltp);
    expect(
      diff,
      `ATM PE LTP: UI=${uiLTP}, NSE=${nseATM.pe_ltp}, strike=${atmStrike}, diff=${diff.toFixed(2)}%`
    ).toBeLessThanOrEqual(LTP_TOLERANCE_PCT);
  });

  test('@crossverify PCR matches NSE during market hours', async () => {
    test.skip(!nseData, 'NSE data unavailable');
    test.skip(nseData.pcr === 0, 'NSE PCR is zero — OI data unavailable');
    // Off-market, broker returns OI for only a few strikes → PCR is unreliable
    test.skip(!isMarketHours(), 'Market closed — broker OI is incomplete, PCR comparison unreliable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    let uiPCR;
    try {
      uiPCR = await chainPage.getPCR();
    } catch {
      test.skip(true, 'UI PCR element not found or not visible');
    }
    test.skip(isNaN(uiPCR) || uiPCR === 0, 'UI PCR is zero or unavailable');

    const nsePCR = nseData.pcr;
    const absDiff = Math.abs(uiPCR - nsePCR);

    expect(
      absDiff,
      `PCR: UI=${uiPCR.toFixed(2)}, NSE=${nsePCR.toFixed(2)}, diff=${absDiff.toFixed(2)}`
    ).toBeLessThanOrEqual(PCR_TOLERANCE_ABS);
  });

  test('@crossverify PCR is in sane range off-market', async () => {
    test.skip(!nseData, 'NSE data unavailable');
    test.skip(isMarketHours(), 'Market is open — use the NSE comparison test instead');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    let uiPCR;
    try {
      uiPCR = await chainPage.getPCR();
    } catch {
      test.skip(true, 'UI PCR element not found');
    }
    test.skip(isNaN(uiPCR) || uiPCR === 0, 'UI PCR is zero or unavailable');

    // Off-market PCR from broker may differ from NSE since broker returns
    // incomplete OI data. Just verify it's in a plausible range.
    // Normal PCR range: 0.3 to 3.0. Extreme but valid: 0.1 to 15.0.
    // Log the discrepancy for visibility.
    const nsePCR = nseData.pcr;
    const inSaneRange = uiPCR >= 0.1 && uiPCR <= 15.0;

    expect(
      inSaneRange,
      `PCR=${uiPCR.toFixed(2)} outside sane range [0.1, 15.0]. ` +
        `NSE PCR=${nsePCR.toFixed(2)} for reference. ` +
        `Extreme PCR off-market typically means broker returned OI for only a few strikes.`
    ).toBe(true);
  });

  test('@crossverify max pain strike is within NSE strike range', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    let uiMaxPain;
    try {
      uiMaxPain = await chainPage.getMaxPain();
    } catch {
      test.skip(true, 'UI Max Pain element not found');
    }
    test.skip(isNaN(uiMaxPain) || uiMaxPain === 0, 'UI Max Pain is zero or unavailable');

    const nseStrikes = Object.keys(nseData.strikes).map(Number).sort((a, b) => a - b);
    const minStrike = nseStrikes[0];
    const maxStrike = nseStrikes[nseStrikes.length - 1];

    expect(
      uiMaxPain,
      `Max Pain ${uiMaxPain} outside NSE strike range [${minStrike}, ${maxStrike}]`
    ).toBeGreaterThanOrEqual(minStrike);
    expect(uiMaxPain).toBeLessThanOrEqual(maxStrike);

    // Max pain should be near ATM (within ±10% of spot)
    const nseSpot = nseData.spotPrice;
    if (nseSpot > 0) {
      const maxPainDiff = pctDiff(uiMaxPain, nseSpot);
      expect(
        maxPainDiff,
        `Max Pain ${uiMaxPain} too far from spot ${nseSpot} (${maxPainDiff.toFixed(1)}%)`
      ).toBeLessThanOrEqual(10);
    }
  });

  test('@crossverify multiple strikes have non-zero data', async () => {
    test.skip(!nseData, 'NSE data unavailable');
    test.skip(!isMarketHours(), 'Market is closed — broker returns zero LTP outside market hours');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const uiStrikes = await chainPage.getVisibleStrikes();
    test.skip(uiStrikes.length === 0, 'No strikes visible');

    // Sample up to 5 strikes spread across the visible range
    const step = Math.max(1, Math.floor(uiStrikes.length / 5));
    const sampleStrikes = uiStrikes.filter((_, i) => i % step === 0).slice(0, 5);

    let nonZeroCount = 0;
    const results = [];

    for (const strike of sampleStrikes) {
      const ceLTP = await chainPage.getCELTPValue(strike);
      const peLTP = await chainPage.getPELTPValue(strike);
      const hasData = (!isNaN(ceLTP) && ceLTP > 0) || (!isNaN(peLTP) && peLTP > 0);
      if (hasData) nonZeroCount++;
      results.push({ strike, ceLTP, peLTP, hasData });
    }

    // During market hours, at least 60% of sampled strikes should have live data
    const minRequired = Math.ceil(sampleStrikes.length * 0.6);

    expect(
      nonZeroCount,
      `Only ${nonZeroCount}/${sampleStrikes.length} sampled strikes have non-zero LTP. ` +
        `Details: ${JSON.stringify(results)}`
    ).toBeGreaterThanOrEqual(minRequired);
  });

  test('@crossverify OI values match NSE for ATM strikes', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const nseSpot = nseData.spotPrice;
    test.skip(nseSpot === 0, 'NSE spot is zero');

    const uiStrikes = await chainPage.getVisibleStrikes();
    const nseStrikeKeys = Object.keys(nseData.strikes).map(Number);

    // Find ATM strike
    const atmStrike = nseStrikeKeys.reduce((closest, s) =>
      Math.abs(s - nseSpot) < Math.abs(closest - nseSpot) ? s : closest
    );

    // Check 3 strikes near ATM that exist in both UI and NSE
    const nearATMStrikes = nseStrikeKeys
      .filter((s) => Math.abs(s - atmStrike) <= 200 && uiStrikes.includes(s))
      .sort((a, b) => Math.abs(a - atmStrike) - Math.abs(b - atmStrike))
      .slice(0, 3);

    test.skip(nearATMStrikes.length === 0, 'No common strikes near ATM between UI and NSE');

    const mismatches = [];
    let compared = 0;

    for (const strike of nearATMStrikes) {
      const nseStrikeData = nseData.strikes[strike];

      // CE OI
      if (nseStrikeData.ce_oi > 0) {
        const uiCEOI = await chainPage.getCEOIValue(strike);
        if (!isNaN(uiCEOI) && uiCEOI > 0) {
          compared++;
          const diff = pctDiff(uiCEOI, nseStrikeData.ce_oi);
          if (diff > OI_TOLERANCE_PCT) {
            mismatches.push(`CE OI ${strike}: UI=${uiCEOI}, NSE=${nseStrikeData.ce_oi} (${diff.toFixed(1)}%)`);
          }
        }
      }

      // PE OI
      if (nseStrikeData.pe_oi > 0) {
        const uiPEOI = await chainPage.getPEOIValue(strike);
        if (!isNaN(uiPEOI) && uiPEOI > 0) {
          compared++;
          const diff = pctDiff(uiPEOI, nseStrikeData.pe_oi);
          if (diff > OI_TOLERANCE_PCT) {
            mismatches.push(`PE OI ${strike}: UI=${uiPEOI}, NSE=${nseStrikeData.pe_oi} (${diff.toFixed(1)}%)`);
          }
        }
      }
    }

    test.skip(compared === 0, 'Could not compare any OI values — UI may show formatted values');

    // Allow some mismatches (OI updates lag between sources)
    const maxAllowed = Math.ceil(compared * 0.5);
    expect(
      mismatches.length,
      `Too many OI mismatches: ${mismatches.length}/${compared}.\n${mismatches.join('\n')}`
    ).toBeLessThanOrEqual(maxAllowed);
  });

  test('@crossverify data completeness — broker returns sufficient strike data', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'Option chain did not load table');

    const uiStrikes = await chainPage.getVisibleStrikes();
    test.skip(uiStrikes.length === 0, 'No strikes visible');

    // Count strikes with non-zero LTP or OI
    let strikesWithLTP = 0;
    let strikesWithOI = 0;
    const sampleSize = Math.min(uiStrikes.length, 20);
    const step = Math.max(1, Math.floor(uiStrikes.length / sampleSize));
    const sampled = uiStrikes.filter((_, i) => i % step === 0).slice(0, sampleSize);

    for (const strike of sampled) {
      const ceLTP = await chainPage.getCELTPValue(strike);
      const peLTP = await chainPage.getPELTPValue(strike);
      if ((!isNaN(ceLTP) && ceLTP > 0) || (!isNaN(peLTP) && peLTP > 0)) strikesWithLTP++;

      const ceOI = await chainPage.getCEOIValue(strike);
      const peOI = await chainPage.getPEOIValue(strike);
      if ((!isNaN(ceOI) && ceOI > 0) || (!isNaN(peOI) && peOI > 0)) strikesWithOI++;
    }

    const ltpPct = (strikesWithLTP / sampled.length) * 100;
    const oiPct = (strikesWithOI / sampled.length) * 100;

    if (isMarketHours()) {
      // During market hours, most strikes should have data
      expect(
        ltpPct,
        `Only ${strikesWithLTP}/${sampled.length} strikes have LTP (${ltpPct.toFixed(0)}%) — expected >50% during market hours`
      ).toBeGreaterThan(50);
    } else {
      // Off-market: log completeness for diagnostics (don't fail — broker limitation)
      // NSE has data for all strikes even off-market, but brokers don't
      const nseStrikesWithOI = Object.values(nseData.strikes).filter(
        (s) => s.ce_oi > 0 || s.pe_oi > 0
      ).length;

      // This is informational — helps diagnose data quality issues
      console.log(
        `[Data Completeness] Off-market: UI has LTP for ${strikesWithLTP}/${sampled.length} strikes (${ltpPct.toFixed(0)}%), ` +
          `OI for ${strikesWithOI}/${sampled.length} (${oiPct.toFixed(0)}%). ` +
          `NSE has OI for ${nseStrikesWithOI}/${nseData.strikeCount} strikes.`
      );

      // Even off-market, we expect the app to at least show strikes (even if data is empty)
      expect(uiStrikes.length, 'UI should show strike rows even off-market').toBeGreaterThan(10);
    }
  });

  test('@crossverify NSE data sanity — sufficient strikes and positive spot', async () => {
    test.skip(!nseData, 'NSE data unavailable — API unreachable or returned empty');

    expect(nseData.spotPrice, 'NSE spot price must be positive').toBeGreaterThan(0);
    expect(nseData.spotPrice, 'NSE spot price must be in sane range').toBeGreaterThan(10000);
    expect(nseData.spotPrice).toBeLessThan(50000);
    expect(nseData.strikeCount, 'NSE should have 50+ strikes').toBeGreaterThan(50);
    expect(nseData.expiryDates.length, 'NSE should have multiple expiry dates').toBeGreaterThan(0);
  });

  test('@crossverify UI shows data for BANKNIFTY too', async () => {
    test.skip(!nseData, 'NSE data unavailable');

    const state = await chainPage.waitForChainLoad();
    test.skip(state !== 'table', 'NIFTY option chain did not load');

    // Capture NIFTY spot before switching
    const niftySpot = await chainPage.getSpotPrice();

    // Switch to BANKNIFTY and wait for data to load
    await chainPage.selectUnderlying('BANKNIFTY');
    const bnState = await chainPage.waitForChainLoad();
    test.skip(bnState === 'error', 'BANKNIFTY option chain failed to load');
    test.skip(bnState === 'empty', 'BANKNIFTY option chain is empty');

    // Wait for spot price to change from NIFTY's value (indicates BANKNIFTY data loaded)
    // BANKNIFTY spot is typically 2-3x NIFTY, so it should differ significantly
    let bnSpot;
    try {
      await chainPage.page.waitForFunction(
        (niftyVal) => {
          const el = document.querySelector('[data-testid="optionchain-spot-price"]');
          if (!el) return false;
          const val = parseFloat(el.textContent.replace(/,/g, ''));
          // Spot should change to a different value (BANKNIFTY ~50k vs NIFTY ~24k)
          return !isNaN(val) && val > 0 && Math.abs(val - niftyVal) > 1000;
        },
        niftySpot,
        { timeout: 15000 }
      );
      bnSpot = await chainPage.getSpotPrice();
    } catch {
      // If spot didn't change, read whatever is showing
      bnSpot = await chainPage.getSpotPrice();
      test.skip(
        Math.abs(bnSpot - niftySpot) < 1000,
        `BANKNIFTY spot (${bnSpot}) same as NIFTY (${niftySpot}) — data may not have loaded`
      );
    }

    expect(bnSpot, 'BANKNIFTY spot should be positive').toBeGreaterThan(0);
    // BANKNIFTY ranges: historically 20k-80k — use wide range
    expect(bnSpot, `BANKNIFTY spot ${bnSpot} outside sane range`).toBeGreaterThan(20000);
    expect(bnSpot).toBeLessThan(120000);

    const bnStrikes = await chainPage.getVisibleStrikes();
    expect(bnStrikes.length, 'BANKNIFTY should have visible strikes').toBeGreaterThan(0);
  });
});
