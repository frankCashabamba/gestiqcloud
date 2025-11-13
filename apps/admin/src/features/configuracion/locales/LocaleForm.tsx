import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createLocale, getLocale, updateLocale, type Locale } from '../../../services/configuracion/locales'

export default function LocaleForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const isEdit = !!id
  const [form, setForm] = useState<Locale>({ code: '', name: '', active: true })
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit) return
    ;(async () => {
      try { setLoading(true); const data = await getLocale(id as string); setForm(data) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
    })()
  }, [id])

  async function save() {
    setMsg(null); setLoading(true)
    try {
      const payload = { ...form, code: String(form.code||'').trim() }
      if (!payload.code) throw new Error('Código requerido')
      if (isEdit) await updateLocale(id as string, payload as any)
      else await createLocale(payload as any)
      nav('..')
    } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }

  return (
    <div className="admin-form">
      <h2 style={{ marginTop: 0 }}>{isEdit ? 'Editar Locale' : 'Nuevo Locale'}</h2>
      {msg && <div className="notice">{msg}</div>}
      <div className="grid" style={{ gap: 12, maxWidth: 520 }}>
        <label>Código
          <input className="input" value={form.code} onChange={(e)=> setForm(prev=> ({...prev, code: e.target.value}))} disabled={isEdit} />
        </label>
        <label>Nombre
          <input className="input" value={form.name} onChange={(e)=> setForm(prev=> ({...prev, name: e.target.value}))} />
        </label>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={form.active !== false} onChange={(e)=> setForm(prev=> ({...prev, active: e.target.checked}))} /> Activo
        </label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="gc-button gc-button--primary" onClick={save} disabled={loading}>Guardar</button>
        <button className="gc-button" onClick={()=> nav('..')} disabled={loading} style={{ marginLeft: 8 }}>Cancelar</button>
      </div>
    </div>
  )
}

