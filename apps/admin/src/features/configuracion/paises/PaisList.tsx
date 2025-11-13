import React, { useEffect, useState } from 'react'
import { listPaises, removePais, type Pais } from '../../../services/configuracion/paises'
import { Link } from 'react-router-dom'

export default function PaisList() {
  const [items, setItems] = useState<Pais[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try { setItems(await listPaises()) } catch (e: any) { setMsg(e?.message || 'Error') } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function del(id: number) {
    if (!confirm('¿Eliminar país?')) return
    await removePais(id)
    setItems(prev => prev.filter(x => x.id !== id))
  }

  return (
    <div className="admin-list">
      <div className="admin-list__header">
        <h2>Países</h2>
        <Link to="nuevo" className="gc-button gc-button--primary">Nuevo</Link>
      </div>
      {msg && <div className="notice">{msg}</div>}
      {loading ? 'Cargando…' : (
        <table className="min-w-full text-sm">
          <thead><tr><th>Código</th><th>Nombre</th><th>Activo</th><th></th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={4}>Sin países</td></tr>}
            {items.map((it) => (
              <tr key={it.id}>
                <td>{it.code}</td>
                <td>{it.name}</td>
                <td>{it.active ? 'Sí' : 'No'}</td>
                <td style={{ textAlign: 'right' }}>
                  <Link to={`${it.id}/editar`} className="gc-button">Editar</Link>
                  <button className="gc-button" onClick={() => del(it.id)}>Eliminar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
