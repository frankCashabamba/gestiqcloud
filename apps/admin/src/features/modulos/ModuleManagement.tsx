import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listModulos, removeModulo, toggleModulo, registrarModulosFS, type Modulo } from '../../services/modulos'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function ModuleManagement() {
  const [modulos, setModulos] = useState<Modulo[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { success, error: toastError } = useToast()
  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const data = await listModulos()
        setModulos(data)
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <h2>Gestión de Módulos</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="bg-gray-200 px-3 py-2 rounded"
            onClick={async () => {
              try {
                setLoading(true)
                const res = await registrarModulosFS()
                const data = await listModulos()
                setModulos(data)
                const reg = res.registrados?.length || 0
                const dup = res.ya_existentes?.length || 0
                const ign = res.ignorados?.length || 0
                success(`Registrados: ${reg}, existentes: ${dup}, ignorados: ${ign}`)
              } catch(e:any) {
                toastError(getErrorMessage(e))
              } finally {
                setLoading(false)
              }
            }}
          >
            Detectar desde FS
          </button>
          <Link to="crear" className="bg-blue-600 text-white px-3 py-2 rounded">Crear módulo</Link>
        </div>
      </div>
      {loading && <div className="text-sm text-gray-500 mt-2">Cargando módulos…</div>}
      {error && <div className="mt-2 bg-red-100 text-red-700 px-3 py-2 rounded">{error}</div>}
      <table className="mt-4 min-w-full bg-white border border-gray-200 rounded">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left py-2 px-3">Nombre</th>
            <th className="text-left py-2 px-3">Icono</th>
            <th className="text-left py-2 px-3">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {modulos.map((m) => (
            <tr key={m.id} className="border-t">
              <td className="py-2 px-3">{m.nombre}</td>
              <td className="py-2 px-3">{m.icono || '-'}</td>
              <td className="py-2 px-3">
                <Link to={`editar/${m.id}`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                {m.activo ? (
                  <button className="text-yellow-700 mr-3" onClick={async () => {
                    try {
                      const res = await toggleModulo(m.id, false)
                      setModulos((prev) => prev.map(x => x.id === m.id ? { ...x, activo: res.activo } : x))
                      success('Módulo desactivado')
                    } catch(e:any) { toastError(getErrorMessage(e)) }
                  }}>Desactivar</button>
                ) : (
                  <button className="text-green-700 mr-3" onClick={async () => {
                    try {
                      const res = await toggleModulo(m.id, true)
                      setModulos((prev) => prev.map(x => x.id === m.id ? { ...x, activo: res.activo } : x))
                      success('Módulo activado')
                    } catch(e:any) { toastError(getErrorMessage(e)) }
                  }}>Activar</button>
                )}
                <button className="text-red-700" onClick={async () => {
                  if (!confirm('¿Eliminar módulo?')) return
                  try {
                    await removeModulo(m.id)
                    setModulos((prev) => prev.filter(x => x.id !== m.id))
                    success('Módulo eliminado')
                  } catch(e:any) { toastError(getErrorMessage(e)) }
                }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && modulos.length === 0 && (
            <tr><td className="py-3 px-3" colSpan={5}>Sin módulos por ahora</td></tr>
          )}
        </tbody>
      </table>
      <div className="mt-4">
        <Link to="asignaciones" className="text-sm text-blue-700">Ver asignaciones</Link>
      </div>
    </div>
  )
}


