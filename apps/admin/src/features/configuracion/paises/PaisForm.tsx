import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createPais, getPais, updatePais, type Pais } from '../../../services/configuracion/paises'

export default function PaisForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const isEdit = !!id
  const [form, setForm] = useState<Partial<Pais>>({ code: '', name: '', active: true })
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!isEdit) return
    ;(async () => {
      try { setLoading(true); const data = await getPais(id as string); setForm(data) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
    })()
  }, [id])

  async function save() {
    setMsg(null); setLoading(true)
    try {
      const payload = { code: String(form.code||'').toUpperCase(), name: String(form.name||''), active: !!form.active }
      if (isEdit) await updatePais(id as string, payload as any)
      else await createPais(payload as any)
      nav('..')
    } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }

  return (
    <div className="admin-form">
      <h2 style={{ marginTop: 0 }}>{isEdit ? 'Editar País' : 'Nuevo País'}</h2>
      {msg && <div className="notice">{msg}</div>}
      <div className="grid" style={{ gap: 12, maxWidth: 480 }}>
        <label>Código (ISO2)
          <input className="input" value={form.code||''} onChange={(e)=> setForm(prev=> ({...prev, code: e.target.value}))} />
        </label>
        <label>Nombre
          <input className="input" value={form.name||''} onChange={(e)=> setForm(prev=> ({...prev, name: e.target.value}))} />
        </label>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <input type="checkbox" checked={!!form.active} onChange={(e)=> setForm(prev=> ({...prev, active: e.target.checked}))} /> Activo
        </label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="gc-button gc-button--primary" onClick={save} disabled={loading}>Guardar</button>
        <button className="gc-button" onClick={()=> nav('..')} disabled={loading} style={{ marginLeft: 8 }}>Cancelar</button>
      </div>
    </div>
  )
}

