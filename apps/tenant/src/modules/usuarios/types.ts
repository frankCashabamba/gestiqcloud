export type Usuario = {
  id: number
  tenant_id: number
  nombre_encargado?: string | null
  apellido_encargado?: string | null
  email: string
  username?: string | null
  es_admin_empresa: boolean
  active: boolean
  modulos: number[]
  roles: number[]
  ultimo_login_at?: string | null
}

export type UsuarioCreatePayload = {
  nombre_encargado?: string | null
  apellido_encargado?: string | null
  email: string
  username?: string | null
  password: string
  es_admin_empresa: boolean
  activo?: boolean
  modulos: number[]
  roles: number[]
}

export type UsuarioUpdatePayload = {
  nombre_encargado?: string | null
  apellido_encargado?: string | null
  email?: string
  username?: string | null
  password?: string | null
  es_admin_empresa?: boolean
  activo?: boolean
  modulos?: number[]
  roles?: number[]
}

export type ModuloOption = {
  id: number
  name?: string | null
  nombre?: string | null
  categoria?: string | null
  icono?: string | null
}

export type RolOption = {
  id: number
  name: string
  descripcion?: string | null
}

// Gestión completa de roles
export type Rol = {
  id: number
  name: string
  descripcion?: string
  permisos: Record<string, boolean>
  tenant_id: number
  rol_base_id?: number
  creado_por_empresa: boolean
}
