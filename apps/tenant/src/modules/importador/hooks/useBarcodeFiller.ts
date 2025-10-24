/**
 * Hook para auto-generar códigos de barras faltantes durante importación
 * 
 * Casos de uso:
 * - Excel de cliente real sin códigos de barras
 * - Productos nuevos que necesitan códigos
 * - Generación masiva automática
 */

import { useState, useCallback, useMemo } from 'react'
import { BarcodeGenerator, getBarcodeGeneratorForCountry, validateBarcode, detectBarcodeFormat } from '../utils/barcodeGenerator'

type ProductRow = {
  id?: string
  sku: string
  nombre: string
  codigo_barras?: string
  [key: string]: any
}

type UseBarcodeFiller = {
  /** Productos procesados con códigos generados */
  productsWithBarcodes: ProductRow[]
  /** Cantidad de códigos generados */
  generatedCount: number
  /** ¿Hay productos sin código? */
  hasMissingBarcodes: boolean
  /** Generar códigos faltantes */
  fillMissingBarcodes: (options?: FillOptions) => ProductRow[]
  /** Validar todos los códigos */
  validateAllBarcodes: () => ValidationResult
  /** Resetear estado */
  reset: () => void
}

type FillOptions = {
  /** Prefijo del país ('ES' | 'EC' | 'INTERNAL') */
  country?: 'ES' | 'EC' | 'INTERNAL'
  /** ¿Sobrescribir códigos inválidos? */
  overwriteInvalid?: boolean
  /** ¿Usar SKU como base? */
  useSkuAsBase?: boolean
}

type ValidationResult = {
  valid: number
  invalid: number
  missing: number
  invalidBarcodes: Array<{ index: number; product: ProductRow; reason: string }>
}

export function useBarcodeFiller(initialProducts: ProductRow[]): UseBarcodeFiller {
  const [products, setProducts] = useState<ProductRow[]>(initialProducts)

  // Analizar productos sin código de barras
  const analysis = useMemo(() => {
    let missing = 0
    let invalid = 0
    let valid = 0

    products.forEach((p) => {
      if (!p.codigo_barras || p.codigo_barras.trim() === '') {
        missing++
      } else {
        const format = detectBarcodeFormat(p.codigo_barras)
        if (format && validateBarcode(p.codigo_barras, format)) {
          valid++
        } else {
          invalid++
        }
      }
    })

    return { missing, invalid, valid, total: products.length }
  }, [products])

  // Generar códigos faltantes
  const fillMissingBarcodes = useCallback(
    (options: FillOptions = {}): ProductRow[] => {
      const { country = 'INTERNAL', overwriteInvalid = false, useSkuAsBase = false } = options

      // Crear generador
      const generator = getBarcodeGeneratorForCountry(country, 1)

      // Procesar productos
      const updated = products.map((product) => {
        const hasBarcode = product.codigo_barras && product.codigo_barras.trim() !== ''

        // Si ya tiene código válido, no hacer nada
        if (hasBarcode && !overwriteInvalid) {
          const format = detectBarcodeFormat(product.codigo_barras!)
          if (format && validateBarcode(product.codigo_barras!, format)) {
            return product
          }
        }

        // Generar nuevo código
        let newBarcode: string

        if (useSkuAsBase && product.sku) {
          // Intentar usar SKU como base (solo si es numérico)
          const skuNumeric = product.sku.replace(/\D/g, '')
          if (skuNumeric.length >= 6) {
            const sequence = parseInt(skuNumeric.slice(-6), 10)
            newBarcode = generator.generate(sequence)
          } else {
            newBarcode = generator.next()
          }
        } else {
          newBarcode = generator.next()
        }

        return {
          ...product,
          codigo_barras: newBarcode,
          _barcode_generated: true, // Marcar como generado
          _barcode_type: 'virtual', // Marcar como código VIRTUAL (no EAN del fabricante)
        }
      })

      setProducts(updated)
      return updated
    },
    [products]
  )

  // Validar todos los códigos
  const validateAllBarcodes = useCallback((): ValidationResult => {
    const result: ValidationResult = {
      valid: 0,
      invalid: 0,
      missing: 0,
      invalidBarcodes: [],
    }

    products.forEach((product, index) => {
      if (!product.codigo_barras || product.codigo_barras.trim() === '') {
        result.missing++
        result.invalidBarcodes.push({
          index,
          product,
          reason: 'Falta código de barras',
        })
        return
      }

      const format = detectBarcodeFormat(product.codigo_barras)
      if (!format) {
        result.invalid++
        result.invalidBarcodes.push({
          index,
          product,
          reason: 'Formato no reconocido',
        })
        return
      }

      if (!validateBarcode(product.codigo_barras, format)) {
        result.invalid++
        result.invalidBarcodes.push({
          index,
          product,
          reason: `Checksum inválido (${format})`,
        })
        return
      }

      result.valid++
    })

    return result
  }, [products])

  // Resetear
  const reset = useCallback(() => {
    setProducts(initialProducts)
  }, [initialProducts])

  return {
    productsWithBarcodes: products,
    generatedCount: products.filter((p) => p._barcode_generated).length,
    hasMissingBarcodes: analysis.missing > 0 || analysis.invalid > 0,
    fillMissingBarcodes,
    validateAllBarcodes,
    reset,
  }
}

/**
 * Componente auxiliar: Banner de ayuda para códigos faltantes
 */
export function MissingBarcodesBanner({
  missingCount,
  onGenerate,
}: {
  missingCount: number
  onGenerate: () => void
}) {
  if (missingCount === 0) return null

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <div className="text-2xl">⚠️</div>
        <div className="flex-1">
          <h3 className="font-semibold text-amber-900">
            {missingCount} producto(s) sin código de barras
          </h3>
          <p className="mt-1 text-sm text-amber-700">
            Estos productos no tienen código de barras. Se generarán <strong>códigos virtuales internos</strong> 
            (prefijo 200-299) para usar con tu pistola lectora.
          </p>
          <p className="mt-1 text-xs text-amber-600">
            ℹ️ Los códigos virtuales son válidos solo para uso interno, no son EAN del fabricante.
          </p>
          <button
            onClick={onGenerate}
            className="mt-3 px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded-lg hover:bg-amber-700"
          >
            🏷️ Generar códigos virtuales (200xxx...)
          </button>
        </div>
      </div>
    </div>
  )
}
