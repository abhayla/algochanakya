#!/usr/bin/env node
/**
 * Test Scaffold Generator
 *
 * Generates test scaffolds for new screens following the established patterns.
 *
 * Usage:
 *   npm run generate:test -- --screen MyNewScreen --path /mynewscreen
 *
 * Generates:
 *   - pages/MyNewScreenPage.js (Page Object)
 *   - specs/mynewscreen/mynewscreen.happy.spec.js
 *   - specs/mynewscreen/mynewscreen.edge.spec.js
 *   - specs/mynewscreen/mynewscreen.visual.spec.js
 *   - specs/mynewscreen/mynewscreen.api.spec.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const result = { screen: null, path: null };

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--screen' && args[i + 1]) {
      result.screen = args[i + 1];
      i++;
    } else if (args[i] === '--path' && args[i + 1]) {
      result.path = args[i + 1];
      i++;
    }
  }

  return result;
}

// Generate Page Object template
function generatePageObject(screenName, routePath) {
  const className = `${screenName}Page`;
  const testIdPrefix = screenName.toLowerCase();

  return `/**
 * ${screenName} Page Object
 *
 * Usage:
 *   import { ${className} } from '../pages/${className}.js';
 *   const page = new ${className}(page);
 *   await page.navigate();
 */

import { BasePage } from './BasePage.js';

export class ${className} extends BasePage {
  constructor(page) {
    super(page);
    this.url = '${routePath}';
  }

  // Selectors
  get container() {
    return this.getByTestId('${testIdPrefix}-page');
  }

  // Add more selectors as needed:
  // get someElement() {
  //   return this.getByTestId('${testIdPrefix}-some-element');
  // }

  // Actions
  async waitForPageLoad() {
    await this.waitForTestId('${testIdPrefix}-page');
    await this.waitForLoad();
  }

  // Add more actions as needed:
  // async clickSomeButton() {
  //   await this.clickTestId('${testIdPrefix}-some-button');
  // }

  // Assertions
  async isPageVisible() {
    return await this.isTestIdVisible('${testIdPrefix}-page');
  }
}
`;
}

// Generate Happy Path test template
function generateHappySpec(screenName, routePath) {
  const className = `${screenName}Page`;
  const testIdPrefix = screenName.toLowerCase();
  const specName = testIdPrefix;

  return `/**
 * ${screenName} Happy Path Tests
 *
 * Tests for normal user flows and expected behavior.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { ${className} } from '../../pages/${className}.js';

test.describe('${screenName} - Happy Path @happy', () => {
  let ${specName}Page;

  test.beforeEach(async ({ authenticatedPage }) => {
    ${specName}Page = new ${className}(authenticatedPage);
    await ${specName}Page.navigate();
  });

  test('page loads successfully', async ({ authenticatedPage }) => {
    await expect(${specName}Page.container).toBeVisible();
  });

  test('has correct URL', async ({ authenticatedPage }) => {
    expect(${specName}Page.urlContains('${routePath}')).toBe(true);
  });

  // TODO: Add more happy path tests specific to ${screenName}
  // Examples:
  // test('displays main content', async () => {
  //   await expect(${specName}Page.getByTestId('${testIdPrefix}-main-content')).toBeVisible();
  // });
  //
  // test('user can perform main action', async () => {
  //   await ${specName}Page.clickSomeButton();
  //   await expect(${specName}Page.getByTestId('${testIdPrefix}-result')).toBeVisible();
  // });
});
`;
}

// Generate Edge Case test template
function generateEdgeSpec(screenName, routePath) {
  const className = `${screenName}Page`;
  const testIdPrefix = screenName.toLowerCase();
  const specName = testIdPrefix;

  return `/**
 * ${screenName} Edge Case Tests
 *
 * Tests for error states, edge cases, and boundary conditions.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { ${className} } from '../../pages/${className}.js';

test.describe('${screenName} - Edge Cases @edge', () => {
  let ${specName}Page;

  test.beforeEach(async ({ authenticatedPage }) => {
    ${specName}Page = new ${className}(authenticatedPage);
  });

  test('handles empty state gracefully', async ({ authenticatedPage }) => {
    await ${specName}Page.navigate();
    // TODO: Implement empty state check
    // await expect(${specName}Page.getByTestId('${testIdPrefix}-empty-state')).toBeVisible();
  });

  test('handles loading state', async ({ authenticatedPage }) => {
    await ${specName}Page.navigate();
    // Loading state should appear briefly then resolve
    await ${specName}Page.waitForPageLoad();
    await expect(${specName}Page.container).toBeVisible();
  });

  test('no horizontal overflow at any viewport', async ({ authenticatedPage }) => {
    await ${specName}Page.navigate();
    await ${specName}Page.waitForPageLoad();

    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1440, height: 900 },
      { width: 1024, height: 768 }
    ];

    for (const viewport of viewports) {
      await ${specName}Page.setViewportSize(viewport.width, viewport.height);
      const hasOverflow = await ${specName}Page.hasHorizontalOverflow();
      expect(hasOverflow).toBe(false);
    }
  });

  // TODO: Add more edge case tests specific to ${screenName}
  // Examples:
  // test('handles network error', async () => { ... });
  // test('handles invalid data', async () => { ... });
});
`;
}

// Generate Visual Regression test template
function generateVisualSpec(screenName, routePath) {
  const className = `${screenName}Page`;
  const testIdPrefix = screenName.toLowerCase();
  const specName = testIdPrefix;

  return `/**
 * ${screenName} Visual Regression Tests
 *
 * Screenshot comparisons for UI consistency.
 */

import { test, expect } from '../../fixtures/auth.fixture.js';
import { ${className} } from '../../pages/${className}.js';
import { prepareForVisualTest, getVisualCompareOptions, VIEWPORTS } from '../../helpers/visual.helper.js';

test.describe('${screenName} - Visual Regression @visual', () => {
  let ${specName}Page;

  test.beforeEach(async ({ authenticatedPage }) => {
    ${specName}Page = new ${className}(authenticatedPage);
    await ${specName}Page.navigate();
    await ${specName}Page.waitForPageLoad();
  });

  test('desktop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.desktop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      '${testIdPrefix}-desktop.png',
      getVisualCompareOptions()
    );
  });

  test('laptop layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.laptop);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      '${testIdPrefix}-laptop.png',
      getVisualCompareOptions()
    );
  });

  test('tablet layout matches baseline', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize(VIEWPORTS.tablet);
    await prepareForVisualTest(authenticatedPage);
    await expect(authenticatedPage).toHaveScreenshot(
      '${testIdPrefix}-tablet.png',
      getVisualCompareOptions()
    );
  });

  // TODO: Add state-specific visual tests
  // test('empty state matches baseline', async ({ authenticatedPage }) => {
  //   await prepareForVisualTest(authenticatedPage);
  //   await expect(authenticatedPage).toHaveScreenshot(
  //     '${testIdPrefix}-empty.png',
  //     getVisualCompareOptions()
  //   );
  // });
});
`;
}

// Generate API Validation test template
function generateApiSpec(screenName, routePath) {
  const testIdPrefix = screenName.toLowerCase();

  return `/**
 * ${screenName} API Validation Tests
 *
 * Tests for API endpoint responses and data integrity.
 */

import { test, expect } from '@playwright/test';

const API_BASE = process.env.API_BASE || 'http://localhost:8001';

test.describe('${screenName} - API Validation @api', () => {
  // TODO: Add API tests specific to ${screenName}
  // Example structure:

  // test('GET /api/${testIdPrefix} returns valid data', async ({ request }) => {
  //   const response = await request.get(\`\${API_BASE}/api/${testIdPrefix}\`, {
  //     headers: {
  //       'Authorization': \`Bearer \${process.env.TEST_AUTH_TOKEN}\`
  //     }
  //   });
  //
  //   expect(response.ok()).toBe(true);
  //   const data = await response.json();
  //   expect(data).toBeDefined();
  // });

  // test('POST /api/${testIdPrefix} creates resource', async ({ request }) => {
  //   const response = await request.post(\`\${API_BASE}/api/${testIdPrefix}\`, {
  //     headers: {
  //       'Authorization': \`Bearer \${process.env.TEST_AUTH_TOKEN}\`,
  //       'Content-Type': 'application/json'
  //     },
  //     data: { /* request body */ }
  //   });
  //
  //   expect(response.ok()).toBe(true);
  // });

  test.skip('placeholder - implement API tests', async () => {
    // Remove this test and implement actual API tests
  });
});
`;
}

// Create directory if it doesn't exist
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`Created directory: ${dirPath}`);
  }
}

// Write file with logging
function writeFile(filePath, content) {
  fs.writeFileSync(filePath, content);
  console.log(`Created file: ${filePath}`);
}

// Main function
function main() {
  const args = parseArgs();

  if (!args.screen || !args.path) {
    console.error('Usage: npm run generate:test -- --screen ScreenName --path /route-path');
    console.error('');
    console.error('Example:');
    console.error('  npm run generate:test -- --screen Orders --path /orders');
    process.exit(1);
  }

  const screenName = args.screen;
  const routePath = args.path;
  const specDir = screenName.toLowerCase();

  // Base paths
  const testsDir = path.resolve(__dirname, '..');
  const pagesDir = path.join(testsDir, 'pages');
  const specsDir = path.join(testsDir, 'specs', specDir);

  console.log(`\nGenerating test scaffolds for ${screenName}...`);
  console.log(`Route: ${routePath}`);
  console.log('');

  // Ensure directories exist
  ensureDir(pagesDir);
  ensureDir(specsDir);

  // Generate Page Object
  const pageObjectPath = path.join(pagesDir, `${screenName}Page.js`);
  if (fs.existsSync(pageObjectPath)) {
    console.log(`Skipping ${pageObjectPath} (already exists)`);
  } else {
    writeFile(pageObjectPath, generatePageObject(screenName, routePath));
  }

  // Generate spec files
  const specFiles = [
    { name: `${specDir}.happy.spec.js`, generator: generateHappySpec },
    { name: `${specDir}.edge.spec.js`, generator: generateEdgeSpec },
    { name: `${specDir}.visual.spec.js`, generator: generateVisualSpec },
    { name: `${specDir}.api.spec.js`, generator: generateApiSpec }
  ];

  for (const spec of specFiles) {
    const specPath = path.join(specsDir, spec.name);
    if (fs.existsSync(specPath)) {
      console.log(`Skipping ${specPath} (already exists)`);
    } else {
      writeFile(specPath, spec.generator(screenName, routePath));
    }
  }

  console.log('');
  console.log('Done! Next steps:');
  console.log(`1. Add data-testid attributes to ${screenName} Vue component`);
  console.log(`2. Customize the generated Page Object: ${pageObjectPath}`);
  console.log(`3. Fill in the TODO sections in the spec files`);
  console.log(`4. Run tests: npx playwright test specs/${specDir}/`);
}

main();
