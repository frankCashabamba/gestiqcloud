import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listLocales, removeLocale, type Locale } from '../../../services/configuracion/locales'

export default function LocaleList() {
  const [items, setItems] = useState<Locale[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try { setItems(await listLocales()) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function del(code: string) {
    if (!confirm('¿Eliminar locale?')) return
    await removeLocale(code)
    setItems(prev => prev.filter(x => x.code !== code))
  }

  return (
    <div className="admin-list">
      <div className="admin-list__header">
        <h2>Locales</h2>
        <Link to="nuevo" className="gc-button gc-button--primary">Nuevo</Link>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {loading ? 'Cargando…' : (
        <table className="min-w-full text-sm">
          <thead><tr><th>Código</th><th>Nombre</th><th>Activo</th><th></th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={4}>Sin locales</td></tr>}
            {items.map((it) => (
              <tr key={it.code}>
                <td>{it.code}</td>
                <td>{it.name}</td>
                <td>{it.active !== false ? 'Sí' : 'No'}</td>
                <td style={{ textAlign: 'right' }}>
                  <Link to={`${encodeURIComponent(it.code)}/editar`} className="gc-button">Editar</Link>
                  <button className="gc-button" onClick={() => del(it.code)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
