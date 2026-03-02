import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000, // 30 seconds - increased for stability with multiple browser contexts
  retries: process.env.CI ? 1 : 0,

  // 4 workers locally (headless), 2 in CI for stability
  workers: process.env.CI ? 2 : 4,
  fullyParallel: true,

  // Global setup runs once before all tests - handles login
  globalSetup: './tests/e2e/global-setup.js',

  // Core reporters always run; heavy reporters (json, junit, allure) only in CI
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ...(process.env.CI ? [
      ['json', { outputFile: 'test-results/results.json' }],
      ['junit', { outputFile: 'test-results/junit.xml' }],
      ['allure-playwright', {
        outputFolder: 'allure-results',
        suiteTitle: true,
        categories: [
          { name: 'Outdated tests', messageRegex: '.*FileNotFound.*' },
          { name: 'Product defects', messageRegex: '.*AssertionError.*' }
        ],
        environmentInfo: {
          Project: 'AlgoChanakya',
          Framework: 'Vue.js 3',
          Browser: 'Chromium'
        }
      }]
    ] : []),
  ],

  use: {
    baseURL: 'http://localhost:5173',
    headless: false,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    viewport: { width: 1280, height: 800 },

    // Increase expect timeout for live broker data assertions (default 5s too tight)
    expect: { timeout: 10000 },

    // Reuse auth state from global setup
    storageState: './tests/config/.auth-state.json',
  },

  // Dev servers - use port 8001 for backend (production uses 8000)
  webServer: [
    {
      command: 'cd backend && venv\\Scripts\\activate && python run.py --port 8001',
      url: 'http://localhost:8001/docs',  // Use /docs - always returns 200 even when Redis is down
      reuseExistingServer: true,
      timeout: 120000, // 2 minutes - allows for SmartAPI instrument master download
    },
    {
      command: 'cd frontend && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 60000,
    },
  ],

  projects: [
    // Main tests - use saved auth state (populated by globalSetup)
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
      },
      testIgnore: /.*\.isolated\.spec\.js/, // Skip isolated tests (they need fresh context)
    },
    // Isolated tests - fresh browser context (no auth state)
    {
      name: 'isolated',
      testMatch: /.*\.isolated\.spec\.js/,
      use: {
        browserName: 'chromium',
        storageState: undefined, // Fresh context, no saved auth
      },
    },
  ],
});
