import tenantApi from '../../../shared/api/client'
import { TENANT_HR } from '@shared/endpoints'
import type { Fichaje } from '../types/fichaje'

type TimeEntryApi = {
  id: string
  empleado_id: string
  fecha: string
  hora_inicio: string
  hora_fin?: string | null
  tipo: 'trabajo' | 'descanso' | 'otro'
  notas?: string | null
}

function normalizeEntry(entry: TimeEntryApi): Fichaje {
  return {
    id: entry.id,
    empleadoId: entry.empleado_id,
    fecha: entry.fecha,
    horaInicio: entry.hora_inicio,
    horaFin: entry.hora_fin || undefined,
    tipo: entry.tipo,
  }
}

export async function getFichajes(): Promise<Fichaje[]> {
  const { data } = await tenantApi.get<TimeEntryApi[] | { items?: TimeEntryApi[] }>(
    TENANT_HR.timekeeping.base
  )
  const items = Array.isArray(data) ? data : data?.items || []
  return items.map(normalizeEntry)
}

export async function registrarFichaje(payload: {
  empleadoId: string
  fecha: string
  horaInicio: string
  horaFin?: string
  tipo?: 'trabajo' | 'descanso' | 'otro'
  notas?: string
}): Promise<Fichaje> {
  const { data } = await tenantApi.post<TimeEntryApi>(TENANT_HR.timekeeping.base, {
    empleado_id: payload.empleadoId,
    fecha: payload.fecha,
    hora_inicio: payload.horaInicio,
    hora_fin: payload.horaFin,
    tipo: payload.tipo || 'trabajo',
    notas: payload.notas,
  })
  return normalizeEntry(data)
}

export async function actualizarFichaje(
  id: string,
  payload: {
    horaInicio?: string
    horaFin?: string
    tipo?: 'trabajo' | 'descanso' | 'otro'
    notas?: string
  }
): Promise<Fichaje> {
  const { data } = await tenantApi.patch<TimeEntryApi>(TENANT_HR.timekeeping.byId(id), {
    hora_inicio: payload.horaInicio,
    hora_fin: payload.horaFin,
    tipo: payload.tipo,
    notas: payload.notas,
  })
  return normalizeEntry(data)
}
