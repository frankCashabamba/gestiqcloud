import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createCliente, getCliente, updateCliente, type Cliente as C } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { type FieldCfg, mergeFieldConfig, getFieldType, renderDynamicField } from '../../hooks/useFieldConfig'
import { useDocumentIDTypes } from '../../hooks/useDocumentIDTypes'
import { BackButton } from '@ui'

const FIELD_ALIASES: Record<string, string> = {
  nombre: 'name',
  telefono: 'phone',
  direccion: 'address',
  provincia: 'state',
}

const normalizeFieldId = (field: string) => FIELD_ALIASES[field] || field

// Campos que van en la sección de contacto principal
const CONTACT_FIELDS = new Set(['name', 'email', 'phone'])
// Campos que van en opciones comerciales
const COMMERCIAL_FIELDS = new Set(['is_wholesale', 'payment_terms_days', 'credit_limit', 'descuento_pct'])

export default function ClienteForm() {
  const { t } = useTranslation(['customers', 'common'])
  const { id, empresa } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Omit<C, 'id'>>>({ name: '', email: '', phone: '', is_wholesale: false })
  const [busy, setBusy] = useState(false)
  const { success, error } = useToast()
  const [fields, setFields] = useState<FieldCfg[] | null>(null)
  const [loadingCfg, setLoadingCfg] = useState(false)
  const { data: idTypes } = useDocumentIDTypes({})

  useEffect(() => {
    if (!id) return
    getCliente(id).then((x) => setForm({ ...x }))
  }, [id])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoadingCfg(true)
        const q = new URLSearchParams({ module: 'customers', ...(empresa ? { empresa } : {}) }).toString()
        const data = await apiFetch<{ items?: FieldCfg[] }>(`/api/v1/company/settings/fields?${q}`)
        if (!cancelled) setFields((data?.items || []).filter(it => it.visible !== false))
      } catch {
        if (!cancelled) setFields(null)
      } finally {
        if (!cancelled) setLoadingCfg(false)
      }
    })()
    return () => { cancelled = true }
  }, [empresa])

  const normalizedFields = useMemo(() =>
    (fields || []).map((cfg) => ({ ...cfg, field: normalizeFieldId(cfg.field) })),
    [fields]
  )

  const MANUAL_FIELDS = new Set(['identificacion', 'identificacion_tipo', 'tax_id', 'tax_id_type'])

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'name',         visible: true, required: true,  ord: 10, label: t('customers:form.name'),      field_type: 'text' },
      { field: 'email',        visible: true, required: false, ord: 20, label: t('customers:form.email'),     field_type: 'email' },
      { field: 'phone',        visible: true, required: false, ord: 21, label: t('customers:form.phone'),     field_type: 'text' },
      { field: 'is_wholesale', visible: true, required: false, ord: 40, label: t('customers:form.wholesale'), field_type: 'boolean' },
    ]
    return mergeFieldConfig(base, normalizedFields).filter(f => !MANUAL_FIELDS.has(f.field))
  }, [normalizedFields])

  const contactFields   = useMemo(() => fieldList.filter(f => CONTACT_FIELDS.has(f.field)), [fieldList])
  const commercialFields = useMemo(() => fieldList.filter(f => COMMERCIAL_FIELDS.has(f.field)), [fieldList])
  const otherFields     = useMemo(() => fieldList.filter(f => !CONTACT_FIELDS.has(f.field) && !COMMERCIAL_FIELDS.has(f.field)), [fieldList])

  const handleFieldChange = (field: string, value: unknown) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      setBusy(true)
      if (!((form as any).identificacion_tipo || '').trim()) {
        throw new Error(t('customers:form.fieldRequired', { field: t('customers:form.idType', { defaultValue: 'Tipo de identificación' }) }))
      }
      if (!((form as any).identificacion || '').trim()) {
        throw new Error(t('customers:form.fieldRequired', { field: t('customers:form.identification', { defaultValue: 'Identificación' }) }))
      }
      for (const f of fieldList) {
        if (f.required && f.visible !== false) {
          const val = (form as any)[f.field]
          if (val === undefined || val === null || String(val).trim() === '') {
            throw new Error(t('customers:form.fieldRequired', { field: f.label || f.field }))
          }
        }
      }
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.email))) {
        throw new Error(t('customers:form.invalidEmail'))
      }
      if (id) await updateCliente(id, form as any)
      else await createCliente(form as any)
      success(t('customers:form.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="p-4 max-w-2xl mx-auto">

      {/* Header */}
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex items-center gap-3 mb-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            {id ? t('customers:form.edit') : t('customers:form.new')}
          </h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {id ? t('customers:form.editSubtitle', 'Modifica los datos del cliente') : t('customers:form.newSubtitle', 'Completa los datos para registrar un nuevo cliente')}
          </p>
        </div>
      </div>

      {loadingCfg && (
        <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
          <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          {t('customers:form.loadingFields')}
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-5">

        {/* Identificación */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
            </svg>
            {t('customers:form.sectionId', 'Identificación')}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">
                {t('customers:form.idType', { defaultValue: 'Tipo de identificación' })}
                <span className="text-rose-500 ml-1">*</span>
              </label>
              <select
                value={(form as any).identificacion_tipo || ''}
                onChange={(e) => setForm(prev => ({ ...prev, identificacion_tipo: e.target.value }))}
                className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
                required
                disabled={busy}
              >
                <option value="">{t('common:select', { defaultValue: 'Seleccionar...' })}</option>
                {idTypes.map((it) => (
                  <option key={it.code} value={it.code}>{it.name_es || it.name_en} ({it.code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">
                {t('customers:form.identification', { defaultValue: 'Número de identificación' })}
                <span className="text-rose-500 ml-1">*</span>
              </label>
              <input
                type="text"
                value={(form as any).identificacion || ''}
                onChange={(e) => setForm(prev => ({ ...prev, identificacion: e.target.value }))}
                className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="Ej: 12345678A"
                required
                disabled={busy}
              />
            </div>
          </div>
        </div>

        {/* Contacto */}
        {contactFields.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              {t('customers:form.sectionContact', 'Datos de contacto')}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {contactFields.map((f) => {
                const label = f.label || f.field
                const value = (form as any)[f.field] ?? ''
                const isRequired = !!f.required && f.visible !== false
                return (
                  <div key={f.field} className={f.field === 'name' ? 'sm:col-span-2' : ''}>
                    <label className="block text-sm font-medium text-slate-600 mb-1.5">
                      {label}
                      {isRequired
                        ? <span className="text-rose-500 ml-1">*</span>
                        : <span className="text-slate-400 ml-1 text-xs">({t('customers:form.optional')})</span>
                      }
                    </label>
                    <div className="[&_input]:w-full [&_input]:border [&_input]:border-slate-200 [&_input]:rounded-xl [&_input]:px-3 [&_input]:py-2 [&_input]:text-sm [&_input]:focus:outline-none [&_input]:focus:ring-2 [&_input]:focus:ring-blue-400 [&_select]:w-full [&_select]:border [&_select]:border-slate-200 [&_select]:rounded-xl [&_select]:px-3 [&_select]:py-2 [&_select]:text-sm [&_select]:bg-white [&_select]:focus:outline-none [&_select]:focus:ring-2 [&_select]:focus:ring-blue-400">
                      {renderDynamicField(f, value, handleFieldChange)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Campos adicionales dinámicos */}
        {otherFields.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {t('customers:form.sectionExtra', 'Información adicional')}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {otherFields.map((f) => {
                const label = f.label || f.field
                const value = (form as any)[f.field] ?? ''
                const isRequired = !!f.required && f.visible !== false
                const fieldType = getFieldType(f)
                return (
                  <div key={f.field}>
                    {fieldType !== 'boolean' && (
                      <label className="block text-sm font-medium text-slate-600 mb-1.5">
                        {label}
                        {isRequired
                          ? <span className="text-rose-500 ml-1">*</span>
                          : <span className="text-slate-400 ml-1 text-xs">({t('customers:form.optional')})</span>
                        }
                      </label>
                    )}
                    <div className="[&_input]:w-full [&_input]:border [&_input]:border-slate-200 [&_input]:rounded-xl [&_input]:px-3 [&_input]:py-2 [&_input]:text-sm [&_input]:focus:outline-none [&_input]:focus:ring-2 [&_input]:focus:ring-blue-400 [&_select]:w-full [&_select]:border [&_select]:border-slate-200 [&_select]:rounded-xl [&_select]:px-3 [&_select]:py-2 [&_select]:text-sm [&_select]:bg-white [&_textarea]:w-full [&_textarea]:border [&_textarea]:border-slate-200 [&_textarea]:rounded-xl [&_textarea]:px-3 [&_textarea]:py-2 [&_textarea]:text-sm">
                      {renderDynamicField(f, value, handleFieldChange)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Opciones comerciales */}
        {commercialFields.length > 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              {t('customers:form.sectionCommercial', 'Opciones comerciales')}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {commercialFields.map((f) => {
                const label = f.label || f.field
                const value = (form as any)[f.field] ?? ''
                const fieldType = getFieldType(f)
                if (fieldType === 'boolean') {
                  return (
                    <label key={f.field} className="flex items-center gap-3 cursor-pointer select-none col-span-full">
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={!!value}
                          onChange={(e) => handleFieldChange(f.field, e.target.checked)}
                          className="sr-only peer"
                          disabled={busy}
                        />
                        <div className="w-10 h-6 bg-slate-200 rounded-full peer-checked:bg-blue-600 transition-colors" />
                        <div className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
                      </div>
                      <span className="text-sm font-medium text-slate-700">{label}</span>
                    </label>
                  )
                }
                return (
                  <div key={f.field}>
                    <label className="block text-sm font-medium text-slate-600 mb-1.5">{label}</label>
                    <div className="[&_input]:w-full [&_input]:border [&_input]:border-slate-200 [&_input]:rounded-xl [&_input]:px-3 [&_input]:py-2 [&_input]:text-sm [&_input]:focus:outline-none [&_input]:focus:ring-2 [&_input]:focus:ring-blue-400">
                      {renderDynamicField(f, value, handleFieldChange)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Acciones */}
        <div className="flex items-center gap-3 pt-1 pb-4">
          <button
            type="submit"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-5 py-2.5 rounded-xl font-semibold text-sm shadow-sm transition-colors"
            disabled={busy}
          >
            {busy && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
            {busy ? t('common:saving', 'Guardando…') : t('customers:form.save')}
          </button>
          <button
            type="button"
            className="px-5 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            onClick={() => nav('..')}
            disabled={busy}
          >
            {t('customers:form.cancel')}
          </button>
        </div>

      </form>
    </div>
  )
}
