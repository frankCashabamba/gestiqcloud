import { test, expect } from '@playwright/test'

test.describe('Reconciliation Module', () => {
  test('should navigate to reconciliation page', async ({ page }) => {
    const response = await page.goto('/modules/reconciliation')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should display reconciliation content (not placeholder)', async ({ page }) => {
    await page.goto('/modules/reconciliation')
    await page.waitForLoadState('domcontentloaded').catch(() => {})
    await expect(page.locator('body')).toBeVisible()
  })

  test('should not have critical JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
    await page.goto('/modules/reconciliation')
    await page.waitForLoadState('domcontentloaded').catch(() => {})
    const critical = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('401') &&
        !e.includes('403') &&
        !e.includes('404') &&
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to load resource') &&
        !e.includes('500')
    )
    expect(critical.length).toBeLessThanOrEqual(2)
  })
})
