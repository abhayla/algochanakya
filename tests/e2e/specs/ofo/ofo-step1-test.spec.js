import { test, expect } from '../../fixtures/auth.fixture.js'

test.describe('OFO Short Straddle - Step 1', () => {
  test('Calculate Short Straddle and capture results', async ({ authenticatedPage }) => {
    const page = authenticatedPage

    // Navigate to OFO
    console.log('Navigating to OFO...')
    await page.goto('/ofo')
    await page.waitForLoadState('domcontentloaded')

    // Wait for page to fully load (wait for calculate button to be ready)
    console.log('Waiting for page to load...')
    const calculateBtn = page.getByTestId('ofo-calculate-btn')
    await calculateBtn.waitFor({ state: 'visible', timeout: 15000 })

    // Ensure NIFTY is selected
    console.log('Ensuring NIFTY is selected...')
    const niftyTab = page.getByTestId('ofo-underlying-nifty')
    if (await niftyTab.isVisible()) {
      await niftyTab.click()
      await page.waitForLoadState('domcontentloaded')
    }

    // Open strategy dropdown
    console.log('Opening strategy dropdown...')
    const strategySelect = page.getByTestId('ofo-strategy-select')
    await strategySelect.click()
    await page.waitForLoadState('domcontentloaded')

    // Click "Select All" first to test with multiple strategies
    console.log('Selecting all strategies to find which ones have results...')
    const selectAllBtn = page.locator('button:has-text("Select All")')
    if (await selectAllBtn.isVisible()) {
      await selectAllBtn.click()
      await page.waitForLoadState('domcontentloaded')
    }

    // Close dropdown
    await page.keyboard.press('Escape')
    await page.waitForLoadState('domcontentloaded')

    // Click Calculate button and wait for results
    console.log('Clicking Calculate button...')
    await calculateBtn.click({ force: true })

    // Wait for calculation — look for result cards or "no results" messages
    console.log('Waiting for calculation to complete...')
    await Promise.race([
      page.locator('[class*="result-card"]').first().waitFor({ state: 'visible', timeout: 60000 }),
      page.locator('text=No valid combinations found').first().waitFor({ state: 'visible', timeout: 60000 })
    ]).catch(() => {
      console.log('No result indicator appeared within timeout')
    })

    // Take screenshot
    await page.screenshot({
      path: 'tests/screenshots/ofo-all-strategies.png',
      fullPage: true
    })
    console.log('Screenshot saved to: tests/screenshots/ofo-all-strategies.png')

    // Check which strategies have results
    console.log('\n=== CHECKING WHICH STRATEGIES HAVE RESULTS ===')

    const strategies = ['Short Straddle', 'Short Strangle', 'Iron Condor', 'Iron Butterfly', 'Long Straddle', 'Long Strangle']

    for (const strategy of strategies) {
      const hasNoResults = await page.locator(`text=No valid combinations found for ${strategy}`).isVisible()
      const hasResults = await page.locator(`[class*="result-card"]:has-text("${strategy}")`).count() > 0

      if (hasNoResults) {
        console.log(`${strategy}: NO RESULTS`)
      } else if (hasResults) {
        console.log(`${strategy}: HAS RESULTS ✓`)
      } else {
        console.log(`${strategy}: Unknown state`)
      }
    }

    // Now specifically select Short Straddle only
    console.log('\n=== NOW SELECTING ONLY SHORT STRADDLE ===')

    // Open dropdown again
    await strategySelect.click()
    await page.waitForLoadState('domcontentloaded')

    // Clear all
    const clearAllBtn = page.locator('button:has-text("Clear All")')
    if (await clearAllBtn.isVisible()) {
      await clearAllBtn.click()
      await page.waitForLoadState('domcontentloaded')
    }

    // Select Short Straddle
    const shortStraddleItem = page.locator('.dropdown-item:has-text("Short Straddle"), label:has-text("Short Straddle")').first()
    if (await shortStraddleItem.isVisible()) {
      await shortStraddleItem.click()
    }
    await page.waitForLoadState('domcontentloaded')

    // Close dropdown
    await page.keyboard.press('Escape')
    await page.waitForLoadState('domcontentloaded')

    // Click Calculate again and wait for results
    await calculateBtn.click({ force: true })
    await Promise.race([
      page.locator('[class*="result-card"]').first().waitFor({ state: 'visible', timeout: 45000 }),
      page.locator('text=No valid combinations found for Short Straddle').waitFor({ state: 'visible', timeout: 45000 })
    ]).catch(() => {
      console.log('No result indicator appeared within timeout')
    })

    // Take final screenshot
    await page.screenshot({
      path: 'tests/screenshots/ofo-step1-results.png',
      fullPage: true
    })
    console.log('\nFinal screenshot saved to: tests/screenshots/ofo-step1-results.png')

    // Check Short Straddle results
    const hasShortStraddleResults = await page.locator('[class*="result-card"]:has-text("Short Straddle")').count() > 0
    const hasNoShortStraddle = await page.locator('text=No valid combinations found for Short Straddle').isVisible()

    console.log('\n=== SHORT STRADDLE RESULT ===')
    console.log('Has result cards:', hasShortStraddleResults)
    console.log('No valid combinations:', hasNoShortStraddle)

    if (hasShortStraddleResults) {
      const card = page.locator('[class*="result-card"]:has-text("Short Straddle")').first()
      const cardText = await card.innerText()
      console.log('\nShort Straddle Result:')
      console.log(cardText)
    }

    console.log('\n=== STEP 1 COMPLETE ===')
  })
})
