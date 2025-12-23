import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createSector,
  getSector,
  updateSector,
  DEFAULT_TEMPLATE_CONFIG,
  type SectorPayload,
  type SectorTemplateConfig,
  type BrandingConfig,
} from '../../../services/configuracion/sectores'
import { listTipoEmpresa, type TipoEmpresa } from '../../../services/configuracion/tipo-empresa'
import { listTipoNegocio, type TipoNegocio } from '../../../services/configuracion/tipo-negocio'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = SectorPayload
type SelectOption = { id: string; name: string }

const TEMPLATE_OPTIONS = [
  'default',
  'panaderia',
  'panaderia_pro',
  'retail',
  'retail_pro',
  'taller',
  'taller_pro',
  'todoa100',
]

const ensureTemplateConfig = (cfg?: Partial<SectorTemplateConfig> | null): SectorTemplateConfig => ({
  ...DEFAULT_TEMPLATE_CONFIG,
  ...(cfg || {}),
  branding: {
    ...DEFAULT_TEMPLATE_CONFIG.branding,
    ...(cfg?.branding || {}),
  },
  defaults: {
    ...DEFAULT_TEMPLATE_CONFIG.defaults,
    ...(cfg?.defaults || {}),
  },
  pos: { ...DEFAULT_TEMPLATE_CONFIG.pos, ...(cfg?.pos || {}) },
  inventory: { ...DEFAULT_TEMPLATE_CONFIG.inventory, ...(cfg?.inventory || {}) },
})

export default function SectorForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const [form, setForm] = useState<FormT>({
    name: '',
    code: '',
    description: '',
    template_config: ensureTemplateConfig(),
    active: true,
  })
  const [rawConfig, setRawConfig] = useState(() => JSON.stringify(ensureTemplateConfig(), null, 2))
  const [empresas, setEmpresas] = useState<SelectOption[]>([])
  const [negocios, setNegocios] = useState<SelectOption[]>([])
  const [loadingCatalogs, setLoadingCatalogs] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        setLoadingCatalogs(true)
        const [es, ns] = await Promise.all([listTipoEmpresa(), listTipoNegocio()])
        setEmpresas(es)
        setNegocios(ns)
      } catch {
        // Ignore; selects will just be empty
      } finally {
        setLoadingCatalogs(false)
      }
    })()
  }, [])

  useEffect(() => {
    // Pre-fill defaults with first option if none selected
    setForm((prev) => {
      const defaults = prev.template_config.defaults || {}
      const nextDefaults = { ...defaults }
      let changed = false
      if (!defaults.business_type_id && empresas[0]?.id) {
        nextDefaults.business_type_id = empresas[0].id
        changed = true
      }
      if (!defaults.business_category_id && negocios[0]?.id) {
        nextDefaults.business_category_id = negocios[0].id
        changed = true
      }
      if (!changed) return prev
      return {
        ...prev,
        template_config: ensureTemplateConfig({
          ...prev.template_config,
          defaults: nextDefaults,
        }),
      }
    })
  }, [empresas, negocios])

  useEffect(() => {
    if (!id) {
      setForm({
        name: '',
        code: '',
        description: '',
        template_config: ensureTemplateConfig(),
        active: true,
      })
      return
    }
    getSector(id)
      .then((m) => {
        const cfg = ensureTemplateConfig(m.template_config)
        setForm({
          name: m.name || '',
          code: m.code || '',
          description: m.description || '',
          template_config: {
            ...cfg,
            defaults: {
              ...cfg.defaults,
              business_type_id: cfg.defaults?.business_type_id || '',
              business_category_id: cfg.defaults?.business_category_id || '',
            },
          },
          active: m.active ?? true,
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
      if (!form.name?.trim()) throw new Error('Name is required')
      let parsedConfig: SectorTemplateConfig
      try {
        parsedConfig = ensureTemplateConfig(JSON.parse(rawConfig))
      } catch {
        throw new Error('Config JSON inválido')
      }

      // Ensure defaults carry business type/category selections
      parsedConfig.defaults = {
        ...parsedConfig.defaults,
        business_type_id: form.template_config.defaults?.business_type_id || '',
        business_category_id: form.template_config.defaults?.business_category_id || '',
      }

      const payload: FormT = {
        name: form.name.trim(),
        code: form.code?.trim() || null,
        description: form.description?.trim() || null,
        template_config: parsedConfig,
        active: form.active ?? true,
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
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block mb-1">Código (opcional)</label>
            <input
              value={form.code || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, code: e.target.value }))}
              className="border px-2 py-1 w-full rounded"
              placeholder="p.ej. bakery"
            />
          </div>
          <div>
            <label className="block mb-1">Descripción (opcional)</label>
            <input
              value={form.description || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              className="border px-2 py-1 w-full rounded"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block mb-1">Tipo de Empresa</label>
            <select
              value={form.template_config.defaults?.business_type_id || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  template_config: ensureTemplateConfig({
                    ...prev.template_config,
                    defaults: {
                      ...prev.template_config.defaults,
                      business_type_id: e.target.value,
                    },
                  }),
                }))
              }
              className="border px-2 py-1 w-full rounded"
            >
              <option value="">Sin seleccionar</option>
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
              value={form.template_config.defaults?.business_category_id || ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  template_config: ensureTemplateConfig({
                    ...prev.template_config,
                    defaults: {
                      ...prev.template_config.defaults,
                      business_category_id: e.target.value,
                    },
                  }),
                }))
              }
              className="border px-2 py-1 w-full rounded"
            >
              <option value="">Sin seleccionar</option>
              {negocios.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <label className="inline-flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!!form.active}
            onChange={(e) => setForm((prev) => ({ ...prev, active: e.target.checked }))}
            className="h-4 w-4"
          />
          Activo
        </label>

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
              Dashboard template
              <select
                value={branding.dashboard_template}
                onChange={(e) => updateBranding({ dashboard_template: e.target.value })}
                className="mt-1 border px-2 py-1 w-full rounded"
              >
                {TEMPLATE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
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
