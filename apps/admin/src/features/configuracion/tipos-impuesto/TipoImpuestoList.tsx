import React, { useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import { listTiposImpuesto, removeTipoImpuesto, type TipoImpuesto } from '../../../services/configuracion/tipos-impuesto'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function TipoImpuestoList() {
  const [items, setItems] = useState<TipoImpuesto[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listTiposImpuesto())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setError(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <div style={{ padding: 16 }}>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xl font-semibold">Tipos de impuesto</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo</button>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">País</th>
            <th className="text-left py-2 px-3">Código</th>
            <th className="text-left py-2 px-3">Nombre</th>
            <th className="text-left py-2 px-3">Tasa</th>
            <th className="text-left py-2 px-3">Estado</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2 px-3">{it.country_code}</td>
              <td className="py-2 px-3">{it.code}</td>
              <td className="py-2 px-3">{it.name}</td>
              <td className="py-2 px-3">{it.rate_default != null ? `${it.rate_default}%` : ''}</td>
              <td className="py-2 px-3">{it.active ? 'Activo' : 'Inactivo'}</td>
              <td className="py-2 px-3">
                <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async () => {
                  if (!confirm('¿Eliminar tipo de impuesto?')) return
                  try {
                    await removeTipoImpuesto(it.id)
                    setItems((prev) => prev.filter(x => x.id !== it.id))
                    success('Tipo de impuesto eliminado')
                  } catch(e:any) { toastError(getErrorMessage(e)) }
                }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr><td className="py-3 px-3" colSpan={6}>Sin tipos de impuesto</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
