import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import SectorPlantillaSelector, { type SectorTemplate } from '../components/SectorPlantillaSelector'
import { useCrearEmpresa } from '../hooks/useCrearEmpresa'
import ModuloSelector from '../modulos/ModuloSelector'
import { buildModuloLookup, normalizeModuloLookupKey, useModulos } from '../modulos/useModulos'
import { getAdminBillingPlans, type CompanyPlan } from '../services/company-settings'
import { listLocales, type Locale } from '../services/configuracion/locales'
import { listMonedas, type Moneda } from '../services/configuracion/monedas'
import { listPaises, type Pais } from '../services/configuracion/paises'
import { listTimezones, type Timezone } from '../services/configuracion/timezones'

import type { BillingCycle, FormularioEmpresa } from '../typesall/empresa'

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
  color_secundario: '',
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

type LastCreatedCompany = {
  id: string
  name: string
  planName?: string | null
  subscriptionPending?: boolean
}

const COUNTRY_DEFAULTS: Record<string, { locale: string[]; timezone: string[]; currency?: string }> = {
  ES: { locale: ['es-es', 'es'], timezone: ['europe/madrid'], currency: 'EUR' },
  EC: { locale: ['es-ec', 'es'], timezone: ['america/guayaquil'], currency: 'USD' },
  MX: { locale: ['es-mx', 'es'], timezone: ['america/mexico_city', 'america/mexico'], currency: 'MXN' },
  PE: { locale: ['es-pe', 'es'], timezone: ['america/lima'], currency: 'PEN' },
  CL: { locale: ['es-cl', 'es'], timezone: ['america/santiago'], currency: 'CLP' },
  AR: { locale: ['es-ar', 'es'], timezone: ['america/argentina/buenos_aires', 'america/buenos_aires'], currency: 'ARS' },
  US: { locale: ['en-us', 'en'], timezone: ['america/new_york', 'utc'], currency: 'USD' },
}

function formatMoney(value?: number | null) {
  if (value == null) return 'Consultar'
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value % 1 === 0 ? 0 : 2,
  }).format(value)
}

function planLabel(plan: CompanyPlan | null) {
  return plan ? plan.display_name || plan.name : 'Sin plan seleccionado'
}

function findLocaleCode(locales: Locale[], patterns: string[]) {
  const items = locales.map((item) => ({ ...item, norm: item.code.toLowerCase() }))
  for (const pattern of patterns) {
    const match = items.find((item) => item.norm === pattern || item.norm.includes(pattern))
    if (match) return match.code
  }
  return ''
}

function findTimezoneName(timezones: Timezone[], patterns: string[]) {
  const items = timezones.map((item) => ({ ...item, norm: item.name.toLowerCase() }))
  for (const pattern of patterns) {
    const match = items.find((item) => item.norm === pattern || item.norm.includes(pattern))
    if (match) return match.name
  }
  return ''
}

export const CrearEmpresa: React.FC = () => {
  const [formData, setFormData] = useState<FormularioEmpresa>(INITIAL_STATE)
  const [localError, setLocalError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [paises, setPaises] = useState<Pais[]>([])
  const [monedas, setMonedas] = useState<Moneda[]>([])
  const [locales, setLocales] = useState<Locale[]>([])
  const [timezones, setTimezones] = useState<Timezone[]>([])
  const [billingPlans, setBillingPlans] = useState<CompanyPlan[]>([])
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('monthly')
  const [selectedPlanId, setSelectedPlanId] = useState('')
  const [plansLoading, setPlansLoading] = useState(false)
  const [lastCreatedCompany, setLastCreatedCompany] = useState<LastCreatedCompany | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showModules, setShowModules] = useState(false)
  const errorAlertRef = useRef<HTMLDivElement | null>(null)
  const { modulos: availableModules } = useModulos()
  const { crear, loading, error, success, fieldErrors, needSecondSurname } = useCrearEmpresa()

  const selectedPlan = useMemo(
    () => billingPlans.find((plan) => plan.id === selectedPlanId) || null,
    [billingPlans, selectedPlanId],
  )
  const moduloLookup = useMemo(() => buildModuloLookup(availableModules), [availableModules])

  const canSubmit = useMemo(() => {
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
      nonEmpty(formData.default_language) &&
      formData.modulos.length > 0
    )
  }, [formData])

  useEffect(() => {
    const nombre = (formData.nombre_encargado || '').trim().toLowerCase()
    const apellido = (formData.apellido_encargado || '').trim().toLowerCase()
    const sugerido = nombre && apellido ? `${nombre}.${apellido}`.replace(/\s+/g, '') : ''
    setFormData((prev) => ({ ...prev, username: sugerido }))
  }, [formData.nombre_encargado, formData.apellido_encargado])

  useEffect(() => {
    let active = true
    async function loadCatalogs() {
      setPlansLoading(true)
      try {
        const [paisesData, monedasData, localesData, timezonesData, plansData] = await Promise.all([
          listPaises(),
          listMonedas(),
          listLocales(),
          listTimezones(),
          getAdminBillingPlans().catch(() => []),
        ])
        if (!active) return
        setPaises((paisesData || []).filter((p) => p.active))
        setMonedas((monedasData || []).filter((m) => m.active))
        setLocales((localesData || []).filter((l) => l.active !== false))
        setTimezones((timezonesData || []).filter((t) => t.active !== false))
        setBillingPlans(plansData || [])
      } catch {
        if (active) setCatalogError('Could not load configuration catalogs.')
      } finally {
        if (active) setPlansLoading(false)
      }
    }
    loadCatalogs()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!localError && !error && !catalogError) return
    const id = window.setTimeout(() => {
      errorAlertRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 0)
    return () => window.clearTimeout(id)
  }, [localError, error, catalogError])

  useEffect(() => {
    const defaults = COUNTRY_DEFAULTS[formData.country_code || '']
    if (!defaults) return

    setFormData((prev) => {
      const next = { ...prev }
      let changed = false

      if (!prev.default_language) {
        const localeCode = findLocaleCode(locales, defaults.locale)
        if (localeCode) {
          next.default_language = localeCode
          changed = true
        }
      }
      if (!prev.timezone) {
        const timezoneName = findTimezoneName(timezones, defaults.timezone)
        if (timezoneName) {
          next.timezone = timezoneName
          changed = true
        }
      }
      if (!prev.currency && defaults.currency && monedas.some((m) => m.code === defaults.currency)) {
        next.currency = defaults.currency
        changed = true
      }

      return changed ? next : prev
    })
  }, [formData.country_code, locales, monedas, timezones])

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
    setFormData((prev) => ({ ...prev, country_code: code, pais: selected?.name || '' }))
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
    if (code === 'PE' || /(peru|peru)/.test(c)) return /^\d{11}$/.test(v) ? null : 'RUC (Peru) must have 11 digits.'
    if (code === 'EC' || /ecuador/.test(c)) return /^\d{13}$/.test(v) ? null : 'RUC (Ecuador) must have 13 digits.'
    if (code === 'AR' || /argentina/.test(c)) return /^\d{11}$/.test(v) ? null : 'CUIT/CUIL (Argentina) must have 11 digits.'
    if (code === 'CL' || /chile/.test(c)) {
      return /^[0-9]{7,8}-[0-9kK]$/.test(v) || /^[0-9]{7,8}[0-9kK]$/.test(v)
        ? null
        : 'RUT (Chile) must be 8 digits + verification digit (e.g: 12345678-9)'
    }
    if (code === 'ES' || /(espana|spain)/.test(c)) {
      return /^([A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])$/.test(v.toUpperCase())
        ? null
        : 'CIF/NIF (Spain) has invalid basic format.'
    }
    return null
  }

  function validate(): string | null {
    const isEmail = /.+@.+\..+/
    const isPhone = (v: string) => v.length === 0 || /^[0-9+()\\-\\s]{6,20}$/.test(v)
    const isUrl = (v: string) => {
      if (!v) return true
      try {
        new URL(v.startsWith('http') ? v : `http://${v}`)
        return true
      } catch {
        return false
      }
    }
    if (!formData.nombre_empresa.trim()) return 'Company name is required.'
    if (!formData.nombre_encargado.trim()) return 'Manager first name is required.'
    if (!formData.apellido_encargado.trim()) return 'Manager last name is required.'
    if (!formData.email.trim()) return 'Email is required.'
    if (!isEmail.test(formData.email.trim())) return 'Email format is invalid.'
    if (!isPhone(formData.telefono || '')) return 'Invalid phone number.'
    if (!formData.sector_plantilla_id) return 'Select a sector to apply base configuration.'
    if (!formData.country_code) return 'Select a country.'
    if (!formData.default_language) return 'Select a language/locale.'
    if (!formData.timezone) return 'Select a timezone.'
    if (!formData.currency) return 'Select a currency.'
    if (!formData.modulos.length) return 'You must select at least one module for the company.'
    const rucErr = validateRucByCountry(formData.country_code || formData.pais, formData.ruc)
    if (rucErr) return rucErr
    if (!isUrl(formData.sitio_web || '')) return 'Website URL is invalid.'
    return null
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLocalError(null)
    if (!canSubmit) {
      if (!formData.modulos.length) setShowModules(true)
      setLocalError(
        'Complete required fields: company, admin, valid email, country, language, timezone, currency, sector, and at least 1 module.',
      )
      return
    }
    const validationError = validate()
    if (validationError) {
      if (validationError.includes('module')) setShowModules(true)
      setLocalError(validationError)
      return
    }
    const companyName = formData.nombre_empresa.trim()
    const res = await crear(formData, {
      subscriptionPlanId: selectedPlanId || null,
      billingCycle,
    })
    if (!res) return
    setLastCreatedCompany({
      id: String(res.id || ''),
      name: companyName,
      planName: planLabel(selectedPlan),
      subscriptionPending: !!res.subscriptionError,
    })
    setFormData(INITIAL_STATE)
    setSelectedPlanId('')
    setBillingCycle('monthly')
    if (res.subscription?.checkout_url) window.location.href = res.subscription.checkout_url
  }

  const err = (k: string) => (fieldErrors as Record<string, string> | undefined)?.[k]

  const handleSectorChange = (sectorId: number | null) => {
    setFormData((prev) => ({ ...prev, sector_plantilla_id: sectorId }))
  }

  const handleTemplateMeta = (template: SectorTemplate | null) => {
    if (!template) return
    setFormData((prev) => ({
      ...prev,
      color_primario: template.branding.color_primario || prev.color_primario,
      color_secundario: template.branding.color_secundario || prev.color_secundario,
      plantilla_inicio: template.branding.plantilla_inicio || prev.plantilla_inicio,
    }))
  }

  const handlePlanSelect = (plan: CompanyPlan) => {
    setSelectedPlanId(plan.id)
    if (formData.modulos.length > 0 || !plan.included_modules.length) return
    const { resolvedIds, unresolved } = resolvePlanModuleIds(plan.included_modules)
    if (resolvedIds.length) {
      setFormData((prev) => ({ ...prev, modulos: resolvedIds }))
    }
    if (unresolved.length) {
      setLocalError(
        `El plan contiene codigos de modulo invalidos: ${unresolved.join(', ')}. Corrige subscription_plans.included_modules con los codigos canonicos en ingles del catalogo.`,
      )
    }
  }

  const applySelectedPlanModules = () => {
    if (!selectedPlan) return
    const { resolvedIds, unresolved } = resolvePlanModuleIds(selectedPlan.included_modules)
    setFormData((prev) => ({
      ...prev,
      modulos: resolvedIds,
    }))
    if (unresolved.length) {
      setLocalError(
        `El plan contiene codigos de modulo invalidos: ${unresolved.join(', ')}. Corrige subscription_plans.included_modules con los codigos canonicos en ingles del catalogo.`,
      )
    } else {
      setLocalError(null)
    }
    setShowModules(true)
  }

  const selectedCountry = paises.find((pais) => pais.code === formData.country_code)

  function resolvePlanModuleIds(moduleKeys: string[]) {
    const resolvedIds: string[] = []
    const unresolved: string[] = []

    for (const moduleKey of moduleKeys || []) {
      const id = moduloLookup.get(normalizeModuloLookupKey(moduleKey))
      if (id) {
        resolvedIds.push(id)
      } else {
        unresolved.push(moduleKey)
      }
    }

    return {
      resolvedIds: [...new Set(resolvedIds)],
      unresolved: [...new Set(unresolved)],
    }
  }

  return (
    <div className="cc-page">
      <style>{`
        .cc-page { max-width: 1320px; margin: 0 auto; padding: 20px 24px 40px; color: #0f172a; }
        .cc-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 18px; }
        .cc-eyebrow { margin: 0 0 4px; font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: #64748b; }
        .cc-title { margin: 0; font-size: 28px; line-height: 1.1; }
        .cc-subtitle { margin: 6px 0 0; max-width: 760px; font-size: 14px; color: #64748b; }
        .cc-link { display: inline-flex; align-items: center; justify-content: center; min-height: 38px; padding: 0 14px; border-radius: 10px; border: 1px solid #dbe4ee; background: #fff; color: #0f172a; text-decoration: none; font-size: 13px; font-weight: 700; }
        .cc-alert { margin-bottom: 14px; padding: 12px 14px; border-radius: 12px; font-size: 13px; line-height: 1.45; border: 1px solid transparent; }
        .cc-alert.error { background: #fff1f2; border-color: #fecdd3; color: #b91c1c; }
        .cc-alert.success { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
        .cc-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
        .cc-layout { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(320px, 0.95fr); gap: 18px; align-items: start; }
        .cc-stack { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
        .cc-panel { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05); overflow: hidden; }
        .cc-panel-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; padding: 16px 18px 0; }
        .cc-panel-title { margin: 0; font-size: 17px; font-weight: 700; }
        .cc-panel-copy { margin: 4px 0 0; font-size: 12px; color: #64748b; }
        .cc-panel-body { padding: 16px 18px 18px; }
        .cc-step { display: inline-flex; align-items: center; justify-content: center; min-height: 24px; padding: 0 8px; border-radius: 999px; background: #eff6ff; color: #1d4ed8; font-size: 11px; font-weight: 700; }
        .cc-grid { display: grid; gap: 12px; grid-template-columns: repeat(12, minmax(0, 1fr)); }
        .cc-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
        .cc-field label { font-size: 12px; font-weight: 700; color: #334155; }
        .cc-field input, .cc-field select, .cc-field textarea { width: 100%; min-height: 40px; padding: 9px 11px; border-radius: 10px; border: 1px solid #dbe4ee; background: #fff; color: #0f172a; font-size: 13px; box-sizing: border-box; }
        .cc-field textarea { min-height: 88px; resize: vertical; }
        .cc-field input:focus, .cc-field select:focus, .cc-field textarea:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12); }
        .cc-field.error input, .cc-field.error select, .cc-field.error textarea { border-color: #fca5a5; background: #fffaf9; }
        .cc-help { font-size: 11px; color: #64748b; line-height: 1.45; }
        .cc-error-text { font-size: 11px; color: #dc2626; font-weight: 700; }
        .cc-chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
        .cc-chip { display: inline-flex; align-items: center; min-height: 26px; padding: 0 10px; border-radius: 999px; background: #f1f5f9; color: #334155; font-size: 11px; font-weight: 700; }
        .cc-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
        .cc-inline { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
        .cc-toggle, .cc-section-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 34px; padding: 0 12px; border-radius: 999px; border: 1px solid #dbe4ee; background: #fff; color: #334155; font-size: 12px; font-weight: 700; cursor: pointer; }
        .cc-toggle.active { background: #e0edff; border-color: #93c5fd; color: #1d4ed8; }
        .cc-plan-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
        .cc-plan-card { border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; padding: 14px; text-align: left; cursor: pointer; transition: all 0.16s ease; }
        .cc-plan-card:hover { transform: translateY(-1px); box-shadow: 0 8px 18px rgba(15, 23, 42, 0.07); }
        .cc-plan-card.selected { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12); background: linear-gradient(180deg, #eff6ff, #fff); }
        .cc-plan-name { margin: 0; font-size: 15px; font-weight: 700; }
        .cc-plan-price { margin: 8px 0 6px; font-size: 24px; font-weight: 800; line-height: 1; }
        .cc-plan-copy { font-size: 12px; color: #64748b; }
        .cc-plan-list { display: grid; gap: 6px; margin: 12px 0; font-size: 12px; color: #334155; }
        .cc-empty { padding: 14px; border: 1px dashed #cbd5e1; border-radius: 12px; background: #f8fafc; font-size: 12px; color: #64748b; }
        .cc-summary { position: sticky; top: 18px; }
        .cc-summary-list { display: grid; gap: 10px; margin: 0 0 16px; }
        .cc-summary-item { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 10px; border-bottom: 1px solid #edf2f7; }
        .cc-summary-item:last-child { border-bottom: 0; padding-bottom: 0; }
        .cc-summary-label { font-size: 12px; color: #64748b; }
        .cc-summary-value { font-size: 12px; font-weight: 700; text-align: right; }
        .cc-submit { width: 100%; min-height: 44px; border: 0; border-radius: 12px; background: linear-gradient(135deg, #0f172a, #1d4ed8); color: #fff; font-size: 14px; font-weight: 700; cursor: pointer; }
        .cc-submit:disabled { opacity: 0.55; cursor: not-allowed; }
        .cc-submit-copy { margin: 10px 0 0; font-size: 11px; color: #64748b; line-height: 1.45; }
        @media (max-width: 1120px) { .cc-layout { grid-template-columns: 1fr; } .cc-summary { position: static; } }
        @media (max-width: 760px) { .cc-page { padding: 16px 14px 30px; } .cc-header { flex-direction: column; } .cc-plan-grid { grid-template-columns: 1fr; } }
      `}</style>

      <header className="cc-header">
        <div>
          <p className="cc-eyebrow">Admin / Companies</p>
          <h1 className="cc-title">Crear empresa</h1>
          <p className="cc-subtitle">
            Flujo compacto para alta rapida: datos base, sector, plan, modulos y usuario principal en una sola vista.
          </p>
        </div>
        <Link className="cc-link" to="/admin/companies">
          Ver empresas
        </Link>
      </header>

      {lastCreatedCompany && (
        <div className="cc-alert success">
          <strong>{lastCreatedCompany.name}</strong> creada correctamente.
          {lastCreatedCompany.planName ? ` Plan: ${lastCreatedCompany.planName}.` : ''}
          {lastCreatedCompany.subscriptionPending ? ' La suscripcion quedo pendiente.' : ''}
          <div className="cc-actions">
            <Link className="cc-link" to={`/admin/companies/${lastCreatedCompany.id}/users`}>
              Ir a usuarios
            </Link>
            <Link className="cc-link" to={`/admin/companies/${lastCreatedCompany.id}/config`}>
              Abrir configuracion
            </Link>
            <Link className="cc-link" to={`/admin/companies/${lastCreatedCompany.id}/edit`}>
              Editar empresa
            </Link>
          </div>
        </div>
      )}

      {(localError || error || catalogError) && (
        <div ref={errorAlertRef} className="cc-alert error">
          {localError || error || catalogError}
        </div>
      )}

      {!lastCreatedCompany && success && <div className="cc-alert success">{success}</div>}

      <form onSubmit={onSubmit}>
        <div className="cc-layout">
          <div className="cc-stack">
            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Datos esenciales</h2>
                  <p className="cc-panel-copy">Solo lo necesario para arrancar. El resto queda abajo como opcional.</p>
                </div>
                <div className="cc-step">Paso 1</div>
              </div>
              <div className="cc-panel-body">
                <div className="cc-grid">
                  <div className={`cc-field ${err('nombre_empresa') ? 'error' : ''}`} style={{ gridColumn: 'span 8' }}>
                    <label htmlFor="nombre_empresa">Nombre de empresa *</label>
                    <input
                      id="nombre_empresa"
                      name="nombre_empresa"
                      value={formData.nombre_empresa}
                      onChange={onChange}
                      placeholder="Ej. Taller Central Norte"
                      disabled={loading}
                    />
                    {err('nombre_empresa') && <span className="cc-error-text">{err('nombre_empresa')}</span>}
                  </div>

                  <div className={`cc-field ${err('ruc') ? 'error' : ''}`} style={{ gridColumn: 'span 4' }}>
                    <label htmlFor="ruc">RUC / NIF</label>
                    <input
                      id="ruc"
                      name="ruc"
                      value={formData.ruc}
                      onChange={onChange}
                      placeholder="Identificacion fiscal"
                      disabled={loading}
                    />
                    {err('ruc') ? (
                      <span className="cc-error-text">{err('ruc')}</span>
                    ) : (
                      <span className="cc-help">Se valida segun el pais cuando aplique.</span>
                    )}
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                    <label htmlFor="country_code">Pais *</label>
                    <select id="country_code" name="country_code" value={formData.country_code || ''} onChange={onCountryChange} disabled={loading}>
                      <option value="">Seleccionar</option>
                      {paises.map((pais) => (
                        <option key={pais.code} value={pais.code}>
                          {pais.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                    <label htmlFor="default_language">Idioma *</label>
                    <select id="default_language" name="default_language" value={formData.default_language || ''} onChange={onChange} disabled={loading}>
                      <option value="">Seleccionar</option>
                      {locales.map((locale) => (
                        <option key={locale.code} value={locale.code}>
                          {locale.name || locale.code}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                    <label htmlFor="currency">Moneda *</label>
                    <select id="currency" name="currency" value={formData.currency || ''} onChange={onChange} disabled={loading}>
                      <option value="">Seleccionar</option>
                      {monedas.map((moneda) => (
                        <option key={moneda.code} value={moneda.code}>
                          {moneda.code} - {moneda.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 6' }}>
                    <label htmlFor="timezone">Timezone *</label>
                    <select id="timezone" name="timezone" value={formData.timezone || ''} onChange={onChange} disabled={loading}>
                      <option value="">Seleccionar</option>
                      {timezones.map((timezone) => (
                        <option key={timezone.name} value={timezone.name}>
                          {timezone.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 3' }}>
                    <label htmlFor="telefono">Telefono</label>
                    <input id="telefono" name="telefono" value={formData.telefono} onChange={onChange} placeholder="+34 600 000 000" disabled={loading} />
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 3' }}>
                    <label htmlFor="sitio_web">Sitio web</label>
                    <input id="sitio_web" name="sitio_web" value={formData.sitio_web} onChange={onChange} placeholder="empresa.com" disabled={loading} />
                  </div>
                </div>

                {selectedCountry && (
                  <div className="cc-chip-row">
                    <span className="cc-chip">Pais: {selectedCountry.name}</span>
                    {formData.default_language && <span className="cc-chip">Idioma: {formData.default_language}</span>}
                    {formData.timezone && <span className="cc-chip">Timezone: {formData.timezone}</span>}
                    {formData.currency && <span className="cc-chip">Moneda: {formData.currency}</span>}
                  </div>
                )}
              </div>
            </section>

            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Sector base</h2>
                  <p className="cc-panel-copy">Define una base de branding y categorias para empezar mas rapido.</p>
                </div>
                <div className="cc-step">Paso 2</div>
              </div>
              <div className="cc-panel-body">
                <SectorPlantillaSelector
                  value={formData.sector_plantilla_id || null}
                  onChange={handleSectorChange}
                  disabled={loading}
                  onTemplateSelected={handleTemplateMeta}
                />
              </div>
            </section>

            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Plan y suscripcion</h2>
                  <p className="cc-panel-copy">Selecciona el plan del cliente y copia sus modulos si quieres acelerar el alta.</p>
                </div>
                <div className="cc-step">Paso 3</div>
              </div>
              <div className="cc-panel-body">
                <div className="cc-toolbar">
                  <div className="cc-inline">
                    <button type="button" className={`cc-toggle ${billingCycle === 'monthly' ? 'active' : ''}`} onClick={() => setBillingCycle('monthly')}>
                      Mensual
                    </button>
                    <button type="button" className={`cc-toggle ${billingCycle === 'yearly' ? 'active' : ''}`} onClick={() => setBillingCycle('yearly')}>
                      Anual
                    </button>
                  </div>

                  {selectedPlan && (
                    <div className="cc-inline">
                      <span className="cc-help">{selectedPlan.included_modules.length} modulos incluidos</span>
                      <button type="button" className="cc-section-btn" onClick={applySelectedPlanModules}>
                        Usar modulos del plan
                      </button>
                    </div>
                  )}
                </div>

                {plansLoading ? (
                  <div className="cc-empty">Cargando planes...</div>
                ) : billingPlans.length === 0 ? (
                  <div className="cc-empty">No hay planes disponibles. Puedes crear la empresa y asignar la suscripcion despues.</div>
                ) : (
                  <div className="cc-plan-grid">
                    {billingPlans.map((plan) => {
                      const price = billingCycle === 'yearly' && plan.price_yearly != null ? plan.price_yearly : plan.price_monthly
                      const isSelected = selectedPlanId === plan.id
                      return (
                        <button key={plan.id} type="button" className={`cc-plan-card ${isSelected ? 'selected' : ''}`} onClick={() => handlePlanSelect(plan)}>
                          <p className="cc-plan-name">{plan.display_name || plan.name}</p>
                          <div className="cc-plan-price">{formatMoney(price)}</div>
                          <div className="cc-plan-copy">por {billingCycle === 'yearly' ? 'ano' : 'mes'}</div>
                          <div className="cc-plan-list">
                            <span>Usuarios: {plan.max_users}</span>
                            <span>Sucursales: {plan.max_branches}</span>
                            <span>Modulos: {plan.included_modules.length}</span>
                          </div>
                          <div className="cc-plan-copy">
                            Incluye: {plan.included_modules.slice(0, 6).join(', ')}
                            {plan.included_modules.length > 6 ? ` +${plan.included_modules.length - 6}` : ''}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </section>

            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Modulos</h2>
                  <p className="cc-panel-copy">Mantener cerrado reduce ruido. Abre solo si necesitas ajustar el paquete.</p>
                </div>
                <button type="button" className="cc-section-btn" onClick={() => setShowModules((prev) => !prev)}>
                  {showModules ? 'Ocultar' : 'Abrir'} ({formData.modulos.length})
                </button>
              </div>
              <div className="cc-panel-body">
                <div className="cc-chip-row">
                  {formData.modulos.length > 0 ? (
                    formData.modulos.slice(0, 8).map((modulo) => (
                      <span key={modulo} className="cc-chip">
                        {modulo}
                      </span>
                    ))
                  ) : (
                    <span className="cc-help">Aun no hay modulos seleccionados.</span>
                  )}
                </div>
                {showModules && (
                  <div style={{ marginTop: '14px' }}>
                    <ModuloSelector selected={formData.modulos} onChange={onModuloChange} />
                  </div>
                )}
              </div>
            </section>

            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Detalles avanzados</h2>
                  <p className="cc-panel-copy">Direccion, branding, logo y configuracion JSON quedan fuera del camino principal.</p>
                </div>
                <button type="button" className="cc-section-btn" onClick={() => setShowAdvanced((prev) => !prev)}>
                  {showAdvanced ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
              {showAdvanced && (
                <div className="cc-panel-body">
                  <div className="cc-grid">
                    <div className="cc-field" style={{ gridColumn: 'span 12' }}>
                      <label htmlFor="direccion">Direccion</label>
                      <input id="direccion" name="direccion" value={formData.direccion} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="provincia">Provincia</label>
                      <input id="provincia" name="provincia" value={formData.provincia} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="ciudad">Ciudad</label>
                      <input id="ciudad" name="ciudad" value={formData.ciudad} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="cp">Codigo postal</label>
                      <input id="cp" name="cp" value={formData.cp} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="color_primario">Color primario</label>
                      <input id="color_primario" name="color_primario" value={formData.color_primario} onChange={onChange} placeholder="#1d4ed8" disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="color_secundario">Color secundario</label>
                      <input id="color_secundario" name="color_secundario" value={formData.color_secundario} onChange={onChange} placeholder="#0f172a" disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 4' }}>
                      <label htmlFor="plantilla_inicio">Plantilla inicio</label>
                      <input id="plantilla_inicio" name="plantilla_inicio" value={formData.plantilla_inicio} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 6' }}>
                      <label htmlFor="logo">Logo</label>
                      <input id="logo" name="logo" type="file" onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 6' }}>
                      <label htmlFor="pais">Nombre pais</label>
                      <input id="pais" name="pais" value={formData.pais} onChange={onChange} disabled={loading} />
                    </div>

                    <div className="cc-field" style={{ gridColumn: 'span 12' }}>
                      <label htmlFor="config_json">Config JSON</label>
                      <textarea
                        id="config_json"
                        name="config_json"
                        value={formData.config_json}
                        onChange={onChange}
                        placeholder='{"feature_flags":{"beta":true}}'
                        disabled={loading}
                      />
                    </div>
                  </div>
                </div>
              )}
            </section>
          </div>

          <div className="cc-stack">
            <section className="cc-panel">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Usuario principal</h2>
                  <p className="cc-panel-copy">Se crea junto con la empresa para entrar al tenant desde el minuto uno.</p>
                </div>
                <div className="cc-step">Paso 4</div>
              </div>
              <div className="cc-panel-body">
                <div className="cc-grid">
                  <div className="cc-field" style={{ gridColumn: 'span 6' }}>
                    <label htmlFor="nombre_encargado">Nombre *</label>
                    <input id="nombre_encargado" name="nombre_encargado" value={formData.nombre_encargado} onChange={onChange} disabled={loading} />
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 6' }}>
                    <label htmlFor="apellido_encargado">Apellido *</label>
                    <input id="apellido_encargado" name="apellido_encargado" value={formData.apellido_encargado} onChange={onChange} disabled={loading} />
                  </div>

                  {needSecondSurname && (
                    <div className="cc-field" style={{ gridColumn: 'span 12' }}>
                      <label htmlFor="segundo_apellido_encargado">Segundo apellido</label>
                      <input
                        id="segundo_apellido_encargado"
                        name="segundo_apellido_encargado"
                        value={formData.segundo_apellido_encargado || ''}
                        onChange={onChange}
                        disabled={loading}
                      />
                      <span className="cc-help">Se usa para generar un username unico si el primero ya existe.</span>
                    </div>
                  )}

                  <div className={`cc-field ${err('email') ? 'error' : ''}`} style={{ gridColumn: 'span 12' }}>
                    <label htmlFor="email">Email *</label>
                    <input id="email" name="email" type="email" value={formData.email} onChange={onChange} placeholder="admin@empresa.com" disabled={loading} />
                    {err('email') && <span className="cc-error-text">{err('email')}</span>}
                  </div>

                  <div className={`cc-field ${err('username') ? 'error' : ''}`} style={{ gridColumn: 'span 12' }}>
                    <label htmlFor="username">Username</label>
                    <input id="username" name="username" value={formData.username} onChange={onChange} placeholder="usuario sugerido" disabled={loading} />
                    {err('username') ? (
                      <span className="cc-error-text">{err('username')}</span>
                    ) : (
                      <span className="cc-help">Se sugiere automaticamente a partir del nombre y apellido.</span>
                    )}
                  </div>

                  <div className="cc-field" style={{ gridColumn: 'span 12' }}>
                    <label htmlFor="password">Password inicial</label>
                    <input id="password" name="password" type="password" value={formData.password || ''} onChange={onChange} placeholder="Opcional" disabled={loading} />
                  </div>
                </div>
              </div>
            </section>

            <section className="cc-panel cc-summary">
              <div className="cc-panel-head">
                <div>
                  <h2 className="cc-panel-title">Resumen y alta</h2>
                  <p className="cc-panel-copy">Panel corto para validar lo minimo antes de crear.</p>
                </div>
                <div className="cc-step">Paso 5</div>
              </div>
              <div className="cc-panel-body">
                <div className="cc-summary-list">
                  <div className="cc-summary-item">
                    <span className="cc-summary-label">Empresa</span>
                    <span className="cc-summary-value">{formData.nombre_empresa || 'Pendiente'}</span>
                  </div>
                  <div className="cc-summary-item">
                    <span className="cc-summary-label">Sector</span>
                    <span className="cc-summary-value">{formData.sector_plantilla_id ? `Seleccionado #${formData.sector_plantilla_id}` : 'Pendiente'}</span>
                  </div>
                  <div className="cc-summary-item">
                    <span className="cc-summary-label">Plan</span>
                    <span className="cc-summary-value">{planLabel(selectedPlan)}</span>
                  </div>
                  <div className="cc-summary-item">
                    <span className="cc-summary-label">Modulos</span>
                    <span className="cc-summary-value">{formData.modulos.length} seleccionados</span>
                  </div>
                  <div className="cc-summary-item">
                    <span className="cc-summary-label">Admin</span>
                    <span className="cc-summary-value">{formData.email || 'Pendiente'}</span>
                  </div>
                </div>

                <button type="submit" className="cc-submit" disabled={loading || !canSubmit}>
                  {loading ? 'Creando empresa...' : 'Crear empresa'}
                </button>
                <p className="cc-submit-copy">
                  Requerido: empresa, sector, pais, idioma, timezone, moneda, admin valido y al menos un modulo.
                </p>
              </div>
            </section>
          </div>
        </div>
      </form>
    </div>
  )
}
