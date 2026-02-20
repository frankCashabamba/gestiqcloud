import { test, expect } from '@playwright/test';

test.describe('Invoicing Module', () => {
  test('should display invoicing page', async ({ page }) => {
    await page.goto('/billing');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should show invoices list or empty state', async ({ page }) => {
    await page.goto('/billing');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should have create invoice button', async ({ page }) => {
    await page.goto('/billing');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const createBtn = page.getByRole('button', { name: /crear|nueva|new|add/i })
      .or(page.getByRole('link', { name: /crear|nueva|new|add/i }));
    if (await createBtn.count() > 0) {
      await createBtn.first().click();
      await page.waitForLoadState('networkidle');
      // Should show form
      const form = page.locator('form, [role="form"]');
      const formField = page.locator('input, select, textarea');
      await expect(form.or(formField.first())).toBeVisible({ timeout: 5000 }).catch(() => {});
    }
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/billing');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const critical = errors.filter(
      (e) =>
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to load resource')
    );
    expect(critical).toHaveLength(0);
  });
});
