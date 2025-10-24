import React from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import UsuariosList from './List'
import UsuarioForm from './Form'
import RolesList from './RolesList'
import RolesForm from './RolesForm'
import { listUsuarios } from './services'

export default function UsuariosRoutes() {
  return (
    <Routes>
      <Route index element={<GuardedList />} />
      <Route path="nuevo" element={<UsuarioForm />} />
      <Route path="roles" element={<RolesList />} />
      <Route path="roles/nuevo" element={<RolesForm />} />
      <Route path="roles/:id" element={<RolesForm />} />
      <Route path=":id/editar" element={<UsuarioForm />} />
      <Route path="*" element={<Navigate to="." replace />} />
    </Routes>
  )
}

function GuardedList() {
  const nav = useNavigate()
  const [allowed, setAllowed] = React.useState<boolean | null>(null)

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const users = await listUsuarios()
        if (cancelled) return
        if (users.length <= 1) {
          // Si solo hay 1 usuario, no tiene sentido mostrar el módulo completo
          nav('..', { replace: true })
        } else {
          setAllowed(true)
        }
      } catch {
        setAllowed(true) // fallback
      }
    })()
    return () => { cancelled = true }
  }, [nav])

  if (allowed === null) return <div className="p-4 text-sm text-slate-500">Cargando…</div>
  return <UsuariosList />
}
