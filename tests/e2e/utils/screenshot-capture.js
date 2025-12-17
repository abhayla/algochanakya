/**
 * AutoPilot Screenshot Capture Script
 *
 * Automated script to capture screenshots of all AutoPilot screens
 * for documentation purposes.
 *
 * Usage:
 *   node tests/e2e/utils/screenshot-capture.js
 *
 * Prerequisites:
 *   - Backend running on http://localhost:8000
 *   - Frontend running on http://localhost:5173
 *   - Valid auth token in tests/config/.auth-token
 *   - Test data seeded (strategies, templates, etc.)
 *
 * Screenshots will be saved to: docs/assets/screenshots/
 */

import { chromium } from '@playwright/test';
import { authFixture } from '../fixtures/auth.fixture.js';
import {
  AutoPilotDashboardPage,
  AutoPilotStrategyBuilderPage,
  AutoPilotStrategyDetailPage,
  AutoPilotSettingsPage,
  AutoPilotTemplatesPage,
  AutoPilotJournalPage,
  AutoPilotAnalyticsPage,
  AutoPilotReportsPage,
  AutoPilotBacktestPage,
  AutoPilotSharingPage
} from '../pages/AutoPilotDashboardPage.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const SCREENSHOTS_DIR = path.join(__dirname, '../../../docs/assets/screenshots');
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';
const VIEWPORT = { width: 1920, height: 1080 }; // Full HD
const WAIT_FOR_LOAD = 2000; // Wait 2s for dynamic content to load

// Ensure screenshots directory exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

/**
 * Wait for page to be fully loaded with dynamic content
 */
async function waitForFullLoad(page, additionalWait = WAIT_FOR_LOAD) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(additionalWait); // Wait for charts, animations, etc.
}

/**
 * Take a full-page screenshot
 */
async function captureScreenshot(page, filename, description) {
  const fullPath = path.join(SCREENSHOTS_DIR, filename);
  console.log(`📸 Capturing: ${description}`);

  await waitForFullLoad(page);

  await page.screenshot({
    path: fullPath,
    fullPage: true,
    animations: 'disabled', // Disable animations for consistency
  });

  console.log(`   ✓ Saved: ${filename}`);
}

/**
 * Main screenshot capture function
 */
async function captureAllScreenshots() {
  console.log('🚀 Starting AutoPilot Screenshot Capture...\n');
  console.log(`📁 Screenshots will be saved to: ${SCREENSHOTS_DIR}\n`);

  // Launch browser
  const browser = await chromium.launch({
    headless: false, // Show browser for debugging
    args: ['--start-maximized']
  });

  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: undefined, // No video recording
  });

  const page = await context.newPage();

  try {
    // =========================================================================
    // AUTHENTICATE
    // =========================================================================
    console.log('🔐 Authenticating...');
    await authFixture.injectToken(page);
    console.log('   ✓ Authenticated\n');

    // =========================================================================
    // 1. AUTOPILOT DASHBOARD
    // =========================================================================
    console.log('1️⃣  AutoPilot Dashboard');
    const dashboardPage = new AutoPilotDashboardPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot`);
    await dashboardPage.waitForDashboardLoad();
    await captureScreenshot(page, 'autopilot-dashboard.png', 'Dashboard with active strategies');

    // =========================================================================
    // 2. STRATEGY BUILDER - ALL STEPS
    // =========================================================================
    console.log('\n2️⃣  Strategy Builder (All Steps)');
    const builderPage = new AutoPilotStrategyBuilderPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/strategies/new`);
    await builderPage.waitForBuilderLoad();

    // STEP 1: Strategy Setup
    console.log('   📋 Step 1: Strategy Setup');
    await builderPage.fillStrategyInfo({
      name: 'Iron Condor - Screenshot Demo',
      description: 'Sample strategy for documentation',
      underlying: 'NIFTY',
      lots: 1
    });
    await waitForFullLoad(page, 500);

    // Add a leg with strike to allow navigation (required for validation)
    try {
      await builderPage.addLeg({ strike: '25000', type: 'CE', action: 'SELL' });
      await waitForFullLoad(page, 500);
      console.log('      ✓ Added leg with strike 25000');
    } catch (error) {
      console.log('      ⚠ Could not add leg:', error.message);
    }

    await captureScreenshot(page, 'autopilot-strategy-builder-step1-setup.png', 'Strategy Builder - Step 1: Strategy Setup');

    // Navigate to Step 2: Entry Conditions (click on step indicator)
    try {
      // Click the "Next" button or step 2 indicator
      const nextButton = await page.getByRole('button', { name: /next/i }).first();
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await waitForFullLoad(page, 1500);
        console.log('   📋 Step 2: Entry Conditions');
        await captureScreenshot(page, 'autopilot-strategy-builder-step2-entry.png', 'Strategy Builder - Step 2: Entry Conditions');
      } else {
        console.log('      ⚠ Next button not found for step 2');
      }
    } catch (error) {
      console.log('      ⚠ Could not navigate to step 2:', error.message);
    }

    // Navigate to Step 3: Monitoring
    try {
      const nextButton = await page.getByRole('button', { name: /next/i }).first();
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await waitForFullLoad(page, 1500);
        console.log('   📋 Step 3: Monitoring');
        await captureScreenshot(page, 'autopilot-strategy-builder-step3-monitoring.png', 'Strategy Builder - Step 3: Monitoring');
      } else {
        console.log('      ⚠ Next button not found for step 3');
      }
    } catch (error) {
      console.log('      ⚠ Could not navigate to step 3:', error.message);
    }

    // Navigate to Step 4: Risk Settings
    try {
      const nextButton = await page.getByRole('button', { name: /next/i }).first();
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await waitForFullLoad(page, 1500);
        console.log('   📋 Step 4: Risk Settings');
        await captureScreenshot(page, 'autopilot-strategy-builder-step4-risk.png', 'Strategy Builder - Step 4: Risk Settings');
      } else {
        console.log('      ⚠ Next button not found for step 4');
      }
    } catch (error) {
      console.log('      ⚠ Could not navigate to step 4:', error.message);
    }

    // Navigate to Step 5: Review
    try {
      const nextButton = await page.getByRole('button', { name: /next/i }).first();
      if (await nextButton.isVisible()) {
        await nextButton.click();
        await waitForFullLoad(page, 1500);
        console.log('   📋 Step 5: Review');
        await captureScreenshot(page, 'autopilot-strategy-builder-step5-review.png', 'Strategy Builder - Step 5: Review');
      } else {
        console.log('      ⚠ Next button not found for step 5');
      }
    } catch (error) {
      console.log('      ⚠ Could not navigate to step 5:', error.message);
    }

    // =========================================================================
    // 3. STRATEGY BUILDER - EDIT (if strategy exists)
    // =========================================================================
    console.log('\n3️⃣  Strategy Builder (Edit Mode)');
    // Navigate to edit an existing strategy (ID: 1 as example)
    // Skip if no strategies exist
    try {
      await page.goto(`${FRONTEND_URL}/autopilot/strategies/1/edit`);
      await builderPage.waitForBuilderLoad();
      await captureScreenshot(page, 'autopilot-strategy-builder-edit.png', 'Strategy Builder - Edit Existing');
    } catch (error) {
      console.log('   ⚠ Skipped: No existing strategy to edit');
    }

    // =========================================================================
    // 4. STRATEGY DETAIL
    // =========================================================================
    console.log('\n4️⃣  Strategy Detail (Monitoring)');
    try {
      const detailPage = new AutoPilotStrategyDetailPage(page, 1);
      await detailPage.navigate();
      await detailPage.waitForStrategyLoad();
      await captureScreenshot(page, 'autopilot-strategy-detail.png', 'Strategy Detail - Real-time Monitoring');
    } catch (error) {
      console.log('   ⚠ Skipped: No existing strategy to view');
    }

    // =========================================================================
    // 5. SETTINGS
    // =========================================================================
    console.log('\n5️⃣  Settings');
    const settingsPage = new AutoPilotSettingsPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/settings`);
    await settingsPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-settings.png', 'Settings - Risk Limits & Preferences');

    // =========================================================================
    // 6. TEMPLATE LIBRARY
    // =========================================================================
    console.log('\n6️⃣  Template Library');
    const templatesPage = new AutoPilotTemplatesPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/templates`);
    await templatesPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-template-library.png', 'Template Library - Pre-built Strategies');

    // Capture template details modal (if templates exist)
    try {
      const templateCount = await templatesPage.getTemplateCount();
      if (templateCount > 0) {
        await templatesPage.clickTemplate(1);
        await page.waitForTimeout(500);
        await captureScreenshot(page, 'autopilot-template-details-modal.png', 'Template Details Modal');
        await templatesPage.closeDetailsModal();
      }
    } catch (error) {
      console.log('   ⚠ Skipped template details: No templates available');
    }

    // =========================================================================
    // 7. TRADE JOURNAL
    // =========================================================================
    console.log('\n7️⃣  Trade Journal');
    const journalPage = new AutoPilotJournalPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/journal`);
    await journalPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-trade-journal.png', 'Trade Journal - Execution History');

    // =========================================================================
    // 8. ANALYTICS
    // =========================================================================
    console.log('\n8️⃣  Analytics Dashboard');
    const analyticsPage = new AutoPilotAnalyticsPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/analytics`);
    await analyticsPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-analytics.png', 'Analytics - Performance Metrics');

    // =========================================================================
    // 9. REPORTS
    // =========================================================================
    console.log('\n9️⃣  Reports');
    const reportsPage = new AutoPilotReportsPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/reports`);
    await reportsPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-reports.png', 'Reports - Detailed Statistics');

    // Capture report generation modal
    try {
      await reportsPage.openGenerateModal();
      await page.waitForTimeout(500);
      await captureScreenshot(page, 'autopilot-reports-generate-modal.png', 'Generate Report Modal');
      await reportsPage.cancelGenerate();
    } catch (error) {
      console.log('   ⚠ Skipped generate modal');
    }

    // =========================================================================
    // 10. BACKTESTS
    // =========================================================================
    console.log('\n🔟 Backtests');
    const backtestPage = new AutoPilotBacktestPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/backtests`);
    await backtestPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-backtests.png', 'Backtests - Historical Simulations');

    // Capture backtest config modal
    try {
      await backtestPage.openConfigModal();
      await page.waitForTimeout(500);
      await captureScreenshot(page, 'autopilot-backtest-config-modal.png', 'Backtest Configuration Modal');
      await backtestPage.cancelConfig();
    } catch (error) {
      console.log('   ⚠ Skipped backtest config modal');
    }

    // =========================================================================
    // 11. SHARED STRATEGIES
    // =========================================================================
    console.log('\n1️⃣1️⃣  Shared Strategies');
    const sharingPage = new AutoPilotSharingPage(page);
    await page.goto(`${FRONTEND_URL}/autopilot/shared`);
    await sharingPage.waitForPageLoad();
    await captureScreenshot(page, 'autopilot-shared-strategies.png', 'Shared Strategies - Community Strategies');

    // =========================================================================
    // 12. SHARED STRATEGY VIEW (Public)
    // =========================================================================
    console.log('\n1️⃣2️⃣  Shared Strategy View (Public)');
    // This would require a valid share token
    // Skip for now unless you have a test share token
    console.log('   ⚠ Skipped: Requires valid share token');

    // =========================================================================
    // BONUS: KEY COMPONENTS & MODALS
    // =========================================================================
    console.log('\n🎁 Bonus: Key Components');

    // Kill Switch Modal (from dashboard)
    try {
      await page.goto(`${FRONTEND_URL}/autopilot`);
      await dashboardPage.waitForDashboardLoad();
      await dashboardPage.activateKillSwitch();
      await page.waitForTimeout(500);
      await captureScreenshot(page, 'autopilot-kill-switch-modal.png', 'Kill Switch Confirmation Modal');
      await dashboardPage.cancelKillSwitch();
    } catch (error) {
      console.log('   ⚠ Skipped kill switch modal');
    }

    // =========================================================================
    // COMPLETE
    // =========================================================================
    console.log('\n✅ Screenshot capture complete!');
    console.log(`\n📊 Summary:`);
    console.log(`   - Total screenshots: ${fs.readdirSync(SCREENSHOTS_DIR).filter(f => f.startsWith('autopilot-')).length}`);
    console.log(`   - Location: ${SCREENSHOTS_DIR}`);
    console.log(`\n💡 Next steps:`);
    console.log(`   1. Review screenshots in ${SCREENSHOTS_DIR}`);
    console.log(`   2. Update documentation with screenshot references`);
    console.log(`   3. Commit changes to git`);

  } catch (error) {
    console.error('\n❌ Error during screenshot capture:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

// Run the capture
captureAllScreenshots().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
