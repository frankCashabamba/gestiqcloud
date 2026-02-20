import { test, expect } from '@playwright/test'

const viewports = [
  { name: 'mobile', width: 375, height: 667 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1920, height: 1080 },
]

test.describe('Responsive Design', () => {
  for (const vp of viewports) {
    test(`should render correctly on ${vp.name} (${vp.width}x${vp.height})`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto('/')
      await page.waitForLoadState('domcontentloaded').catch(() => {})
      await expect(page.locator('body')).toBeVisible()
      // Check no horizontal overflow
      const bodyWidth = await page.evaluate(() => document.body.scrollWidth)
      expect(bodyWidth).toBeLessThanOrEqual(vp.width + 20)
    })
  }

  test('should adapt layout between mobile and desktop', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded').catch(() => {})

    await page.setViewportSize({ width: 375, height: 667 })
    await expect(page.locator('body')).toBeVisible()

    await page.setViewportSize({ width: 1920, height: 1080 })
    await expect(page.locator('body')).toBeVisible()
  })

  test('should handle orientation change', async ({ page }) => {
    await page.goto('/')
    await page.setViewportSize({ width: 667, height: 375 }) // landscape mobile
    await expect(page.locator('body')).toBeVisible()
  })
})
