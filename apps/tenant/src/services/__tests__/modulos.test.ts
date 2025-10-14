import { afterEach, describe, expect, it, vi } from 'vitest'

describe('tenant módulos service routes', () => {
  afterEach(() => {
    vi.resetModules()
    vi.unmock('../lib/http')
    vi.clearAllMocks()
  })

  it('fetches tenant modules list from /v1/modulos/', async () => {
    const apiFetch = vi.fn().mockResolvedValue([])
    vi.doMock('../lib/http', () => ({ apiFetch }))

    const { listMisModulos } = await import('../modulos')

    await expect(listMisModulos('token')).resolves.toEqual([])

    expect(apiFetch).toHaveBeenCalledWith('/v1/modulos/', { authToken: 'token' })
  })

  it('fetches selectable modules using the empresa slug route', async () => {
    const apiFetch = vi.fn().mockResolvedValue([{ id: 1 }])
    vi.doMock('../lib/http', () => ({ apiFetch }))

    const { listModulosSeleccionablesPorEmpresa } = await import('../modulos')

    await expect(listModulosSeleccionablesPorEmpresa('bazár demo')).resolves.toEqual([{ id: 1 }])

    expect(apiFetch).toHaveBeenCalledWith('/v1/modulos/empresa/baz%C3%A1r%20demo/seleccionables')
  })
})
