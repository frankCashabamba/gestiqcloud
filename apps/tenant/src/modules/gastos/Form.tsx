import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createGasto, getGasto, updateGasto, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

type FormT = Omit<Gasto,'id'>

export default function GastoForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const { success, error } = useToast()
  const [form, setForm] = useState<FormT>({ fecha: new Date().toISOString().slice(0,10), monto: 0, proveedor_id: undefined, concepto: '' })

  useEffect(() => { if (id) { getGasto(id).then((x)=> setForm({ fecha: x.fecha, monto: x.monto, proveedor_id: x.proveedor_id, concepto: x.concepto })) } }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.fecha) throw new Error('Fecha requerida')
      if (form.monto <= 0) throw new Error('Monto debe ser > 0')
      if (id) await updateGasto(id, form)
      else await createGasto(form)
      success('Gasto guardado')
      nav('..')
    } catch(e:any) { error(getErrorMessage(e)) }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar gasto' : 'Nuevo gasto'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div><label className="block mb-1">Fecha</label><input type="date" value={form.fecha} onChange={(e)=> setForm({ ...form, fecha: e.target.value })} className="border px-2 py-1 w-full rounded" required /></div>
        <div><label className="block mb-1">Monto</label><input type="number" step="0.01" value={form.monto} onChange={(e)=> setForm({ ...form, monto: Number(e.target.value) })} className="border px-2 py-1 w-full rounded" required /></div>
        <div><label className="block mb-1">Concepto</label><input value={form.concepto || ''} onChange={(e)=> setForm({ ...form, concepto: e.target.value })} className="border px-2 py-1 w-full rounded" /></div>
        <div className="pt-2"><button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button><button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button></div>
      </form>
    </div>
  )
}

