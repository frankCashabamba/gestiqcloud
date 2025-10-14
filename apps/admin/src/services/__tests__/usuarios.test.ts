import { afterEach, describe, expect, it, vi } from 'vitest'
import { ADMIN_USUARIOS } from '@shared/endpoints'

import { loadServiceModule, restoreModules } from './helpers'

describe('admin usuarios service routes', () => {
  afterEach(() => {
    restoreModules()
  })

  it('lists usuarios using the base route', async () => {
    const {
      module: { listUsuarios },
      api,
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios')

    await listUsuarios()

    expect(api.get).toHaveBeenCalledWith(ADMIN_USUARIOS.base)
  })

  it('posts to reenviar-reset endpoint', async () => {
    const {
      module: { reenviarReset },
      api,
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios')

    await reenviarReset(10)

    expect(api.post).toHaveBeenCalledWith(ADMIN_USUARIOS.reenviarReset(10))
  })

  it('toggles activation and company actions using dedicated endpoints', async () => {
    const {
      module: { activarUsuario, desactivarUsuario, desactivarEmpresa },
      api,
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios')

    await activarUsuario('user-1')
    await desactivarUsuario('user-2')
    await desactivarEmpresa('user-3')

    expect(api.post).toHaveBeenNthCalledWith(1, ADMIN_USUARIOS.activar('user-1'))
    expect(api.post).toHaveBeenNthCalledWith(2, ADMIN_USUARIOS.desactivar('user-2'))
    expect(api.post).toHaveBeenNthCalledWith(3, ADMIN_USUARIOS.desactivarEmpresa('user-3'))
  })

  it('assigns a new admin posting the payload to the shared endpoint', async () => {
    const {
      module: { asignarNuevoAdmin },
      api,
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios')

    const payload = { email: 'nuevo@gestiqcloud.com' }
    await asignarNuevoAdmin(9, payload)

    expect(api.post).toHaveBeenCalledWith(ADMIN_USUARIOS.asignarNuevoAdmin(9), payload)
  })

  it('sets passwords posting to the set-password endpoint', async () => {
    const {
      module: { setPasswordDirect },
      api,
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios')

    await setPasswordDirect('u-5', 's3cr3t')

    expect(api.post).toHaveBeenCalledWith(ADMIN_USUARIOS.setPassword('u-5'), { password: 's3cr3t' })
  })

  it('returns list payloads and resolves usuario mutations', async () => {
    const listResult = [{ id: 1, nombre: 'Admin' }]
    const getMock = vi.fn().mockResolvedValue({ data: listResult })
    const postMock = vi
      .fn()
      .mockResolvedValueOnce({ data: undefined })
      .mockResolvedValueOnce({ data: undefined })
      .mockResolvedValueOnce({ data: undefined })
      .mockResolvedValueOnce({ data: undefined })
      .mockResolvedValueOnce({ data: { reassigned: true } })
      .mockResolvedValueOnce({ data: undefined })

    const {
      module: {
        listUsuarios,
        reenviarReset,
        activarUsuario,
        desactivarUsuario,
        desactivarEmpresa,
        asignarNuevoAdmin,
        setPasswordDirect,
      },
    } = await loadServiceModule<typeof import('../usuarios')>('../usuarios', { getMock, postMock })

    await expect(listUsuarios()).resolves.toEqual(listResult)
    await expect(reenviarReset(10)).resolves.toBeUndefined()
    await expect(activarUsuario(11)).resolves.toBeUndefined()
    await expect(desactivarUsuario(12)).resolves.toBeUndefined()
    await expect(desactivarEmpresa(13)).resolves.toBeUndefined()
    await expect(asignarNuevoAdmin(14, { email: 'nuevo@example.com' })).resolves.toBeUndefined()
    await expect(setPasswordDirect(15, 'pw')).resolves.toBeUndefined()
  })
})
