/**
 * Tests for useCurrency hook exports
 */

describe('useCurrency hook', () => {
  it('should export useCurrency function', async () => {
    const module = await import('./useCurrency')
    expect(typeof module.useCurrency).toBe('function')
  })
})
