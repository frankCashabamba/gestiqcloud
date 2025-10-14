import { afterEach, describe, expect, it } from 'vitest'
import { ADMIN_MODULOS, ADMIN_MODULOS_EMPRESA } from '@shared/endpoints'

import { loadServiceModule, restoreModules } from './helpers'

describe('admin modulos service routes', () => {
  afterEach(() => {
    restoreModules()
  })

  it('lists módulos using the base endpoint', async () => {
    const {
      module: { listModulos },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await listModulos()

    expect(api.get).toHaveBeenCalledWith(ADMIN_MODULOS.base)
  })

  it('retrieves módulo detail via the shared endpoint', async () => {
    const {
      module: { getModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await getModulo(11)

    expect(api.get).toHaveBeenCalledWith(ADMIN_MODULOS.byId(11))
  })

  it('creates módulos with POST to the base endpoint', async () => {
    const {
      module: { createModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    const payload = { nombre: 'Inventario' }
    await createModulo(payload)

    expect(api.post).toHaveBeenCalledWith(ADMIN_MODULOS.base, payload)
  })

  it('updates módulos with PUT to the id endpoint', async () => {
    const {
      module: { updateModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    const payload = { nombre: 'POS' }
    await updateModulo('abc', payload)

    expect(api.put).toHaveBeenCalledWith(ADMIN_MODULOS.byId('abc'), payload)
  })

  it('removes módulos using DELETE on the id endpoint', async () => {
    const {
      module: { removeModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await removeModulo('99')

    expect(api.delete).toHaveBeenCalledWith(ADMIN_MODULOS.byId('99'))
  })

  it('toggles módulos hitting activar or desactivar endpoints', async () => {
    const {
      module: { toggleModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await toggleModulo(5, true)
    await toggleModulo(5, false)

    expect(api.post).toHaveBeenNthCalledWith(1, ADMIN_MODULOS.activar(5))
    expect(api.post).toHaveBeenNthCalledWith(2, ADMIN_MODULOS.desactivar(5))
  })

  it('registers módulos from the filesystem using the registrar endpoint', async () => {
    const {
      module: { registrarModulosFS },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await registrarModulosFS()

    expect(api.post).toHaveBeenCalledWith(ADMIN_MODULOS.registrar)
  })

  it('lists public módulos from the publicos endpoint', async () => {
    const {
      module: { listModulosPublicos },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await listModulosPublicos()

    expect(api.get).toHaveBeenCalledWith(ADMIN_MODULOS.publicos)
  })

  it('lists módulos por empresa from the empresa endpoint', async () => {
    const {
      module: { listEmpresaModulos },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await listEmpresaModulos(77)

    expect(api.get).toHaveBeenCalledWith(ADMIN_MODULOS_EMPRESA.base(77))
  })

  it('upserts empresa módulo relations with modulo_id merged in the payload', async () => {
    const {
      module: { upsertEmpresaModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await upsertEmpresaModulo('emp-1', 3, { activo: true })

    expect(api.post).toHaveBeenCalledWith(ADMIN_MODULOS_EMPRESA.upsert('emp-1'), {
      modulo_id: 3,
      activo: true,
    })
  })

  it('removes empresa módulo relations from the dedicated endpoint', async () => {
    const {
      module: { removeEmpresaModulo },
      api,
    } = await loadServiceModule<typeof import('../modulos')>('../modulos')

    await removeEmpresaModulo('emp-1', 'mod-9')

    expect(api.delete).toHaveBeenCalledWith(ADMIN_MODULOS_EMPRESA.remove('emp-1', 'mod-9'))
  })
})
