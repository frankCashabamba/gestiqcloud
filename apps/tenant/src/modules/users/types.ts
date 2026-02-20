export type Usuario = {
  id: string
  tenant_id: string
  first_name?: string | null
  last_name?: string | null
  email: string
  username?: string | null
  is_company_admin: boolean
  active: boolean
  modules: string[]
  roles: string[]
  last_login_at?: string | null
}

export type UsuarioCreatePayload = {
  first_name?: string | null
  last_name?: string | null
  email: string
  username?: string | null
  password: string
  is_company_admin: boolean
  active?: boolean
  modules: string[]
  roles: string[]
}

export type UsuarioUpdatePayload = {
  first_name?: string | null
  last_name?: string | null
  email?: string
  username?: string | null
  password?: string | null
  is_company_admin?: boolean
  active?: boolean
  modules?: string[]
  roles?: string[]
}

export type ModuloOption = {
  id: string
  name?: string | null
  nombre?: string | null
  categoria?: string | null
  icono?: string | null
}

export type RolOption = {
  id: string
  name: string
  description?: string | null
}

// Gestión completa de roles
export type Rol = {
  id: string
  name: string
  description?: string
  permissions: Record<string, boolean>
  tenant_id: string
  base_role_id?: string
  created_by_company: boolean
}
