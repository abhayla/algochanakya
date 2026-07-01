// Performance audit — measures cold-load timing per screen.
// Loads a screen and reports:
//   - domContentLoaded latency
//   - "data-ready" latency (screen-specific: chain rendered, spot populated, etc.)
//   - number of XHR/fetch requests during load
//   - slowest single request
//
// Budget (per feedback_performance_in_rubric):
//   - initial render (login) < 2s
//   - data screens (dashboard/positions) < 5s
//   - data-heavy (option chain, strategy w/spot) < 5s ideally, 8s tolerable
//   - anything > 8s → defect
//
// Usage: node audit-perf.mjs <screenName> <path> [noauth]
import { chromium } from '@playwright/test'

const [, , screenName, screenPath, noAuthStr] = process.argv
const noAuth = noAuthStr === 'noauth'

const STORAGE = 'D:/Abhay/VibeCoding/algochanakya/tests/config/.auth-state.5174.json'
const BASE = 'http://localhost:5174'

// Screen-specific readiness signals — the moment "data is on screen"
const READY_SIGNALS = {
  login: async (page) =>
    !!(await page.locator('[data-testid="login-broker-select"], .login-card, form').first().isVisible().catch(() => false)),
  dashboard: async (page) => {
    const txt = await page.locator('[data-testid="kite-header-index-value-nifty50"]').textContent().catch(() => '')
    return !!(txt && txt !== '--' && txt !== '—' && /\d/.test(txt))
  },
  optionchain: async (page) =>
    !(await page.locator('text=/Loading option chain/i').isVisible().catch(() => false)) &&
    (await page.locator('text=/ATM/').isVisible().catch(() => false)),
  strategy: async (page) => {
    // Detect populated spot card: any of "NIFTY SPOT", "BANKNIFTY SPOT" (varies by underlying)
    // followed by a 4-5 digit number that isn't literal "0".
    const txt = await page.locator('body').textContent().catch(() => '')
    const m = txt.match(/(NIFTY|BANKNIFTY|FINNIFTY|SENSEX)\s*SPOT[\s\S]{0,40}?([\d,]+)/i)
    if (!m) return false
    const num = m[2].replace(/,/g, '')
    return num.length >= 4 && num !== '0'  // "23,995" → "23995" (5 digits), reject "0"
  },
  positions: async (page) =>
    !!(await page.locator('text=/No Open Positions|TOTAL P&L/').first().isVisible().catch(() => false)),
  settings: async (page) =>
    !!(await page.locator('text=/Broker Selection|Market Data Source/').first().isVisible().catch(() => false)),
}

const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext(
  noAuth ? {} : { storageState: STORAGE }
)
const page = await ctx.newPage()

const requests = []
page.on('request', (req) => {
  if (req.url().includes('/api/')) {
    requests.push({ url: req.url().replace(BASE, '').replace(/^http:\/\/[^/]+/, ''), startedAt: Date.now() })
  }
})
page.on('response', (res) => {
  const r = requests.find((x) => x.url === res.url().replace(BASE, '').replace(/^http:\/\/[^/]+/, '') && !x.finishedAt)
  if (r) {
    r.finishedAt = Date.now()
    r.status = res.status()
    r.durationMs = r.finishedAt - r.startedAt
  }
})

const t0 = Date.now()
try {
  await page.goto(BASE + screenPath, { waitUntil: 'domcontentloaded', timeout: 30000 })
  const domReady = Date.now() - t0

  // Poll for the screen-specific ready signal
  const readyCheck = READY_SIGNALS[screenName]
  let dataReady = null
  if (readyCheck) {
    const dataDeadline = Date.now() + 30000
    while (Date.now() < dataDeadline) {
      if (await readyCheck(page)) {
        dataReady = Date.now() - t0
        break
      }
      await page.waitForTimeout(200)
    }
  }

  const apiReqs = requests.filter((r) => r.durationMs != null)
  const slowest = apiReqs.slice().sort((a, b) => b.durationMs - a.durationMs)[0]
  const totalApiTime = apiReqs.reduce((s, r) => s + (r.durationMs || 0), 0)

  console.log(JSON.stringify({
    screen: screenName,
    domReadyMs: domReady,
    dataReadyMs: dataReady,
    verdict: dataReady == null
      ? 'TIMEOUT'
      : dataReady < 2000 ? 'FAST'
        : dataReady < 5000 ? 'OK'
          : dataReady < 8000 ? 'SLOW'
            : 'DEFECT',
    apiRequestCount: apiReqs.length,
    slowestApi: slowest ? { url: slowest.url, ms: slowest.durationMs, status: slowest.status } : null,
    top5SlowestApi: apiReqs.sort((a, b) => b.durationMs - a.durationMs).slice(0, 5)
      .map((r) => ({ url: r.url, ms: r.durationMs, status: r.status })),
  }, null, 2))
} catch (e) {
  console.log(JSON.stringify({ screen: screenName, ERROR: e.message.slice(0, 300) }))
} finally {
  await ctx.close()
  await browser.close()
}
