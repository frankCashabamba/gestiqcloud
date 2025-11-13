import React, { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listSectores,
  removeSector,
  listTipoEmpresa,
  listTipoNegocio,
  type Sector,
} from '../../../services/configuracion/sectores'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function SectorList() {
  const [items, setItems] = useState<Sector[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [empresas, setEmpresas] = useState<Record<number, string>>({})
  const [negocios, setNegocios] = useState<Record<number, string>>({})
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [sectoresData, empresasData, negociosData] = await Promise.all([
          listSectores(),
          listTipoEmpresa(),
          listTipoNegocio(),
        ])
        setItems(sectoresData)
        setEmpresas(Object.fromEntries(empresasData.map((e) => [e.id, e.name])))
        setNegocios(Object.fromEntries(negociosData.map((n) => [n.id, n.name])))
        setError(null)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setError(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const getEmpresaNombre = useCallback(
    (id: number | null) => (id && empresas[id] ? empresas[id] : '—'),
    [empresas]
  )
  const getNegocioNombre = useCallback(
    (id: number | null) => (id && negocios[id] ? negocios[id] : '—'),
    [negocios]
  )

  return (
    <div style={{ padding: 16 }}>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xl font-semibold">Sectores</h3>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>
          Nuevo
        </button>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {error && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{error}</div>}
      <table className="min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">Nombre</th>
            <th className="text-left py-2 px-3">Tipo Empresa</th>
            <th className="text-left py-2 px-3">Tipo Negocio</th>
            <th className="text-left py-2 px-3">Branding</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => {
            const color = it.template_config?.branding?.color_primario
            return (
              <tr key={it.id} className="border-t">
                <td className="py-2 px-3">{it.sector_name}</td>
                <td className="py-2 px-3">{getEmpresaNombre(it.business_type_id)}</td>
                <td className="py-2 px-3">{getNegocioNombre(it.business_category_id)}</td>
                <td className="py-2 px-3">
                  {color ? (
                    <span className="inline-flex items-center gap-2">
                      <span
                        style={{
                          width: 18,
                          height: 18,
                          borderRadius: 4,
                          display: 'inline-block',
                          backgroundColor: color,
                          border: '1px solid #cbd5e1',
                        }}
                      />
                      <span>{color}</span>
                    </span>
                  ) : (
                    <span className="text-gray-400 text-sm">Sin definir</span>
                  )}
                </td>
                <td className="py-2 px-3">
                  <Link to={`${it.id}/editar`} className="text-blue-600 hover:underline mr-3">
                    Editar
                  </Link>
                  <button
                    className="text-red-700"
                    onClick={async () => {
                      if (!confirm('¿Eliminar sector?')) return
                      try {
                        await removeSector(it.id)
                        setItems((prev) => prev.filter((x) => x.id !== it.id))
                        success('Sector eliminado')
                      } catch (e: any) {
                        toastError(getErrorMessage(e))
                      }
                    }}
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            )
          })}
          {!loading && items.length === 0 && (
            <tr>
              <td className="py-3 px-3" colSpan={5}>
                Sin sectores
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
