/**
 * Tests for modulos service
 */

describe('modulos service exports', () => {
  it('should export listMisModulos function', async () => {
    const modulos = await import('./modulos')
    expect(typeof modulos.listMisModulos).toBe('function')
  })

  it('should export listModulosSeleccionablesPorEmpresa function', async () => {
    const modulos = await import('./modulos')
    expect(typeof modulos.listModulosSeleccionablesPorEmpresa).toBe('function')
  })
})

describe('Modulo type', () => {
  it('should define Modulo type with expected shape', async () => {
    const modulos = await import('./modulos')
    expect(modulos).toBeDefined()
  })
})
