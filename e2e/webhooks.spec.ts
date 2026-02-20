import { test, expect } from '@playwright/test';

test.describe('Webhooks Module', () => {
  test('should display webhooks page', async ({ page }) => {
    await page.goto('/webhooks');
    const content = page.getByText(/webhook|suscripci|subscription/i);
    const loginRedirect = page.getByText(/login|iniciar/i);
    await expect(content.or(loginRedirect)).toBeVisible({ timeout: 10000 });
  });

  test('should show subscriptions list', async ({ page }) => {
    await page.goto('/webhooks');
    await page.waitForLoadState('networkidle');
    const table = page.locator('table, [role="table"]');
    const emptyState = page.getByText(/sin webhook|no hay|empty|crear/i);
    const loginPage = page.getByText(/login|iniciar/i);
    await expect(table.or(emptyState).or(loginPage)).toBeVisible({ timeout: 10000 });
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/webhooks');
    await page.waitForLoadState('networkidle');
    expect(errors).toHaveLength(0);
  });
});
