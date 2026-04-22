import { ADMIN_CONFIG } from '@shared/endpoints'

import api from '../../shared/api/client'

export type DiaSemana = { id: number; name: string }

export type HorarioAtencion = {
  id: number
  dayId: number
  startTime: string
  endTime: string
}

function normalizeHorario(raw: any): HorarioAtencion {
  return {
    id: Number(raw?.id ?? 0),
    dayId: Number(raw?.dayId ?? raw?.dia_id ?? 0),
    startTime: String(raw?.startTime ?? raw?.inicio ?? ''),
    endTime: String(raw?.endTime ?? raw?.fin ?? ''),
  }
}

function toApiHorario(payload: Omit<HorarioAtencion, 'id'>) {
  return {
    dia_id: payload.dayId,
    inicio: payload.startTime,
    fin: payload.endTime,
  }
}

export async function listHorarios(): Promise<HorarioAtencion[]> {
  const { data } = await api.get<HorarioAtencion[]>(ADMIN_CONFIG.attentionSchedule.base)
  return (data || []).map(normalizeHorario)
}

export async function getHorario(id: number | string): Promise<HorarioAtencion> {
  const { data } = await api.get<HorarioAtencion>(ADMIN_CONFIG.attentionSchedule.byId(id))
  return normalizeHorario(data)
}

export async function createHorario(payload: Omit<HorarioAtencion, 'id'>): Promise<HorarioAtencion> {
  const { data } = await api.post<HorarioAtencion>(ADMIN_CONFIG.attentionSchedule.base, toApiHorario(payload))
  return normalizeHorario(data)
}

export async function updateHorario(id: number | string, payload: Omit<HorarioAtencion, 'id'>): Promise<HorarioAtencion> {
  const { data } = await api.put<HorarioAtencion>(ADMIN_CONFIG.attentionSchedule.byId(id), toApiHorario(payload))
  return normalizeHorario(data)
}

export async function removeHorario(id: number | string): Promise<void> {
  await api.delete(ADMIN_CONFIG.attentionSchedule.byId(id))
}

export async function listDiasSemana(): Promise<DiaSemana[]> {
  const { data } = await api.get<DiaSemana[]>(ADMIN_CONFIG.weekdays.base)
  return (data || []).map((raw: any) => ({
    id: Number(raw?.id ?? 0),
    name: String(raw?.name ?? raw?.nombre ?? ''),
  }))
}
