export const rolesMock = [
  {
    id: 1,
    nombre: 'Administrador',
    descripcion: 'Acceso completo',
    permisos: { ver: true, crear: true, editar: true, eliminar: true }
  },
  {
    id: 2,
    nombre: 'Editor',
    descripcion: 'Puede editar',
    permisos: { ver: true, crear: true, editar: true, eliminar: false }
  }
];
