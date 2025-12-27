/**
 * sectorHelpers
 *
 * Helper functions for sectors/templates.
 */

export function getSectorIcon(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const iconMap: Record<string, string> = {
    panaderia: 'B',
    bakery: 'B',
    pasteleria: 'P',
    reposteria: 'P',

    taller: 'T',
    tallermecanico: 'T',
    tallermotriz: 'T',
    mecanica: 'T',
    automotriz: 'T',
    workshop: 'T',

    retail: 'R',
    tienda: 'R',
    bazar: 'R',
    comercio: 'R',
    store: 'R',

    restaurante: 'F',
    restaurant: 'F',
    cafeteria: 'C',
    bar: 'B',

    farmacia: 'P',
    pharmacy: 'P',

    veterinaria: 'V',
    vet: 'V',

    ferreteria: 'H',
    hardware: 'H',

    libreria: 'L',
    bookstore: 'L',

    peluqueria: 'S',
    salon: 'S',
    estetica: 'B',
    spa: 'S',

    default: 'G',
    general: 'G',
  }

  return iconMap[normalized] || iconMap.default
}

export function getSectorColor(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const colorMap: Record<string, string> = {
    panaderia: '#f59e0b',
    bakery: '#f59e0b',
    pasteleria: '#ec4899',
    reposteria: '#ec4899',

    taller: '#1e40af',
    tallermecanico: '#1e40af',
    tallermotriz: '#1e3a8a',
    mecanica: '#1e40af',
    automotriz: '#1e3a8a',
    workshop: '#1e40af',

    retail: '#059669',
    tienda: '#059669',
    bazar: '#10b981',
    comercio: '#059669',
    store: '#059669',

    restaurante: '#dc2626',
    restaurant: '#dc2626',
    cafeteria: '#7c2d12',
    bar: '#92400e',

    farmacia: '#0891b2',
    pharmacy: '#0891b2',

    veterinaria: '#16a34a',
    vet: '#16a34a',

    ferreteria: '#4b5563',
    hardware: '#4b5563',

    libreria: '#7c3aed',
    bookstore: '#7c3aed',

    peluqueria: '#db2777',
    salon: '#db2777',
    estetica: '#ec4899',
    spa: '#c026d3',

    default: '#6366f1',
    general: '#6366f1',
  }

  return colorMap[normalized] || colorMap.default
}

export function formatBySector(
  value: any,
  type: 'currency' | 'quantity' | 'date' | 'weight' | 'percentage',
  plantilla?: string,
  currency: string = 'EUR'
): string {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  const normalized = plantilla?.toLowerCase().replace(/[_-]/g, '') || 'default'

  switch (type) {
    case 'currency': {
      const numValue = typeof value === 'string' ? parseFloat(value) : value
      return new Intl.NumberFormat(currency === 'USD' ? 'en-US' : 'en-GB', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(numValue)
    }

    case 'quantity':
      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        return `${Math.floor(parseFloat(value))} units`
      }

      if (normalized.includes('taller') || normalized.includes('workshop')) {
        return `${parseFloat(value).toFixed(2)} units`
      }

      return `${Math.floor(parseFloat(value))}`

    case 'weight': {
      const weight = parseFloat(value)
      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        if (weight < 1) {
          return `${Math.round(weight * 1000)} g`
        }
        return `${weight.toFixed(2)} kg`
      }

      return `${weight.toFixed(3)} kg`
    }

    case 'date': {
      const date = new Date(value)

      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        return date.toLocaleDateString('en-GB', {
          day: '2-digit',
          month: 'short',
        })
      }

      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    }

    case 'percentage':
      return `${parseFloat(value).toFixed(1)}%`

    default:
      return String(value)
  }
}

export function getSectorDisplayName(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const nameMap: Record<string, string> = {
    panaderia: 'Bakery',
    bakery: 'Bakery',
    pasteleria: 'Pastry Shop',
    reposteria: 'Confectionery',
    taller: 'Auto Shop',
    tallermecanico: 'Auto Shop',
    tallermotriz: 'Auto Shop',
    mecanica: 'Mechanic',
    automotriz: 'Automotive',
    workshop: 'Workshop',
    retail: 'Retail',
    tienda: 'Store',
    bazar: 'Bazaar',
    comercio: 'Commerce',
    restaurante: 'Restaurant',
    restaurant: 'Restaurant',
    cafeteria: 'Cafe',
    bar: 'Bar',
    farmacia: 'Pharmacy',
    pharmacy: 'Pharmacy',
    veterinaria: 'Veterinary',
    vet: 'Veterinary',
    ferreteria: 'Hardware',
    hardware: 'Hardware',
    libreria: 'Bookstore',
    bookstore: 'Bookstore',
    peluqueria: 'Hair Salon',
    salon: 'Beauty Salon',
    estetica: 'Esthetics',
    spa: 'Spa',
    default: 'General',
    general: 'General',
  }

  return (
    nameMap[normalized] ||
    plantilla
      .split(/[_-]/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  )
}

export function getSectorUnits(plantilla: string): Array<[string, string]> {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    return [
      ['unit', 'Unit'],
      ['kg', 'Kilogram'],
      ['g', 'Gram'],
      ['dozen', 'Dozen'],
    ]
  }

  if (normalized.includes('taller') || normalized.includes('workshop')) {
    return [
      ['unit', 'Unit'],
      ['pair', 'Pair'],
      ['set', 'Set'],
      ['l', 'Liter'],
      ['ml', 'Milliliter'],
    ]
  }

  return [
    ['unit', 'Unit'],
    ['kg', 'Kilogram'],
    ['l', 'Liter'],
    ['m', 'Meter'],
    ['m2', 'Square meter'],
    ['m3', 'Cubic meter'],
  ]
}

export function getSectorPrintConfig(plantilla: string): {
  width: number
  fontSize: number
  showLogo: boolean
  showDetails: boolean
} {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    return {
      width: 58,
      fontSize: 9,
      showLogo: false,
      showDetails: false,
    }
  }

  if (normalized.includes('taller') || normalized.includes('workshop')) {
    return {
      width: 80,
      fontSize: 10,
      showLogo: true,
      showDetails: true,
    }
  }

  return {
    width: 58,
    fontSize: 10,
    showLogo: true,
    showDetails: false,
  }
}

export function isFieldRequired(
  fieldName: string,
  plantilla: string,
  context: 'product' | 'inventory' | 'sale'
): boolean {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    if (context === 'product' && fieldName === 'expires_at') return true
    if (context === 'inventory' && fieldName === 'expires_at') return true
  }

  if (normalized.includes('taller') || normalized.includes('workshop')) {
    if (context === 'product' && fieldName === 'codigo_oem') return false
  }

  if (normalized.includes('retail') || normalized.includes('tienda')) {
    if (context === 'product' && fieldName === 'sku') return true
  }

  return false
}
