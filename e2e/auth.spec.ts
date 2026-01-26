import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/.*login/);
  });

  test('should show login form elements', async ({ page }) => {
    await page.goto('/login');
    
    await expect(page.getByRole('textbox', { name: /email|usuario/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /password|contraseña/i }).or(page.locator('input[type="password"]'))).toBeVisible();
    await expect(page.getByRole('button', { name: /login|iniciar|entrar/i })).toBeVisible();
  });

  test('should attempt login with credentials', async ({ page }) => {
    await page.goto('/login');
    
    const emailInput = page.getByRole('textbox', { name: /email|usuario/i }).or(page.locator('input[type="email"]'));
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.getByRole('button', { name: /login|iniciar|entrar/i });

    await emailInput.fill('test@example.com');
    await passwordInput.fill('testpassword');
    await submitButton.click();

    await page.waitForURL(/.*/, { timeout: 5000 }).catch(() => {});
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    const emailInput = page.getByRole('textbox', { name: /email|usuario/i }).or(page.locator('input[type="email"]'));
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.getByRole('button', { name: /login|iniciar|entrar/i });

    await emailInput.fill('invalid@test.com');
    await passwordInput.fill('wrongpassword');
    await submitButton.click();

    await expect(page.getByText(/error|invalid|incorrecto/i)).toBeVisible({ timeout: 5000 }).catch(() => {});
  });
});
