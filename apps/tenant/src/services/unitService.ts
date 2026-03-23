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

const DEFAULT_UNITS: Unit[] = [
  { code: 'uds', label: 'Unidad' },
  { code: 'kg', label: 'Kilogramo' },
  { code: 'g', label: 'Gramo' },
  { code: 'L', label: 'Litro' },
  { code: 'ml', label: 'Mililitro' },
  { code: 'm', label: 'Metro' },
  { code: 'm2', label: 'Metro cuadrado' },
  { code: 'm3', label: 'Metro cubico' },
  { code: 'pair', label: 'Par' },
  { code: 'set', label: 'Juego' },
  { code: 'dozen', label: 'Docena' },
]

const UNIT_ALIASES: Record<string, string> = {
  '-': 'uds',
  un: 'uds',
  unit: 'uds',
  units: 'uds',
  und: 'uds',
  uni: 'uds',
  unid: 'uds',
  unidad: 'uds',
  unidades: 'uds',
  uds: 'uds',
  ud: 'uds',
  pcs: 'uds',
  pc: 'uds',
  pieza: 'uds',
  piezas: 'uds',
  pza: 'uds',
  cantidad: 'uds',
  doc: 'dozen',
  docena: 'dozen',
  docenas: 'dozen',
  dozen: 'dozen',
  kg: 'kg',
  kilo: 'kg',
  kilos: 'kg',
  kilogramo: 'kg',
  kilogramos: 'kg',
  g: 'g',
  gr: 'g',
  gramo: 'g',
  gramos: 'g',
  lb: 'lb',
  lbs: 'lb',
  libra: 'lb',
  libras: 'lb',
  pound: 'lb',
  pounds: 'lb',
  oz: 'oz',
  onza: 'oz',
  onzas: 'oz',
  ton: 'ton',
  tonelada: 'ton',
  toneladas: 'ton',
  mg: 'mg',
  l: 'L',
  lt: 'L',
  ltr: 'L',
  litr: 'L',
  litro: 'L',
  litros: 'L',
  ml: 'ml',
  mililitro: 'ml',
  mililitros: 'ml',
  gal: 'gal',
  galon: 'gal',
  galones: 'gal',
  qt: 'qt',
  pt: 'pt',
  cup: 'cup',
  fl_oz: 'fl_oz',
  tbsp: 'tbsp',
  tsp: 'tsp',
  pair: 'pair',
  par: 'pair',
  set: 'set',
  juego: 'set',
  m: 'm',
  metro: 'm',
  metros: 'm',
  m2: 'm2',
  'm^2': 'm2',
  m3: 'm3',
  'm^3': 'm3',
}

const STANDARD_UNIT_CODES = new Set([
  'uds',
  'dozen',
  'kg',
  'g',
  'lb',
  'oz',
  'ton',
  'mg',
  'L',
  'ml',
  'gal',
  'qt',
  'pt',
  'cup',
  'fl_oz',
  'tbsp',
  'tsp',
])

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

    const encodedCode = encodeURIComponent(sectorCode)
    const response = await tenantApi.get<SectorUnitsResponse>(
      `/api/v1/sectors/${encodedCode}/units`
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
  return DEFAULT_UNITS.map(unit => ({ ...unit }))
}

function sanitizeUnitToken(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .replace(/[-\s]+/g, '_')
    .replace(/[^\w]/g, '')
}

function normalizeKnownUnitCode(value: string | null | undefined): string {
  const raw = String(value || '').trim()
  if (!raw || raw === '-' || /^\d+$/.test(raw)) return 'uds'
  const lowered = raw.toLowerCase()
  if (UNIT_ALIASES[lowered]) return UNIT_ALIASES[lowered]
  const sanitized = sanitizeUnitToken(raw).toLowerCase()
  return UNIT_ALIASES[sanitized] || sanitized || 'uds'
}

export function normalizeUnitCode(
  value: string | null | undefined,
  units: Unit[] = getDefaultUnits()
): string {
  const raw = String(value || '').trim()
  const normalized = normalizeKnownUnitCode(raw)

  for (const unit of units) {
    if (!unit?.code) continue
    if (raw && unit.code.toLowerCase() === raw.toLowerCase()) return unit.code
    if (normalizeKnownUnitCode(unit.code).toLowerCase() === normalized.toLowerCase()) {
      return unit.code
    }
  }

  return normalized
}

export function isStandardUnitCode(value: string | null | undefined): boolean {
  return STANDARD_UNIT_CODES.has(normalizeKnownUnitCode(value))
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

  const normalized = normalizeUnitCode(code, units)
  return units.find(u => normalizeUnitCode(u.code, units) === normalized) || null
}

// ── Conversion tables ────────────────────────────────────────────────────────
// Each entry: [fromUnit, toUnit, factor]  →  result = qty * factor
const UNIT_CONVERSIONS: [string, string, number][] = [
  // Mass
  ['g',   'kg',  1 / 1000],
  ['kg',  'g',   1000],
  ['g',   'lb',  1 / 453.592],
  ['lb',  'g',   453.592],
  ['g',   'oz',  1 / 28.3495],
  ['oz',  'g',   28.3495],
  ['kg',  'lb',  2.20462],
  ['lb',  'kg',  1 / 2.20462],
  ['kg',  'oz',  35.274],
  ['oz',  'kg',  1 / 35.274],
  ['lb',  'oz',  16],
  ['oz',  'lb',  1 / 16],
  ['ton', 'kg',  1000],
  ['kg',  'ton', 1 / 1000],
  ['ton', 'lb',  2204.62],
  ['lb',  'ton', 1 / 2204.62],
  ['mg',  'g',   1 / 1000],
  ['g',   'mg',  1000],
  // Volume
  ['ml',  'L',   1 / 1000],
  ['L',   'ml',  1000],
  ['gal', 'L',   3.78541],
  ['L',   'gal', 1 / 3.78541],
  ['qt',  'L',   0.946353],
  ['L',   'qt',  1 / 0.946353],
  ['pt',  'L',   0.473176],
  ['L',   'pt',  1 / 0.473176],
  ['cup', 'ml',  236.588],
  ['ml',  'cup', 1 / 236.588],
  ['fl_oz','ml', 29.5735],
  ['ml',  'fl_oz', 1 / 29.5735],
  ['tbsp','ml',  14.7868],
  ['ml',  'tbsp', 1 / 14.7868],
  ['tsp', 'ml',  4.92892],
  ['ml',  'tsp', 1 / 4.92892],
]

const conversionMap = new Map<string, number>()
for (const [from, to, factor] of UNIT_CONVERSIONS) {
  conversionMap.set(`${from}→${to}`, factor)
}

/**
 * Convierte una cantidad de `fromUnit` a `toUnit`.
 * Devuelve el valor original si las unidades son incompatibles o iguales.
 */
export function convertQtyToUnit(
  qty: number,
  fromUnit: string | null | undefined,
  toUnit: string | null | undefined,
): number {
  const from = normalizeKnownUnitCode(fromUnit)
  const to   = normalizeKnownUnitCode(toUnit)
  if (from === to) return qty
  const factor = conversionMap.get(`${from}→${to}`)
  return factor != null ? qty * factor : qty
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
