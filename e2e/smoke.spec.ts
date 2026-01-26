import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('app should load successfully', async ({ page }) => {
    const response = await page.goto('/');

    expect(response?.status()).toBeLessThan(400);
  });

  test('page should have a title', async ({ page }) => {
    await page.goto('/');

    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('page should not have console errors', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404')
    );

    expect(criticalErrors).toHaveLength(0);
  });

  test('page should be responsive', async ({ page }) => {
    await page.goto('/');

    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();

    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('body')).toBeVisible();
  });

  test('login page should load', async ({ page }) => {
    const response = await page.goto('/login');

    expect(response?.status()).toBeLessThan(400);
  });
});
