import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createModulo, getModulo, updateModulo } from '../../services/modulos'
import { useToast, getErrorMessage } from '../../shared/toast'
import type { Module } from '../../modulos/types'

export default function ModuloForm({ mode }: { mode: 'create' | 'edit' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const [form, setForm] = useState<Partial<Module>>({
    name: '',
    initial_template: '',
    category: null,
    description: null,
    icon: null,
    url: null,
    active: true,
  })
  const { success, error } = useToast()

  useEffect(() => {
    if (mode === 'edit' && id) {
      getModulo(id)
        .then((m) =>
          setForm({
            ...m,
            initial_template: m.initial_template || '',
            description: m.description ?? '',
          }),
        )
        .catch((e: any) => {
          const status = e?.response?.status
          if (status === 404) {
            error('El módulo ya no existe; regresando al listado')
            navigate('..')
          } else {
            error(getErrorMessage(e))
          }
        })
    }
  }, [mode, id])

  const onChange: React.ChangeEventHandler<HTMLInputElement> = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.name?.trim() || !form.initial_template?.trim()) throw new Error('Complete name and initial template')
      if (mode === 'edit' && id) {
        await updateModulo(id, form)
      } else {
        await createModulo(form)
      }
      success('Module saved')
      navigate('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>{mode === 'edit' ? 'Edit module' : 'Create module'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Name</label>
          <input name="name" value={form.name || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">URL</label>
          <input name="url" value={form.url || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Initial template</label>
          <input name="initial_template" value={form.initial_template || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Icon</label>
          <input name="icon" value={form.icon || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Category</label>
          <input
            name="category"
            value={form.category || ''}
            onChange={(e) => setForm((f) => ({ ...f, category: e.target.value || null }))}
            className="border px-2 py-1 w-full rounded"
            placeholder="operations | tools | ..."
          />
        </div>
        <div>
          <label className="block mb-1">Description</label>
          <input
            name="description"
            value={form.description || ''}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value || null }))}
            className="border px-2 py-1 w-full rounded"
            placeholder="Short description"
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Save</button>
        </div>
      </form>
    </div>
  )
}
