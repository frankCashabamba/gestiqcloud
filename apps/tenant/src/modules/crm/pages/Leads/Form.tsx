import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createLead, getLead, updateLead, type Lead } from '../../services'
import { useToast, getErrorMessage } from '../../../../shared/toast'
import { LeadStatus, LeadSource } from '../../types'

export default function LeadForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<Partial<Omit<Lead, 'id' | 'tenant_id' | 'created_at' | 'updated_at'>>>({
    name: '',
    email: '',
    phone: '',
    company: '',
    position: '',
    source: LeadSource.WEBSITE,
    status: LeadStatus.NEW,
    score: 0,
    notes: '',
    assigned_to: '',
  })
  const { success, error } = useToast()

  useEffect(() => {
    if (!id) return
    getLead(id).then((x)=> setForm({ ...x }))
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.name || String(form.name).trim() === '') throw new Error('El campo "Nombre" es obligatorio')
      if (!form.email || String(form.email).trim() === '') throw new Error('El campo "Email" es obligatorio')
      if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(form.email))) throw new Error('Email inválido')
      if (id) await updateLead(id, form)
      else await createLead(form as any)
      success('Lead guardado')
      nav('..')
    } catch (e: any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar lead' : 'Nuevo lead'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Nombre *</label>
          <input
            type="text"
            value={form.name ?? ''}
            onChange={(e)=> setForm({ ...form, name: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>
        <div>
          <label className="block mb-1">Email *</label>
          <input
            type="email"
            value={form.email ?? ''}
            onChange={(e)=> setForm({ ...form, email: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            required
          />
        </div>
        <div>
          <label className="block mb-1">Teléfono</label>
          <input
            type="text"
            value={form.phone ?? ''}
            onChange={(e)=> setForm({ ...form, phone: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Empresa</label>
          <input
            type="text"
            value={form.company ?? ''}
            onChange={(e)=> setForm({ ...form, company: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Cargo</label>
          <input
            type="text"
            value={form.position ?? ''}
            onChange={(e)=> setForm({ ...form, position: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Estado</label>
          <select
            value={form.status ?? LeadStatus.NEW}
            onChange={(e)=> setForm({ ...form, status: e.target.value as LeadStatus })}
            className="border px-2 py-1 w-full rounded"
          >
            <option value={LeadStatus.NEW}>Nuevo</option>
            <option value={LeadStatus.CONTACTED}>Contactado</option>
            <option value={LeadStatus.QUALIFIED}>Calificado</option>
            <option value={LeadStatus.LOST}>Perdido</option>
            <option value={LeadStatus.CONVERTED}>Convertido</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">Fuente</label>
          <select
            value={form.source ?? LeadSource.WEBSITE}
            onChange={(e)=> setForm({ ...form, source: e.target.value as LeadSource })}
            className="border px-2 py-1 w-full rounded"
          >
            <option value={LeadSource.WEBSITE}>Website</option>
            <option value={LeadSource.REFERRAL}>Referido</option>
            <option value={LeadSource.SOCIAL_MEDIA}>Redes Sociales</option>
            <option value={LeadSource.EMAIL}>Email</option>
            <option value={LeadSource.PHONE}>Teléfono</option>
            <option value={LeadSource.EVENT}>Evento</option>
            <option value={LeadSource.OTHER}>Otro</option>
          </select>
        </div>
        <div>
          <label className="block mb-1">Asignado a</label>
          <input
            type="text"
            value={form.assigned_to ?? ''}
            onChange={(e)=> setForm({ ...form, assigned_to: e.target.value })}
            className="border px-2 py-1 w-full rounded"
          />
        </div>
        <div>
          <label className="block mb-1">Puntuación</label>
          <input
            type="number"
            value={form.score ?? 0}
            onChange={(e)=> setForm({ ...form, score: Number(e.target.value) })}
            className="border px-2 py-1 w-full rounded"
            min="0"
            max="100"
          />
        </div>
        <div>
          <label className="block mb-1">Notas</label>
          <textarea
            value={form.notes ?? ''}
            onChange={(e)=> setForm({ ...form, notes: e.target.value })}
            className="border px-2 py-1 w-full rounded"
            rows={4}
          />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
