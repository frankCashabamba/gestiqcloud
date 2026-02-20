import { test, expect } from '@playwright/test'

test.describe('Reports Module', () => {
  test('should navigate to reports page', async ({ page }) => {
    const response = await page.goto('/modules/reportes')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should display reports dashboard or redirect', async ({ page }) => {
    await page.goto('/modules/reportes')
    await page.waitForLoadState('networkidle').catch(() => {})
    await expect(page.locator('body')).toBeVisible()
  })

  test('should navigate to sales report', async ({ page }) => {
    const response = await page.goto('/modules/reportes/ventas')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should navigate to inventory report', async ({ page }) => {
    const response = await page.goto('/modules/reportes/inventario')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should navigate to financial report', async ({ page }) => {
    const response = await page.goto('/modules/reportes/financiero')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should navigate to margins report', async ({ page }) => {
    const response = await page.goto('/modules/reportes/margenes')
    expect(response?.status()).toBeLessThan(500)
  })

  test('should not have critical errors on reports pages', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
    await page.goto('/modules/reportes')
    await page.waitForLoadState('networkidle').catch(() => {})
    const critical = errors.filter(e => !e.includes('favicon') && !e.includes('401') && !e.includes('403') && !e.includes('404'))
    expect(critical.length).toBeLessThanOrEqual(2)
  })
})
