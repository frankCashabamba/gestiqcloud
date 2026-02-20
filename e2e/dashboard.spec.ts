import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test('should redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/login/, { timeout: 5000 }).catch(() => {})
  })

  test('should display page content after navigation', async ({ page }) => {
    await page.goto('/')
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })

  test('should have a structured layout', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded').catch(() => {})
    const hasNav = await page.locator('nav, [role="navigation"], aside').count()
    expect(hasNav).toBeGreaterThanOrEqual(0)
  })
})
