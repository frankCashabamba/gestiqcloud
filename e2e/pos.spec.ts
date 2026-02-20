import { test, expect } from '@playwright/test';

test.describe('POS Module', () => {
  test('should display POS interface', async ({ page }) => {
    await page.goto('/pos');
    // Should show POS or redirect to login
    await expect(page.locator('body')).not.toBeEmpty();
    const hasError = await page.locator('.error, [role="alert"]').count();
    expect(hasError).toBe(0);
  });

  test('should show register selection or POS view', async ({ page }) => {
    await page.goto('/pos');
    // Either shows register selector or POS main view
    const posContent = page.getByText(/caja|register|punto de venta|POS/i);
    const loginRedirect = page.getByText(/login|iniciar/i);
    await expect(posContent.or(loginRedirect)).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to POS shifts', async ({ page }) => {
    await page.goto('/pos');
    const shiftsLink = page.getByRole('link', { name: /turno|shift/i })
      .or(page.getByText(/turno|shift/i));
    if (await shiftsLink.count() > 0) {
      await shiftsLink.first().click();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('body')).not.toBeEmpty();
    }
  });

  test('should not have JavaScript errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/pos');
    await page.waitForLoadState('networkidle');
    expect(errors).toHaveLength(0);
  });
});
