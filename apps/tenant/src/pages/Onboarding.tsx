import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import tenantApi from '../shared/api/client'
import { TENANT_ONBOARDING } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'
import PageContainer from '../components/PageContainer'

type Step = 'info' | 'regional' | 'branding' | 'review'

interface FormData {
  company_name: string
  tax_id: string
  country_code: string
  phone: string
  address: string
  city: string
  state: string
  postal_code: string
  website: string
  default_language: string
  timezone: string
  currency: string
  logo: string | null
  primary_color: string
  secondary_color: string
}

interface SectorConfig {
  key: string
  nombre: string
  icono: string
  color: string
  mensaje: string
  tipRegional: string
  placeholderEmpresa: string
}

const SECTOR_CONFIGS: Record<string, SectorConfig> = {
  panaderia: {
    key: 'panaderia',
    nombre: 'Panadería',
    icono: '🥐',
    color: '#92400e',
    mensaje: 'Configurá tu panadería en minutos. Luego podrás cargar ingredientes, recetas y empezar a producir.',
    tipRegional: 'Para panaderías en Ecuador recomendamos USD como moneda y America/Guayaquil como zona horaria.',
    placeholderEmpresa: 'Ej: Panadería El Trigo Dorado',
  },
  restaurante: {
    key: 'restaurante',
    nombre: 'Restaurante',
    icono: '🍴',
    color: '#dc2626',
    mensaje: 'Configurá tu restaurante. Después podrás crear tu menú, registrar insumos y gestionar mesas.',
    tipRegional: 'Recomendamos configurar bien la zona horaria para que los reportes diarios coincidan con tus turnos.',
    placeholderEmpresa: 'Ej: Restaurante La Buena Mesa',
  },
  retail: {
    key: 'retail',
    nombre: 'Retail / Tienda',
    icono: '🛍️',
    color: '#2563eb',
    mensaje: 'Configurá tu tienda. Luego cargarás tu catálogo de productos y empezarás a vender desde el POS.',
    tipRegional: 'Si vendés en múltiples monedas, podés configurarlas después desde Configuración.',
    placeholderEmpresa: 'Ej: Tienda Ferretería Central',
  },
  taller: {
    key: 'taller',
    nombre: 'Taller Mecánico',
    icono: '🔧',
    color: '#1e40af',
    mensaje: 'Configurá tu taller. Podrás registrar servicios, repuestos, clientes y órdenes de trabajo.',
    tipRegional: 'El idioma y zona horaria correctos son clave para que las órdenes de trabajo tengan la fecha exacta.',
    placeholderEmpresa: 'Ej: Taller Mecánico Don Pedro',
  },
}

const DEFAULT_SECTOR: SectorConfig = {
  key: 'general',
  nombre: 'Tu empresa',
  icono: '🏢',
  color: '#4f46e5',
  mensaje: 'Configurá tu empresa en pocos pasos. Podrás ajustar todo esto más adelante desde Configuración.',
  tipRegional: 'Podés cambiar el idioma y zona horaria después desde Configuración de empresa.',
  placeholderEmpresa: 'Ej: Mi Empresa S.A.',
}

function getSectorConfig(sectorNombre: string | null): SectorConfig {
  if (!sectorNombre) return DEFAULT_SECTOR
  const s = sectorNombre.toLowerCase()
  if (s.includes('panaderia') || s.includes('panadería') || s.includes('bakery')) return SECTOR_CONFIGS.panaderia
  if (s.includes('restaurante') || s.includes('restaurant')) return SECTOR_CONFIGS.restaurante
  if (s.includes('retail') || s.includes('tienda')) return SECTOR_CONFIGS.retail
  if (s.includes('taller') || s.includes('mecanic')) return SECTOR_CONFIGS.taller
  return DEFAULT_SECTOR
}

const COUNTRIES = [
  { code: 'EC', name: 'Ecuador' },
  { code: 'PE', name: 'Perú' },
  { code: 'CO', name: 'Colombia' },
  { code: 'CL', name: 'Chile' },
  { code: 'AR', name: 'Argentina' },
  { code: 'ES', name: 'España' },
  { code: 'MX', name: 'México' },
]

const LANGUAGES = [
  { code: 'es', name: 'Español' },
  { code: 'en', name: 'English' },
]

const CURRENCIES = ['USD', 'EUR', 'PEN', 'CLP', 'COP', 'ARS', 'MXN']

const STEPS: Step[] = ['info', 'regional', 'branding', 'review']

const STEP_LABELS: Record<Step, string> = {
  info: 'Empresa',
  regional: 'Regional',
  branding: 'Marca',
  review: 'Revisar',
}

const normalizeLanguage = (value?: string | null) => {
  const v = (value || '').trim().toLowerCase()
  if (v.startsWith('es')) return 'es'
  if (v.startsWith('en')) return 'en'
  return v
}

export default function Onboarding() {
  const { t } = useTranslation()
  const [step, setStep] = useState<Step>('info')
  const [sector, setSector] = useState<SectorConfig>(DEFAULT_SECTOR)
  const [formData, setFormData] = useState<FormData>({
    company_name: '',
    tax_id: '',
    country_code: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    postal_code: '',
    website: '',
    default_language: 'es',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    currency: 'USD',
    logo: null,
    primary_color: DEFAULT_SECTOR.color,
    secondary_color: '#ffffff',
  })
  const [saving, setSaving] = useState(false)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const { success, error } = useToast()
  const navigate = useNavigate()

  // Cargar sector y datos existentes
  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [{ data: me }, { data: general }, { data: branding }] = await Promise.all([
          tenantApi.get('/api/v1/me/tenant'),
          tenantApi.get('/api/v1/company/settings/general'),
          tenantApi.get('/api/v1/company/settings/branding'),
        ])
        if (!active) return

        const cfg = getSectorConfig((me as any)?.sector_nombre)
        setSector(cfg)

        setFormData(prev => ({
          ...prev,
          company_name: prev.company_name || general?.company_name || '',
          tax_id: prev.tax_id || general?.tax_id || '',
          country_code: prev.country_code || general?.country_code || '',
          phone: prev.phone || general?.phone || '',
          address: prev.address || general?.address || '',
          city: prev.city || general?.city || '',
          state: prev.state || general?.state || '',
          postal_code: prev.postal_code || general?.postal_code || '',
          website: prev.website || general?.website || '',
          default_language: normalizeLanguage(general?.default_language) || prev.default_language,
          timezone: general?.timezone || prev.timezone,
          currency: general?.currency || prev.currency,
          logo: prev.logo || branding?.company_logo || null,
          primary_color: branding?.primary_color || cfg.color,
          secondary_color: branding?.secondary_color || prev.secondary_color,
        }))
        if (branding?.company_logo) setLogoPreview(branding.company_logo)
      } catch {
        // continuar con defaults
      }
    }
    load()
    return () => { active = false }
  }, [])

  const handleInput = (field: keyof FormData, value: string) =>
    setFormData(prev => ({ ...prev, [field]: value }))

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onloadend = () => {
      setLogoPreview(reader.result as string)
      setFormData(prev => ({ ...prev, logo: reader.result as string }))
    }
    reader.readAsDataURL(file)
  }

  const validateStep = (s: Step) => {
    if (s === 'info') return !!(formData.company_name && formData.country_code)
    if (s === 'regional') return !!(formData.default_language && formData.timezone && formData.currency)
    if (s === 'branding') return !!(formData.primary_color)
    return true
  }

  const nextStep = () => {
    if (!validateStep(step)) { error(t('pages.onboarding.requiredFields')); return }
    const idx = STEPS.indexOf(step)
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1])
  }

  const prevStep = () => {
    const idx = STEPS.indexOf(step)
    if (idx > 0) setStep(STEPS[idx - 1])
  }

  const onSubmit = async () => {
    try {
      setSaving(true)
      const result = await tenantApi.post(TENANT_ONBOARDING.init, {
        company_name: formData.company_name,
        tax_id: formData.tax_id || null,
        country_code: formData.country_code,
        phone: formData.phone || null,
        address: formData.address || null,
        city: formData.city || null,
        state: formData.state || null,
        postal_code: formData.postal_code || null,
        website: formData.website || null,
        default_language: formData.default_language,
        timezone: formData.timezone,
        currency: formData.currency,
        logo_empresa: formData.logo,
        primary_color: formData.primary_color,
        secondary_color: formData.secondary_color,
      })
      success(t('pages.onboarding.savedSuccess'))
      const token = searchParams.get('token')
      if (token) {
        navigate(`/set-password?token=${token}`)
      } else {
        const slug = result?.data?.empresa_slug
        navigate(slug ? `/${slug}` : '/')
      }
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const stepIdx = STEPS.indexOf(step)
  const languageLabel = normalizeLanguage(formData.default_language) === 'es' ? 'Español' : 'English'

  return (
    <PageContainer className="min-h-screen bg-slate-50">
      <div className="max-w-2xl mx-auto">

        {/* Header con sector */}
        <div className="text-center mb-8">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-white text-sm font-semibold mb-4"
            style={{ backgroundColor: sector.color }}
          >
            <span className="text-lg">{sector.icono}</span>
            <span>{sector.nombre}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Configuración inicial</h1>
          <p className="text-slate-500 mt-1 text-sm max-w-md mx-auto">{sector.mensaje}</p>
        </div>

        {/* Barra de progreso */}
        <div className="mb-8">
          <div className="flex items-center">
            {STEPS.map((s, idx) => (
              <React.Fragment key={s}>
                <div className="flex flex-col items-center">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all"
                    style={{
                      backgroundColor: idx <= stepIdx ? sector.color : '#e2e8f0',
                      color: idx <= stepIdx ? '#fff' : '#94a3b8',
                    }}
                  >
                    {idx < stepIdx ? '✓' : idx + 1}
                  </div>
                  <span className="text-xs mt-1 text-slate-500 hidden sm:block">{STEP_LABELS[s]}</span>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className="flex-1 h-1 mx-2 rounded transition-all"
                    style={{ backgroundColor: idx < stepIdx ? sector.color : '#e2e8f0' }}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Tarjeta del formulario */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8">

          {/* Step 1: Empresa */}
          {step === 'info' && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Tu empresa</h2>
                <p className="text-slate-500 text-sm mt-1">Información básica de tu negocio</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="gc-label">Nombre de la empresa *</label>
                  <input
                    type="text"
                    value={formData.company_name}
                    onChange={e => handleInput('company_name', e.target.value)}
                    placeholder={sector.placeholderEmpresa}
                    className="gc-input"
                    required
                  />
                </div>
                <div>
                  <label className="gc-label">País *</label>
                  <select value={formData.country_code} onChange={e => handleInput('country_code', e.target.value)} className="gc-input" required>
                    <option value="">Seleccionar país...</option>
                    {COUNTRIES.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="gc-label">RUC / NIT / CIF</label>
                  <input type="text" value={formData.tax_id} onChange={e => handleInput('tax_id', e.target.value)} placeholder="Ej: 1234567890001" className="gc-input" />
                </div>
                <div>
                  <label className="gc-label">Teléfono</label>
                  <input type="tel" value={formData.phone} onChange={e => handleInput('phone', e.target.value)} placeholder="Ej: +593 99 123 4567" className="gc-input" />
                </div>
                <div>
                  <label className="gc-label">Ciudad</label>
                  <input type="text" value={formData.city} onChange={e => handleInput('city', e.target.value)} placeholder="Ej: Cuenca" className="gc-input" />
                </div>
                <div className="md:col-span-2">
                  <label className="gc-label">Dirección</label>
                  <input type="text" value={formData.address} onChange={e => handleInput('address', e.target.value)} placeholder="Ej: Av. Solano y Av. 12 de Abril" className="gc-input" />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Regional */}
          {step === 'regional' && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Configuración regional</h2>
                <p className="text-slate-500 text-sm mt-1">Idioma, zona horaria y moneda de tu operación</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="gc-label">Idioma</label>
                  <select value={formData.default_language} onChange={e => handleInput('default_language', e.target.value)} className="gc-input">
                    {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="gc-label">Zona horaria</label>
                  <input type="text" value={formData.timezone} onChange={e => handleInput('timezone', e.target.value)} placeholder="America/Guayaquil" className="gc-input" />
                </div>
                <div>
                  <label className="gc-label">Moneda</label>
                  <select value={formData.currency} onChange={e => handleInput('currency', e.target.value)} className="gc-input">
                    {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              {/* Tip por sector */}
              <div
                className="flex gap-3 p-4 rounded-lg text-sm"
                style={{ backgroundColor: `${sector.color}15`, borderLeft: `4px solid ${sector.color}` }}
              >
                <span className="text-lg">{sector.icono}</span>
                <p style={{ color: sector.color }}><strong>Tip para {sector.nombre}:</strong> {sector.tipRegional}</p>
              </div>
            </div>
          )}

          {/* Step 3: Branding */}
          {step === 'branding' && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Identidad visual</h2>
                <p className="text-slate-500 text-sm mt-1">Logo y colores de tu marca</p>
              </div>

              {/* Sugerencia de color por sector */}
              <div
                className="flex items-center gap-3 p-3 rounded-lg text-sm cursor-pointer border-2 transition-all"
                style={{ borderColor: sector.color, backgroundColor: `${sector.color}10` }}
                onClick={() => setFormData(prev => ({ ...prev, primary_color: sector.color }))}
              >
                <div className="w-8 h-8 rounded-full flex-shrink-0" style={{ backgroundColor: sector.color }} />
                <div>
                  <p className="font-medium" style={{ color: sector.color }}>Color sugerido para {sector.nombre}</p>
                  <p className="text-xs text-slate-500">Clic para aplicar {sector.color}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="gc-label">Color principal</label>
                  <div className="flex items-center gap-3">
                    <input type="color" value={formData.primary_color} onChange={e => handleInput('primary_color', e.target.value)} className="w-12 h-12 border border-slate-200 rounded-lg cursor-pointer" />
                    <input type="text" value={formData.primary_color} onChange={e => handleInput('primary_color', e.target.value)} className="gc-input flex-1 font-mono text-sm" />
                  </div>
                </div>
                <div>
                  <label className="gc-label">Color secundario</label>
                  <div className="flex items-center gap-3">
                    <input type="color" value={formData.secondary_color} onChange={e => handleInput('secondary_color', e.target.value)} className="w-12 h-12 border border-slate-200 rounded-lg cursor-pointer" />
                    <input type="text" value={formData.secondary_color} onChange={e => handleInput('secondary_color', e.target.value)} className="gc-input flex-1 font-mono text-sm" />
                  </div>
                </div>
              </div>

              <div>
                <label className="gc-label">Logo (opcional)</label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-6 text-center">
                  {logoPreview ? (
                    <div className="space-y-3">
                      <img src={logoPreview} alt="Logo preview" className="h-20 mx-auto object-contain" />
                      <button type="button" onClick={() => { setLogoPreview(null); setFormData(prev => ({ ...prev, logo: null })) }} className="text-sm text-red-500 hover:text-red-600">
                        Cambiar logo
                      </button>
                    </div>
                  ) : (
                    <label className="cursor-pointer">
                      <p className="text-2xl mb-1">📤</p>
                      <p className="text-sm font-medium text-slate-700">Subir logo</p>
                      <p className="text-xs text-slate-400 mt-1">PNG, JPG o SVG recomendado</p>
                      <input type="file" accept="image/*" onChange={handleFile} className="hidden" />
                    </label>
                  )}
                </div>
              </div>

              {/* Preview */}
              <div className="rounded-lg p-4 flex items-center gap-3" style={{ backgroundColor: formData.primary_color }}>
                {logoPreview && <img src={logoPreview} alt="" className="h-8 w-8 rounded object-contain bg-white" />}
                <p className="text-white font-semibold">{formData.company_name || 'Tu empresa'}</p>
              </div>
            </div>
          )}

          {/* Step 4: Review */}
          {step === 'review' && (
            <div className="space-y-5">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Todo listo para empezar</h2>
                <p className="text-slate-500 text-sm mt-1">Revisá los datos antes de guardar</p>
              </div>

              {/* Banner sector */}
              <div className="flex items-center gap-3 p-4 rounded-xl text-white" style={{ backgroundColor: sector.color }}>
                <span className="text-3xl">{sector.icono}</span>
                <div>
                  <p className="font-bold text-lg">{formData.company_name}</p>
                  <p className="text-sm opacity-90">{sector.nombre} · {formData.country_code} · {formData.currency}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="border rounded-lg p-4 space-y-2">
                  <p className="font-semibold text-slate-700 text-sm">📋 Empresa</p>
                  {formData.tax_id && <p className="text-xs text-slate-500">RUC: {formData.tax_id}</p>}
                  {formData.phone && <p className="text-xs text-slate-500">Tel: {formData.phone}</p>}
                  {formData.city && <p className="text-xs text-slate-500">Ciudad: {formData.city}</p>}
                  {formData.address && <p className="text-xs text-slate-500">{formData.address}</p>}
                </div>
                <div className="border rounded-lg p-4 space-y-2">
                  <p className="font-semibold text-slate-700 text-sm">🌍 Regional</p>
                  <p className="text-xs text-slate-500">Idioma: {languageLabel}</p>
                  <p className="text-xs text-slate-500">Zona: {formData.timezone}</p>
                  <p className="text-xs text-slate-500">Moneda: {formData.currency}</p>
                </div>
              </div>

              <div
                className="flex gap-3 p-4 rounded-lg text-sm"
                style={{ backgroundColor: `${sector.color}15`, borderLeft: `4px solid ${sector.color}` }}
              >
                <span>✅</span>
                <p style={{ color: sector.color }}>
                  <strong>¡Listo!</strong> Después del guardado podés cargar tus productos y empezar a operar.
                </p>
              </div>
            </div>
          )}

          {/* Botones de navegación */}
          <div className="flex gap-3 mt-8 pt-6 border-t border-slate-100">
            <button
              onClick={prevStep}
              disabled={step === 'info' || saving}
              className="gc-btn gc-btn--secondary"
            >
              ← Atrás
            </button>
            {step !== 'review' ? (
              <button
                onClick={nextStep}
                disabled={saving}
                className="gc-btn gc-btn--primary ml-auto"
                style={{ backgroundColor: sector.color, borderColor: sector.color }}
              >
                Siguiente →
              </button>
            ) : (
              <button
                onClick={onSubmit}
                disabled={saving}
                className="gc-btn gc-btn--primary ml-auto"
                style={{ backgroundColor: sector.color, borderColor: sector.color }}
              >
                {saving ? 'Guardando...' : `Comenzar con ${sector.nombre} →`}
              </button>
            )}
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
