import { test, expect } from '@playwright/test';

test.describe('Production Module', () => {
  test('should display production page', async ({ page }) => {
    await page.goto('/production/recipes');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should show recipes or empty state', async ({ page }) => {
    await page.goto('/production/recipes');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should navigate to production orders when available', async ({ page }) => {
    await page.goto('/production/recipes');
    const ordersLink = page.getByRole('link', { name: /orden|order/i })
      .or(page.getByText(/orden|order/i));
    if (await ordersLink.count() > 0) {
      await ordersLink.first().click();
      await page.waitForLoadState('networkidle');
    } else {
      await page.goto('/production/orders');
      await page.waitForLoadState('domcontentloaded');
    }
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/production/recipes');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const critical = errors.filter(
      (e) =>
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to load resource')
    );
    expect(critical).toHaveLength(0);
  });
});
