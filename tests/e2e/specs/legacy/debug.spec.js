import { test, expect } from '@playwright/test';

test('debug: check what Playwright sees', async ({ page }) => {
  // Go to login page
  await page.goto('http://localhost:5174/login', { waitUntil: 'networkidle' });

  // Wait for Vue to mount
  await page.waitForTimeout(3000);

  // Take screenshot
  await page.screenshot({ path: 'tests/screenshots/login-page.png', fullPage: true });

  // Print page content
  const html = await page.content();
  console.log('Page HTML length:', html.length);
  console.log('First 2000 chars:', html.substring(0, 2000));

  // Check what's in the DOM
  const body = await page.locator('body').innerHTML();
  console.log('Body content:', body.substring(0, 1000));

  // Check for Vue app mount point
  const appDiv = await page.locator('#app').count();
  console.log('Found #app div:', appDiv);

  // Check for any buttons
  const buttons = await page.locator('button').count();
  console.log('Found buttons:', buttons);

  // Check for any links
  const links = await page.locator('a').count();
  console.log('Found links:', links);

  // List all visible text
  const allText = await page.locator('body').innerText();
  console.log('Visible text:', allText);

  // Check for JavaScript errors
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
});
