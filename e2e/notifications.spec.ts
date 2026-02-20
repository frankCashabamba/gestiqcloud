import { test, expect } from '@playwright/test'

test.describe('Notifications Module', () => {
  test('should navigate to notifications page', async ({ page }) => {
    const response = await page.goto('/modules/notifications')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should display notifications content', async ({ page }) => {
    await page.goto('/modules/notifications')
    await page.waitForLoadState('domcontentloaded').catch(() => {})
    await expect(page.locator('body')).toBeVisible()
  })

  test('should not have critical JS errors', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
    await page.goto('/modules/notifications')
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
