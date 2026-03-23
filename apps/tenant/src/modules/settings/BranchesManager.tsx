import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import tenantApi from '../../shared/api/client'
import { useToast } from '../../shared/toast'

interface Branch {
  id: string
  name: string
  code: string
  address: string | null
  city: string | null
  phone: string | null
  is_main: boolean
  is_active: boolean
}

interface BranchForm {
  name: string
  code: string
  address: string
  city: string
  phone: string
  is_main: boolean
}

const emptyForm: BranchForm = { name: '', code: '', address: '', city: '', phone: '', is_main: false }

export default function BranchesManager() {
  const { t } = useTranslation('common')
  const { success, error: showError } = useToast()
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [form, setForm] = useState<BranchForm>(emptyForm)
  const [deleteTarget, setDeleteTarget] = useState<Branch | null>(null)

  const load = () => {
    setLoading(true)
    tenantApi.get('/api/v1/tenant/branches')
      .then(r => setBranches(r.data))
      .catch(() => showError('Error cargando sucursales'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editing) {
        await tenantApi.put(`/api/v1/tenant/branches/${editing}`, form)
        success('Sucursal actualizada')
      } else {
        await tenantApi.post('/api/v1/tenant/branches', form)
        success('Sucursal creada')
      }
      setShowForm(false)
      setEditing(null)
      setForm(emptyForm)
      load()
    } catch {
      showError('Error guardando sucursal')
    }
  }

  const handleEdit = (b: Branch) => {
    setForm({ name: b.name, code: b.code, address: b.address || '', city: b.city || '', phone: b.phone || '', is_main: b.is_main })
    setEditing(b.id)
    setShowForm(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await tenantApi.delete(`/api/v1/tenant/branches/${id}`)
      success('Sucursal eliminada')
      load()
    } catch {
      showError('Error eliminando sucursal')
    } finally {
      setDeleteTarget(null)
    }
  }

  if (loading) return <div className="p-6">Cargando...</div>

  return (
    <div className="p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">🏢 Sucursales</h2>
        <button
          onClick={() => { setShowForm(true); setEditing(null); setForm(emptyForm) }}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Nueva Sucursal
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border rounded-lg p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input
              placeholder="Nombre *"
              value={form.name}
              onChange={e => setForm({ ...form, name: e.target.value })}
              required
              className="border rounded px-3 py-2"
            />
            <input
              placeholder="Código *"
              value={form.code}
              onChange={e => setForm({ ...form, code: e.target.value })}
              required
              disabled={!!editing}
              className="border rounded px-3 py-2 disabled:bg-gray-100"
            />
            <input
              placeholder="Dirección"
              value={form.address}
              onChange={e => setForm({ ...form, address: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              placeholder="Ciudad"
              value={form.city}
              onChange={e => setForm({ ...form, city: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <input
              placeholder="Teléfono"
              value={form.phone}
              onChange={e => setForm({ ...form, phone: e.target.value })}
              className="border rounded px-3 py-2"
            />
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.is_main}
                onChange={e => setForm({ ...form, is_main: e.target.checked })}
              />
              Sucursal principal
            </label>
          </div>
          <div className="flex gap-2">
            <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
              {editing ? 'Actualizar' : 'Crear'}
            </button>
            <button type="button" onClick={() => { setShowForm(false); setEditing(null) }} className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400">
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Código</th>
              <th className="px-4 py-3 text-left">Ciudad</th>
              <th className="px-4 py-3 text-left">Teléfono</th>
              <th className="px-4 py-3 text-center">Principal</th>
              <th className="px-4 py-3 text-center">Activa</th>
              <th className="px-4 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {branches.map(b => (
              <tr key={b.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3">{b.name}</td>
                <td className="px-4 py-3 font-mono">{b.code}</td>
                <td className="px-4 py-3">{b.city || '—'}</td>
                <td className="px-4 py-3">{b.phone || '—'}</td>
                <td className="px-4 py-3 text-center">{b.is_main ? '⭐' : ''}</td>
                <td className="px-4 py-3 text-center">{b.is_active ? '✅' : '❌'}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleEdit(b)} className="text-blue-600 hover:underline">Editar</button>
                  {!b.is_main && (
                    <button onClick={() => setDeleteTarget(b)} className="text-red-600 hover:underline">Eliminar</button>
                  )}
                </td>
              </tr>
            ))}
            {branches.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No hay sucursales configuradas</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm">
            <h3 className="font-semibold text-lg mb-2">Eliminar sucursal</h3>
            <p className="text-sm text-slate-600 mb-4">¿Eliminar <strong>{deleteTarget.name}</strong>? Esta acción no se puede deshacer.</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">Cancelar</button>
              <button onClick={() => handleDelete(deleteTarget.id)} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">Eliminar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
