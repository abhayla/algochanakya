/**
 * Verification Screenshot Capture Script
 *
 * Usage:
 *   node tests/e2e/utils/verification-screenshot.js --feature=positions --screen=main
 *   node tests/e2e/utils/verification-screenshot.js --feature=positions --screen=exit-modal --state=open
 *
 * Arguments:
 *   --feature  : Feature name (positions, watchlist, autopilot, etc.)
 *   --screen   : Screen/component to capture (main, exit-modal, add-modal, etc.)
 *   --state    : Optional state (open, filled, error, success)
 */

import { chromium } from '@playwright/test';
import { authFixture } from '../fixtures/auth.fixture.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const SCREENSHOTS_DIR = path.join(__dirname, '../../../screenshots/verification');
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

// Feature URL mapping
const FEATURE_URLS = {
  'positions': '/positions',
  'watchlist': '/watchlist',
  'optionchain': '/option-chain',
  'strategy-builder': '/strategy',
  'strategy-library': '/strategies',
  'autopilot': '/autopilot',
  'dashboard': '/dashboard',
  'login': '/login'
};

// Main capture function
async function captureVerificationScreenshot(feature, screen, state) {
  // Create directory if needed
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  try {
    console.log(`📸 Capturing screenshot for ${feature}/${screen}`);

    // Authenticate
    await authFixture.injectToken(page);

    // Navigate to feature
    const baseUrl = FEATURE_URLS[feature] || `/${feature}`;
    await page.goto(`${FRONTEND_URL}${baseUrl}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // Handle specific screens/states (modals, etc.)
    if (screen !== 'main') {
      await triggerScreenState(page, feature, screen, state);
    }

    // Generate filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const stateSuffix = state ? `_${state}` : '';
    const filename = `${feature}_${screen}${stateSuffix}_${timestamp}.png`;

    // Capture screenshot
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, filename),
      fullPage: true,
      animations: 'disabled'
    });

    console.log(`   ✓ Screenshot saved: ${filename}`);
    return filename;

  } catch (error) {
    console.error(`   ✗ Error capturing screenshot: ${error.message}`);
    throw error;
  } finally {
    await browser.close();
  }
}

// Trigger specific screen states (modals, dropdowns, etc.)
async function triggerScreenState(page, feature, screen, state) {
  // Feature-specific state triggers
  const triggers = {
    'positions': {
      'exit-modal': async () => {
        await page.click('[data-testid="positions-row-exit-button"]');
        await page.waitForSelector('[data-testid="positions-exit-modal"]');
      },
      'add-modal': async () => {
        await page.click('[data-testid="positions-row-add-button"]');
        await page.waitForSelector('[data-testid="positions-add-modal"]');
      }
    },
    'autopilot': {
      'kill-switch-modal': async () => {
        await page.click('[data-testid="autopilot-kill-switch-button"]');
        await page.waitForSelector('[data-testid="autopilot-kill-switch-modal"]');
      }
    },
    'watchlist': {
      'add-instrument-modal': async () => {
        await page.click('[data-testid="watchlist-add-button"]');
        await page.waitForSelector('[data-testid="watchlist-add-instrument-modal"]');
      }
    },
    'strategy-builder': {
      'add-leg': async () => {
        await page.click('[data-testid="strategy-add-row-button"]');
        await page.waitForTimeout(500);
      }
    }
    // Add more feature/screen triggers as needed
  };

  const featureTriggers = triggers[feature];
  if (featureTriggers && featureTriggers[screen]) {
    await featureTriggers[screen]();
    await page.waitForTimeout(500); // Wait for animations
  }
}

// Parse CLI arguments and run
const args = process.argv.slice(2).reduce((acc, arg) => {
  const [key, value] = arg.replace('--', '').split('=');
  acc[key] = value;
  return acc;
}, {});

if (!args.feature) {
  console.error('Error: --feature argument is required');
  console.log('Usage: node verification-screenshot.js --feature=positions --screen=main');
  process.exit(1);
}

captureVerificationScreenshot(args.feature, args.screen || 'main', args.state)
  .then(() => {
    console.log('\n✅ Screenshot capture complete!');
    process.exit(0);
  })
  .catch(error => {
    console.error('\n❌ Screenshot capture failed:', error);
    process.exit(1);
  });
