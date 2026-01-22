import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000, // 30 seconds - increased for stability with multiple browser contexts
  retries: 0,

  // 2 parallel workers for stability (reduced from 4 to prevent context creation timeouts)
  workers: 2,
  fullyParallel: true,

  // Global setup runs once before all tests - handles login
  globalSetup: './tests/e2e/global-setup.js',

  // Multiple reporters for comprehensive test reporting
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['allure-playwright', {
      outputFolder: 'allure-results',
      suiteTitle: true,
      categories: [
        {
          name: 'Outdated tests',
          messageRegex: '.*FileNotFound.*'
        },
        {
          name: 'Product defects',
          messageRegex: '.*AssertionError.*'
        }
      ],
      environmentInfo: {
        Project: 'AlgoChanakya',
        Framework: 'Vue.js 3',
        Browser: 'Chromium'
      }
    }]
  ],

  use: {
    baseURL: 'http://localhost:5173',
    headless: false,
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Maximized browser window (viewport: null uses actual window size)
    viewport: null,
    launchOptions: {
      args: ['--start-maximized'],
    },

    // Reuse auth state from global setup
    storageState: './tests/config/.auth-state.json',
  },

  // Dev servers - use port 8001 for backend (production uses 8000)
  webServer: [
    {
      command: 'cd backend && venv\\Scripts\\activate && python run.py --port 8001',
      url: 'http://localhost:8001/health',
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: 'cd frontend && npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],

  projects: [
    // Setup project - runs first, does login
    {
      name: 'setup',
      testMatch: /global-setup\.spec\.js/,
      use: {
        storageState: undefined, // No auth state for setup
      },
    },
    // Main tests - use saved auth state
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        viewport: null, // Ensure maximized window is not overridden
      },
      dependencies: ['setup'], // Wait for setup to complete
      testIgnore: /.*\.isolated\.spec\.js/, // Skip isolated tests (they need fresh context)
    },
    // Isolated tests - fresh browser context (no auth state)
    {
      name: 'isolated',
      testMatch: /.*\.isolated\.spec\.js/,
      use: {
        browserName: 'chromium',
        viewport: null,
        storageState: undefined, // Fresh context, no saved auth
      },
    },
  ],
});
