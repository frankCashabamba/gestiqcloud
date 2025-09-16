import { recibosMock } from '../mock/recibosMock'
import type { ReciboNomina } from '../types/nomina'

export async function getRecibos(): Promise<ReciboNomina[]> {
  return new Promise((resolve) => setTimeout(() => resolve(recibosMock), 300))
}

