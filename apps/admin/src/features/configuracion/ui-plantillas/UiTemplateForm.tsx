import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createUiTemplate, updateUiTemplate, listUiTemplates, type UiTemplateItem } from '../../../services/configuracion/uiTemplates'
import { useToast } from '../../../shared/toast'

export default function UiTemplateForm() {
  const { slug } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const editing = Boolean(slug)
  const [form, setForm] = useState<UiTemplateItem>({ slug: '', label: '', description: '', pro: false, active: true, ord: 10 })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (editing) {
      ;(async () => {
        try {
          const items = await listUiTemplates()
          const row = items.find(i => i.slug === slug)
          if (row) setForm(row)
        } catch {
          // noop
        }
      })()
    }
  }, [editing, slug])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      setLoading(true)
      if (!form.slug.trim() || !form.label.trim()) throw new Error('Slug y Label son requeridos')
      if (editing) await updateUiTemplate(slug!, form)
      else await createUiTemplate(form)
      success('Guardado')
      nav('..')
    } catch (e: any) {
      error(e?.message || 'Error guardando')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold mb-4">{editing ? 'Editar' : 'Nueva'} Plantilla UI</h1>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Slug *</label>
          <input className="input" value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} required disabled={loading} />
        </div>
        <div>
          <label className="block text-sm font-medium">Label *</label>
          <input className="input" value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} required disabled={loading} />
        </div>
        <div>
          <label className="block text-sm font-medium">Descripción</label>
          <textarea className="textarea" value={form.description || ''} onChange={e => setForm({ ...form, description: e.target.value })} disabled={loading} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={!!form.pro} onChange={e => setForm({ ...form, pro: e.target.checked })} /> Pro
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={!!form.active} onChange={e => setForm({ ...form, active: e.target.checked })} /> Activo
          </label>
        </div>
        <div>
          <label className="block text-sm font-medium">Orden</label>
          <input type="number" className="input" value={form.ord ?? 0} onChange={e => setForm({ ...form, ord: Number(e.target.value) })} disabled={loading} />
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" className="btn" onClick={() => nav('..')} disabled={loading}>Cancelar</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Guardando…' : 'Guardar'}</button>
        </div>
      </form>
    </div>
  )
}

