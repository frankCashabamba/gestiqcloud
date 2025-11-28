import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createSector,
  getSector,
  updateSector,
  listTipoEmpresa,
  listTipoNegocio,
  DEFAULT_TEMPLATE_CONFIG,
  type SectorPayload,
  type SectorTemplateConfig,
  type BrandingConfig,
} from '../../../services/configuracion/sectores'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = SectorPayload

const ensureTemplateConfig = (cfg?: Partial<SectorTemplateConfig> | null): SectorTemplateConfig => ({
  ...DEFAULT_TEMPLATE_CONFIG,
  ...(cfg || {}),
  branding: {
    ...DEFAULT_TEMPLATE_CONFIG.branding,
    ...(cfg?.branding || {}),
  },
  defaults: { ...DEFAULT_TEMPLATE_CONFIG.defaults, ...(cfg?.defaults || {}) },
  pos: { ...DEFAULT_TEMPLATE_CONFIG.pos, ...(cfg?.pos || {}) },
  inventory: { ...DEFAULT_TEMPLATE_CONFIG.inventory, ...(cfg?.inventory || {}) },
})

export default function SectorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const [form, setForm] = useState<FormT>({
    sector_name: '',
    business_type_id: 0,
    business_category_id: 0,
    template_config: ensureTemplateConfig(),
  })
  const [rawConfig, setRawConfig] = useState(() => JSON.stringify(ensureTemplateConfig(), null, 2))
  const [empresas, setEmpresas] = useState<Array<{ id: number; name: string }>>([])
  const [negocios, setNegocios] = useState<Array<{ id: number; name: string }>>([])

  useEffect(() => {
    ;(async () => {
      const [es, ns] = await Promise.all([listTipoEmpresa(), listTipoNegocio()])
      setEmpresas(es)
      setNegocios(ns)
      setForm((prev) => ({
        ...prev,
        business_type_id: prev.business_type_id || es[0]?.id || 0,
        business_category_id: prev.business_category_id || ns[0]?.id || 0,
      }))
    })()
  }, [])

  useEffect(() => {
    if (!id) {
      setForm((prev) => ({
        ...prev,
        sector_name: '',
        template_config: ensureTemplateConfig(),
      }))
      return
    }
    getSector(id)
      .then((m) => {
        setForm({
          sector_name: m.sector_name,
          business_type_id: m.business_type_id ?? 0,
          business_category_id: m.business_category_id ?? 0,
          template_config: ensureTemplateConfig(m.template_config),
        })
      })
      .catch(() => {})
  }, [id])

  useEffect(() => {
    setRawConfig(JSON.stringify(form.template_config, null, 2))
  }, [form.template_config])

  const updateBranding = (patch: Partial<BrandingConfig>) => {
    setForm((prev) => ({
      ...prev,
      template_config: ensureTemplateConfig({
        ...prev.template_config,
        branding: { ...prev.template_config?.branding, ...patch },
      }),
    }))
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.sector_name?.trim()) throw new Error('Name is required')
      if (!form.business_type_id || !form.business_category_id)
        throw new Error('Seleccione tipo de empresa y de negocio')
      let parsedConfig: SectorTemplateConfig
      try {
        parsedConfig = ensureTemplateConfig(JSON.parse(rawConfig))
      } catch {
        throw new Error('Config JSON inválido')
      }
      const payload: FormT = {
        sector_name: form.sector_name.trim(),
        business_type_id: form.business_type_id,
        business_category_id: form.business_category_id,
        template_config: parsedConfig,
      }
      if (id) await updateSector(id, payload)
      else await createSector(payload)
      success('Sector guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const branding = form.template_config?.branding || DEFAULT_TEMPLATE_CONFIG.branding

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar Sector' : 'Nuevo Sector'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 720 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input
            value={form.sector_name}
            onChange={(e) => setForm((prev) => ({ ...prev, sector_name: e.target.value }))}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block mb-1">Tipo de Empresa</label>
            <select
              value={form.business_type_id ?? 0}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, business_type_id: Number(e.target.value) }))
              }
              className="border px-2 py-1 w-full rounded"
            >
              {empresas.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block mb-1">Tipo de Negocio</label>
            <select
              value={form.business_category_id ?? 0}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, business_category_id: Number(e.target.value) }))
              }
              className="border px-2 py-1 w-full rounded"
            >
              {negocios.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="border rounded px-3 py-3 bg-slate-50">
          <h4 className="font-semibold mb-2">Branding</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="block text-sm">
              Color primario
              <input
                type="color"
                value={branding.color_primario}
                onChange={(e) => updateBranding({ color_primario: e.target.value })}
                className="mt-2 h-10 w-20 border border-slate-300 rounded"
              />
            </label>
            <label className="block text-sm">
              Plantilla inicial
              <input
                value={branding.plantilla_inicio}
                onChange={(e) => updateBranding({ plantilla_inicio: e.target.value })}
                className="mt-1 border px-2 py-1 w-full rounded"
              />
            </label>
            <label className="block text-sm">
              Dashboard template
              <input
                value={branding.dashboard_template}
                onChange={(e) => updateBranding({ dashboard_template: e.target.value })}
                className="mt-1 border px-2 py-1 w-full rounded"
              />
            </label>
          </div>
        </div>

        <div>
          <label className="block mb-1">Config JSON (opcional)</label>
          <textarea
            value={rawConfig}
            onChange={(e) => {
              const value = e.target.value
              setRawConfig(value)
              try {
                const parsed = JSON.parse(value || '{}')
                setForm((prev) => ({ ...prev, template_config: ensureTemplateConfig(parsed) }))
              } catch {
                // ignorar hasta que sea válido
              }
            }}
            rows={8}
            className="w-full border px-3 py-2 font-mono rounded"
          />
          <p className="text-xs text-slate-500 mt-1">
            Puedes editar la configuración avanzada; debe ser un JSON válido.
          </p>
        </div>

        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">
            Guardar
          </button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  )
}
