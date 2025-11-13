import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createModulo, getModulo, updateModulo } from '../../services/modulos'
import { useToast, getErrorMessage } from '../../shared/toast'

type Modulo = {
  nombre: string
  url?: string
  plantilla_inicial: string
  icono?: string
  categoria?: string | null
  descripcion?: string | null
}

export default function ModuloForm({ mode }: { mode: 'create' | 'edit' }) {
  const navigate = useNavigate()
  const { id } = useParams()
  const [form, setForm] = useState<Modulo>({ nombre: '', plantilla_inicial: '', categoria: null, descripcion: null })
  const { success, error } = useToast()

  useEffect(() => {
    if (mode === 'edit' && id) {
      getModulo(id).then((m) => setForm({
        nombre: m.nombre,
        url: m.url,
        plantilla_inicial: m.plantilla_inicial || '',
        icono: m.icono,
        categoria: m.categoria ?? null,
        descripcion: m.descripcion ?? null,
      })).catch(() => {})
    }
  }, [mode, id])

  const onChange: React.ChangeEventHandler<HTMLInputElement> = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.nombre?.trim() || !form.plantilla_inicial?.trim()) throw new Error('Complete nombre y plantilla inicial')
      if (mode === 'edit' && id) {
        await updateModulo(id, form)
      } else {
        await createModulo(form)
      }
      success('Módulo guardado')
      navigate('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>{mode === 'edit' ? 'Editar módulo' : 'Crear módulo'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre</label>
          <input name="nombre" value={form.nombre} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">URL</label>
          <input name="url" value={form.url || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Plantilla inicial</label>
          <input name="plantilla_inicial" value={form.plantilla_inicial} onChange={onChange} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Icono</label>
          <input name="icono" value={form.icono || ''} onChange={onChange} className="border px-2 py-1 w-full rounded" />
        </div>
        <div>
          <label className="block mb-1">Categoría</label>
          <input
            name="categoria"
            value={form.categoria || ''}
            onChange={(e) => setForm((f) => ({ ...f, categoria: e.target.value || null }))}
            className="border px-2 py-1 w-full rounded"
            placeholder="operaciones | herramientas | ..."
          />
        </div>
        <div>
          <label className="block mb-1">Descripción</label>
          <input
            name="descripcion"
            value={form.descripcion || ''}
            onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value || null }))}
            className="border px-2 py-1 w-full rounded"
            placeholder="Breve descripción del módulo"
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
        </div>
      </form>
    </div>
  )
}
