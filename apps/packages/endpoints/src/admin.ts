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
  createFull: '/v1/admin/empresas/completa-json',
  byId: (id: number | string) => `/v1/admin/empresas/${id}`,
}

export const ADMIN_MODULOS_EMPRESA = {
  base: (tenantId: number | string) => `/v1/admin/modulos/empresa/${tenantId}`,
  upsert: (tenantId: number | string) => `/v1/admin/modulos/empresa/${tenantId}/upsert`,
  remove: (tenantId: number | string, moduloId: number | string) => `/v1/admin/modulos/empresa/${tenantId}/modulo/${moduloId}`,
}

export const ADMIN_CONFIG = {
  monedas: {
    base: '/v1/admin/config/moneda',
    byId: (id: number | string) => `/v1/admin/config/moneda/${id}`,
  },
  paises: {
    base: '/v1/admin/config/pais',
    byId: (id: number | string) => `/v1/admin/config/pais/${id}`,
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
    base: '/v1/admin/config/idioma',
    byId: (id: number | string) => `/v1/admin/config/idioma/${id}`,
  },
  sectores: {
    base: '/v1/admin/config/sectores',
    byId: (id: number | string) => `/v1/admin/config/sectores/${id}`,
  },
  tipoEmpresa: {
    base: '/v1/admin/config/tipo-empresa',
    byId: (id: number | string) => `/v1/admin/config/tipo-empresa/${id}`,
  },
  tipoNegocio: {
    base: '/v1/admin/config/tipo-negocio',
    byId: (id: number | string) => `/v1/admin/config/tipo-negocio/${id}`,
  },
  diasSemana: {
    base: '/v1/admin/config/dias',
  },
  horarioAtencion: {
    base: '/v1/admin/config/horario_atencion',
    byId: (id: number | string) => `/v1/admin/config/horario_atencion/${id}`,
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
  setPassword: (id: string) => `/v1/admin/usuarios/${id}/set-password`,
}
