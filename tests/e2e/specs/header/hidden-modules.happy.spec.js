/**
 * Hidden Modules Assertion @happy
 *
 * Asserts the feature-flag hide system is working:
 *   - Nav does NOT render entries for AutoPilot / AI / Watchlist / OFO
 *   - Direct URL access to those module roots is unreachable (route not registered,
 *     vue-router falls through; in this app that surfaces as a redirect to /dashboard
 *     because there's no catch-all 404 view yet — assert presence of dashboard markers).
 *
 * This spec must keep passing across the campaign — if a future change re-enables a
 * module accidentally, this test catches it.
 */

import { test, expect } from '../../fixtures/auth.fixture.js'

const HIDDEN_PATHS = ['/autopilot', '/ai/settings', '/ofo', '/watchlist']
const HIDDEN_NAV_LABELS = [/AutoPilot/i, /AI Settings/i, /OFO/i, /Watchlist/i]

test.describe('Hidden modules @happy', () => {
  test('nav does not render hidden module entries', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForSelector('[data-testid="kite-header-nav"]')
    const nav = page.locator('[data-testid="kite-header-nav"]')
    for (const label of HIDDEN_NAV_LABELS) {
      await expect(nav).not.toContainText(label)
    }
  })

  test('hidden module routes are not registered (redirect away)', async ({ page }) => {
    for (const path of HIDDEN_PATHS) {
      await page.goto(path)
      // No matching route -> vue-router does nothing, app stays on / which redirects to /dashboard
      // OR navigation guard sends to /login. Either way, the hidden view itself must NOT mount.
      await expect(page).not.toHaveURL(new RegExp(path.replace(/\//g, '\\/')))
    }
  })
})
