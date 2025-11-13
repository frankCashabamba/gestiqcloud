/**
 * Generador automático de códigos de barras para productos
 *
 * Casos de uso:
 * - Productos de cliente real sin código de barras
 * - Generación masiva desde Excel
 * - Productos internos de tienda
 */

export type BarcodeFormat =
  | 'EAN13'    // Estándar europeo (13 dígitos)
  | 'EAN8'     // Versión corta (8 dígitos)
  | 'CODE128'  // Alfanumérico (uso interno)
  | 'CODE39'   // Alfanumérico simple

export type BarcodeGeneratorConfig = {
  /** Formato del código de barras */
  format: BarcodeFormat
  /** Prefijo para identificar la tienda/tenant (2-3 dígitos) */
  prefix?: string
  /** ¿Usar checksum? (recomendado para EAN) */
  useChecksum?: boolean
  /** Rango de inicio para secuencia */
  startFrom?: number
}

/**
 * Calcula el dígito de control para EAN-13
 * Algoritmo estándar: módulo 10 con pesos alternados 1-3
 */
export function calculateEAN13Checksum(code: string): string {
  if (code.length !== 12) {
    throw new Error('EAN-13 checksum requires 12 digits')
  }

  let sum = 0
  for (let i = 0; i < 12; i++) {
    const digit = parseInt(code[i], 10)
    sum += digit * (i % 2 === 0 ? 1 : 3)
  }

  const checksum = (10 - (sum % 10)) % 10
  return checksum.toString()
}

/**
 * Calcula el dígito de control para EAN-8
 */
export function calculateEAN8Checksum(code: string): string {
  if (code.length !== 7) {
    throw new Error('EAN-8 checksum requires 7 digits')
  }

  let sum = 0
  for (let i = 0; i < 7; i++) {
    const digit = parseInt(code[i], 10)
    sum += digit * (i % 2 === 0 ? 3 : 1) // Invertido respecto a EAN-13
  }

  const checksum = (10 - (sum % 10)) % 10
  return checksum.toString()
}

/**
 * Genera un código EAN-13 válido
 *
 * Estructura EAN-13:
 * - 2-3 dígitos: Prefijo del país/tienda (ej: "200-299" = uso interno)
 * - 9-10 dígitos: Código del producto
 * - 1 dígito: Checksum
 *
 * @example
 * generateEAN13({ prefix: '200', sequence: 1 })
 * // => '2000000000018' (200 + 000000001 + checksum=8)
 */
export function generateEAN13(config: { prefix: string; sequence: number }): string {
  const { prefix, sequence } = config

  if (prefix.length < 2 || prefix.length > 3) {
    throw new Error('EAN-13 prefix must be 2-3 digits')
  }

  // Calcular cuántos dígitos quedan para el producto
  const remainingDigits = 12 - prefix.length
  const productCode = sequence.toString().padStart(remainingDigits, '0')

  if (productCode.length > remainingDigits) {
    throw new Error(`Sequence ${sequence} exceeds available digits`)
  }

  const code12 = prefix + productCode
  const checksum = calculateEAN13Checksum(code12)

  return code12 + checksum
}

/**
 * Genera un código EAN-8 válido (versión corta)
 */
export function generateEAN8(config: { prefix: string; sequence: number }): string {
  const { prefix, sequence } = config

  if (prefix.length !== 2) {
    throw new Error('EAN-8 prefix must be 2 digits')
  }

  const productCode = sequence.toString().padStart(5, '0')
  if (productCode.length > 5) {
    throw new Error(`Sequence ${sequence} exceeds available digits`)
  }

  const code7 = prefix + productCode
  const checksum = calculateEAN8Checksum(code7)

  return code7 + checksum
}

/**
 * Genera un código CODE-128 (alfanumérico, uso interno)
 * Más flexible, soporta letras y números
 *
 * @example
 * generateCODE128({ prefix: 'INT', sequence: 1 })
 * // => 'INT-000001'
 */
export function generateCODE128(config: { prefix: string; sequence: number }): string {
  const { prefix, sequence } = config
  const sequenceStr = sequence.toString().padStart(6, '0')
  return `${prefix}-${sequenceStr}`
}

/**
 * Genera un código CODE-39 (alfanumérico simple)
 */
export function generateCODE39(config: { prefix: string; sequence: number }): string {
  const { prefix, sequence } = config
  // CODE-39 soporta: 0-9, A-Z, y algunos caracteres especiales
  const sequenceStr = sequence.toString().padStart(5, '0')
  return `${prefix}${sequenceStr}`
}

/**
 * Generador de códigos de barras con contador interno
 * Útil para importaciones masivas
 *
 * IMPORTANTE: Por defecto genera códigos VIRTUALES/INTERNOS (prefijo 200-299)
 * Estos códigos NO son EAN del fabricante, solo para uso interno con pistola lectora.
 */
export class BarcodeGenerator {
  private config: Required<BarcodeGeneratorConfig>
  private currentSequence: number

  constructor(config: BarcodeGeneratorConfig) {
    this.config = {
      format: config.format,
      prefix: config.prefix || '200', // 200-299 = VIRTUAL/INTERNO (no EAN del fabricante)
      useChecksum: config.useChecksum ?? true,
      startFrom: config.startFrom || 1,
    }
    this.currentSequence = this.config.startFrom
  }

  /**
   * Genera el siguiente código de barras
   */
  next(): string {
    const barcode = this.generate(this.currentSequence)
    this.currentSequence++
    return barcode
  }

  /**
   * Genera un código de barras para una secuencia específica
   */
  generate(sequence: number): string {
    const { format, prefix } = this.config

    switch (format) {
      case 'EAN13':
        return generateEAN13({ prefix, sequence })
      case 'EAN8':
        return generateEAN8({ prefix, sequence })
      case 'CODE128':
        return generateCODE128({ prefix, sequence })
      case 'CODE39':
        return generateCODE39({ prefix, sequence })
      default:
        throw new Error(`Unsupported barcode format: ${format}`)
    }
  }

  /**
   * Genera múltiples códigos de barras
   */
  generateBatch(count: number): string[] {
    const barcodes: string[] = []
    for (let i = 0; i < count; i++) {
      barcodes.push(this.next())
    }
    return barcodes
  }

  /**
   * Resetea el contador
   */
  reset(startFrom?: number): void {
    this.currentSequence = startFrom ?? this.config.startFrom
  }

  /**
   * Obtiene la secuencia actual
   */
  getCurrentSequence(): number {
    return this.currentSequence
  }
}

/**
 * Valida si un código de barras es válido
 */
export function validateBarcode(barcode: string, format: BarcodeFormat): boolean {
  try {
    switch (format) {
      case 'EAN13':
        if (barcode.length !== 13 || !/^\d+$/.test(barcode)) return false
        const ean13Check = calculateEAN13Checksum(barcode.slice(0, 12))
        return barcode[12] === ean13Check

      case 'EAN8':
        if (barcode.length !== 8 || !/^\d+$/.test(barcode)) return false
        const ean8Check = calculateEAN8Checksum(barcode.slice(0, 7))
        return barcode[7] === ean8Check

      case 'CODE128':
      case 'CODE39':
        // Validación básica de caracteres
        return /^[A-Z0-9\-]+$/.test(barcode)

      default:
        return false
    }
  } catch {
    return false
  }
}

/**
 * Detecta el formato de un código de barras
 */
export function detectBarcodeFormat(barcode: string): BarcodeFormat | null {
  if (/^\d{13}$/.test(barcode) && validateBarcode(barcode, 'EAN13')) return 'EAN13'
  if (/^\d{8}$/.test(barcode) && validateBarcode(barcode, 'EAN8')) return 'EAN8'
  if (/^[A-Z]+-\d{6}$/.test(barcode)) return 'CODE128'
  if (/^[A-Z0-9]{6,}$/.test(barcode)) return 'CODE39'
  return null
}

/**
 * Configuración recomendada según país
 */
export const COUNTRY_BARCODE_CONFIG: Record<string, BarcodeGeneratorConfig> = {
  ES: {
    format: 'EAN13',
    prefix: '84', // España
    useChecksum: true,
  },
  EC: {
    format: 'EAN13',
    prefix: '786', // Ecuador
    useChecksum: true,
  },
  INTERNAL: {
    format: 'EAN13',
    prefix: '200', // Uso interno (200-299)
    useChecksum: true,
  },
  SIMPLE: {
    format: 'CODE128',
    prefix: 'INT',
    useChecksum: false,
  },
}

/**
 * Obtiene un generador configurado para el país
 */
export function getBarcodeGeneratorForCountry(
  country: 'ES' | 'EC' | 'INTERNAL' | 'SIMPLE',
  startFrom?: number
): BarcodeGenerator {
  const config = { ...COUNTRY_BARCODE_CONFIG[country], startFrom }
  return new BarcodeGenerator(config)
}
