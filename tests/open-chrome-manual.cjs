/**
 * Open Chrome with authentication for manual testing
 * Usage: node tests/open-chrome-manual.js [path]
 * Example: node tests/open-chrome-manual.js /ai/settings
 */

const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

let targetPath = process.argv[2] || '/ai/settings'
// Fix Git Bash path mangling on Windows (converts /ai to C:/Program Files/Git/ai)
if (targetPath.includes('Program Files') || targetPath.includes(':')) {
  targetPath = '/ai/settings'
}
const authStatePath = path.join(__dirname, 'config', '.auth-state.json')

async function main() {
  console.log(`Opening Chrome with auth state...`)
  console.log(`Target: http://localhost:5173${targetPath}`)

  // Read auth state
  if (!fs.existsSync(authStatePath)) {
    console.error('Auth state not found. Run: npm test first')
    process.exit(1)
  }

  const authState = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'))

  // Launch browser with persistent context
  const browser = await chromium.launch({
    headless: false,
    slowMo: 100
  })

  const context = await browser.newContext({
    storageState: authStatePath
  })

  const page = await context.newPage()

  // Navigate to target page
  await page.goto(`http://localhost:5173${targetPath}`)

  // Wait for page to load
  await page.waitForLoadState('networkidle')

  console.log('\n✅ Chrome opened with authentication!')
  console.log('📍 Page loaded: ' + page.url())
  console.log('\n⏳ Browser will stay open for manual testing...')
  console.log('   Press Ctrl+C to close when done.\n')

  // Keep the browser open for manual testing
  await new Promise(() => {}) // Wait forever
}

main().catch(console.error)
