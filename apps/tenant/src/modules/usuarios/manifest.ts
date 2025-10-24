import React from 'react'

const UsuariosList = React.lazy(() => import('./List'))
const UsuariosForm = React.lazy(() => import('./Form'))

export const manifest = {
  id: 'usuarios',
  name: 'Usuarios',
  version: '1.0.0',
  permissions: ['usuarios.read', 'usuarios.write'],
  routes: [
    { path: '/usuarios', element: UsuariosList },
    { path: '/usuarios/nuevo', element: UsuariosForm },
    { path: '/usuarios/:id/editar', element: UsuariosForm }
  ],
  menu: {
    title: 'Usuarios',
    icon: '👤',
    route: '/usuarios',
    order: 70
  }
}
