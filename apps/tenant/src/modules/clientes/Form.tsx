import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCliente, getCliente, updateCliente, type Cliente as C } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { apiFetch } from '../../lib/http'

type FieldCfg = { field: string; visible?: boolean; required?: boolean; ord?: number | null; label?: string | null; help?: string | null }

const FIELD_ALIASES: Record<string, string> = {
  nombre: 'name',
  telefono: 'phone',
  direccion: 'address',
  provincia: 'state',
}

const normalizeFieldId = (field: string) => FIELD_ALIASES[field] || field

export default function ClienteForm() {
  const { id, empresa } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Omit<C, 'id'>>>({ name: '', email: '', phone: '' })
  const { success, error } = useToast()
  const [fields, setFields] = useState<FieldCfg[] | null>(null)
  const [loadingCfg, setLoadingCfg] = useState(false)

  useEffect(() => {
    if (!id) return
    getCliente(id).then((x)=> setForm({ ...x }))
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

  const fieldList = useMemo(() => {
    const base: FieldCfg[] = [
      { field: 'name', visible: true, required: true, ord: 10, label: 'Nombre' },
      { field: 'email', visible: true, required: false, ord: 20, label: 'Email' },
      { field: 'phone', visible: true, required: false, ord: 21, label: 'Phone' },
    ]

    // Merge base configuration with remote overrides (if any) so required fields never disappear.
    const baseMap = new Map(base.map((cfg) => [cfg.field, cfg]))
    normalizedFields.forEach((cfg) => {
      if (cfg.visible === false) {
        baseMap.delete(cfg.field)
        return
      }
      const prev = baseMap.get(cfg.field) || {}
      baseMap.set(cfg.field, { ...prev, ...cfg })
    })

    return Array.from(baseMap.values()).sort((a, b) => (a.ord || 999) - (b.ord || 999))
  }, [normalizedFields])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      for (const f of (fieldList || [])) {
        if (f.required && f.visible !== false) {
          const val = (form as any)[f.field]
          if (val === undefined || val === null || String(val).trim() === '') {
            throw new Error(`El campo "${f.label || f.field}" es obligatorio`)
          }
        }
      }
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.email))) throw new Error('Email inválido')
      if (id) await updateCliente(id, form as any)
      else await createCliente(form as any)
      success('Cliente guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar cliente' : 'New Customer'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        {loadingCfg && <div className="text-sm text-gray-500">Cargando campos…</div>}
        {fieldList.map((f) => {
          const label = f.label || (f.field.charAt(0).toUpperCase() + f.field.slice(1).replace(/_/g, ' '))
          const type = f.field.toLowerCase().includes('email') ? 'email' : 'text'
          const value = (form as any)[f.field] ?? ''
          const isRequired = !!f.required && f.visible !== false
          return (
            <div key={f.field}>
              <label className="block mb-1">
                {label}
                {isRequired ? (
                  <span className="text-red-600 ml-1" aria-label="Obligatorio">
                    *
                  </span>
                ) : (
                  <span className="text-gray-500 ml-1 text-xs">(opcional)</span>
                )}
              </label>
              <input
                type={type}
                value={value}
                onChange={(e)=> setForm({ ...form, [f.field]: e.target.value })}
                className={`border px-2 py-1 w-full rounded ${isRequired ? 'border-gray-400' : 'border-gray-300'}`}
                required={isRequired}
                placeholder={f.help || ''}
              />
            </div>
          )
        })}
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
