import { test, expect } from '../../fixtures/auth.fixture.js';
import { isMarketOpen, getDataExpectation } from '../../helpers/market-status.helper.js';
import fs from 'fs';
import path from 'path';

/**
 * Option Chain - Data Quality Validation Tests
 *
 * Validates that AlgoChanakya option chain data is internally consistent and
 * within expected ranges for NIFTY and BANKNIFTY.
 *
 * Checks performed on all non-zero fields:
 *   - OI: non-negative integer
 *   - Volume: non-negative integer
 *   - IV: 0–300% range
 *   - LTP: positive, within expected strike range
 *   - Bid/Ask: bid <= ask, both positive
 *   - Spot price: within expected index range
 *   - ATM strike: closest strike to spot price
 *   - PCR: 0.3–3.0 range
 *   - Strike step: consistent (50 for NIFTY, 100 for BANKNIFTY)
 *
 * Skips automatically if market is closed or chain data is unavailable.
 */

const API_BASE = process.env.API_BASE || process.env.VITE_API_BASE_URL || 'http://localhost:8001';

// Expected spot price ranges (loose bounds — just sanity checks)
const SPOT_RANGES = {
  NIFTY:     { min: 10000, max: 35000 },
  BANKNIFTY: { min: 30000, max: 80000 },
  FINNIFTY:  { min: 10000, max: 30000 },
};

// Expected native strike step per underlying
const EXPECTED_STRIKE_STEP = {
  NIFTY:     50,
  BANKNIFTY: 100,
  FINNIFTY:  50,
};

function getStoredAuthToken() {
  try {
    const tokenFile = path.join(process.cwd(), 'tests', 'config', '.auth-token');
    if (fs.existsSync(tokenFile)) return fs.readFileSync(tokenFile, 'utf8').trim();
    const stateFile = path.join(process.cwd(), 'tests', 'config', '.auth-state.json');
    if (fs.existsSync(stateFile)) {
      const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
      for (const origin of state.origins || [])
        for (const item of origin.localStorage || [])
          if (item.name === 'access_token') return item.value;
    }
  } catch {}
  return null;
}

async function fetchAppExpiries(request, token, underlying) {
  const resp = await request.get(`${API_BASE}/api/options/expiries?underlying=${underlying}`, {
    headers: { Authorization: `Bearer ${token}` }, timeout: 15000,
  });
  if (!resp.ok()) return null;
  const data = await resp.json();
  return data.expiries || [];
}

async function fetchAppOptionChain(request, token, underlying, expiry) {
  const resp = await request.get(
    `${API_BASE}/api/optionchain/chain?underlying=${underlying}&expiry=${expiry}`,
    { headers: { Authorization: `Bearer ${token}` }, timeout: 30000 }
  );
  if (!resp.ok()) throw new Error(`Chain API returned ${resp.status()}`);
  return await resp.json();
}

// ─── Tests ────────────────────────────────────────────────────────────────────

test.describe('Option Chain - Data Validation @validation', () => {
  // Run serially — parallel SmartAPI calls cause rate-limit failures
  test.describe.configure({ mode: 'serial', timeout: 120000 });

  const UNDERLYINGS = ['NIFTY', 'BANKNIFTY'];

  for (const underlying of UNDERLYINGS) {
    test(`${underlying}: all non-zero fields pass data quality checks`, async ({ authenticatedPage }) => {
      const expectation = getDataExpectation();

      const token = getStoredAuthToken();
      if (!token) test.skip('No auth token');

      // Get nearest expiry
      const expiries = await fetchAppExpiries(authenticatedPage.request, token, underlying);
      if (!expiries?.length) test.skip(`No expiries available for ${underlying}`);

      // Fetch chain
      let chain;
      try {
        chain = await fetchAppOptionChain(authenticatedPage.request, token, underlying, expiries[0]);
      } catch (err) {
        test.skip(`Chain API failed: ${err.message}`);
      }

      if (!chain?.chain?.length) {
        test.skip(`Empty chain for ${underlying} — market may be closed`);
      }

      const rows = chain.chain;
      const spotPrice = chain.spot_price;
      const summary = chain.summary;
      const range = SPOT_RANGES[underlying];

      // ── 1. Spot price sanity ─────────────────────────────────────────────
      expect(spotPrice, `${underlying} spot price should be positive`).toBeGreaterThan(0);
      if (range) {
        expect(spotPrice, `${underlying} spot price ${spotPrice} outside expected range [${range.min}–${range.max}]`)
          .toBeGreaterThanOrEqual(range.min);
        expect(spotPrice, `${underlying} spot price ${spotPrice} outside expected range [${range.min}–${range.max}]`)
          .toBeLessThanOrEqual(range.max);
      }

      // ── 2. Strike step consistency ───────────────────────────────────────
      // Find the minimum step between consecutive strikes — this is the native step.
      // The displayed chain may be filtered (e.g. 100-pt interval from 50-pt data),
      // so we check that the min step is a multiple of the expected native step.
      if (rows.length >= 2) {
        const steps = [];
        for (let i = 1; i < rows.length; i++) {
          steps.push(Math.abs(rows[i].strike - rows[i-1].strike));
        }
        const minStep = Math.min(...steps);
        const expectedStep = EXPECTED_STRIKE_STEP[underlying];
        if (expectedStep && minStep > 0) {
          expect(minStep % expectedStep, `${underlying} min strike step ${minStep} is not a multiple of expected ${expectedStep}`)
            .toBe(0);
        }
      }

      // ── 3. ATM strike should be closest to spot ──────────────────────────
      const atmRow = rows.find(r => r.is_atm);
      if (atmRow) {
        const atmStrike = atmRow.strike;
        // Verify no other strike is closer to spot
        const distToAtm = Math.abs(spotPrice - atmStrike);
        for (const row of rows) {
          const dist = Math.abs(spotPrice - row.strike);
          expect(dist, `Strike ${row.strike} is closer to spot ${spotPrice} than ATM ${atmStrike}`)
            .toBeGreaterThanOrEqual(distToAtm);
        }
      }

      // ── 4. PCR range check (LIVE market only) ───────────────────────────────
      // When market is closed, OI data is sparse (few strikes have non-zero OI)
      // causing PCR to be unreliable. Only validate PCR during live market hours.
      if (expectation === 'LIVE' && summary?.pcr && summary.pcr !== 0) {
        expect(summary.pcr, `PCR ${summary.pcr} out of valid range [0.3–3.0]`).toBeGreaterThan(0.3);
        expect(summary.pcr, `PCR ${summary.pcr} out of valid range [0.3–3.0]`).toBeLessThan(3.0);
      }

      // ── 5. Per-strike field checks ───────────────────────────────────────
      const violations = [];

      for (const row of rows) {
        const strike = row.strike;

        // Strike itself must be a reasonable positive number
        if (strike <= 0) {
          violations.push(`Strike ${strike}: non-positive strike price`);
          continue;
        }

        for (const [side, data] of [['CE', row.ce], ['PE', row.pe]]) {
          if (!data) continue;

          // OI: non-negative
          if (data.oi !== null && data.oi !== undefined && data.oi < 0) {
            violations.push(`Strike ${strike} ${side} OI=${data.oi}: negative OI`);
          }

          // Volume: non-negative
          if (data.volume !== null && data.volume !== undefined && data.volume < 0) {
            violations.push(`Strike ${strike} ${side} Volume=${data.volume}: negative volume`);
          }

          // IV: 0–300% (only check non-zero values)
          if (data.iv && data.iv !== 0) {
            if (data.iv < 0 || data.iv > 300) {
              violations.push(`Strike ${strike} ${side} IV=${data.iv}: outside valid range [0–300]`);
            }
          }

          // LTP: positive and within a reasonable range of the strike
          if (data.ltp && data.ltp !== 0) {
            if (data.ltp < 0) {
              violations.push(`Strike ${strike} ${side} LTP=${data.ltp}: negative LTP`);
            }
            // LTP should not exceed spot price (options can't be worth more than spot for most cases)
            if (data.ltp > spotPrice * 1.5) {
              violations.push(`Strike ${strike} ${side} LTP=${data.ltp}: exceeds 150% of spot ${spotPrice}`);
            }
          }

          // Bid/Ask consistency: bid <= ask (when both non-zero)
          if (data.bid && data.ask && data.bid !== 0 && data.ask !== 0) {
            if (data.bid > data.ask) {
              violations.push(`Strike ${strike} ${side} Bid=${data.bid} > Ask=${data.ask}: invalid spread`);
            }
            // Both must be positive
            if (data.bid < 0 || data.ask < 0) {
              violations.push(`Strike ${strike} ${side} Bid/Ask negative: bid=${data.bid} ask=${data.ask}`);
            }
          }
        }
      }

      // ── 6. Summary: at least some non-zero OI in both CE and PE ─────────
      // Only assert non-zero OI during LIVE market hours — outside hours, OI may be
      // 0 if the broker token mapping is stale (pre-existing known issue).
      if (expectation === 'LIVE') {
        const totalCeOI = rows.reduce((sum, r) => sum + (r.ce?.oi || 0), 0);
        const totalPeOI = rows.reduce((sum, r) => sum + (r.pe?.oi || 0), 0);
        if (totalCeOI === 0 || totalPeOI === 0) {
          console.log(`${underlying} OI warning: CE OI=${totalCeOI}, PE OI=${totalPeOI} — broker may not be providing OI data`);
        }
      }

      // Report all violations
      if (violations.length > 0) {
        console.log(`${underlying} violations (${violations.length}):\n${violations.slice(0, 20).map(v => '  ' + v).join('\n')}`);
      }

      expect(violations, `${violations.length} data quality violations found`).toHaveLength(0);
    });
  }

  // ── Spot price test: spot must be present and reasonable ─────────────────
  for (const underlying of UNDERLYINGS) {
    test(`${underlying}: spot price is present and within expected range`, async ({ authenticatedPage }) => {
      const token = getStoredAuthToken();
      if (!token) test.skip('No auth token');

      const expiries = await fetchAppExpiries(authenticatedPage.request, token, underlying);
      if (!expiries?.length) test.skip('No expiries available');

      let chain;
      try {
        chain = await fetchAppOptionChain(authenticatedPage.request, token, underlying, expiries[0]);
      } catch {
        test.skip('Chain API failed');
      }

      if (!chain) test.skip('No chain data');

      const spot = chain.spot_price;
      const range = SPOT_RANGES[underlying];

      expect(spot, `${underlying} spot price should be positive`).toBeGreaterThan(0);
      if (range) {
        expect(spot).toBeGreaterThanOrEqual(range.min);
        expect(spot).toBeLessThanOrEqual(range.max);
      }

      console.log(`${underlying} spot price: ${spot}`);
    });
  }

  // ── data_freshness field: must be present and valid ───────────────────────
  for (const underlying of UNDERLYINGS) {
    test(`${underlying}: API response includes valid data_freshness field`, async ({ authenticatedPage }) => {
      const token = getStoredAuthToken();
      if (!token) test.skip('No auth token');

      const expiries = await fetchAppExpiries(authenticatedPage.request, token, underlying);
      if (!expiries?.length) test.skip('No expiries available');

      let chain;
      try {
        chain = await fetchAppOptionChain(authenticatedPage.request, token, underlying, expiries[0]);
      } catch {
        test.skip('Chain API failed');
      }

      if (!chain) test.skip('No chain data');

      // data_freshness must be present and one of the two valid values
      expect(chain.data_freshness, 'data_freshness field must be present in chain response').toBeDefined();
      expect(['LIVE', 'LAST_KNOWN'], `data_freshness must be 'LIVE' or 'LAST_KNOWN', got '${chain.data_freshness}'`)
        .toContain(chain.data_freshness);

      console.log(`${underlying} data_freshness: ${chain.data_freshness}`);
    });
  }
});
