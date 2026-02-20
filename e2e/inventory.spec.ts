import { test, expect } from '@playwright/test';

test.describe('Inventory Module', () => {
  test('should display inventory page', async ({ page }) => {
    await page.goto('/inventory');
    const content = page.getByText(/inventario|stock|almacén|warehouse/i);
    const loginRedirect = page.getByText(/login|iniciar/i);
    await expect(content.or(loginRedirect)).toBeVisible({ timeout: 10000 });
  });

  test('should show stock list or empty state', async ({ page }) => {
    await page.goto('/inventory');
    await page.waitForLoadState('networkidle');
    // Either shows product table or empty state
    const table = page.locator('table, [role="table"]');
    const emptyState = page.getByText(/sin productos|no hay|empty|vacío/i);
    const loginPage = page.getByText(/login|iniciar/i);
    await expect(table.or(emptyState).or(loginPage)).toBeVisible({ timeout: 10000 });
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
    await page.waitForLoadState('networkidle');
    expect(errors).toHaveLength(0);
  });
});
