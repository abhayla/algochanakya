import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 180000, // 3 minutes for manual login
  retries: 0,

  // Single worker = single browser window, no flickering
  workers: 1,
  fullyParallel: false,

  // Global setup runs once before all tests - handles login
  globalSetup: './tests/e2e/global-setup.js',

  use: {
    baseURL: 'http://localhost:5173',
    headless: false,
    screenshot: 'on',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Reuse auth state from global setup
    storageState: './tests/config/.auth-state.json',
  },

  webServer: [
    {
      command: 'cd backend && venv\\Scripts\\activate && python run.py',
      url: 'http://localhost:8000/api/health',
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
      use: { browserName: 'chromium' },
      dependencies: ['setup'], // Wait for setup to complete
    },
  ],
});
