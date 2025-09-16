import api from '../../shared/api/client'
import { ADMIN_CONFIG } from '@shared/endpoints'

export type DiaSemana = { id: number; nombre: string }

export type HorarioAtencion = {
  id: number
  dia_id: number
  inicio: string
  fin: string
}

export async function listHorarios(): Promise<HorarioAtencion[]> {
  const { data } = await api.get<HorarioAtencion[]>(ADMIN_CONFIG.horarioAtencion.base)
  return data || []
}

export async function getHorario(id: number | string): Promise<HorarioAtencion> {
  const { data } = await api.get<HorarioAtencion>(ADMIN_CONFIG.horarioAtencion.byId(id))
  return data
}

export async function createHorario(payload: Omit<HorarioAtencion, 'id'>): Promise<HorarioAtencion> {
  const { data } = await api.post<HorarioAtencion>(ADMIN_CONFIG.horarioAtencion.base, payload)
  return data
}

export async function updateHorario(id: number | string, payload: Omit<HorarioAtencion, 'id'>): Promise<HorarioAtencion> {
  const { data } = await api.put<HorarioAtencion>(ADMIN_CONFIG.horarioAtencion.byId(id), payload)
  return data
}

export async function removeHorario(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.horarioAtencion.byId(id))
}

export async function listDiasSemana(): Promise<DiaSemana[]> {
  const { data } = await api.get<DiaSemana[]>(ADMIN_CONFIG.diasSemana.base)
  return data || []
}

