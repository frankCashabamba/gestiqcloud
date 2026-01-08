import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createPermiso, getPermiso, updatePermiso, type GlobalPermission } from '../../../services/configuracion/permisos'
import { useToast, getErrorMessage } from '../../../shared/toast'

type FormT = Omit<GlobalPermission, 'id'>

export default function PermisoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ key: '', module: '', description: '' })
  const { success, error } = useToast()

  useEffect(() => {
    if (id) {
      getPermiso(id)
        .then((p) => setForm({ key: p.key, module: p.module || '', description: p.description || '' }))
        .catch(() => {})
    }
  }, [id])

  const isValid = !!form.module?.trim() && !!form.key?.trim() && !!form.description?.trim()

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.module?.trim()) throw new Error('El módulo es obligatorio')
      if (!form.key?.trim()) throw new Error('El key es obligatorio')
      const payload = {
        key: form.key.trim(),
        module: form.module.trim(),
        description: form.description.trim(),
      }
      if (id) await updatePermiso(id, payload)
      else await createPermiso(payload)
      success('Permiso guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar permiso' : 'Nuevo permiso'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Módulo</label>
          <input
            value={form.module || ''}
            onChange={(e) => setForm({ ...form, module: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            placeholder="pos"
            required
          />
        </div>
        <div>
          <label className="block mb-1">Key</label>
          <input
            value={form.key}
            onChange={(e) => setForm({ ...form, key: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            placeholder="pos.receipt.pay"
            required
          />
          <p className="text-xs text-gray-500 mt-1">Usa prefijo por módulo, ej: pos.*, sales.*</p>
        </div>
        <div>
          <label className="block mb-1">Descripción</label>
          <input
            value={form.description || ''}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded disabled:opacity-50" disabled={!isValid}>Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={() => nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
