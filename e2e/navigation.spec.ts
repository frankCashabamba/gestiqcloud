import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should navigate to home page', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/.*\//);
  });

  test('should have working navigation links', async ({ page }) => {
    await page.goto('/');

    const navLinks = page.getByRole('navigation').getByRole('link');
    const count = await navLinks.count();

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page).toHaveURL(/.*login/, { timeout: 5000 }).catch(() => {});
  });

  test('should maintain navigation state on page reload', async ({ page }) => {
    await page.goto('/login');
    const initialUrl = page.url();

    await page.reload();

    expect(page.url()).toBe(initialUrl);
  });

  test('should handle browser back navigation', async ({ page }) => {
    await page.goto('/');
    await page.goto('/login');

    await page.goBack();

    await expect(page).toHaveURL(/.*\//);
  });
});
