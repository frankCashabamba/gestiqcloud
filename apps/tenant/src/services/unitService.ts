/**
 * Unit Service
 *
 * Servicio para obtener unidades de medida dinámicamente desde BD.
 * Reemplaza hardcoding anterior de getSectorUnits() en sectorHelpers.ts
 *
 * Endpoints:
 * - GET /api/v1/sectors/{code}/units - Obtener unidades por sector
 */

import tenantApi from '../shared/api/client'

export interface Unit {
  code: string
  label: string
}

export interface SectorUnitsResponse {
  ok: boolean
  code: string
  units: Unit[]
}

/**
 * Obtiene unidades de medida para un sector desde BD
 *
 * @param sectorCode - Código del sector (ej: 'panaderia', 'taller')
 * @returns Lista de unidades disponibles
 */
export async function getSectorUnits(sectorCode: string): Promise<Unit[]> {
  try {
    if (!sectorCode) {
      return getDefaultUnits()
    }

    const response = await tenantApi.get<SectorUnitsResponse>(
      `/api/v1/sectors/${sectorCode}/units`
    )

    if (!response.data.ok || !response.data.units) {
      console.warn('Invalid units response from API:', response.data)
      return getDefaultUnits()
    }

    return response.data.units
  } catch (error) {
    console.error(
      `Error obteniendo unidades del sector '${sectorCode}':`,
      error
    )
    return getDefaultUnits()
  }
}

/**
 * Unidades por defecto (fallback)
 *
 * Se usan cuando:
 * - No hay sector configurado
 * - El API falla
 * - No hay unidades en BD
 */
export function getDefaultUnits(): Unit[] {
  return [
    { code: 'unit', label: 'Unidad' },
    { code: 'kg', label: 'Kilogramo' },
    { code: 'g', label: 'Gramo' },
    { code: 'l', label: 'Litro' },
    { code: 'ml', label: 'Mililitro' },
    { code: 'm', label: 'Metro' },
    { code: 'm2', label: 'Metro cuadrado' },
    { code: 'm3', label: 'Metro cúbico' },
    { code: 'pair', label: 'Par' },
    { code: 'set', label: 'Juego' },
    { code: 'dozen', label: 'Docena' },
  ]
}

/**
 * Obtener unidad por código
 *
 * @param code - Código de la unidad
 * @param sectorCode - Código del sector (para cargar unidades correctas)
 * @returns Unidad encontrada o null
 */
export async function getUnitByCode(
  code: string,
  sectorCode?: string
): Promise<Unit | null> {
  const units = await getSectorUnits(sectorCode || '')

  return units.find(u => u.code === code) || null
}

/**
 * Formatear valor con unidad
 *
 * Ejemplo: formatWithUnit(5, 'kg') → '5 kg'
 */
export function formatWithUnit(value: number | string, unitCode: string, units: Unit[]): string {
  const unit = units.find(u => u.code === unitCode)
  const label = unit?.label || unitCode

  return `${value} ${label}`.trim()
}
