/**
 * Roles Form - Crear/Editar roles de empresa
 */
import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createRol, getRol, updateRol } from './rolesServices'

const PERMISOS_DISPONIBLES = [
  { key: 'usuarios.crear', label: 'Crear usuarios' },
  { key: 'usuarios.editar', label: 'Editar usuarios' },
  { key: 'usuarios.eliminar', label: 'Eliminar usuarios' },
  { key: 'ventas.crear', label: 'Crear ventas' },
  { key: 'ventas.editar', label: 'Editar ventas' },
  { key: 'ventas.eliminar', label: 'Eliminar ventas' },
  { key: 'inventario.ver', label: 'Ver inventario' },
  { key: 'inventario.ajustar', label: 'Ajustar inventario' },
  { key: 'facturacion.crear', label: 'Crear facturas' },
  { key: 'facturacion.enviar', label: 'Enviar e-factura' },
  { key: 'reportes.ver', label: 'Ver reportes' },
  { key: 'reportes.exportar', label: 'Exportar reportes' },
  { key: 'configuracion.ver', label: 'Ver configuración' },
  { key: 'configuracion.editar', label: 'Editar configuración' },
]

export default function RolesForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEdit = Boolean(id)

  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [permisosSeleccionados, setPermisosSeleccionados] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isEdit && id) {
      loadRol(parseInt(id))
    }
  }, [id, isEdit])

  const loadRol = async (rolId: number) => {
    try {
      const rol = await getRol(rolId)
      setNombre(rol.nombre)
      setDescripcion(rol.descripcion || '')
      setPermisosSeleccionados(Object.keys(rol.permisos || {}))
    } catch (err) {
      console.error(err)
      alert('Error al cargar rol')
    }
  }

  const handleTogglePermiso = (key: string) => {
    setPermisosSeleccionados((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!nombre.trim()) {
      alert('El nombre es obligatorio')
      return
    }

    try {
      setLoading(true)

      const payload = {
        nombre,
        descripcion,
        permisos: permisosSeleccionados,
      }

      if (isEdit && id) {
        await updateRol(parseInt(id), payload)
        alert('Rol actualizado')
      } else {
        await createRol(payload)
        alert('Rol creado')
      }

      navigate('/usuarios/roles')
    } catch (err: any) {
      alert(err.message || 'Error al guardar rol')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          {isEdit ? 'Editar Rol' : 'Nuevo Rol'}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Define un rol personalizado con permisos específicos
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-6">
          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Nombre del Rol *
            </label>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="ej: Cajero, Gerente de Tienda, Contador"
              required
            />
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Descripción (opcional)
            </label>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              rows={3}
              placeholder="Describe las responsabilidades de este rol"
            />
          </div>

          {/* Permisos */}
          <div>
            <label className="mb-3 block text-sm font-medium text-slate-700">
              Permisos del Rol
            </label>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {PERMISOS_DISPONIBLES.map((permiso) => (
                  <label
                    key={permiso.key}
                    className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 hover:bg-blue-50"
                  >
                    <input
                      type="checkbox"
                      checked={permisosSeleccionados.includes(permiso.key)}
                      onChange={() => handleTogglePermiso(permiso.key)}
                      className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm font-medium text-slate-900">
                      {permiso.label}
                    </span>
                  </label>
                ))}
              </div>

              <div className="mt-4 rounded-lg bg-blue-50 p-3">
                <p className="text-xs text-blue-700">
                  ✓ Seleccionados: {permisosSeleccionados.length} de {PERMISOS_DISPONIBLES.length}
                </p>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 border-t border-slate-200 pt-6">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-500 disabled:bg-slate-300"
            >
              {loading ? 'Guardando...' : isEdit ? 'Actualizar Rol' : 'Crear Rol'}
            </button>

            <button
              type="button"
              onClick={() => navigate('/usuarios/roles')}
              className="rounded-lg border border-slate-300 px-6 py-3 font-medium hover:bg-slate-50"
            >
              Cancelar
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
