import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createHorario, getHorario, updateHorario, listDiasSemana, type HorarioAtencion, type DiaSemana } from '../../../services/configuracion/horarios'

type FormT = Omit<HorarioAtencion, 'id'>

export default function HorarioForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ dia_id: 0, inicio: '08:00', fin: '17:00' })
  const [dias, setDias] = useState<DiaSemana[]>([])

  useEffect(() => { listDiasSemana().then(setDias).catch(()=>{}) }, [])

  useEffect(() => {
    if (id) { getHorario(id).then((m)=> setForm({ dia_id: m.dia_id, inicio: m.inicio, fin: m.fin })).catch(()=>{}) }
  }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    if (id) await updateHorario(id, form)
    else await createHorario(form)
    nav('..')
  }

  return (
    <div style={{ padding: 16 }}>
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar horario' : 'Nuevo horario'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Día</label>
          <select value={form.dia_id} onChange={(e)=> setForm({ ...form, dia_id: Number(e.target.value) })} className="border px-2 py-1 w-full rounded">
            {dias.map((d)=> <option key={d.id} value={d.id}>{d.nombre}</option>)}
          </select>
        </div>
        <div>
          <label className="block mb-1">Hora de inicio</label>
          <input type="time" value={form.inicio} onChange={(e)=> setForm({ ...form, inicio: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Hora de fin</label>
          <input type="time" value={form.fin} onChange={(e)=> setForm({ ...form, fin: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
