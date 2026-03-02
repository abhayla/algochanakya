import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('OFO to Strategy Builder - Step 2', () => {
  test('Click Open in Builder and verify columns', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Navigate to OFO (assuming Short Straddle results are already there)
    console.log('Navigating to OFO...')
    await page.goto('/ofo')
    await page.waitForLoadState('domcontentloaded')

    // Take screenshot of current OFO state
    await page.screenshot({
      path: 'tests/screenshots/ofo-before-open-builder.png',
      fullPage: true
    })

    // Find and click "Open in Builder" button on the first result card
    console.log('Looking for "Open in Builder" button...')
    const openInBuilderBtn = page.locator('button:has-text("Open in Builder")').first()

    if (await openInBuilderBtn.isVisible()) {
      console.log('Found "Open in Builder" button, clicking...')

      // Get the card content before clicking
      const card = openInBuilderBtn.locator('..').locator('..')
      const cardText = await card.innerText().catch(() => 'Could not get card text')
      console.log('\n=== RESULT CARD BEING OPENED ===')
      console.log(cardText)

      // Extract strike info
      const strikes = cardText.match(/\b(2[4-7],?\d{3})\b/g)
      if (strikes) {
        console.log('\nStrikes in this card:', [...new Set(strikes)])
      }

      // Click the button
      await openInBuilderBtn.click()

      // Wait for navigation to Strategy Builder
      console.log('\nWaiting for Strategy Builder to load...')
      await page.waitForURL(/\/strategy/, { timeout: 10000 })
      await page.waitForLoadState('domcontentloaded')

      // Take screenshot of Strategy Builder
      await page.screenshot({
        path: 'tests/screenshots/strategy-builder-from-ofo.png',
        fullPage: true
      })
      console.log('Screenshot saved to: tests/screenshots/strategy-builder-from-ofo.png')

      // Analyze the P/L grid columns
      console.log('\n=== ANALYZING STRATEGY BUILDER COLUMNS ===')

      // Get backend data
      const gridData = await page.evaluate(() => {
        const app = document.querySelector('#app')?.__vue_app__
        if (!app) return { error: 'No Vue app' }

        const pinia = app.config.globalProperties.$pinia
        const strategyStore = pinia._s.get('strategy')

        if (!strategyStore || !strategyStore.pnlGrid) {
          return { error: 'No pnlGrid data' }
        }

        return {
          spot_prices: strategyStore.pnlGrid.spot_prices,
          breakeven: strategyStore.pnlGrid.breakeven,
          legs: strategyStore.legs.map(l => ({ strike: l.strike_price, type: l.contract_type, bs: l.transaction_type }))
        }
      })

      console.log('Backend spot_prices:', JSON.stringify(gridData.spot_prices))
      console.log('Backend breakeven:', JSON.stringify(gridData.breakeven))
      console.log('Legs:', JSON.stringify(gridData.legs))

      // Get displayed columns
      const spotHeaders = await page.locator('[data-testid="strategy-spot-column"]').allTextContents()
      console.log('\nDisplayed columns:', spotHeaders.length)
      console.log('Columns:', JSON.stringify(spotHeaders))

      // Parse numeric values
      const numericSpots = spotHeaders
        .map(s => parseInt(s.replace(/SPOT/g, '').replace(/,/g, '').trim()))
        .filter(n => !isNaN(n) && n > 0)
        .sort((a, b) => a - b)

      console.log('Numeric spots sorted:', JSON.stringify(numericSpots))

      // Calculate expected 100-point intervals
      if (gridData.spot_prices && gridData.spot_prices.length > 0) {
        const minSpot = Math.min(...gridData.spot_prices)
        const maxSpot = Math.max(...gridData.spot_prices)
        const start = Math.floor(minSpot / 100) * 100
        const end = Math.ceil(maxSpot / 100) * 100

        const expected100 = []
        for (let s = start; s <= end; s += 100) {
          expected100.push(s)
        }

        console.log('\n=== COLUMN ANALYSIS ===')
        console.log('Min spot from backend:', minSpot)
        console.log('Max spot from backend:', maxSpot)
        console.log('Expected 100-pt intervals:', JSON.stringify(expected100))
        console.log('Expected count:', expected100.length)
        console.log('Actual count:', numericSpots.length)

        // Find missing
        const missing = expected100.filter(e => !numericSpots.some(n => Math.abs(n - e) < 5))
        console.log('\nMISSING 100-point intervals:', JSON.stringify(missing))

        if (missing.length > 0) {
          console.log('\n*** BUG CONFIRMED: Missing columns! ***')
        } else {
          console.log('\n*** All 100-point intervals present! ***')
        }

        // Extra columns (breakevens, spot)
        const extra = numericSpots.filter(n => !expected100.includes(n))
        console.log('Extra columns (breakevens/spot):', JSON.stringify(extra))
      }

    } else {
      console.log('ERROR: "Open in Builder" button not found!')
      console.log('Taking screenshot to see current state...')
      await page.screenshot({
        path: 'tests/screenshots/ofo-no-button.png',
        fullPage: true
      })
    }

    console.log('\n=== STEP 2 COMPLETE ===')
  })
})
