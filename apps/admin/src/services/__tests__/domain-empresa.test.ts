import { describe, expect, it, vi } from 'vitest'

import { createEmpresaService } from '@shared/domain/empresa'

describe('createEmpresaService (shared domain)', () => {
  it('uses the provided base path for CRUD helpers and returns backend payloads', async () => {
    const get = vi.fn().mockResolvedValue({ data: [{ id: 1 }] })
    const post = vi.fn().mockResolvedValue({ data: { id: 5 } })
    const put = vi.fn().mockResolvedValue({ data: { id: 7 } })
    const del = vi.fn().mockResolvedValue({ data: undefined })

    const api = { get, post, put, delete: del } as any
    const svc = createEmpresaService(api, { base: '/v1/custom/empresas' })

    await expect(svc.getEmpresas()).resolves.toEqual([{ id: 1 }])
    await expect(svc.createEmpresa({ nombre: 'Nueva' })).resolves.toEqual({ id: 5 })
    await expect(svc.updateEmpresa('2', { nombre: 'Editada' })).resolves.toEqual({ id: 7 })
    await expect(svc.deleteEmpresa('3')).resolves.toBeUndefined()

    expect(post).toHaveBeenNthCalledWith(1, '/v1/custom/empresas', { nombre: 'Nueva' })
    expect(put).toHaveBeenCalledWith('/v1/custom/empresas/2', { nombre: 'Editada' })
    expect(del).toHaveBeenCalledWith('/v1/custom/empresas/3')
  })

  it('defaults to /v1/admin/empresas when no base is provided', async () => {
    const api = {
      get: vi.fn().mockResolvedValue({ data: [] }),
      post: vi.fn().mockResolvedValue({ data: { id: 9 } }),
      put: vi.fn().mockResolvedValue({ data: { id: 10 } }),
      delete: vi.fn().mockResolvedValue({ data: undefined }),
    }

    const svc = createEmpresaService(api as any, { base: '' as any })

    await svc.createEmpresa({ nombre: 'Default' })
    await svc.updateEmpresa(1, { nombre: 'Default edit' })
    await svc.deleteEmpresa(1)

    expect(api.post).toHaveBeenCalledWith('/v1/admin/empresas', { nombre: 'Default' })
    expect(api.put).toHaveBeenCalledWith('/v1/admin/empresas/1', { nombre: 'Default edit' })
    expect(api.delete).toHaveBeenCalledWith('/v1/admin/empresas/1')
  })
})

