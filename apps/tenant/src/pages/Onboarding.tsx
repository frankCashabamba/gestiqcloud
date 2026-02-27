import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import tenantApi from '../shared/api/client'
import { TENANT_ONBOARDING } from '@shared/endpoints'
import { useToast, getErrorMessage } from '../shared/toast'
import { resolveTenantPath } from '../lib/tenantNavigation'

type Step = 'info' | 'regional' | 'branding' | 'review'

interface FormData {
  // Tenant info (step 1)
  company_name: string
  tax_id: string
  country_code: string
  phone: string
  address: string
  city: string
  state: string
  postal_code: string
  website: string

  // Regional (step 2)
  default_language: string
  timezone: string
  currency: string

  // Branding (step 3)
  logo: string | null
  primary_color: string
  secondary_color: string
}

const INITIAL_STATE: FormData = {
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
  primary_color: '#4f46e5',
  secondary_color: '#ffffff',
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

const normalizeLanguage = (value?: string | null) => {
  const v = (value || '').trim().toLowerCase()
  if (v.startsWith('es')) return 'es'
  if (v.startsWith('en')) return 'en'
  return v
}

export default function Onboarding() {
  const { t } = useTranslation()
  const [step, setStep] = useState<Step>('info')
  const [formData, setFormData] = useState<FormData>(INITIAL_STATE)
  const [saving, setSaving] = useState(false)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const { success, error } = useToast()
  const navigate = useNavigate()

  // Auto-detect language
  useEffect(() => {
    const lang = navigator.language?.startsWith('es') ? 'es' : 'en'
    setFormData(prev => ({ ...prev, default_language: lang }))
  }, [])

  useEffect(() => {
    let active = true
    const loadExisting = async () => {
      try {
        const [{ data: general }, { data: branding }] = await Promise.all([
          tenantApi.get('/api/v1/company/settings/general'),
          tenantApi.get('/api/v1/company/settings/branding'),
        ])
        if (!active) return
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
          default_language:
            prev.default_language === INITIAL_STATE.default_language
              ? normalizeLanguage(general?.default_language) || prev.default_language
              : prev.default_language,
          timezone:
            prev.timezone === INITIAL_STATE.timezone
              ? general?.timezone || prev.timezone
              : prev.timezone,
          currency:
            prev.currency === INITIAL_STATE.currency
              ? general?.currency || prev.currency
              : prev.currency,
          logo: prev.logo || branding?.company_logo || null,
          primary_color:
            prev.primary_color === INITIAL_STATE.primary_color
              ? branding?.primary_color || prev.primary_color
              : prev.primary_color,
          secondary_color:
            prev.secondary_color === INITIAL_STATE.secondary_color
              ? branding?.secondary_color || prev.secondary_color
              : prev.secondary_color,
        }))
        if (branding?.company_logo) setLogoPreview(branding.company_logo)
      } catch (e) {
        // Best-effort: onboarding should still work without prefills.
      }
    }
    loadExisting()
    return () => {
      active = false
    }
  }, [])

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onloadend = () => {
      setLogoPreview(reader.result as string)
      setFormData(prev => ({ ...prev, logo: reader.result as string }))
    }
    reader.readAsDataURL(file)
  }

  const handleColorChange = (field: 'primary_color' | 'secondary_color', value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const validateStep = (currentStep: Step): boolean => {
    switch (currentStep) {
      case 'info':
        return !!(formData.company_name && formData.country_code)
      case 'regional':
        return !!(formData.default_language && formData.timezone && formData.currency)
      case 'branding':
        return !!(formData.primary_color && formData.secondary_color)
      case 'review':
        return true
      default:
        return false
    }
  }

  const nextStep = () => {
    if (!validateStep(step)) {
      error(t('pages.onboarding.requiredFields'))
      return
    }
    const steps: Step[] = ['info', 'regional', 'branding', 'review']
    const currentIndex = steps.indexOf(step)
    if (currentIndex < steps.length - 1) {
      setStep(steps[currentIndex + 1])
    }
  }

  const prevStep = () => {
    const steps: Step[] = ['info', 'regional', 'branding', 'review']
    const currentIndex = steps.indexOf(step)
    if (currentIndex > 0) {
      setStep(steps[currentIndex - 1])
    }
  }

  const onSubmit = async () => {
    try {
      setSaving(true)
      await tenantApi.post(TENANT_ONBOARDING.init, {
        // Tenant info
        company_name: formData.company_name,
        tax_id: formData.tax_id || null,
        country_code: formData.country_code,
        phone: formData.phone || null,
        address: formData.address || null,
        city: formData.city || null,
        state: formData.state || null,
        postal_code: formData.postal_code || null,
        website: formData.website || null,

        // Settings
        default_language: formData.default_language,
        timezone: formData.timezone,
        currency: formData.currency,
        logo_empresa: formData.logo,
        primary_color: formData.primary_color,
        secondary_color: formData.secondary_color,
      })
      success(t('pages.onboarding.savedSuccess'))

      // Redirect to set-password if token present
      const token = searchParams.get('token')
      if (token) {
        navigate(`/set-password?token=${token}`)
      } else {
        const target = await resolveTenantPath()
        navigate(target)
      }
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const getStepNumber = (s: Step) => {
    const steps: Step[] = ['info', 'regional', 'branding', 'review']
    return steps.indexOf(s) + 1
  }

  const normalizedLanguage = normalizeLanguage(formData.default_language)
  const languageLabel =
    normalizedLanguage === 'es'
      ? 'Español'
      : normalizedLanguage === 'en'
        ? 'English'
        : formData.default_language

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-blue-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">GestiqCloud</h1>
          <p className="text-gray-600 mt-2">{t('pages.onboarding.subtitle')}</p>
        </div>

        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {['info', 'regional', 'branding', 'review'].map((s: any, idx) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition ${
                    step === s
                      ? 'bg-indigo-600 text-white'
                      : idx < ['info', 'regional', 'branding', 'review'].indexOf(step)
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                  }`}
                >
                  {idx + 1}
                </div>
                {idx < 3 && <div className={`h-1 flex-1 mx-2 ${idx < ['info', 'regional', 'branding', 'review'].indexOf(step) ? 'bg-indigo-600' : 'bg-gray-200'}`}></div>}
              </div>
            ))}
          </div>
          <div className="text-sm text-gray-600 text-center">
            {t('pages.onboarding.stepOf', { current: getStepNumber(step), total: 4 })}
          </div>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Step 1: Company Info */}
          {step === 'info' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('pages.onboarding.steps.info.title')}</h2>
                <p className="text-gray-600">{t('pages.onboarding.steps.info.subtitle')}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('pages.onboarding.steps.info.companyName')}
                  </label>
                  <input
                    type="text"
                    value={formData.company_name}
                    onChange={(e) => handleInputChange('company_name', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.companyNamePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.country')}</label>
                  <select
                    value={formData.country_code}
                    onChange={(e) => handleInputChange('country_code', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  >
                    <option value="">{t('pages.onboarding.steps.info.selectCountry')}</option>
                    {COUNTRIES.map(c => (
                      <option key={c.code} value={c.code}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.taxId')}</label>
                  <input
                    type="text"
                    value={formData.tax_id}
                    onChange={(e) => handleInputChange('tax_id', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.taxIdPlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.phone')}</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => handleInputChange('phone', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.phonePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.address')}</label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => handleInputChange('address', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.addressPlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.city')}</label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => handleInputChange('city', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.cityPlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.stateProvince')}</label>
                  <input
                    type="text"
                    value={formData.state}
                    onChange={(e) => handleInputChange('state', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.statePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.postalCode')}</label>
                  <input
                    type="text"
                    value={formData.postal_code}
                    onChange={(e) => handleInputChange('postal_code', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.postalCodePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.info.website')}</label>
                  <input
                    type="url"
                    value={formData.website}
                    onChange={(e) => handleInputChange('website', e.target.value)}
                    placeholder={t('pages.onboarding.steps.info.websitePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Regional Config */}
          {step === 'regional' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('pages.onboarding.steps.regional.title')}</h2>
                <p className="text-gray-600">{t('pages.onboarding.steps.regional.subtitle')}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.regional.language')}</label>
                  <select
                    value={formData.default_language}
                    onChange={(e) => handleInputChange('default_language', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  >
                    {LANGUAGES.map(l => (
                      <option key={l.code} value={l.code}>{l.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.regional.timezone')}</label>
                  <input
                    type="text"
                    value={formData.timezone}
                    onChange={(e) => handleInputChange('timezone', e.target.value)}
                    placeholder={t('pages.onboarding.steps.regional.timezonePlaceholder')}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('pages.onboarding.steps.regional.currency')}</label>
                  <select
                    value={formData.currency}
                    onChange={(e) => handleInputChange('currency', e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    required
                  >
                    {CURRENCIES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>💡 Tip:</strong> {t('pages.onboarding.steps.regional.tip')}
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Branding */}
          {step === 'branding' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('pages.onboarding.steps.branding.title')}</h2>
                <p className="text-gray-600">{t('pages.onboarding.steps.branding.subtitle')}</p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">{t('pages.onboarding.steps.branding.logoOptional')}</label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                    {logoPreview ? (
                      <div className="space-y-4">
                        <img src={logoPreview} alt="Logo preview" className="h-24 mx-auto object-contain" />
                        <button
                          type="button"
                          onClick={() => {
                            setLogoPreview(null)
                            setFormData(prev => ({ ...prev, logo: null }))
                          }}
                          className="text-sm text-red-600 hover:text-red-700"
                        >
                          {t('pages.onboarding.steps.branding.changeLogo')}
                        </button>
                      </div>
                    ) : (
                      <label className="cursor-pointer">
                        <div className="space-y-2">
                          <p className="text-2xl">📤</p>
                          <p className="text-sm font-medium text-gray-700">{t('pages.onboarding.steps.branding.uploadPrompt')}</p>
                          <p className="text-xs text-gray-500">{t('pages.onboarding.steps.branding.uploadHint')}</p>
                        </div>
                        <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                      </label>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t('pages.onboarding.steps.branding.primaryColor')}</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={formData.primary_color}
                        onChange={(e) => handleColorChange('primary_color', e.target.value)}
                        className="w-12 h-12 border border-gray-300 rounded-lg cursor-pointer"
                      />
                      <input
                        type="text"
                        value={formData.primary_color}
                        onChange={(e) => handleColorChange('primary_color', e.target.value)}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">{t('pages.onboarding.steps.branding.secondaryColor')}</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="color"
                        value={formData.secondary_color}
                        onChange={(e) => handleColorChange('secondary_color', e.target.value)}
                        className="w-12 h-12 border border-gray-300 rounded-lg cursor-pointer"
                      />
                      <input
                        type="text"
                        value={formData.secondary_color}
                        onChange={(e) => handleColorChange('secondary_color', e.target.value)}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                      />
                    </div>
                  </div>
                </div>

                <div className="p-4 rounded-lg" style={{ backgroundColor: formData.primary_color }}>
                  <p className="text-white text-center font-medium">{t('pages.onboarding.steps.branding.colorPreview')}</p>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Review */}
          {step === 'review' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('pages.onboarding.steps.review.title')}</h2>
                <p className="text-gray-600">{t('pages.onboarding.steps.review.subtitle')}</p>
              </div>

              <div className="space-y-4">
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">📋 {t('pages.onboarding.steps.review.companyInfo')}</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <p className="text-gray-600">{t('pages.onboarding.steps.review.company')}</p>
                    <p className="font-medium">{formData.company_name}</p>
                    <p className="text-gray-600">{t('pages.onboarding.steps.review.countryLabel')}</p>
                    <p className="font-medium">{formData.country_code}</p>
                    {formData.tax_id && (
                      <>
                        <p className="text-gray-600">{t('pages.onboarding.steps.review.taxIdLabel')}</p>
                        <p className="font-medium">{formData.tax_id}</p>
                      </>
                    )}
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">🌍 {t('pages.onboarding.steps.review.regionalConfig')}</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <p className="text-gray-600">{t('pages.onboarding.steps.review.languageLabel')}</p>
                    <p className="font-medium">{languageLabel}</p>
                    <p className="text-gray-600">{t('pages.onboarding.steps.review.timezoneLabel')}</p>
                    <p className="font-medium">{formData.timezone}</p>
                    <p className="text-gray-600">{t('pages.onboarding.steps.review.currencyLabel')}</p>
                    <p className="font-medium">{formData.currency}</p>
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-3">🎨 {t('pages.onboarding.steps.review.brandingSection')}</h3>
                  <div className="space-y-2 text-sm">
                    {logoPreview && <p>✓ {t('pages.onboarding.steps.review.logoLoaded')}</p>}
                    <div className="flex items-center gap-2">
                      <div
                        className="w-6 h-6 rounded"
                        style={{ backgroundColor: formData.primary_color }}
                      ></div>
                      <p>{t('pages.onboarding.steps.review.primaryColorLabel')} {formData.primary_color}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-6 h-6 rounded border border-gray-300"
                        style={{ backgroundColor: formData.secondary_color }}
                      ></div>
                      <p>{t('pages.onboarding.steps.review.secondaryColorLabel')} {formData.secondary_color}</p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-800">
                    <strong>✓</strong> {t('pages.onboarding.steps.review.allReady')}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex gap-3 mt-8">
            <button
              onClick={prevStep}
              disabled={step === 'info' || saving}
              className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('pages.onboarding.back')}
            </button>

            {step !== 'review' ? (
              <button
                onClick={nextStep}
                disabled={saving}
                className="ml-auto px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('pages.onboarding.next')}
              </button>
            ) : (
              <button
                onClick={onSubmit}
                disabled={saving}
                className="ml-auto px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? t('pages.onboarding.saving') : t('pages.onboarding.saveConfig')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
