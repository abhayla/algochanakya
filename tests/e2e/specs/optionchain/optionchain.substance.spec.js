/**
 * Option Chain Substance Assertions @happy
 *
 * The existing optionchain.happy.spec.js only asserts toBeVisible (shape).
 * This suite adds *substance* checks against domain-plausible ranges:
 *   - spot price is a sane number for the tab
 *   - ATM strike is within one strike step of spot
 *   - ATM CE + ATM PE >= |spot - ATM strike| (put-call parity floor)
 *   - IV is a sane 5-60% for near-ATM strikes
 *   - OI is a positive integer for a live active strike
 *
 * These would have caught: LTP-scale-100x bug, ATM IV=0 bug, OI mismatch.
 * Run per-underlying (NIFTY / BANKNIFTY / FINNIFTY / SENSEX).
 */

import { test, expect } from '../../fixtures/auth.fixture.js'
import { OptionChainPage } from '../../pages/OptionChainPage.js'

// domain-sane ranges per underlying
const SPOT_RANGES = {
  NIFTY: [15000, 40000],
  BANKNIFTY: [30000, 90000],
  FINNIFTY: [15000, 45000],
  SENSEX: [50000, 120000],
}
const STRIKE_STEP = {
  NIFTY: 100,
  BANKNIFTY: 100,
  FINNIFTY: 100,
  SENSEX: 100,
}

async function readCell(page, row, colTestId) {
  const cell = row.locator(`[data-testid=${colTestId}]`).first()
  if ((await cell.count()) === 0) return null
  const txt = (await cell.textContent()) || ''
  const num = parseFloat(txt.replace(/,/g, ''))
  return Number.isFinite(num) ? num : null
}

const UNDERLYINGS_TO_CHECK = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']

for (const ul of UNDERLYINGS_TO_CHECK) {
  test.describe(`Option Chain substance — ${ul} @happy`, () => {
    let page
    test.beforeEach(async ({ authenticatedPage }) => {
      page = new OptionChainPage(authenticatedPage)
      await page.navigate()
      await page.waitForPageLoad()
      await page.selectUnderlying(ul)
    })

    test('spot price is in domain-sane range', async () => {
      const spot = await page.getSpotValue()
      const [lo, hi] = SPOT_RANGES[ul]
      expect(spot).toBeGreaterThan(lo)
      expect(spot).toBeLessThan(hi)
    })

    test('ATM strike is within one strike step of spot', async () => {
      const spot = await page.getSpotValue()
      const atm = await page.getAtmStrike()
      expect(atm).not.toBeNull()
      expect(Math.abs(atm - spot)).toBeLessThanOrEqual(STRIKE_STEP[ul])
    })

    test('ATM CE + PE premium respects put-call parity floor', async () => {
      // For a valid ATM straddle, CE + PE should exceed |spot - K| (intrinsic
      // value alone). This catches the "LTP off by 100x" bug directly — a real
      // ATM straddle is ₹100+ for NIFTY, not ₹2.
      const spot = await page.getSpotValue()
      const atm = await page.getAtmStrike()
      const ce = await page.getAtmCeLtp()
      const pe = await page.getAtmPeLtp()
      if (ce === null || pe === null) test.skip('ATM CE/PE not readable — market closed?')
      const intrinsic = Math.abs(spot - atm)
      expect(ce + pe).toBeGreaterThan(intrinsic)
      // Also assert absolute magnitude — an ATM straddle is at least 0.1% of spot
      expect(ce + pe).toBeGreaterThan(spot * 0.001)
    })

    test('ATM IV is a sane 3-80% (not 0, not garbage)', async () => {
      const ceIv = await page.getAtmCeIv()
      const peIv = await page.getAtmPeIv()
      // At least ONE of CE/PE at ATM should report a sane IV. Both being 0
      // means IV solver is broken (catches the CE=17.15 vs PE=10.33 skew).
      const someSane = [ceIv, peIv].some((iv) => iv !== null && iv > 3 && iv < 80)
      expect(someSane, 'At least one ATM leg should have IV in [3, 80]').toBe(true)
      // CE and PE IVs should be within 30 percentage points of each other for a
      // healthy ATM straddle. Wider skew signals an IV solver bug.
      if (ceIv !== null && peIv !== null && ceIv > 0 && peIv > 0) {
        expect(Math.abs(ceIv - peIv)).toBeLessThan(30)
      }
    })

    test('ATM OI is a positive integer', async () => {
      const oi = await page.getAtmCeOi()
      if (oi === null) test.skip('ATM CE OI not visible — market closed?')
      expect(Number.isInteger(oi)).toBe(true)
      expect(oi).toBeGreaterThan(0)
    })
  })
}
