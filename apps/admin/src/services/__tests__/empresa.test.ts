import { describe, expect, it, afterEach } from 'vitest'
import { ADMIN_EMPRESAS } from '@shared/endpoints'

import { loadServiceModule, restoreModules } from './helpers'

describe('admin empresa service routes', () => {
  afterEach(() => {
    restoreModules()
  })

  it('fetches the empresas collection from the shared endpoint', async () => {
    const {
      module: { getEmpresas },
      api,
    } = await loadServiceModule<typeof import('../empresa')>('../empresa')

    await getEmpresas()

    expect(api.get).toHaveBeenCalledWith(ADMIN_EMPRESAS.base)
  })

  it('targets the empresa detail route when requesting a single empresa', async () => {
    const {
      module: { getEmpresa },
      api,
    } = await loadServiceModule<typeof import('../empresa')>('../empresa')

    await getEmpresa(42)

    expect(api.get).toHaveBeenCalledWith(ADMIN_EMPRESAS.byId(42))
  })

  it('posts full empresa payloads to the dedicated create endpoint', async () => {
    const {
      module: { createEmpresaFull },
      api,
    } = await loadServiceModule<typeof import('../empresa')>('../empresa')

    const payload = { razonSocial: 'Gestión QCloud' }

    await createEmpresaFull(payload)

    expect(api.post).toHaveBeenCalledWith(ADMIN_EMPRESAS.createFull, payload)
  })

  it('updates empresas via the shared domain service using the base route', async () => {
    const {
      module: { updateEmpresa },
      api,
    } = await loadServiceModule<typeof import('../empresa')>('../empresa')

    const payload = { nombre: 'Nuevo nombre' }

    await updateEmpresa(7, payload)

    expect(api.put).toHaveBeenCalledWith(`${ADMIN_EMPRESAS.base}/7`, payload)
  })

  it('delegates deleteEmpresa to the shared domain route', async () => {
    const {
      module: { deleteEmpresa },
      api,
    } = await loadServiceModule<typeof import('../empresa')>('../empresa')

    await deleteEmpresa('empresa-9')

    expect(api.delete).toHaveBeenCalledWith(`${ADMIN_EMPRESAS.base}/empresa-9`)
  })
})
