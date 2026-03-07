import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { getBranding, saveBranding, uploadBrandingLogo } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { SettingsBranding } from './types'
import { env } from '../../env'
import { invalidateCompanyThemeCache } from '../../services/theme'

function toAbsoluteAssetUrl(url?: string) {
  if (!url) return ''
  if (/^(https?:)?\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) return url
  const apiRoot = (env.apiUrl || '').replace(/\/+$/g, '').replace(/\/api(?:\/v1)?$/i, '')
  if (!apiRoot) return url
  return `${apiRoot}${url.startsWith('/') ? '' : '/'}${url}`
}

export default function BrandingSettings() {
  const { empresa } = useParams()
  const { t } = useTranslation(['settings', 'common'])
  const [form, setForm] = useState<SettingsBranding>({ colorPrimario: '#2563eb', colorSecundario: '#1e293b', logoUrl: '' })
  const [uploadingLogo, setUploadingLogo] = useState(false)
  const [saving, setSaving] = useState(false)
  const { success, error } = useToast()
  useEffect(() => { getBranding().then(setForm).catch(()=>{}) }, [])

  const logoPreview = toAbsoluteAssetUrl(form.logoUrl)

  async function onSelectLogo(file?: File | null) {
    if (!file) return
    try {
      setUploadingLogo(true)
      const logoPath = await uploadBrandingLogo(file)
      setForm((prev) => ({ ...prev, logoUrl: logoPath }))
      invalidateCompanyThemeCache(empresa)
      window.dispatchEvent(new Event('gc-theme-updated'))
      success(t('settings:branding.logoUploaded'))
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setUploadingLogo(false)
    }
  }

  async function onSave() {
    try {
      setSaving(true)
      await saveBranding(form)
      invalidateCompanyThemeCache(empresa)
      window.dispatchEvent(new Event('gc-theme-updated'))
      success(t('settings:branding.saved'))
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="gc-container py-6" style={{ maxWidth: 640 }}>
      <div className="gc-page-header mb-6">
        <div className="gc-page-header__text">
          <h1 className="gc-page-header__title">{t('settings:branding.title')}</h1>
          <p className="gc-page-header__subtitle">{t('settings:branding.subtitle', { defaultValue: 'Personaliza la apariencia de tu empresa' })}</p>
        </div>
      </div>

      <div className="gc-card space-y-6">
        {/* Color pickers */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="gc-field">
            <label className="gc-label">{t('settings:branding.primaryColor')}</label>
            <div className="flex items-center gap-3 mt-1">
              <input
                type="color"
                className="h-11 w-14 cursor-pointer rounded-lg border border-[var(--gc-border)]"
                value={form.colorPrimario || '#2563eb'}
                onChange={(e) => setForm({ ...form, colorPrimario: e.target.value })}
              />
              <input
                type="text"
                className="gc-input flex-1 font-mono text-sm"
                value={form.colorPrimario || '#2563eb'}
                onChange={(e) => setForm({ ...form, colorPrimario: e.target.value })}
                placeholder="#2563eb"
              />
            </div>
            <p className="gc-field-hint">{t('settings:branding.primaryColorHint', { defaultValue: 'Topbar, botones principales y links' })}</p>
          </div>

          <div className="gc-field">
            <label className="gc-label">{t('settings:branding.secondaryColor', { defaultValue: 'Color secundario' })}</label>
            <div className="flex items-center gap-3 mt-1">
              <input
                type="color"
                className="h-11 w-14 cursor-pointer rounded-lg border border-[var(--gc-border)]"
                value={form.colorSecundario || '#1e293b'}
                onChange={(e) => setForm({ ...form, colorSecundario: e.target.value })}
              />
              <input
                type="text"
                className="gc-input flex-1 font-mono text-sm"
                value={form.colorSecundario || '#1e293b'}
                onChange={(e) => setForm({ ...form, colorSecundario: e.target.value })}
                placeholder="#1e293b"
              />
            </div>
            <p className="gc-field-hint">{t('settings:branding.secondaryColorHint', { defaultValue: 'Acentos, gradientes y hovers' })}</p>
          </div>
        </div>

        {/* Live preview */}
        <div>
          <label className="gc-label mb-2">{t('settings:branding.preview', { defaultValue: 'Vista previa' })}</label>
          <div className="overflow-hidden rounded-xl border border-[var(--gc-border)]">
            <div
              className="flex h-14 items-center gap-3 px-4"
              style={{
                background: `linear-gradient(120deg, ${form.colorPrimario || '#2563eb'} 0%, ${form.colorSecundario || '#1e293b'} 100%)`,
                color: '#fff',
              }}
            >
              {logoPreview ? (
                <img src={logoPreview} alt="Logo" className="h-8 w-8 rounded-lg bg-white/20 object-contain" />
              ) : (
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/20 text-xs font-bold">GC</div>
              )}
              <span className="text-sm font-semibold">{empresa || 'Mi Empresa'}</span>
              <div className="ml-auto flex gap-2">
                <span className="rounded-lg bg-white/15 px-3 py-1 text-xs font-medium">Módulo</span>
                <span className="rounded-lg bg-white px-3 py-1 text-xs font-semibold" style={{ color: form.colorPrimario || '#2563eb' }}>Acción</span>
              </div>
            </div>
            <div className="bg-[var(--gc-bg)] p-4">
              <div className="flex gap-3">
                <div className="h-4 w-24 rounded" style={{ background: form.colorPrimario || '#2563eb', opacity: 0.2 }} />
                <div className="h-4 w-16 rounded" style={{ background: form.colorSecundario || '#1e293b', opacity: 0.15 }} />
              </div>
            </div>
          </div>
        </div>

        {/* Logo */}
        <div className="gc-field">
          <label className="gc-label">{t('settings:branding.logo')}</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="gc-input mt-1"
            onChange={(e) => onSelectLogo(e.target.files?.[0])}
            disabled={uploadingLogo}
          />
          <p className="gc-field-hint">{t('settings:branding.formats')}</p>
          {logoPreview ? (
            <div className="mt-3 gc-card flex items-center gap-4">
              <img src={logoPreview} alt="Logo empresa" className="h-12 w-auto object-contain" />
              <button
                type="button"
                className="text-sm font-medium text-[var(--gc-danger)] hover:underline"
                onClick={() => setForm((prev) => ({ ...prev, logoUrl: '' }))}
              >
                {t('settings:branding.removeLogo')}
              </button>
            </div>
          ) : null}
        </div>

        {/* Save */}
        <button
          className="gc-btn gc-btn--primary"
          onClick={onSave}
          disabled={saving || uploadingLogo}
        >
          {saving ? t('settings:branding.saving') : t('settings:branding.save')}
        </button>
      </div>
    </div>
  )
}
