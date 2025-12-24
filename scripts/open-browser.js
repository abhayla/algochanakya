import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

(async () => {
  // Read auth state
  const authStatePath = path.join(__dirname, '../tests/config/.auth-state.json');

  let authState;
  try {
    authState = JSON.parse(fs.readFileSync(authStatePath, 'utf-8'));
    console.log('✅ Auth state loaded successfully');
  } catch (error) {
    console.error('❌ Failed to load auth state:', error.message);
    process.exit(1);
  }

  // Launch browser in headed mode
  const browser = await chromium.launch({
    headless: false,
    args: ['--start-maximized']
  });

  const context = await browser.newContext({
    viewport: null, // Use full window size
    storageState: authState
  });

  const page = await context.newPage();

  // Navigate to dashboard
  console.log('🌐 Opening dashboard at http://localhost:5173/dashboard');
  await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle' });

  console.log('✅ Browser opened successfully!');
  console.log('📝 Auth token injected from tests/config/.auth-state.json');
  console.log('⏸️  Browser will remain open for manual testing');
  console.log('🛑 Close the browser window to exit');

  // Keep the script running until browser is closed
  await page.waitForEvent('close').catch(() => {});

  await browser.close();
  console.log('👋 Browser closed');
})();
