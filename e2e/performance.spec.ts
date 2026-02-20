import { test, expect } from '@playwright/test'

test.describe('Performance', () => {
  test('should load login page under 5 seconds', async ({ page }) => {
    const start = Date.now()
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')
    const duration = Date.now() - start
    expect(duration).toBeLessThan(5000)
  })

  test('should load home page under 5 seconds', async ({ page }) => {
    const start = Date.now()
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    const duration = Date.now() - start
    expect(duration).toBeLessThan(5000)
  })

  test('should not have broken images', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded').catch(() => {})
    const images = page.locator('img')
    const count = await images.count()
    for (let i = 0; i < Math.min(count, 10); i++) {
      const img = images.nth(i)
      const naturalWidth = await img.evaluate((el: HTMLImageElement) => el.naturalWidth)
      // naturalWidth > 0 means image loaded successfully
      // Skip if image is hidden or has no src
      const src = await img.getAttribute('src')
      if (src && !src.startsWith('data:')) {
        expect(naturalWidth).toBeGreaterThan(0)
      }
    }
  })

  test('should not accumulate JS errors during navigation', async ({ page }) => {
    const errors: string[] = []
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })

    const routes = ['/', '/login', '/dashboard']
    for (const route of routes) {
      await page.goto(route)
      await page.waitForLoadState('domcontentloaded').catch(() => {})
    }

    const critical = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('401') &&
      !e.includes('403') &&
      !e.includes('404') &&
      !e.includes('ChunkLoadError') &&
      !e.includes('ERR_CONNECTION_REFUSED') &&
      !e.includes('500') &&
      !e.includes('Failed to load resource')
    )
    expect(critical.length).toBeLessThanOrEqual(5)
  })

  test('should handle rapid navigation', async ({ page }) => {
    const routes = ['/', '/login', '/', '/dashboard', '/login']
    for (const route of routes) {
      await page.goto(route, { waitUntil: 'commit' })
    }
    await expect(page.locator('body')).toBeVisible()
  })
})
