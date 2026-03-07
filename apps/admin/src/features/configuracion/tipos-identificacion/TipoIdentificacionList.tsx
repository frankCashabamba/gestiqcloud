import React, { useEffect, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import { listTiposIdentificacion, removeTipoIdentificacion, type TipoIdentificacion } from '../../../services/configuracion/tipos-identificacion'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function TipoIdentificacionList() {
  const [items, setItems] = useState<TipoIdentificacion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listTiposIdentificacion())
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
        <h3 className="text-xl font-semibold">Tipos de identificación</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo</button>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        Catálogo global de tipos de documento de identidad por país (CEDULA, RUC, DNI, etc.).
        Estos tipos se asignan automáticamente a los tenants según su país.
      </p>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">País</th>
            <th className="text-left py-2 px-3">Código</th>
            <th className="text-left py-2 px-3">Etiqueta</th>
            <th className="text-left py-2 px-3">Estado</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2 px-3">
                <span className="bg-gray-100 text-gray-700 text-xs font-mono px-2 py-0.5 rounded">{it.country_code}</span>
              </td>
              <td className="py-2 px-3 font-mono font-medium">{it.code}</td>
              <td className="py-2 px-3">{it.label}</td>
              <td className="py-2 px-3">{it.active ? 'Activo' : 'Inactivo'}</td>
              <td className="py-2 px-3">
                <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async () => {
                  if (!confirm(`¿Eliminar "${it.code}" (${it.country_code})?`)) return
                  try {
                    await removeTipoIdentificacion(it.id)
                    setItems((prev) => prev.filter(x => x.id !== it.id))
                    success('Tipo de identificación eliminado')
                  } catch (e: any) { toastError(getErrorMessage(e)) }
                }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr><td className="py-3 px-3 text-gray-500" colSpan={5}>Sin tipos de identificación</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
