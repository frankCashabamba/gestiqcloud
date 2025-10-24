import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listMonedas, removeMoneda, type Moneda } from '../../../services/configuracion/monedas'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function MonedaList() {
  const [items, setItems] = useState<Moneda[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        setItems(await listMonedas())
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
        <h3 className="text-xl font-semibold">Monedas</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nueva</button>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">Código</th>
            <th className="text-left py-2 px-3">Nombre</th>
            <th className="text-left py-2 px-3">Símbolo</th>
            <th className="text-left py-2 px-3">Estado</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2 px-3">{it.codigo}</td>
              <td className="py-2 px-3">{it.nombre}</td>
              <td className="py-2 px-3">{it.simbolo}</td>
              <td className="py-2 px-3">{it.activo ? 'Activo' : 'Inactivo'}</td>
              <td className="py-2 px-3">
                <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async () => {
                  if (!confirm('¿Eliminar moneda?')) return
                  try {
                    await removeMoneda(it.id)
                    setItems((prev) => prev.filter(x => x.id !== it.id))
                    success('Moneda eliminada')
                  } catch(e:any) { toastError(getErrorMessage(e)) }
                }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr><td className="py-3 px-3" colSpan={5}>Sin monedas</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
