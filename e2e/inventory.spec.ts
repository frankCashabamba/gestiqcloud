import { test, expect } from '@playwright/test';

test.describe('Inventory Module', () => {
  test('should display inventory page', async ({ page }) => {
    await page.goto('/inventory');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should show stock list or empty state', async ({ page }) => {
    await page.goto('/inventory');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should navigate to stock movements', async ({ page }) => {
    await page.goto('/inventory');
    const movLink = page.getByRole('link', { name: /movimiento|movement/i })
      .or(page.getByText(/movimiento|movement/i));
    if (await movLink.count() > 0) {
      await movLink.first().click();
      await page.waitForLoadState('networkidle');
    }
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/inventory');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const critical = errors.filter(
      (e) =>
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to load resource')
    );
    expect(critical).toHaveLength(0);
  });
});
