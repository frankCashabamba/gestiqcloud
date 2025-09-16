import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { createCompra, getCompra, updateCompra, type Compra as C } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

type FormT = Omit<C, 'id'>

export default function CompraForm() {
  const { id } = useParams()
  const nav = useNavigate()
  const [form, setForm] = useState<FormT>({ fecha: new Date().toISOString().slice(0,10), total: 0, proveedor_id: undefined, estado: 'borrador' })
  const { success, error } = useToast()

  useEffect(() => { if (id) { getCompra(id).then((x)=> setForm({ fecha: x.fecha, total: x.total, proveedor_id: x.proveedor_id, estado: x.estado })) } }, [id])

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (!form.fecha) throw new Error('Fecha es requerida')
      if (form.total < 0) throw new Error('Total debe ser >= 0')
      if (id) await updateCompra(id, form)
      else await createCompra(form)
      success('Compra guardada')
      nav('..')
    } catch(e:any) {
      error(getErrorMessage(e))
    }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">{id ? 'Editar compra' : 'Nueva compra'}</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 520 }}>
        <div>
          <label className="block mb-1">Fecha</label>
          <input type="date" value={form.fecha} onChange={(e)=> setForm({ ...form, fecha: e.target.value })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Total</label>
          <input type="number" step="0.01" value={form.total} onChange={(e)=> setForm({ ...form, total: Number(e.target.value) })} className="border px-2 py-1 w-full rounded" required />
        </div>
        <div>
          <label className="block mb-1">Estado</label>
          <select value={form.estado || 'borrador'} onChange={(e)=> setForm({ ...form, estado: e.target.value })} className="border px-2 py-1 w-full rounded">
            <option value="borrador">Borrador</option>
            <option value="registrada">Registrada</option>
            <option value="anulada">Anulada</option>
          </select>
        </div>
        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('..')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
