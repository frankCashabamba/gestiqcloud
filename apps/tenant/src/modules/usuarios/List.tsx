import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listUsuarios, removeUsuario } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import type { Usuario } from './types'

export default function UsuariosList() {
  const [items, setItems] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    (async () => {
      try { setLoading(true); setItems(await listUsuarios()) }
      catch (e: any) { const m = getErrorMessage(e); setErrMsg(m); toastError(m) }
      finally { setLoading(false) }
    })()
  }, [])

  const filtered = items.filter(u => (u.nombre||'').toLowerCase().includes(q.toLowerCase()) || (u.email||'').toLowerCase().includes(q.toLowerCase()))
  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">Usuarios</h2>
        <button className="bg-blue-600 text-white px-3 py-1 rounded" onClick={() => nav('nuevo')}>Nuevo</button>
      </div>
      <input value={q} onChange={(e)=> setQ(e.target.value)} placeholder="Buscar nombre o email..." className="mb-3 w-full px-3 py-2 border rounded text-sm" />
      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b"><th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr>
        </thead>
        <tbody>
          {view.map((u) => (
            <tr key={u.id} className="border-b">
              <td>{u.nombre}</td>
              <td>{u.email}</td>
              <td>{u.rol || '-'}</td>
              <td>{u.activo ? 'Activo' : 'Inactivo'}</td>
              <td>
                <Link to={`${u.id}/editar`} className="text-blue-600 hover:underline mr-3">Editar</Link>
                <button className="text-red-700" onClick={async () => { if (!confirm('¿Eliminar usuario?')) return; try { await removeUsuario(u.id); setItems((p)=>p.filter(x=>x.id!==u.id)); success('Usuario eliminado') } catch(e:any){ toastError(getErrorMessage(e)) } }}>Eliminar</button>
              </td>
            </tr>
          ))}
          {!loading && items.length === 0 && (<tr><td className="py-3 px-3" colSpan={5}>Sin registros</td></tr>)}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
