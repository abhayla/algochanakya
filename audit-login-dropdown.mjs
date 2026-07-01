import { chromium } from '@playwright/test'
const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
await page.goto('http://localhost:5173/login', { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(3000)
const options = await page.evaluate(() => {
  const sel = document.querySelector('select')
  if (!sel) return { error: 'no select found' }
  return Array.from(sel.options).map((o) => ({ value: o.value, text: o.textContent.trim() }))
})
console.log(JSON.stringify(options))
await browser.close()
