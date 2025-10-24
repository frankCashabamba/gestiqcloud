import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listGastos, removeGasto, type Gasto } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'

export default function GastosList() {
  const [items, setItems] = useState<Gasto[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => { (async ()=> {
    try { setLoading(true); setItems(await listGastos()) }
    catch(e:any){ const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
    finally { setLoading(false) }
  })() }, [])

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Gastos</h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={()=> nav('nuevo')}>Nuevo</button>
      </div>
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <table className="min-w-full text-sm">
        <thead><tr className="text-left border-b"><th>Fecha</th><th>Monto</th><th>Concepto</th><th>Acciones</th></tr></thead>
        <tbody>
          {items.map((v) => (
            <tr key={v.id} className="border-b">
              <td>{v.fecha}</td>
              <td>{v.monto.toFixed(2)}</td>
              <td>{v.concepto || '-'}</td>
              <td>
                <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async ()=> { if(!confirm('¿Eliminar gasto?')) return; try { await removeGasto(v.id); setItems((p)=>p.filter(x=>x.id!==v.id)); success('Gasto eliminado') } catch(e:any){ toastError(getErrorMessage(e)) } }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length===0 && <tr><td className="py-3 px-3" colSpan={4}>Sin registros</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

