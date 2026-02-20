import React, { useEffect, useState } from 'react'
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
  const [form, setForm] = useState<SettingsBranding>({ colorPrimario: '#0f172a', logoUrl: '' })
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
      success('Logo subido correctamente')
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
      success('Branding guardado')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-4" style={{ maxWidth: 640 }}>
      <h2 className="font-semibold text-lg mb-3">Branding</h2>
      <div className="space-y-3">
        <div>
          <label className="block mb-1">Color primario</label>
          <input
            type="color"
            className="border px-2 py-1 rounded"
            value={form.colorPrimario || '#0f172a'}
            onChange={(e) => setForm({ ...form, colorPrimario: e.target.value })}
          />
        </div>
        <div>
          <label className="block mb-1">Logo</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="border px-2 py-1 w-full rounded bg-white"
            onChange={(e) => onSelectLogo(e.target.files?.[0])}
            disabled={uploadingLogo}
          />
          <p className="mt-1 text-xs text-slate-500">Formatos: PNG, JPG, WEBP</p>
          {logoPreview ? (
            <div className="mt-3 rounded-lg border bg-white p-3">
              <p className="mb-2 text-sm font-medium text-slate-700">Vista previa</p>
              <img src={logoPreview} alt="Logo empresa" className="h-12 w-auto object-contain" />
            </div>
          ) : null}
          {form.logoUrl ? (
            <button
              type="button"
              className="mt-2 text-sm text-red-600 hover:text-red-700"
              onClick={() => setForm((prev) => ({ ...prev, logoUrl: '' }))}
            >
              Quitar logo
            </button>
          ) : null}
        </div>
        <button
          className="bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-60"
          onClick={onSave}
          disabled={saving || uploadingLogo}
        >
          {saving ? 'Guardando...' : 'Guardar'}
        </button>
      </div>
    </div>
  )
}
