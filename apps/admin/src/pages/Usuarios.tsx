import React, { useEffect, useState } from 'react'
import { useToast, getErrorMessage } from '../shared/toast'
import { listUsuarios, reenviarReset, activarUsuario, desactivarUsuario, desactivarEmpresa, type AdminUsuario } from '../services/usuarios'

export default function Usuarios() {
  const [items, setItems] = useState<AdminUsuario[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [confirmEmpresaId, setConfirmEmpresaId] = useState<number | string | null>(null)
  const { success, error: toastError } = useToast()

  const load = async () => {
    try {
      setLoading(true)
      const data = await listUsuarios()
      // filtrar por es_admin === true (o es_admin_empresa si tu API usa ese campo)
      const filtrados = (data || []).filter((u: any) => u.es_admin === true || u.es_admin_empresa === true)
      setItems(filtrados)
    } catch (e: any) {
      const m = getErrorMessage(e)
      setErrMsg(m)
      toastError(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = items.filter((u) => {
    const name = `${u.nombre || ''}`.toLowerCase()
    const email = `${u.email || ''}`.toLowerCase()
    const q = query.toLowerCase()
    return name.includes(q) || email.includes(q)
  })

  return (
    <div className="max-w-6xl mx-auto px-4 py-10 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          <img src="/icons/usuario.png" alt="Usuarios" className="w-7 h-7" />
          Usuarios Principales
        </h1>
      </div>

      <input
        type="text"
        placeholder="Buscar nombre o correo..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
      />

      {loading && <div className="text-sm text-gray-500">Cargando…</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      {filtered.length > 0 ? (
        <ul className="space-y-4">
          {filtered.map((u) => (
            <li key={u.id} className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold text-gray-900">{u.nombre}</p>
                <p className="text-sm text-gray-500">{u.email || '-'}</p>
                <span className={`inline-block text-xs px-2 py-1 rounded ${u.activo ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700'}`}>
                  {u.activo ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 mt-3 sm:mt-0">
                <button onClick={async () => { try { await reenviarReset(u.id); success('Correo de restablecimiento enviado') } catch(e:any){ toastError(getErrorMessage(e)) } }} className="bg-purple-600 hover:bg-purple-700 text-white text-sm px-3 py-1.5 rounded-md">Reenviar restablecer</button>
                {u.activo ? (
                  <>
                    <button onClick={async () => { try { await desactivarUsuario(u.id); success('Usuario desactivado'); load() } catch(e:any){ toastError(getErrorMessage(e)) } }} className="bg-red-500 hover:bg-red-600 text-white text-sm px-3 py-1.5 rounded-md">Desactivar</button>
                    <button onClick={() => setConfirmEmpresaId(u.id)} className="bg-gray-500 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded-md">Eliminar</button>
                  </>
                ) : (
                  <button onClick={async () => { try { await activarUsuario(u.id); success('Usuario activado'); load() } catch(e:any){ toastError(getErrorMessage(e)) } }} className="bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1.5 rounded-md">Activar</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        !loading && <p className="text-gray-500 text-sm mt-4">No hay usuarios principales.</p>
      )}

      {confirmEmpresaId !== null && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-40 flex items-center justify-center">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-gray-800">¿Qué deseas hacer con la empresa?</h2>
            <p className="text-sm text-gray-600">Este usuario es el administrador principal. Puedes asignar otro usuario o desactivar la empresa completa.</p>
            <div className="space-y-3">
              <a href={`/admin/usuarios/${confirmEmpresaId}/asignar-nuevo-admin`} className="block text-center bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md">Asignar otro administrador</a>
              <button onClick={async ()=> { try { await desactivarEmpresa(confirmEmpresaId!); success('Empresa desactivada'); setConfirmEmpresaId(null); load() } catch(e:any){ toastError(getErrorMessage(e)) } }} className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md">Desactivar empresa</button>
              <button onClick={()=> setConfirmEmpresaId(null)} className="w-full text-gray-600 hover:text-gray-900 text-sm mt-2">Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
