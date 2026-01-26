/**
 * Tests for useMisModulos hook exports
 */

describe('useMisModulos hook', () => {
  it('should export useMisModulos function', async () => {
    const module = await import('./useMisModulos')
    expect(typeof module.useMisModulos).toBe('function')
  })
})
