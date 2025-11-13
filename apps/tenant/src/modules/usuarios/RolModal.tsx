import React, { useState, useEffect } from 'react'
import { createRol, updateRol, type RolCreatePayload } from './services'
import type { Rol } from './types'
import { useToast, getErrorMessage } from '../../shared/toast'

type Props = {
  rol?: Rol | null
  onClose: () => void
  onSuccess: () => void
}

export default function RolModal({ rol, onClose, onSuccess }: Props) {
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [permisos, setPermisos] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(false)
  const { success, error: toastError } = useToast()

  useEffect(() => {
    if (rol) {
      setNombre(rol.name)
      setDescripcion(rol.descripcion || '')
      setPermisos(rol.permisos || {})
    }
  }, [rol])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!nombre.trim()) {
      toastError('El nombre del rol es obligatorio')
      return
    }

    try {
      setLoading(true)
      const payload: RolCreatePayload = {
        name: nombre.trim(),
        descripcion: descripcion.trim() || undefined,
        permisos
      }

      if (rol) {
        await updateRol(rol.id, payload)
        success('Rol actualizado correctamente')
      } else {
        await createRol(payload)
        success('Rol creado correctamente')
      }

      onSuccess()
      onClose()
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  const togglePermiso = (key: string) => {
    setPermisos(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  // Permisos comunes
  const permisosDisponibles = [
    { key: 'ver_ventas', label: 'Ver Ventas' },
    { key: 'crear_ventas', label: 'Crear Ventas' },
    { key: 'editar_ventas', label: 'Editar Ventas' },
    { key: 'eliminar_ventas', label: 'Eliminar Ventas' },
    { key: 'ver_compras', label: 'Ver Compras' },
    { key: 'crear_compras', label: 'Crear Compras' },
    { key: 'editar_compras', label: 'Editar Compras' },
    { key: 'ver_inventario', label: 'Ver Inventario' },
    { key: 'editar_inventario', label: 'Editar Inventario' },
    { key: 'ver_clientes', label: 'Ver Clientes' },
    { key: 'editar_clientes', label: 'Editar Clientes' },
    { key: 'ver_proveedores', label: 'Ver Proveedores' },
    { key: 'editar_proveedores', label: 'Editar Proveedores' },
    { key: 'ver_reportes', label: 'Ver Reportes' },
    { key: 'ver_configuracion', label: 'Ver Configuración' },
    { key: 'editar_configuracion', label: 'Editar Configuración' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white p-6 shadow-lg"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-slate-900 mb-4">
          {rol ? 'Editar Rol' : 'Nuevo Rol'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Nombre del Rol <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej: Cajero, Vendedor, Contador"
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Descripción
            </label>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Describe las responsabilidades de este rol"
              rows={3}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Permisos
            </label>
            <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto border border-slate-200 rounded-md p-3">
              {permisosDisponibles.map(({ key, label }) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 p-2 rounded">
                  <input
                    type="checkbox"
                    checked={permisos[key] || false}
                    onChange={() => togglePermiso(key)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900"
              disabled={loading}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Guardando...' : (rol ? 'Actualizar' : 'Crear Rol')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
