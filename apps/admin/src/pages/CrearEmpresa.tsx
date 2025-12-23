import React, { useEffect, useState } from 'react'
import ModuloSelector from '../modulos/ModuloSelector'
import { useCrearEmpresa } from '../hooks/useCrearEmpresa'
import type { FormularioEmpresa } from '../typesall/empresa'
import SectorPlantillaSelector, { type SectorTemplate } from '../components/SectorPlantillaSelector'
import { listPaises, type Pais } from '../services/configuracion/paises'
import { listMonedas, type Moneda } from '../services/configuracion/monedas'
import { listLocales, type Locale } from '../services/configuracion/locales'
import { listTimezones, type Timezone } from '../services/configuracion/timezones'

const INITIAL_STATE: FormularioEmpresa = {
  nombre_empresa: '',
  sector_plantilla_id: null,
  ruc: '',
  telefono: '',
  direccion: '',
  pais: '',
  country_code: '',
  provincia: '',
  ciudad: '',
  cp: '',
  sitio_web: '',
  logo: null,
  color_primario: '',
  plantilla_inicio: '',
  config_json: '',
  default_language: '',
  timezone: '',
  currency: '',
  nombre_encargado: '',
  apellido_encargado: '',
  email: '',
  username: '',
  password: '',
  modulos: [],
}

export const CrearEmpresa: React.FC = () => {
  const [formData, setFormData] = useState<FormularioEmpresa>(INITIAL_STATE)
  const [localError, setLocalError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [paises, setPaises] = useState<Pais[]>([])
  const [monedas, setMonedas] = useState<Moneda[]>([])
  const [locales, setLocales] = useState<Locale[]>([])
  const [timezones, setTimezones] = useState<Timezone[]>([])
  const { crear, loading, error, success, fieldErrors, needSecondSurname } = useCrearEmpresa()

  // Habilitar el submit solo cuando los campos mínimos estén completos
  const canSubmit = React.useMemo(() => {
    const nonEmpty = (v?: string) => (v || '').trim().length > 0
    const emailOk = /.+@.+\..+/.test((formData.email || '').trim())
    return (
      nonEmpty(formData.nombre_empresa) &&
      nonEmpty(formData.nombre_encargado) &&
      nonEmpty(formData.apellido_encargado) &&
      emailOk &&
      !!formData.sector_plantilla_id &&
      nonEmpty(formData.country_code) &&
      nonEmpty(formData.currency) &&
      nonEmpty(formData.timezone) &&
      nonEmpty(formData.default_language)
    )
  }, [
    formData.nombre_empresa,
    formData.nombre_encargado,
    formData.apellido_encargado,
    formData.email,
    formData.sector_plantilla_id,
    formData.country_code,
    formData.currency,
    formData.timezone,
    formData.default_language,
  ])

  // Autogenerar username visual (no editable) nombre.apellido
  useEffect(() => {
    const nombre = (formData.nombre_encargado || '').trim().toLowerCase()
    const apellido = (formData.apellido_encargado || '').trim().toLowerCase()
    const sugerido = nombre && apellido ? `${nombre}.${apellido}`.replace(/\s+/g, '') : ''
    setFormData((prev) => ({ ...prev, username: sugerido }))
  }, [formData.nombre_encargado, formData.apellido_encargado])

  useEffect(() => {
    let active = true
    async function loadCatalogs() {
      try {
        const [paisesData, monedasData, localesData, timezonesData] = await Promise.all([
          listPaises(),
          listMonedas(),
          listLocales(),
          listTimezones(),
        ])
        if (!active) return
        setPaises((paisesData || []).filter((p) => p.active))
        setMonedas((monedasData || []).filter((m) => m.active))
        setLocales((localesData || []).filter((l) => l.active !== false))
        setTimezones((timezonesData || []).filter((t) => t.active !== false))
      } catch (err) {
        if (!active) return
        setCatalogError('No se pudieron cargar los catálogos de configuración.')
      }
    }
    loadCatalogs()
    return () => {
      active = false
    }
  }, [])

  function onChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) {
    const { name, value, type } = e.target
    if (type === 'file') {
      setFormData({ ...formData, [name]: (e.target as HTMLInputElement).files?.[0] || null })
    } else {
      setFormData({ ...formData, [name]: value })
    }
  }

  function onCountryChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const code = e.target.value
    const selected = paises.find((p) => p.code === code)
    setFormData((prev) => ({
      ...prev,
      country_code: code,
      pais: selected?.name || '',
    }))
  }

  function onModuloChange(moduloId: string) {
    setFormData((prev) => ({
      ...prev,
      modulos: prev.modulos.includes(moduloId)
        ? prev.modulos.filter((id) => id !== moduloId)
        : [...prev.modulos, moduloId],
    }))
  }

  function validateRucByCountry(country: string, ruc: string): string | null {
    const raw = (country || '').trim()
    const code = raw.toUpperCase()
    const c = raw.toLowerCase()
    const v = (ruc || '').trim()
    if (!v) return null
    if (code === 'PE' || /(peru|peru)/.test(c)) {
      if (!/^\d{11}$/.test(v)) return 'RUC (Peru) debe tener 11 digitos.'
      return null
    }
    if (code === 'EC' || /ecuador/.test(c)) {
      if (!/^\d{13}$/.test(v)) return 'RUC (Ecuador) debe tener 13 digitos.'
      return null
    }
    if (code === 'AR' || /argentina/.test(c)) {
      if (!/^\d{11}$/.test(v)) return 'CUIT/CUIL (Argentina) debe tener 11 digitos.'
      return null
    }
    if (code === 'CL' || /chile/.test(c)) {
      if (!/^[0-9]{7,8}-[0-9kK]$/.test(v) && !/^[0-9]{7,8}[0-9kK]$/.test(v)) {
        return 'RUT (Chile) debe ser 8 digitos + digito verificador (ej: 12345678-9)'
      }
      return null
    }
    if (code === 'ES' || /(espana|spain)/.test(c)) {
      if (!/^([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])$/.test(v.toUpperCase())) {
        return 'CIF/NIF (Espana) con formato basico invalido.'
      }
      return null
    }
    return null
  }

  function validate(): string | null {
    const isEmail = /.+@.+\..+/
    const isPhone = (v: string) => v.length === 0 || /^[0-9+()\-\s]{6,20}$/.test(v)
    const isUrl = (v: string) => {
      if (!v) return true
      try {
        // Permite sin protocolo
        // eslint-disable-next-line no-new
        new URL(v.startsWith('http') ? v : `http://${v}`)
        return true
      } catch {
        return false
      }
    }
    if (!formData.nombre_empresa.trim()) return 'El nombre de la empresa es obligatorio.'
    if (!formData.nombre_encargado.trim()) return 'El nombre del encargado es obligatorio.'
    if (!formData.apellido_encargado.trim()) return 'El apellido del encargado es obligatorio.'
    if (!formData.email.trim()) return 'El correo es obligatorio.'
    if (!isEmail.test(formData.email.trim())) return 'El correo no tiene un formato válido.'
    if (!isPhone(formData.telefono || '')) return 'Teléfono inválido.'
    if (!formData.sector_plantilla_id) return 'Selecciona un sector para aplicar la configuracion base.'
    if (!formData.country_code) return 'Selecciona un pais.'
    if (!formData.default_language) return 'Selecciona un idioma/locale.'
    if (!formData.timezone) return 'Selecciona una zona horaria.'
    if (!formData.currency) return 'Selecciona una moneda.'
    const rucErr = validateRucByCountry(formData.country_code || formData.pais, formData.ruc)
    if (rucErr) return rucErr
    if (!isUrl(formData.sitio_web || '')) return 'El sitio web no es una URL válida.'
    return null
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLocalError(null)
    const v = validate()
    if (v) return setLocalError(v)
    const res = await crear(formData)
    if (res) setFormData(INITIAL_STATE)
  }

  const err = (k: string) => (fieldErrors as any)?.[k]

  const handleSectorChange = (sectorId: number | null) => {
    setFormData((prev) => ({ ...prev, sector_plantilla_id: sectorId }))
  }

  const handleTemplateMeta = (template: SectorTemplate | null) => {
    if (!template) return
    setFormData((prev) => ({
      ...prev,
      color_primario: template.branding.color_primario || prev.color_primario,
      plantilla_inicio: template.branding.plantilla_inicio || prev.plantilla_inicio,
    }))
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="bg-white rounded-3xl shadow-sm border border-slate-200">
        <header className="px-6 py-5 border-b border-slate-200 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Registrar nueva empresa</h1>
            <p className="text-slate-500 text-sm mt-1">
              Completa los datos para crear una empresa, su usuario principal y módulos activos.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input id="import-excel" type="file" accept=".xlsx,.xls" className="hidden" disabled title="Próximamente" />
            <label
              htmlFor="import-excel"
              className="inline-flex items-center rounded-lg px-3 py-2 text-sm font-semibold border border-slate-300 text-slate-600 bg-white opacity-60 cursor-not-allowed"
              title="Importar empresas desde Excel (próximamente)"
            >
              Importar Excel
            </label>
          </div>
        </header>

        <form onSubmit={onSubmit} className="px-6 py-6 space-y-10">
          {(localError || error || catalogError) && (
            <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {localError || error || catalogError}
            </div>
          )}

          {/* Datos de la empresa */}
          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Datos de la empresa</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Nombre de la empresa *</label>
                <input name="nombre_empresa" value={formData.nombre_empresa} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">RUC</label>
                <input name="ruc" value={formData.ruc} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Teléfono</label>
                <input name="telefono" value={formData.telefono} onChange={onChange} placeholder="+34 600 000 000" className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-600">Dirección</label>
                <input name="direccion" value={formData.direccion} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Pais *</label>
                <select
                  name="country_code"
                  value={formData.country_code || ''}
                  onChange={onCountryChange}
                  className="border border-slate-300 rounded-lg px-4 py-2 text-sm bg-white"
                >
                  <option value="">Selecciona un pais</option>
                  {paises.map((p) => (
                    <option key={p.code} value={p.code}>
                      {p.name} ({p.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Provincia</label>
                <input name="provincia" value={formData.provincia} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Ciudad</label>
                <input name="ciudad" value={formData.ciudad} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Código postal</label>
                <input name="cp" value={formData.cp} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Idioma / Locale *</label>
                <select
                  name="default_language"
                  value={formData.default_language || ''}
                  onChange={onChange}
                  className="border border-slate-300 rounded-lg px-4 py-2 text-sm bg-white"
                >
                  <option value="">Selecciona un idioma</option>
                  {locales.map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.name} ({l.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Zona horaria *</label>
                <select
                  name="timezone"
                  value={formData.timezone || ''}
                  onChange={onChange}
                  className="border border-slate-300 rounded-lg px-4 py-2 text-sm bg-white"
                >
                  <option value="">Selecciona una zona horaria</option>
                  {timezones.map((tz) => (
                    <option key={tz.name} value={tz.name}>
                      {tz.display_name || tz.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Moneda *</label>
                <select
                  name="currency"
                  value={formData.currency || ''}
                  onChange={onChange}
                  className="border border-slate-300 rounded-lg px-4 py-2 text-sm bg-white"
                >
                  <option value="">Selecciona una moneda</option>
                  {monedas.map((m) => (
                    <option key={m.code} value={m.code}>
                      {m.name} ({m.code})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-600">Sitio web</label>
                <input name="sitio_web" value={formData.sitio_web} onChange={onChange} placeholder="https://" className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Color primario</label>
                <input name="color_primario" type="color" value={formData.color_primario} onChange={onChange} className="h-10 w-20 border border-slate-300 rounded" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Logo</label>
                <input name="logo" type="file" onChange={onChange} className="text-sm" />
              </div>
              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-600">Config JSON (opcional)</label>
                <textarea name="config_json" value={formData.config_json} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm min-h-[90px]" />
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Sector / Plantilla base *</h2>
            <SectorPlantillaSelector
              value={formData.sector_plantilla_id ?? null}
              onChange={handleSectorChange}
              onTemplateSelected={handleTemplateMeta}
            />
          </section>

          {/* Módulos */}
          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Módulos a contratar</h2>
            <ModuloSelector selected={formData.modulos} onChange={onModuloChange} />
          </section>

          {/* Usuario administrador */}
          <section>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Usuario administrador</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Nombre *</label>
                <input name="nombre_encargado" value={formData.nombre_encargado} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Apellido *</label>
                <input name="apellido_encargado" value={formData.apellido_encargado} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Correo *</label>
                <input name="email" type="email" value={formData.email} onChange={onChange} aria-invalid={!!err('email')} className={`border rounded-lg px-4 py-2 text-sm ${err('email') ? 'border-rose-400' : 'border-slate-300'}`} />
                {err('email') && <span className="text-xs text-rose-600">{err('email')}</span>}
              </div>

              {needSecondSurname && (
                <div className="flex flex-col gap-1">
                  <label className="text-xs font-semibold text-slate-600">Segundo apellido (para sugerir username único)</label>
                  <input name="segundo_apellido_encargado" value={(formData as any).segundo_apellido_encargado || ''} onChange={onChange} className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
                </div>
              )}

              <div className="flex flex-col gap-1 md:col-span-2">
                <label className="text-xs font-semibold text-slate-600">Usuario generado</label>
                <div className={`bg-slate-50 border rounded-lg px-3 py-2 text-sm ${err('username') ? 'border-rose-400' : 'border-slate-300'}`} title="Se genera automáticamente como nombre.apellido">
                  <span className="font-mono text-slate-700 select-all">{formData.username || '—'}</span>
                </div>
                {err('username') && <span className="text-xs text-rose-600">{err('username')}</span>}
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-xs font-semibold text-slate-600">Contraseña (opcional)</label>
                <input name="password" type="password" value={formData.password} onChange={onChange} placeholder="Se enviará email si no la informas" className="border border-slate-300 rounded-lg px-4 py-2 text-sm" />
              </div>
            </div>
          </section>

          <div className="sticky bottom-0 left-0 right-0 bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/60 border-t border-slate-200 px-4 py-4 mt-6 flex items-center justify-between gap-4">
            <button
              type="submit"
              disabled={loading || !canSubmit}
              className={`inline-flex items-center justify-center rounded-xl px-6 py-3 font-semibold text-white shadow-sm transition ${
                loading || !canSubmit ? 'bg-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {loading && (
                <svg className="-ml-1 mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
                </svg>
              )}
              {loading ? 'Saving…' : 'Crear empresa y usuario'}
            </button>

            {!canSubmit && (
              <div className="text-xs text-slate-600">
                Completa: empresa, admin, correo valido, pais, idioma, zona horaria, moneda y sector base.
              </div>
            )}

            <a href="/admin/empresas" className="text-sm font-medium text-indigo-600 hover:underline">Volver al listado de empresas</a>
          </div>

          {success && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div>
          )}
        </form>
      </div>
    </div>
  )
}
