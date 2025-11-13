import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createTimezone, getTimezone, updateTimezone, type Timezone } from '../../../services/configuracion/timezones'

export default function TimezoneForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const isEdit = !!id
  const [form, setForm] = useState<Timezone>({ name: '', display_name: '', offset_minutes: 0, active: true })
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit) return
    ;(async () => {
      try { setLoading(true); const data = await getTimezone(id as string); setForm(data) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
    })()
  }, [id])

  async function save() {
    setMsg(null); setLoading(true)
    try {
      const payload = { ...form, name: String(form.name||'').trim() }
      if (!payload.name) throw new Error('Nombre requerido')
      if (isEdit) await updateTimezone(id as string, payload as any)
      else await createTimezone(payload as any)
      nav('..')
    } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }

  return (
    <div className="admin-form">
      <h2 style={{ marginTop: 0 }}>{isEdit ? 'Editar Timezone' : 'Nuevo Timezone'}</h2>
      {msg && <div className="notice">{msg}</div>}
      <div className="grid" style={{ gap: 12, maxWidth: 520 }}>
        <label>Nombre (ID)
          <input className="input" value={form.name} onChange={(e)=> setForm(prev=> ({...prev, name: e.target.value}))} disabled={isEdit} />
        </label>
        <label>Mostrar como
          <input className="input" value={form.display_name} onChange={(e)=> setForm(prev=> ({...prev, display_name: e.target.value}))} />
        </label>
        <label>Offset (minutos)
          <input className="input" type="number" value={form.offset_minutes ?? 0} onChange={(e)=> setForm(prev=> ({...prev, offset_minutes: Number(e.target.value)}))} />
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

