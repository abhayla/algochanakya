// Screenshot a single screen with defined config
// Usage: node audit-single.mjs <config> <screenName> <path> <waitMs>
import { chromium } from '@playwright/test'
import fs from 'fs'
import path from 'path'

const [, , config, screenName, screenPath, waitStr, noAuthStr] = process.argv
const wait = parseInt(waitStr || '8000', 10)
const noAuth = noAuthStr === 'noauth'

const OUT_ROOT = 'D:/Abhay/VibeCoding/algochanakya/docs/reviews/2026-07-01'
const OUT_DIR = path.join(OUT_ROOT, config)
fs.mkdirSync(OUT_DIR, { recursive: true })

const STORAGE = 'D:/Abhay/VibeCoding/algochanakya/tests/config/.auth-state.json'
const BASE = 'http://localhost:5173'

const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext(
  noAuth ? { viewport: { width: 1440, height: 900 } } : { storageState: STORAGE, viewport: { width: 1440, height: 900 } }
)
const page = await ctx.newPage()
const errors = []
page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text().slice(0, 200)) })
page.on('pageerror', (err) => errors.push('PAGE:' + err.message.slice(0, 200)))

try {
  await page.goto(BASE + screenPath, { waitUntil: 'domcontentloaded', timeout: 30000 })
  await page.waitForTimeout(wait)
  const shot = path.join(OUT_DIR, `${screenName}.png`)
  await page.screenshot({ path: shot, fullPage: true })

  const navCheck = await page.evaluate(() => {
    const nav = document.querySelector('[data-testid="kite-header-nav"]')
    if (!nav) return { present: false }
    const txt = nav.innerText
    const bad = ['AutoPilot', 'AI Settings', 'OFO', 'Watchlist'].filter((l) => txt.includes(l))
    return { present: true, badLabels: bad, nav: txt }
  })
  const nifty = await page.locator('[data-testid="kite-header-index-value-nifty50"]').textContent().catch(() => null)
  const sensex = await page.locator('[data-testid="kite-header-index-value-sensex"]').textContent().catch(() => null)
  const dashes = await page.evaluate(() => {
    const walkAll = []
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    let n
    while ((n = walker.nextNode())) {
      const t = n.textContent.trim()
      if (t === '--' || t === '—' || t === '- -') walkAll.push(t)
    }
    return walkAll.length
  })
  console.log(JSON.stringify({
    config, screenName, url: page.url(), shot,
    navPresent: navCheck.present, badNavLabels: navCheck.badLabels,
    niftyHeader: nifty, sensexHeader: sensex,
    dashCount: dashes,
    consoleErrors: errors.length, errors: errors.slice(0, 3),
  }))
} catch (e) {
  console.log(JSON.stringify({ config, screenName, ERROR: e.message.slice(0, 300) }))
} finally {
  await ctx.close()
  await browser.close()
}
