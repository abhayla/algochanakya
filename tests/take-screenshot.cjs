/**
 * Take screenshot of current page
 * Usage: node tests/take-screenshot.cjs [url] [filename]
 */

const { chromium } = require('playwright')
const path = require('path')

const targetUrl = process.argv[2] || 'http://localhost:5173/ai/settings'
const filename = process.argv[3] || 'ai-settings-screenshot'
const authStatePath = path.join(__dirname, 'config', '.auth-state.json')

async function main() {
  console.log(`Taking screenshot of: ${targetUrl}`)

  const browser = await chromium.launch({ headless: false })
  const context = await browser.newContext({
    storageState: authStatePath,
    viewport: { width: 1920, height: 1080 }
  })

  const page = await context.newPage()
  await page.goto(targetUrl)
  await page.waitForLoadState('networkidle')
  await page.waitForTimeout(2000) // Wait for animations

  const screenshotPath = path.join(__dirname, 'screenshots', `${filename}.png`)
  await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log(`Screenshot saved to: ${screenshotPath}`)

  await browser.close()
}

main().catch(console.error)
