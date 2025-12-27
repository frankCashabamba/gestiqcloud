import api from '../shared/api/client'
import { ADMIN_MODULOS, ADMIN_MODULOS_EMPRESA } from '@shared/endpoints'

import { Module, CompanyModule } from '../modulos/types'

export type { Module, CompanyModule }

const normalizeModule = (raw: any): Module => ({
  id: String(raw?.id),
  name: raw?.name,
  description: raw?.description ?? null,
  icon: raw?.icon ?? null,
  category: raw?.category ?? null,
  active: Boolean(raw?.active),
  initial_template: raw?.initial_template ?? '',
  context_type: raw?.context_type ?? null,
  target_model: raw?.target_model ?? null,
  context_filters: raw?.context_filters ?? null,
  url: raw?.url ?? null,
})

const toApiPayload = (payload: Partial<Module>) => ({
  name: payload.name,
  description: payload.description,
  icon: payload.icon,
  category: payload.category,
  url: payload.url,
  initial_template: payload.initial_template,
  active: payload.active,
  context_type: payload.context_type,
  target_model: payload.target_model,
  context_filters: payload.context_filters,
})

export async function listModulos(): Promise<Module[]> {
  const { data } = await api.get<Module[]>(ADMIN_MODULOS.base)
  return (data || []).map(normalizeModule)
}

export async function getModulo(id: number | string): Promise<Module> {
  const { data } = await api.get<Module>(ADMIN_MODULOS.byId(id))
  return normalizeModule(data)
}

export async function createModulo(payload: Partial<Module>): Promise<Module> {
  const { data } = await api.post<Module>(ADMIN_MODULOS.base, toApiPayload(payload))
  return normalizeModule(data)
}

export async function updateModulo(id: number | string, payload: Partial<Module>): Promise<Module> {
  const { data } = await api.put<Module>(ADMIN_MODULOS.byId(id), toApiPayload(payload))
  return normalizeModule(data)
}

export async function removeModulo(id: number | string): Promise<void> {
  await api.delete(ADMIN_MODULOS.byId(id))
}

export async function toggleModulo(id: number | string, activar: boolean): Promise<Module> {
  const endpoint = activar ? ADMIN_MODULOS.activar(id) : ADMIN_MODULOS.desactivar(id)
  const { data } = await api.post<Module>(endpoint)
  return normalizeModule(data)
}

export type RegistrarRespuesta = {
  registrados: string[]
  ya_existentes?: string[]
  ignorados?: string[]
}

export async function registrarModulosFS(): Promise<RegistrarRespuesta> {
  const { data } = await api.post<RegistrarRespuesta>(ADMIN_MODULOS.registrar)
  return data
}

// ---- Empresa <-> Módulos ----
export async function listModulosPublicos(): Promise<Module[]> {
  const { data } = await api.get<Module[]>(ADMIN_MODULOS.publicos)
  return (data || []).map(normalizeModule)
}

export async function listEmpresaModulos(empresaId: number | string): Promise<CompanyModule[]> {
  const { data } = await api.get<any[]>(ADMIN_MODULOS_EMPRESA.base(empresaId))
  return (
    data?.map((item) => ({
      id: String(item.id),
      tenant_id: String(item.tenant_id),
      company_slug: item.company_slug ?? null,
      module_id: String(item.module_id),
      active: Boolean(item.active),
      activation_date: item.activation_date ?? item.fecha_activacion ?? null,
      expiration_date: item.expiration_date ?? item.fecha_expiracion ?? null,
      initial_template: item.initial_template ?? item.plantilla_inicial ?? null,
      module: item.module ? normalizeModule(item.module) : (null as any),
    })) || []
  )
}

export async function upsertEmpresaModulo(
  empresaId: number | string,
  moduloId: string | number,
  payload?: { active?: boolean; expiration_date?: string | null; initial_template?: string | null },
) {
  const body = {
    module_id: moduloId,
    active: payload?.active ?? true,
    expiration_date: payload?.expiration_date,
    initial_template: payload?.initial_template,
  }
  const { data } = await api.post(ADMIN_MODULOS_EMPRESA.upsert(empresaId), body)
  return data
}

export async function removeEmpresaModulo(empresaId: number | string, moduloId: number | string): Promise<void> {
  await api.delete(ADMIN_MODULOS_EMPRESA.remove(empresaId, moduloId))
}
