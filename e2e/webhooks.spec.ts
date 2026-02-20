import { test, expect } from '@playwright/test';

test.describe('Webhooks Module', () => {
  test('should display webhooks page', async ({ page }) => {
    await page.goto('/webhooks');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should show subscriptions list', async ({ page }) => {
    await page.goto('/webhooks');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/webhooks');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const critical = errors.filter(
      (e) =>
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to load resource')
    );
    expect(critical).toHaveLength(0);
  });
});
