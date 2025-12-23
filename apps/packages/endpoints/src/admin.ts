export const ADMIN_AUTH = {
  login: '/v1/admin/auth/login',
  refresh: '/v1/admin/auth/refresh',
  csrf: '/v1/admin/auth/csrf',
  logout: '/v1/admin/auth/logout',
}

export const ADMIN_MODULOS = {
  publicos: '/v1/admin/modulos/publicos',
  base: '/v1/admin/modulos',
  byId: (id: number | string) => `/v1/admin/modulos/${id}`,
  activar: (id: number | string) => `/v1/admin/modulos/${id}/activar`,
  desactivar: (id: number | string) => `/v1/admin/modulos/${id}/desactivar`,
  registrar: '/v1/admin/modulos/registrar-modulos',
}

export const ADMIN_EMPRESAS = {
  base: '/v1/admin/empresas',
  createFull: '/v1/admin/empresas/full-json',
  byId: (id: number | string) => `/v1/admin/empresas/${id}`,
}

export const ADMIN_MODULOS_EMPRESA = {
  base: (tenantId: number | string) => `/v1/admin/modulos/empresa/${tenantId}`,
  upsert: (tenantId: number | string) => `/v1/admin/modulos/empresa/${tenantId}/upsert`,
  remove: (tenantId: number | string, moduloId: number | string) => `/v1/admin/modulos/empresa/${tenantId}/modulo/${moduloId}`,
}

export const ADMIN_CONFIG = {
  monedas: {
    // Backend expone rutas en inglés (/currency); mantener alias en español aquí solo rompía el panel (404)
    base: '/v1/admin/config/currency',
    byId: (id: number | string) => `/v1/admin/config/currency/${id}`,
  },
  paises: {
    base: '/v1/admin/config/country',
    byId: (id: number | string) => `/v1/admin/config/country/${id}`,
  },
  timezones: {
    base: '/v1/admin/config/timezone',
    byId: (name: string) => `/v1/admin/config/timezone/${encodeURIComponent(name)}`,
  },
  locales: {
    base: '/v1/admin/config/locale',
    byId: (code: string) => `/v1/admin/config/locale/${encodeURIComponent(code)}`,
  },
  idiomas: {
    // El backend usa /language; el endpoint anterior /language fallaba por ruta en español
    base: '/v1/admin/config/language',
    byId: (id: number | string) => `/v1/admin/config/language/${id}`,
  },
  settingsDefaults: {
    base: '/v1/admin/config/settings-defaults',
    byId: (id: number | string) => `/v1/admin/config/settings-defaults/${id}`,
  },
  sectores: {
    base: '/v1/admin/config/template-sector',
    byId: (id: number | string) => `/v1/admin/config/template-sector/${id}`,
  },
  tipoEmpresa: {
    base: '/v1/admin/config/business-type',
    byId: (id: number | string) => `/v1/admin/config/business-type/${id}`,
  },
  tipoNegocio: {
    base: '/v1/admin/config/business-category',
    byId: (id: number | string) => `/v1/admin/config/business-category/${id}`,
  },
  diasSemana: {
    base: '/v1/admin/config/weekday',
  },
  horarioAtencion: {
    base: '/v1/admin/config/attention-schedule',
    byId: (id: number | string) => `/v1/admin/config/attention-schedule/${id}`,
  },
}

export const ADMIN_USUARIOS = {
  base: '/v1/admin/usuarios',
  byId: (id: string) => `/v1/admin/usuarios/${id}`,
  reenviarReset: (id: string) => `/v1/admin/usuarios/${id}/reenviar-reset`,
  activar: (id: string) => `/v1/admin/usuarios/${id}/activar`,
  desactivar: (id: string) => `/v1/admin/usuarios/${id}/desactivar`,
  desactivarEmpresa: (id: string) => `/v1/admin/usuarios/${id}/desactivar-empresa`,
  asignarNuevoAdmin: (id: string) => `/v1/admin/usuarios/${id}/asignar-nuevo-admin`,
  // Password management for admin users lives under /admin/users (english, no legacy alias)
  setPassword: (id: string) => `/v1/admin/users/${id}/set-password`,
}
