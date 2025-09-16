import type { Fichaje } from '../types/fichaje'

export async function getFichajes(): Promise<Fichaje[]> {
  return [
    { id: '1', empleadoId: '1', fecha: '2025-08-06', horaInicio: '08:00', horaFin: '17:00', tipo: 'trabajo' },
  ]
}

export async function registrarFichaje(_tipo: 'entrada' | 'salida'): Promise<void> {
  return
}

