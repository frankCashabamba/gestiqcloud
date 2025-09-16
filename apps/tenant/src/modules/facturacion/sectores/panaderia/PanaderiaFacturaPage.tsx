import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createFactura } from '../../services'
import { useToast, getErrorMessage } from '../../../../shared/toast'

type Linea = { descripcion: string; cantidad: number; precio_unitario: number; iva: number }

const nueva = (): Linea => ({ descripcion: '', cantidad: 1, precio_unitario: 0, iva: 12 })

export default function PanaderiaFacturaPage() {
  const nav = useNavigate()
  const { success, error } = useToast()
  const [fecha, setFecha] = useState(() => new Date().toISOString().slice(0,10))
  const [estado, setEstado] = useState<'borrador'|'emitida'|'anulada'>('borrador')
  const [lineas, setLineas] = useState<Linea[]>([nueva()])

  const totals = useMemo(() => {
    let subtotal = 0, iva = 0
    for (const l of lineas) { const base = (l.cantidad||0)*(l.precio_unitario||0); subtotal += base; iva += base*(l.iva||0)/100 }
    return { subtotal, iva, total: subtotal + iva }
  }, [lineas])

  const update = (i:number, next: Partial<Linea>) => setLineas(prev => prev.map((l, idx)=> idx===i ? { ...l, ...next } : l))
  const add = () => setLineas(prev => [...prev, nueva()])
  const remove = (i:number) => setLineas(prev => prev.filter((_,idx)=> idx!==i))

  const onSubmit: React.FormEventHandler = async (e) => {
    e.preventDefault()
    try {
      if (lineas.length === 0) throw new Error('Agrega al menos una línea')
      await createFactura({ fecha, total: Number(totals.total.toFixed(2)), estado, cliente_id: undefined })
      success('Factura creada (panadería)')
      nav('/mod/facturacion')
    } catch(e:any) { error(getErrorMessage(e)) }
  }

  return (
    <div className="p-4">
      <h3 className="text-xl font-semibold mb-3">Factura sector Panadería</h3>
      <form onSubmit={onSubmit} className="space-y-4" style={{ maxWidth: 720 }}>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="block mb-1">Fecha</label><input type="date" value={fecha} onChange={(e)=> setFecha(e.target.value)} className="border px-2 py-1 w-full rounded" /></div>
          <div><label className="block mb-1">Estado</label><select value={estado} onChange={(e)=> setEstado(e.target.value as any)} className="border px-2 py-1 w-full rounded"><option value="borrador">Borrador</option><option value="emitida">Emitida</option><option value="anulada">Anulada</option></select></div>
        </div>

        <div className="space-y-3">
          <div className="font-semibold">Líneas</div>
          {lineas.map((l, i) => (
            <div key={i} className="border rounded p-3">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div><label className="block mb-1">Descripción</label><input className="border px-2 py-1 w-full rounded" value={l.descripcion} onChange={(e)=> update(i,{ descripcion: e.target.value })} /></div>
                <div><label className="block mb-1">Cantidad</label><input type="number" min={0} className="border px-2 py-1 w-full rounded" value={l.cantidad} onChange={(e)=> update(i,{ cantidad: Number(e.target.value) })} /></div>
                <div><label className="block mb-1">Precio Unitario</label><input type="number" step="0.01" min={0} className="border px-2 py-1 w-full rounded" value={l.precio_unitario} onChange={(e)=> update(i,{ precio_unitario: Number(e.target.value) })} /></div>
                <div><label className="block mb-1">IVA %</label><input type="number" min={0} className="border px-2 py-1 w-full rounded" value={l.iva} onChange={(e)=> update(i,{ iva: Number(e.target.value) })} /></div>
              </div>
              <div className="text-right mt-2">
                <button type="button" className="text-red-700" onClick={()=> remove(i)}>Eliminar</button>
              </div>
            </div>
          ))}
          <button type="button" className="bg-gray-200 px-3 py-1 rounded" onClick={add}>+ Agregar línea</button>
        </div>

        <div className="text-right font-semibold">
          Subtotal: $ {totals.subtotal.toFixed(2)}<br/>IVA: $ {totals.iva.toFixed(2)}<br/>Total: $ {totals.total.toFixed(2)}
        </div>

        <div className="pt-2">
          <button type="submit" className="bg-blue-600 text-white px-3 py-2 rounded">Guardar</button>
          <button type="button" className="ml-3 px-3 py-2" onClick={()=> nav('/mod/facturacion/sectores')}>Cancelar</button>
        </div>
      </form>
    </div>
  )
}
