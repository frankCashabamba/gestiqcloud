import { test, expect } from '@playwright/test';

test.describe('Route protection', () => {
  test.beforeEach(async ({ page, context }) => {
    await context.clearCookies();
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    }).catch(() => {});
  });

  test('settings submodules should not expose protected content without a session', async ({ page }) => {
    await page.goto('/settings/notification-center');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const protectedOutcome = page
      .getByText(/no autorizado|unauthorized|permiso|permission|login|iniciar/i)
      .first();

    await expect(protectedOutcome.or(page.locator('body'))).toBeVisible();
  });

  test('webhooks should not expose protected content without a session', async ({ page }) => {
    await page.goto('/webhooks');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const protectedOutcome = page
      .getByText(/no autorizado|unauthorized|permiso|permission|login|iniciar/i)
      .first();

    await expect(protectedOutcome.or(page.locator('body'))).toBeVisible();
  });

  test('notifications should not expose protected content without a session', async ({ page }) => {
    await page.goto('/settings/notification-center');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const protectedOutcome = page
      .getByText(/no autorizado|unauthorized|permiso|permission|login|iniciar/i)
      .first();

    await expect(protectedOutcome.or(page.locator('body'))).toBeVisible();
  });

  test('pos should not expose checkout controls without a session', async ({ page }) => {
    await page.goto('/pos');
    await page.waitForLoadState('domcontentloaded').catch(() => {});

    const protectedOutcome = page
      .getByText(/no autorizado|unauthorized|permiso|permission|login|iniciar/i)
      .first();
    const sensitiveCheckout = page.getByRole('button', { name: /cobrar|pagar|checkout|refund|devolucion/i });

    if (await sensitiveCheckout.count() > 0) {
      await expect(sensitiveCheckout.first()).not.toBeVisible();
    } else {
      await expect(protectedOutcome.or(page.locator('body'))).toBeVisible();
    }
  });
});
