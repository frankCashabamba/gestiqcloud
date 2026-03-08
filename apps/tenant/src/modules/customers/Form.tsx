import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { createCliente, getCliente, updateCliente, type Cliente as C } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'
import { type FieldCfg, mergeFieldConfig, getFieldType, renderDynamicField } from '../../hooks/useFieldConfig'
import { useDocumentIDTypes } from '../../hooks/useDocumentIDTypes'

const FIELD_ALIASES: Record<string, string> = {
  nombre: 'name',
  telefono: 'phone',
  direccion: 'address',
  provincia: 'state',
}

const normalizeFieldId = (field: string) => FIELD_ALIASES[field] || field

export default function ClienteForm() {
  const { t } = useTranslation(['customers', 'common'])
  const { id, empresa } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Omit<C, 'id'>>>({ name: '', email: '', phone: '', is_wholesale: false })
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
        const q = new URLSearchParams({ module: 'clientes', ...(empresa ? { empresa } : {}) }).toString()
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

  const normalizedFields = useMemo(() => {
    return (fields || []).map((cfg) => ({
      ...cfg,
      field: normalizeFieldId(cfg.field),
    }))
  }, [fields])

  // Campos gestionados manualmente — excluir del sistema dinámico para evitar duplicados
  const MANUAL_FIELDS = new Set(['identificacion', 'identificacion_tipo', 'tax_id', 'tax_id_type'])

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'name', visible: true, required: true, ord: 10, label: t('customers:form.name'), field_type: 'text' },
      { field: 'email', visible: true, required: false, ord: 20, label: t('customers:form.email'), field_type: 'email' },
      { field: 'phone', visible: true, required: false, ord: 21, label: t('customers:form.phone'), field_type: 'text' },
      { field: 'is_wholesale', visible: true, required: false, ord: 40, label: t('customers:form.wholesale'), field_type: 'boolean' },
    ]
    return mergeFieldConfig(base, normalizedFields).filter(f => !MANUAL_FIELDS.has(f.field))
  }, [normalizedFields])

  const handleFieldChange = (field: string, value: unknown) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
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
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.email))) throw new Error(t('customers:form.invalidEmail'))
      if (id) await updateCliente(id, form as any)
      else await createCliente(form as any)
      success(t('customers:form.saved'))
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="gc-container py-6">
      <h3 className="text-xl font-semibold mb-3">{id ? t('customers:form.edit') : t('customers:form.new')}</h3>
      <form onSubmit={onSubmit} className="space-y-4 max-w-xl">
        {loadingCfg && <div className="text-sm text-slate-500">{t('customers:form.loadingFields')}</div>}

        {/* Tipo de identificación — obligatorio, cargado desde catálogo del país */}
        <div>
          <label className="gc-label">
            {t('customers:form.idType', { defaultValue: 'Tipo de identificación' })}
            <span className="text-red-600 ml-1">*</span>
          </label>
          <select
            value={(form as any).identificacion_tipo || ''}
            onChange={(e) => setForm(prev => ({ ...prev, identificacion_tipo: e.target.value }))}
            className="gc-input w-full"
            required
          >
            <option value="">{t('common:select', { defaultValue: 'Seleccionar...' })}</option>
            {idTypes.map((t) => (
              <option key={t.code} value={t.code}>{t.name_es || t.name_en} ({t.code})</option>
            ))}
          </select>
        </div>

        {/* Número de identificación — obligatorio */}
        <div>
          <label className="gc-label">
            {t('customers:form.identification', { defaultValue: 'Identificación' })}
            <span className="text-red-600 ml-1">*</span>
          </label>
          <input
            type="text"
            value={(form as any).identificacion || ''}
            onChange={(e) => setForm(prev => ({ ...prev, identificacion: e.target.value }))}
            className="gc-input w-full"
            required
          />
        </div>

        {fieldList.map((f) => {
          const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
          const value = (form as any)[f.field] ?? ''
          const isRequired = !!f.required && f.visible !== false
          const fieldType = getFieldType(f)

          return (
            <div key={f.field}>
              {fieldType !== 'boolean' && (
                <label className="gc-label">
                  {label}
                  {isRequired ? (
                    <span className="text-red-600 ml-1" aria-label={t('customers:form.required')}>*</span>
                  ) : (
                    <span className="text-slate-500 ml-1 text-xs">({t('customers:form.optional')})</span>
                  )}
                </label>
              )}
              {fieldType === 'boolean' && (
                <label className="gc-label">{label}</label>
              )}
              {renderDynamicField(f, value, handleFieldChange)}
            </div>
          )
        })}
        <div className="pt-2">
          <button type="submit" className="gc-btn gc-btn--primary">{t('customers:form.save')}</button>
          <button type="button" className="gc-btn gc-btn--ghost" onClick={() => nav('..')}>{t('customers:form.cancel')}</button>
        </div>
      </form>
    </div>
  )
}
