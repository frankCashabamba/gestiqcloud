/**
 * Tests for useSectorValidation hook exports
 */

describe('useSectorValidation hook', () => {
  it('should export useSectorValidation function', async () => {
    const module = await import('./useSectorValidation')
    expect(typeof module.useSectorValidation).toBe('function')
  })
})
