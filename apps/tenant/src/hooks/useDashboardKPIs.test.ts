/**
 * Tests for useDashboardKPIs hook exports
 */

describe('useDashboardKPIs hook', () => {
  it('should export useDashboardKPIs function', async () => {
    const module = await import('./useDashboardKPIs')
    expect(typeof module.useDashboardKPIs).toBe('function')
  })
})
