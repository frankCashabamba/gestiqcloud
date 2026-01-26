/**
 * Tests for useCountryValidation hook exports
 */

describe('useCountryValidation hook', () => {
  it('should export useCountryValidation function', async () => {
    const module = await import('./useCountryValidation')
    expect(typeof module.useCountryValidation).toBe('function')
  })
})
