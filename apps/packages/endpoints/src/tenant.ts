export const TENANT_AUTH = {
  login: '/v1/tenant/auth/login',
  refresh: '/v1/tenant/auth/refresh',
  csrf: '/v1/tenant/auth/csrf',
  logout: '/v1/tenant/auth/logout',
  setPassword: '/v1/tenant/auth/set-password',
}

export const TENANT_MODULOS = {
  // añade endpoints de tenant si los expones públicamente
}

export const TENANT_EMPRESAS = {
  base: '/v1/empresa',
}

export const TENANT_CLIENTES = {
  base: '/v1/tenant/clientes',
  byId: (id: number | string) => `/v1/tenant/clientes/${id}`,
}

export const TENANT_PROVEEDORES = {
  base: '/v1/tenant/proveedores/',
  byId: (id: number | string) => `/v1/tenant/proveedores/${id}`,
}

export const TENANT_VENTAS = {
  base: '/v1/tenant/ventas',
  byId: (id: number | string) => `/v1/tenant/ventas/${id}`,
}

export const TENANT_COMPRAS = {
  base: '/v1/tenant/compras',
  byId: (id: number | string) => `/v1/tenant/compras/${id}`,
}

export const TENANT_CAJA = {
  base: '/v1/tenant/caja/movimientos',
}

export const TENANT_BANCOS = {
  base: '/v1/tenant/bancos/movimientos',
}

export const TENANT_ONBOARDING = {
  init: '/v1/tenant/configuracion-inicial',
}

export const TENANT_USUARIOS = {
  base: '/v1/tenant/usuarios',
  byId: (id: number | string) => `/v1/tenant/usuarios/${id}`,
  modules: '/v1/tenant/usuarios/modulos',
  roles: '/v1/tenant/usuarios/roles',
  checkUsername: (username: string) => `/v1/usuarios/check-username/${encodeURIComponent(username)}`,
  setPassword: (id: number | string) => `/v1/tenant/usuarios/${id}/set-password`,
}

export const TENANT_SETTINGS = {
  general: '/v1/tenant/settings/general',
  branding: '/v1/tenant/settings/branding',
  fiscal: '/v1/tenant/settings/fiscal',
  horarios: '/v1/tenant/settings/horarios',
  limites: '/v1/tenant/settings/limites',
}

export const TENANT_FACTURACION = {
  base: '/v1/tenant/facturacion',
  byId: (id: number | string) => `/v1/tenant/facturacion/${id}`,
}

export const TENANT_FACTURAE = {
  base: '/v1/tenant/facturae',
}

export const TENANT_GASTOS = {
  base: '/v1/tenant/gastos',
  byId: (id: number | string) => `/v1/tenant/gastos/${id}`,
}

export const TENANT_RRHH = {
  vacaciones: {
    base: '/v1/tenant/rrhh/vacaciones',
    byId: (id: number | string) => `/v1/tenant/rrhh/vacaciones/${id}`,
  },
}

