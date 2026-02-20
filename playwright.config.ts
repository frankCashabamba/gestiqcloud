import { defineConfig, devices } from '@playwright/test';

declare const process: any;

const devPort = Number(process.env.PLAYWRIGHT_WEB_PORT || 5173);
const devHost = process.env.PLAYWRIGHT_WEB_HOST || 'localhost';
const baseURL = process.env.BASE_URL || `http://${devHost}:${devPort}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? Number(process.env.PLAYWRIGHT_RETRIES || 1) : 0,
  workers: process.env.CI ? Number(process.env.PLAYWRIGHT_WORKERS || 2) : undefined,
  reporter: process.env.CI ? [['line'], ['html', { open: 'never' }]] : 'html',
  timeout: 30000,

  use: {
    baseURL,
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: `http://${devHost}:${devPort}`,
    reuseExistingServer: !process.env.CI,
    cwd: './apps/tenant',
    env: {
      ...process.env,
      HOST: process.env.HOST || '0.0.0.0',
      PORT: process.env.PORT || String(devPort),
      VITE_API_URL: process.env.VITE_API_URL || `http://${devHost}:${devPort}/api`,
      VITE_BASE_PATH: process.env.VITE_BASE_PATH || '/',
      VITE_TENANT_ORIGIN: process.env.VITE_TENANT_ORIGIN || 'http://localhost:8082',
      VITE_ADMIN_ORIGIN: process.env.VITE_ADMIN_ORIGIN || 'http://localhost:8081',
    },
  },
});
