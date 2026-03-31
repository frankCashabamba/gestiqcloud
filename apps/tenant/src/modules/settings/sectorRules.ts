const BAKERY_OPERATIVE_SECTORS = new Set(['panaderia', 'panaderia_pro', 'bakery', 'bakery_pro'])

export function isBakeryOperativeSector(value?: string | null) {
  return BAKERY_OPERATIVE_SECTORS.has((value || '').trim().toLowerCase())
}
