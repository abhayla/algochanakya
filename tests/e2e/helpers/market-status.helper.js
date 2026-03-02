/**
 * Market Status Helper — NSE Market Hours Detection
 *
 * Enables tests to behave appropriately based on whether NSE is open or closed.
 * Per project rules: NEVER mock broker data. Tests must adapt to real market state.
 *
 * Usage:
 *   import { isMarketOpen, getDataExpectation } from '../helpers/market-status.helper.js';
 *
 *   const expectation = getDataExpectation();
 *   if (expectation === 'LIVE') {
 *     // Assert live data is present
 *   } else {
 *     // Assert empty state OR last-known data
 *   }
 */

/**
 * NSE 2026 Holiday Calendar (trading holidays only — no settlement-only holidays)
 * Format: 'YYYY-MM-DD'
 * Source: NSE India official holiday list for 2026
 *
 * IMPORTANT: Update this list annually. Use isHolidayListStale() to detect staleness.
 */
const NSE_HOLIDAYS_2026 = [
  '2026-01-26', // Republic Day
  '2026-02-18', // Mahashivratri
  '2026-03-02', // Holi
  '2026-03-31', // Id-Ul-Fitr (Ramzan Id)
  '2026-04-02', // Ram Navami
  '2026-04-03', // Good Friday
  '2026-04-14', // Dr. Baba Saheb Ambedkar Jayanti
  '2026-04-21', // Ram Navami
  '2026-05-01', // Maharashtra Day
  '2026-07-16', // Bakri Id
  '2026-08-15', // Independence Day
  '2026-09-07', // Ganesh Chaturthi
  '2026-10-02', // Mahatma Gandhi Jayanti
  '2026-10-21', // Dussehra
  '2026-10-28', // Id-E-Milad
  '2026-11-04', // Diwali - Laxmi Pujan (Muhurat Trading)
  '2026-11-05', // Diwali - Balipratipada
  '2026-11-19', // Guru Nanak Jayanti
  '2026-12-25', // Christmas
];

/**
 * NSE market session times in IST (UTC+5:30)
 * Pre-open: 9:00 AM - 9:15 AM
 * Regular: 9:15 AM - 3:30 PM
 */
const MARKET_OPEN_HOUR = 9;
const MARKET_OPEN_MINUTE = 15;
const MARKET_CLOSE_HOUR = 15;
const MARKET_CLOSE_MINUTE = 30;
const PRE_OPEN_START_HOUR = 9;
const PRE_OPEN_START_MINUTE = 0;

/**
 * Get current IST date/time components.
 * IST = UTC + 5:30
 */
function getISTNow() {
  const now = new Date();
  // UTC offset in ms: 5.5 hours
  const istOffset = 5.5 * 60 * 60 * 1000;
  const istTime = new Date(now.getTime() + istOffset);
  return {
    year: istTime.getUTCFullYear(),
    month: istTime.getUTCMonth() + 1, // 1-indexed
    day: istTime.getUTCDate(),
    weekday: istTime.getUTCDay(), // 0=Sun, 6=Sat
    hour: istTime.getUTCHours(),
    minute: istTime.getUTCMinutes(),
    dateStr: istTime.toISOString().split('T')[0], // 'YYYY-MM-DD'
  };
}

/**
 * Returns true if today is a NSE trading holiday.
 */
function isTodayHoliday() {
  const { dateStr, year } = getISTNow();
  // Check 2026 list
  if (year === 2026) {
    return NSE_HOLIDAYS_2026.includes(dateStr);
  }
  // For other years, warn and assume no holiday (stale list)
  console.warn(`[MarketStatus] No holiday list for year ${year}. Assuming no holiday. Update market-status.helper.js annually.`);
  return false;
}

/**
 * Returns true if NSE regular market session is currently open.
 * Regular session: Monday–Friday, 9:15 AM – 3:30 PM IST, excluding holidays.
 */
export function isMarketOpen() {
  const { weekday, hour, minute } = getISTNow();

  // Check weekend
  if (weekday === 0 || weekday === 6) return false;

  // Check holiday
  if (isTodayHoliday()) return false;

  // Check market hours
  const currentMinutes = hour * 60 + minute;
  const openMinutes = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE;   // 9:15 = 555
  const closeMinutes = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE; // 15:30 = 930

  return currentMinutes >= openMinutes && currentMinutes < closeMinutes;
}

/**
 * Returns true if NSE pre-open session is active (9:00–9:15 AM IST).
 */
export function isPreOpen() {
  const { weekday, hour, minute } = getISTNow();

  if (weekday === 0 || weekday === 6) return false;
  if (isTodayHoliday()) return false;

  const currentMinutes = hour * 60 + minute;
  const preOpenStart = PRE_OPEN_START_HOUR * 60 + PRE_OPEN_START_MINUTE; // 9:00 = 540
  const marketOpen = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE;          // 9:15 = 555

  return currentMinutes >= preOpenStart && currentMinutes < marketOpen;
}

/**
 * Returns the data expectation for the current market state.
 *
 * @returns {'LIVE' | 'LAST_KNOWN' | 'PRE_OPEN' | 'CLOSED'}
 *
 * - LIVE: Market is open. Expect real-time ticking data. No empty states expected.
 * - PRE_OPEN: Pre-open session. Data may be delayed/partial. ATM strikes may shift.
 * - LAST_KNOWN: After market close on a trading day. Previous close data available.
 * - CLOSED: Weekend or holiday. Only historical data. WebSocket may show stale data.
 */
export function getDataExpectation() {
  if (isMarketOpen()) return 'LIVE';
  if (isPreOpen()) return 'PRE_OPEN';

  const { weekday } = getISTNow();
  if (weekday === 0 || weekday === 6 || isTodayHoliday()) return 'CLOSED';

  // Weekday, but outside market hours — last known data from today/previous session
  return 'LAST_KNOWN';
}

/**
 * Returns the current IST time as a readable string for debug logging.
 */
export function getISTTimeString() {
  const { year, month, day, hour, minute, weekday } = getISTNow();
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const pad = (n) => String(n).padStart(2, '0');
  return `${dayNames[weekday]} ${year}-${pad(month)}-${pad(day)} ${pad(hour)}:${pad(minute)} IST`;
}

/**
 * Returns true if the holiday list may be stale (no data for current year).
 * Use in health checks to warn when annual update is needed.
 */
export function isHolidayListStale() {
  const { year } = getISTNow();
  return year !== 2026; // Update this condition annually
}

/**
 * Asserts that EITHER a data element OR an empty state element is visible.
 * Use instead of silent `if (hasData) { assert } // else: nothing`
 *
 * This ensures every test makes at least one assertion, regardless of market state.
 *
 * @param {import('@playwright/test').Page} page
 * @param {string} dataTestId - testid of the element shown when data exists
 * @param {string} emptyTestId - testid of the empty state element
 * @param {import('@playwright/test').expect} expect - Playwright expect
 */
export async function assertDataOrEmptyState(page, dataTestId, emptyTestId, expect) {
  const dataLocator = page.locator(`[data-testid="${dataTestId}"]`);
  const emptyLocator = page.locator(`[data-testid="${emptyTestId}"]`);

  const hasData = await dataLocator.isVisible().catch(() => false);
  const hasEmpty = await emptyLocator.isVisible().catch(() => false);

  if (!hasData && !hasEmpty) {
    // Neither visible — log market state for diagnosis and fail descriptively
    const expectation = getDataExpectation();
    throw new Error(
      `Neither data element [${dataTestId}] nor empty state [${emptyTestId}] is visible.\n` +
      `Market state: ${expectation} (${getISTTimeString()})\n` +
      `Expected: one of these two elements must always be present.`
    );
  }

  // At least one is visible — this is always correct behavior
  expect(hasData || hasEmpty).toBe(true);
}
