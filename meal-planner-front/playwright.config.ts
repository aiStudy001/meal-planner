import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for screenshot capture
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',

  // Run tests sequentially for consistent screenshots
  fullyParallel: false,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // No retries for screenshot capture
  retries: 0,

  // Single worker for consistent screenshot timing
  workers: 1,

  // Reporter to use
  reporter: 'list',

  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:5173',

    // Collect screenshot only when test fails
    screenshot: 'only-on-failure',

    // Collect trace only when test fails
    trace: 'retain-on-failure',

    // Consistent viewport size for all screenshots
    viewport: { width: 1280, height: 800 },
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Run dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120000, // 2 minutes for server startup
  },
});
