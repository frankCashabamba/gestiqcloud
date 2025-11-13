import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listTipoEmpresa, removeTipoEmpresa, type TipoEmpresa } from '../../../services/configuracion/tipo-empresa'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function TipoEmpresaList() {
  const [items, setItems] = useState<TipoEmpresa[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        setItems(await listTipoEmpresa())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  return (
    <div style={{ padding: 16 }}>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xl font-semibold">Tipo de empresa</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo</button>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">Nombre</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2 px-3">{it.name}</td>
              <td className="py-2 px-3">
                <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button
                  className="text-red-700"
                  onClick={async () => {
                    if (!confirm('¿Eliminar?')) return
                    try {
                      await removeTipoEmpresa(it.id)
                      setItems((p) => p.filter((x) => x.id !== it.id))
                      success('Tipo de empresa eliminada')
                    } catch (e: any) {
                      toastError(getErrorMessage(e))
                    }
                  }}
                >
                  Eliminar
                </button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (
            <tr>
              <td className="py-3 px-3" colSpan={2}>
                Sin registros
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
