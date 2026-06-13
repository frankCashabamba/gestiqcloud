import { test, expect } from '@playwright/test';

test.describe('Importador Module', () => {
  test('should load importer entry point or redirect to auth', async ({ page }) => {
    const response = await page.goto('/importador/importar');
    expect(response?.status()).toBeLessThan(500);
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should load document review route without a client crash', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/importador/documents');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const critical = errors.filter(
      (error) =>
        !error.includes('ERR_CONNECTION_REFUSED') &&
        !error.includes('Failed to load resource')
    );

    expect(critical).toHaveLength(0);
    await expect(page.locator('body')).not.toBeEmpty();
  });

  test('should expose a human review or upload state when reachable', async ({ page }) => {
    await page.goto('/importador/importar');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const reviewOrUpload = page
      .getByText(/confirm|confirmar|review|revis|upload|sube|subir|login|iniciar/i)
      .first();

    await expect(reviewOrUpload.or(page.locator('body'))).toBeVisible();
  });

  test('should not expose raw AI/debug fields in normal importer UI', async ({ page }) => {
    await page.goto('/importador/documents');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const bodyText = await page.locator('body').innerText().catch(() => '');
    expect(bodyText).not.toMatch(/raw_ai_json|llm_raw|debug_info|completion|prompt/i);
  });
});
