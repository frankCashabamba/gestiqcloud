/**
 * sectorHelpers
 * 
 * Funciones helper para manejo de sectores/plantillas
 * Íconos, colores, formateo, etc.
 */

/**
 * Retorna el emoji/icono correspondiente al sector
 * 
 * @param plantilla - Nombre de la plantilla/sector
 * @returns Emoji representativo
 */
export function getSectorIcon(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const iconMap: Record<string, string> = {
    // Panadería
    panaderia: '🥐',
    bakery: '🥐',
    pasteleria: '🍰',
    reposteria: '🧁',

    // Taller Mecánico
    taller: '🔧',
    tallermecánico: '🔧',
    tallermotriz: '🚗',
    mecanica: '🔧',
    automotriz: '🚗',
    workshop: '🔧',

    // Retail
    retail: '🏪',
    tienda: '🏬',
    bazar: '🛒',
    comercio: '🏪',
    store: '🏪',

    // Restaurante
    restaurante: '🍽️',
    restaurant: '🍽️',
    cafeteria: '☕',
    bar: '🍺',

    // Farmacia
    farmacia: '💊',
    pharmacy: '💊',

    // Veterinaria
    veterinaria: '🐾',
    vet: '🐾',

    // Ferretería
    ferreteria: '🔨',
    hardware: '🔨',

    // Librería
    libreria: '📚',
    bookstore: '📚',

    // Belleza
    peluqueria: '💇',
    salon: '💇',
    estetica: '💅',
    spa: '🧖',

    // Default
    default: '🏢',
    general: '🏢'
  }

  return iconMap[normalized] || iconMap.default
}

/**
 * Retorna el color hexadecimal correspondiente al sector
 * 
 * @param plantilla - Nombre de la plantilla/sector
 * @returns Color hex (ej: '#f59e0b')
 */
export function getSectorColor(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const colorMap: Record<string, string> = {
    // Panadería - Amarillo/Dorado
    panaderia: '#f59e0b',
    bakery: '#f59e0b',
    pasteleria: '#ec4899',
    reposteria: '#ec4899',

    // Taller - Azul oscuro
    taller: '#1e40af',
    tallermecánico: '#1e40af',
    tallermotriz: '#1e3a8a',
    mecanica: '#1e40af',
    automotriz: '#1e3a8a',
    workshop: '#1e40af',

    // Retail - Verde
    retail: '#059669',
    tienda: '#059669',
    bazar: '#10b981',
    comercio: '#059669',
    store: '#059669',

    // Restaurante - Rojo
    restaurante: '#dc2626',
    restaurant: '#dc2626',
    cafeteria: '#7c2d12',
    bar: '#92400e',

    // Farmacia - Verde azulado
    farmacia: '#0891b2',
    pharmacy: '#0891b2',

    // Veterinaria - Verde suave
    veterinaria: '#16a34a',
    vet: '#16a34a',

    // Ferretería - Gris oscuro
    ferreteria: '#4b5563',
    hardware: '#4b5563',

    // Librería - Morado
    libreria: '#7c3aed',
    bookstore: '#7c3aed',

    // Belleza - Rosa
    peluqueria: '#db2777',
    salon: '#db2777',
    estetica: '#ec4899',
    spa: '#c026d3',

    // Default
    default: '#6366f1',
    general: '#6366f1'
  }

  return colorMap[normalized] || colorMap.default
}

/**
 * Formatea un valor según las convenciones del sector
 * 
 * @param value - Valor a formatear
 * @param type - Tipo de dato ('currency', 'quantity', 'date', 'weight')
 * @param plantilla - Plantilla/sector activo
 * @param currency - Código de moneda (default: 'EUR')
 * @returns String formateado
 */
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
    case 'currency':
      const numValue = typeof value === 'string' ? parseFloat(value) : value
      return new Intl.NumberFormat(currency === 'USD' ? 'es-EC' : 'es-ES', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(numValue)

    case 'quantity':
      // Panadería usa unidades sin decimales (panes enteros)
      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        return `${Math.floor(parseFloat(value))} uds`
      }
      
      // Taller puede tener decimales (repuestos fraccionables)
      if (normalized.includes('taller') || normalized.includes('workshop')) {
        return `${parseFloat(value).toFixed(2)} uds`
      }

      // Default: 0 decimales
      return `${Math.floor(parseFloat(value))}`

    case 'weight':
      const weight = parseFloat(value)
      // Panadería usa gramos y kilos
      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        if (weight < 1) {
          return `${Math.round(weight * 1000)}g`
        }
        return `${weight.toFixed(2)}kg`
      }
      
      return `${weight.toFixed(3)}kg`

    case 'date':
      const date = new Date(value)
      
      // Panadería: formato corto (día/mes)
      if (normalized.includes('panaderia') || normalized.includes('bakery')) {
        return date.toLocaleDateString('es-ES', {
          day: '2-digit',
          month: 'short'
        })
      }

      // Default: formato completo
      return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      })

    case 'percentage':
      return `${parseFloat(value).toFixed(1)}%`

    default:
      return String(value)
  }
}

/**
 * Retorna el nombre displayable del sector
 * 
 * @param plantilla - Nombre técnico de la plantilla
 * @returns Nombre formateado para mostrar
 */
export function getSectorDisplayName(plantilla: string): string {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  const nameMap: Record<string, string> = {
    panaderia: 'Panadería',
    bakery: 'Panadería',
    pasteleria: 'Pastelería',
    reposteria: 'Repostería',
    taller: 'Taller Mecánico',
    tallermecánico: 'Taller Mecánico',
    tallermotriz: 'Taller Automotriz',
    mecanica: 'Mecánica',
    automotriz: 'Automotriz',
    workshop: 'Taller',
    retail: 'Retail',
    tienda: 'Tienda',
    bazar: 'Bazar',
    comercio: 'Comercio',
    restaurante: 'Restaurante',
    restaurant: 'Restaurante',
    cafeteria: 'Cafetería',
    bar: 'Bar',
    farmacia: 'Farmacia',
    pharmacy: 'Farmacia',
    veterinaria: 'Veterinaria',
    vet: 'Veterinaria',
    ferreteria: 'Ferretería',
    hardware: 'Ferretería',
    libreria: 'Librería',
    bookstore: 'Librería',
    peluqueria: 'Peluquería',
    salon: 'Salón de Belleza',
    estetica: 'Estética',
    spa: 'Spa',
    default: 'General',
    general: 'General'
  }

  return nameMap[normalized] || plantilla
    .split(/[_-]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * Retorna las unidades de medida típicas del sector
 * 
 * @param plantilla - Plantilla/sector
 * @returns Array de unidades [código, label]
 */
export function getSectorUnits(plantilla: string): Array<[string, string]> {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    return [
      ['unit', 'Unidad'],
      ['kg', 'Kilogramo'],
      ['g', 'Gramo'],
      ['dozen', 'Docena']
    ]
  }

  if (normalized.includes('taller') || normalized.includes('workshop')) {
    return [
      ['unit', 'Unidad'],
      ['pair', 'Par'],
      ['set', 'Juego'],
      ['l', 'Litro'],
      ['ml', 'Mililitro']
    ]
  }

  // Default
  return [
    ['unit', 'Unidad'],
    ['kg', 'Kilogramo'],
    ['l', 'Litro'],
    ['m', 'Metro'],
    ['m2', 'Metro cuadrado'],
    ['m3', 'Metro cúbico']
  ]
}

/**
 * Retorna configuración de impresión por sector
 * 
 * @param plantilla - Plantilla/sector
 * @returns Config de impresión
 */
export function getSectorPrintConfig(plantilla: string): {
  width: number
  fontSize: number
  showLogo: boolean
  showDetails: boolean
} {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  // Panadería: tickets simples y rápidos
  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    return {
      width: 58,
      fontSize: 9,
      showLogo: false,
      showDetails: false
    }
  }

  // Taller: tickets detallados
  if (normalized.includes('taller') || normalized.includes('workshop')) {
    return {
      width: 80,
      fontSize: 10,
      showLogo: true,
      showDetails: true
    }
  }

  // Retail: balance
  return {
    width: 58,
    fontSize: 10,
    showLogo: true,
    showDetails: false
  }
}

/**
 * Validaciones específicas por sector (helper simple)
 * Ver useSectorValidation.ts para validaciones completas
 */
export function isFieldRequired(
  fieldName: string,
  plantilla: string,
  context: 'product' | 'inventory' | 'sale'
): boolean {
  const normalized = plantilla.toLowerCase().replace(/[_-]/g, '')

  // Panadería
  if (normalized.includes('panaderia') || normalized.includes('bakery')) {
    if (context === 'product' && fieldName === 'expires_at') return true
    if (context === 'inventory' && fieldName === 'expires_at') return true
  }

  // Taller
  if (normalized.includes('taller') || normalized.includes('workshop')) {
    if (context === 'product' && fieldName === 'codigo_oem') return false // Recomendado, no obligatorio
  }

  // Retail
  if (normalized.includes('retail') || normalized.includes('tienda')) {
    if (context === 'product' && fieldName === 'sku') return true
  }

  return false
}
