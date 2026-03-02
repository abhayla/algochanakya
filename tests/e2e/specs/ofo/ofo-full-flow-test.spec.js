import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('OFO to Strategy Builder - Full Flow', () => {
  test('Calculate Short Straddle then Open in Builder', { timeout: 120000 }, async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Step 1: Navigate to OFO
    console.log('=== STEP 1: Navigate to OFO ===')
    await page.goto('/ofo')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // Take initial screenshot
    await page.screenshot({
      path: 'tests/screenshots/ofo-step1-initial.png',
      fullPage: true
    })

    // Ensure NIFTY is selected
    const niftyTab = page.getByTestId('ofo-underlying-nifty')
    if (await niftyTab.isVisible()) {
      await niftyTab.click()
      await page.waitForTimeout(1000)
    }

    // Step 2: Select Short Straddle strategy
    console.log('=== STEP 2: Select Short Straddle ===')
    const strategySelect = page.getByTestId('ofo-strategy-select')
    await strategySelect.click()
    await page.waitForTimeout(500)

    // Take screenshot of dropdown open
    await page.screenshot({
      path: 'tests/screenshots/ofo-step2-dropdown-open.png',
      fullPage: true
    })

    // Clear all first
    const clearAllBtn = page.locator('button:has-text("Clear All")')
    if (await clearAllBtn.isVisible()) {
      await clearAllBtn.click()
      await page.waitForTimeout(300)
    }

    // Select Short Straddle
    const shortStraddleItem = page.locator('label:has-text("Short Straddle")').first()
    if (await shortStraddleItem.isVisible()) {
      await shortStraddleItem.click()
      console.log('Clicked Short Straddle checkbox')
    } else {
      console.log('ERROR: Short Straddle option not visible')
    }
    await page.waitForTimeout(500)

    // Close dropdown by clicking on the backdrop overlay
    const backdrop = page.locator('.dropdown-backdrop')
    if (await backdrop.isVisible()) {
      await backdrop.click()
      console.log('Clicked backdrop to close dropdown')
    } else {
      // Fallback: press Escape
      await page.keyboard.press('Escape')
      console.log('Pressed Escape to close dropdown')
    }
    await page.waitForTimeout(500)

    // Take screenshot after selection
    await page.screenshot({
      path: 'tests/screenshots/ofo-step2-after-selection.png',
      fullPage: true
    })

    // Verify dropdown is closed
    const dropdownClosed = !(await page.locator('button:has-text("Clear All")').isVisible())
    console.log('Dropdown closed:', dropdownClosed)

    // Step 3: Click Calculate button
    console.log('=== STEP 3: Click Calculate ===')
    const calculateBtn = page.getByTestId('ofo-calculate-btn')

    // Ensure button is visible and enabled
    await expect(calculateBtn).toBeVisible()
    console.log('Calculate button is visible')

    // Click calculate
    await calculateBtn.click()
    console.log('Clicked Calculate button')

    // Wait for calculation to complete (watch for loading state to finish)
    console.log('Waiting for calculation results...')
    await page.waitForTimeout(15000)

    // Take screenshot of OFO results
    await page.screenshot({
      path: 'tests/screenshots/ofo-step3-calculated.png',
      fullPage: true
    })
    console.log('OFO calculation screenshot saved')

    // Check for results
    const noResultsMsg = await page.locator('text=No valid combinations found for Short Straddle').isVisible()
    const resultCardCount = await page.locator('[class*="result-card"]').count()
    const hasResultCards = resultCardCount > 0
    const hasOpenInBuilder = await page.locator('button:has-text("Open in Builder")').first().isVisible()

    console.log('No results message visible:', noResultsMsg)
    console.log('Result card count:', resultCardCount)
    console.log('Has result cards:', hasResultCards)
    console.log('Has Open in Builder button:', hasOpenInBuilder)

    if (noResultsMsg || !hasOpenInBuilder) {
      console.log('\n*** Short Straddle has no results, trying Iron Butterfly ***')

      // Open dropdown again
      await strategySelect.click()
      await page.waitForTimeout(500)

      // Clear and select Iron Butterfly
      if (await clearAllBtn.isVisible()) {
        await clearAllBtn.click()
        await page.waitForTimeout(300)
      }

      const ironButterflyItem = page.locator('label:has-text("Iron Butterfly")').first()
      if (await ironButterflyItem.isVisible()) {
        await ironButterflyItem.click()
        console.log('Selected Iron Butterfly')
      }

      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)

      // Click Calculate again
      await calculateBtn.click()
      console.log('Clicked Calculate for Iron Butterfly')
      await page.waitForTimeout(15000)

      await page.screenshot({
        path: 'tests/screenshots/ofo-step3-iron-butterfly.png',
        fullPage: true
      })
    }

    // Step 4: Click Open in Builder
    console.log('\n=== STEP 4: Click Open in Builder ===')
    const openInBuilderBtn = page.locator('button:has-text("Open in Builder")').first()

    if (await openInBuilderBtn.isVisible()) {
      // Get strike information from the result card
      const resultCard = page.locator('[class*="result-card"]').first()
      const cardText = await resultCard.innerText().catch(() => 'Could not get card text')
      console.log('\nResult Card Content (first 500 chars):')
      console.log(cardText.substring(0, 500))

      // Extract strikes from card
      const strikeMatches = cardText.match(/\b(2[4-7],?\d{3})\b/g)
      if (strikeMatches) {
        const strikes = [...new Set(strikeMatches.map(s => s.replace(',', '')))]
        console.log('\nStrikes found in card:', strikes)
      }

      // Click Open in Builder
      await openInBuilderBtn.click()
      console.log('Clicked Open in Builder')

      // Wait for Strategy Builder to load
      await page.waitForURL(/\/strategy/, { timeout: 15000 })
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(5000)

      // Take screenshot of Strategy Builder
      await page.screenshot({
        path: 'tests/screenshots/ofo-step4-strategy-builder.png',
        fullPage: true
      })
      console.log('Strategy Builder screenshot saved')

      // Step 5: Verify P/L Grid columns
      console.log('\n=== STEP 5: Verify P/L Grid Columns ===')

      // Get data from Vue store
      const gridData = await page.evaluate(() => {
        const app = document.querySelector('#app')?.__vue_app__
        if (!app) return { error: 'No Vue app found' }

        const pinia = app.config.globalProperties.$pinia
        const strategyStore = pinia._s.get('strategy')

        if (!strategyStore?.pnlGrid) {
          return { error: 'No pnlGrid data' }
        }

        return {
          spot_prices: strategyStore.pnlGrid.spot_prices,
          breakeven: strategyStore.pnlGrid.breakeven,
          legs: strategyStore.legs.map(l => ({
            strike: l.strike_price,
            type: l.contract_type,
            action: l.transaction_type
          }))
        }
      })

      if (gridData.error) {
        console.log('ERROR:', gridData.error)
      } else {
        console.log('\nBackend Data:')
        console.log('Spot prices from backend:', JSON.stringify(gridData.spot_prices))
        console.log('Breakeven points:', JSON.stringify(gridData.breakeven))
        console.log('Legs:', JSON.stringify(gridData.legs))

        // Get displayed column headers
        const spotHeaders = await page.locator('.th-spot').allTextContents()
        console.log('\nDisplayed Columns:')
        console.log('Column count:', spotHeaders.length)
        console.log('Columns:', JSON.stringify(spotHeaders))

        // Parse numeric values from headers
        const numericSpots = spotHeaders
          .map(s => parseInt(s.replace(/SPOT/g, '').replace(/,/g, '').trim()))
          .filter(n => !isNaN(n) && n > 0)
          .sort((a, b) => a - b)

        console.log('Numeric columns (sorted):', JSON.stringify(numericSpots))

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

          console.log('\n=== COLUMN VERIFICATION ===')
          console.log('Backend range:', minSpot, 'to', maxSpot)
          console.log('Expected 100-pt columns:', expected100.length)
          console.log('Expected values:', JSON.stringify(expected100))

          // Check for missing columns
          const missing = expected100.filter(e => !numericSpots.some(n => Math.abs(n - e) < 5))

          if (missing.length > 0) {
            console.log('\n*** FAIL: Missing columns:', JSON.stringify(missing), '***')
          } else {
            console.log('\n*** PASS: All 100-pt interval columns present! ***')
          }

          // Show extra columns (breakevens, current spot)
          const extra = numericSpots.filter(n => !expected100.includes(n))
          if (extra.length > 0) {
            console.log('Extra columns (breakevens/spot):', JSON.stringify(extra))
          }
        }
      }

    } else {
      console.log('ERROR: Open in Builder button not found!')
      await page.screenshot({
        path: 'tests/screenshots/ofo-step4-no-button.png',
        fullPage: true
      })
    }

    console.log('\n=== TEST COMPLETE ===')
  })
})
