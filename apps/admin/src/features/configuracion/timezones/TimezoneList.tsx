import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTimezones, removeTimezone, type Timezone } from '../../../services/configuracion/timezones'

export default function TimezoneList() {
  const [items, setItems] = useState<Timezone[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try { setItems(await listTimezones()) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function del(name: string) {
    if (!confirm('¿Eliminar timezone?')) return
    await removeTimezone(name)
    setItems(prev => prev.filter(x => x.name !== name))
  }

  return (
    <div className="admin-list">
      <div className="admin-list__header">
        <h2>Timezones</h2>
        <Link to="nuevo" className="gc-button gc-button--primary">Nuevo</Link>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {loading ? 'Cargando…' : (
        <table className="min-w-full text-sm">
          <thead><tr><th>Nombre</th><th>Mostrar</th><th>Offset</th><th>Activo</th><th></th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={5}>Sin timezones</td></tr>}
            {items.map((it) => (
              <tr key={it.name}>
                <td>{it.name}</td>
                <td>{it.display_name}</td>
                <td>{it.offset_minutes ?? ''}</td>
                <td>{it.active !== false ? 'Sí' : 'No'}</td>
                <td style={{ textAlign: 'right' }}>
                  <Link to={`${encodeURIComponent(it.name)}/editar`} className="gc-button">Editar</Link>
                  <button className="gc-button" onClick={() => del(it.name)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
