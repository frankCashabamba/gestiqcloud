import React, { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { listEmpresaModulos, listModulosPublicos, upsertEmpresaModulo, removeEmpresaModulo } from '../services/modulos'
import type { CompanyModule, Module } from '../modulos/types'
import { useToast, getErrorMessage } from '../shared/toast'

export function EmpresaModulos() {
  const { id } = useParams()
  const empresaId = id as string
  const { success, error } = useToast()

  const [loading, setLoading] = useState(true)
  const [catalogo, setCatalogo] = useState<Module[]>([])
  const [asignados, setAsignados] = useState<CompanyModule[]>([])
  const [seleccion, setSeleccion] = useState<string>('')

  const asignadosIds = useMemo(() => new Set(asignados.map(a => a.module_id)), [asignados])
  const candidatos = useMemo(() => catalogo.filter(m => !asignadosIds.has(m.id)), [catalogo, asignadosIds])

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const [mods, empMods] = await Promise.all([
          listModulosPublicos(),
          listEmpresaModulos(empresaId),
        ])
        const moduloLookup = new Map(mods.map(m => [m.id, m]))
        const enrichedAsignados = empMods.map((registro: any) => {
          if (registro.module?.name) return registro
          const moduloInfo = moduloLookup.get(registro.module_id)
          return moduloInfo ? { ...registro, module: moduloInfo } : registro
        })
        setCatalogo(mods)
        setAsignados(enrichedAsignados)
      } catch (e: any) {
        error(getErrorMessage(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [empresaId])

  const onAgregar = async () => {
    if (!seleccion) return
    try {
      const moduloId = seleccion
      await upsertEmpresaModulo(empresaId, moduloId)
      const nuevo = catalogo.find(m => m.id === moduloId)
      if (nuevo) {
        setAsignados(prev => [
          ...prev,
          {
            id: Date.now(),
            tenant_id: empresaId,
            active: true,
            module_id: moduloId,
            module: nuevo,
          } as any,
        ])
      }
      setSeleccion('')
      success('Módulo asignado')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  const onEliminar = async (moduloId: number | string) => {
    if (!confirm('¿Eliminar módulo de la empresa?')) return
    try {
      await removeEmpresaModulo(empresaId, moduloId)
      setAsignados(prev => prev.filter(x => x.module_id !== moduloId))
      success('Módulo eliminado')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Módulos de la Empresa</h2>
        <Link to="/admin/empresas" className="text-sm text-blue-600">Volver</Link>
      </div>

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}

      {!loading && (
        <>
          <div className="flex gap-2 items-end mb-4">
            <div>
              <label className="block text-sm mb-1">Agregar módulo</label>
              <select value={seleccion} onChange={e => setSeleccion(e.target.value)} className="border px-2 py-1 rounded min-w-[240px]">
                <option value="">Selecciona un módulo</option>
                {candidatos.map(m => (
                  <option key={m.id} value={m.id}>{m.icon || ''} {m.name}</option>
                ))}
              </select>
            </div>
            <button onClick={onAgregar} className="bg-blue-600 text-white px-3 py-2 rounded">Agregar</button>
          </div>

          <table className="min-w-full bg-white border border-gray-200 rounded">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left py-2 px-3">Nombre</th>
                <th className="text-left py-2 px-3">Activo</th>
                <th className="text-left py-2 px-3">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {asignados.map(a => (
                <tr key={a.module_id} className="border-t">
                  <td className="py-2 px-3">{a.module?.icon || ''} {a.module?.name || a.module_id}</td>
                  <td className="py-2 px-3">{a.active ? 'Yes' : 'No'}</td>
                  <td className="py-2 px-3">
                    <button onClick={() => onEliminar(a.module_id)} className="text-red-700">Remove</button>
                  </td>
                </tr>
              ))}
              {asignados.length === 0 && (
                <tr><td className="py-3 px-3" colSpan={3}>Sin módulos asignados</td></tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}
