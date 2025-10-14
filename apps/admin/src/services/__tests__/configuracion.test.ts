import { afterEach, describe, expect, it } from 'vitest'
import { ADMIN_CONFIG } from '@shared/endpoints'

import { loadServiceModule, restoreModules } from './helpers'

type ConfigModuleSpec = {
  name: string
  modulePath: string
  listFn: string
  getFn: string
  createFn: string
  updateFn: string
  removeFn: string
  base: string
  byId: (id: string | number) => string
}

describe('admin configuración service routes', () => {
  afterEach(() => {
    restoreModules()
  })

  const specs: ConfigModuleSpec[] = [
    {
      name: 'monedas',
      modulePath: '../configuracion/monedas',
      listFn: 'listMonedas',
      getFn: 'getMoneda',
      createFn: 'createMoneda',
      updateFn: 'updateMoneda',
      removeFn: 'removeMoneda',
      base: ADMIN_CONFIG.monedas.base,
      byId: ADMIN_CONFIG.monedas.byId,
    },
    {
      name: 'idiomas',
      modulePath: '../configuracion/idiomas',
      listFn: 'listIdiomas',
      getFn: 'getIdioma',
      createFn: 'createIdioma',
      updateFn: 'updateIdioma',
      removeFn: 'removeIdioma',
      base: ADMIN_CONFIG.idiomas.base,
      byId: ADMIN_CONFIG.idiomas.byId,
    },
    {
      name: 'sectores',
      modulePath: '../configuracion/sectores',
      listFn: 'listSectores',
      getFn: 'getSector',
      createFn: 'createSector',
      updateFn: 'updateSector',
      removeFn: 'removeSector',
      base: ADMIN_CONFIG.sectores.base,
      byId: ADMIN_CONFIG.sectores.byId,
    },
    {
      name: 'tipo-empresa',
      modulePath: '../configuracion/tipo-empresa',
      listFn: 'listTipoEmpresa',
      getFn: 'getTipoEmpresa',
      createFn: 'createTipoEmpresa',
      updateFn: 'updateTipoEmpresa',
      removeFn: 'removeTipoEmpresa',
      base: ADMIN_CONFIG.tipoEmpresa.base,
      byId: ADMIN_CONFIG.tipoEmpresa.byId,
    },
    {
      name: 'tipo-negocio',
      modulePath: '../configuracion/tipo-negocio',
      listFn: 'listTipoNegocio',
      getFn: 'getTipoNegocio',
      createFn: 'createTipoNegocio',
      updateFn: 'updateTipoNegocio',
      removeFn: 'removeTipoNegocio',
      base: ADMIN_CONFIG.tipoNegocio.base,
      byId: ADMIN_CONFIG.tipoNegocio.byId,
    },
  ]

  specs.forEach((spec) => {
    describe(spec.name, () => {
      it('reads the collection from the base endpoint', async () => {
        const { module, api } = await loadServiceModule<any>(spec.modulePath)

        await module[spec.listFn]()

        expect(api.get).toHaveBeenCalledWith(spec.base)
      })

      it('reads a specific record using the byId endpoint', async () => {
        const { module, api } = await loadServiceModule<any>(spec.modulePath)

        await module[spec.getFn]('id-1')

        expect(api.get).toHaveBeenCalledWith(spec.byId('id-1'))
      })

      it('creates records posting to the base endpoint', async () => {
        const { module, api } = await loadServiceModule<any>(spec.modulePath)
        const payload = { nombre: 'Nuevo' }

        await module[spec.createFn](payload)

        expect(api.post).toHaveBeenCalledWith(spec.base, payload)
      })

      it('updates records putting to the byId endpoint', async () => {
        const { module, api } = await loadServiceModule<any>(spec.modulePath)
        const payload = { nombre: 'Actualizado' }

        await module[spec.updateFn]('id-9', payload)

        expect(api.put).toHaveBeenCalledWith(spec.byId('id-9'), payload)
      })

      it('removes records hitting the byId endpoint', async () => {
        const { module, api } = await loadServiceModule<any>(spec.modulePath)

        await module[spec.removeFn]('id-4')

        expect(api.delete).toHaveBeenCalledWith(spec.byId('id-4'))
      })
    })
  })

  describe('horarios extras', () => {
    it('lists horarios and días de la semana from their dedicated endpoints', async () => {
      const { module, api } = await loadServiceModule<typeof import('../configuracion/horarios')>(
        '../configuracion/horarios',
      )

      await module.listHorarios()
      await module.listDiasSemana()

      expect(api.get).toHaveBeenNthCalledWith(1, ADMIN_CONFIG.horarioAtencion.base)
      expect(api.get).toHaveBeenNthCalledWith(2, ADMIN_CONFIG.diasSemana.base)
    })

    it('manages horarios using the RESTful endpoints', async () => {
      const { module, api } = await loadServiceModule<typeof import('../configuracion/horarios')>(
        '../configuracion/horarios',
      )

      const payload = { dia_id: 1, inicio: '08:00', fin: '17:00' }

      await module.getHorario(3)
      await module.createHorario(payload)
      await module.updateHorario(3, payload)
      await module.removeHorario(3)

      expect(api.get).toHaveBeenCalledWith(ADMIN_CONFIG.horarioAtencion.byId(3))
      expect(api.post).toHaveBeenCalledWith(ADMIN_CONFIG.horarioAtencion.base, payload)
      expect(api.put).toHaveBeenCalledWith(ADMIN_CONFIG.horarioAtencion.byId(3), payload)
      expect(api.delete).toHaveBeenCalledWith(ADMIN_CONFIG.horarioAtencion.byId(3))
    })
  })
})
