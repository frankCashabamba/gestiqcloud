/**
 * Componente de impresión de etiquetas con códigos de barras
 *
 * Genera etiquetas imprimibles para:
 * - Productos importados desde Excel
 * - Productos sin código de barras original
 * - Uso con pistola lectora
 */

import React, { useRef, useState } from 'react'
import JsBarcode from 'jsbarcode'

export type ProductLabel = {
  id: string
  sku: string
  name: string
  codigo_barras: string
  precio_venta?: number
  categoria?: string
}

export type LabelSize =
  | '40x30'  // 40mm x 30mm (pequeña, solo código)
  | '50x40'  // 50mm x 40mm (estándar con precio)
  | '70x50'  // 70mm x 50mm (grande con info completa)

type PrintBarcodeLabelsProps = {
  products: ProductLabel[]
  labelSize?: LabelSize
  showPrice?: boolean
  showCategory?: boolean
  copies?: number
  onClose?: () => void
}

const LABEL_SIZES: Record<LabelSize, { width: string; height: string; fontSize: string }> = {
  '40x30': { width: '40mm', height: '30mm', fontSize: '8px' },
  '50x40': { width: '50mm', height: '40mm', fontSize: '9px' },
  '70x50': { width: '70mm', height: '50mm', fontSize: '10px' },
}

export default function PrintBarcodeLabels({
  products,
  labelSize = '50x40',
  showPrice = true,
  showCategory = false,
  copies = 1,
  onClose,
}: PrintBarcodeLabelsProps) {
  const [generating, setGenerating] = useState(false)
  const printRef = useRef<HTMLDivElement>(null)

  const labelDimensions = LABEL_SIZES[labelSize]

  // Genera códigos de barras usando JsBarcode
  const generateBarcodes = () => {
    setGenerating(true)

    setTimeout(() => {
      if (!printRef.current) return

      const barcodes = printRef.current.querySelectorAll('.barcode-canvas')
      barcodes.forEach((canvas, index) => {
        const product = products[Math.floor(index / copies)]
        if (!product) return

        try {
          JsBarcode(canvas, product.codigo_barras, {
            format: detectFormat(product.codigo_barras),
            width: 2,
            height: labelSize === '40x30' ? 40 : labelSize === '50x40' ? 50 : 60,
            displayValue: true,
            fontSize: 12,
            margin: 5,
          })
        } catch (error) {
          console.error('Error generating barcode:', product.codigo_barras, error)
        }
      })

      setGenerating(false)
    }, 100)
  }

  // Detecta el formato del código de barras
  const detectFormat = (barcode: string): string => {
    if (/^\d{13}$/.test(barcode)) return 'EAN13'
    if (/^\d{8}$/.test(barcode)) return 'EAN8'
    if (/^\d{12}$/.test(barcode)) return 'UPC'
    return 'CODE128'
  }

  // Imprime las etiquetas
  const handlePrint = () => {
    if (generating) return
    window.print()
  }

  // Genera códigos al montar el componente
  React.useEffect(() => {
    generateBarcodes()
  }, [products, copies, labelSize])

  // Genera array de etiquetas con copias
  const labels = React.useMemo(() => {
    const result: ProductLabel[] = []
    products.forEach((product) => {
      for (let i = 0; i < copies; i++) {
        result.push(product)
      }
    })
    return result
  }, [products, copies])

  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-white">
      {/* Barra de acciones (no se imprime) */}
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Imprimir etiquetas ({labels.length} total)
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {products.length} productos × {copies} copia(s) = {labels.length} etiquetas
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handlePrint}
            disabled={generating}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {generating ? 'Generando...' : '🖨️ Imprimir'}
          </button>
        </div>
      </div>

      {/* Preview de etiquetas (no se imprime) */}
      <div className="print:hidden px-6 py-4 bg-gray-50">
        <div className="text-sm text-gray-600 space-y-1">
          <p>✓ Tamaño: <strong>{labelSize}mm</strong></p>
          <p>✓ price: <strong>{showPrice ? 'Sí' : 'No'}</strong></p>
          <p>✓ Categoría: <strong>{showCategory ? 'Sí' : 'No'}</strong></p>
        </div>
      </div>

      {/* Etiquetas para imprimir */}
      <div ref={printRef} className="p-6 print:p-0">
        <div className="grid grid-cols-3 gap-2 print:gap-1">
          {labels.map((product, index) => (
            <div
              key={`${product.id}-${index}`}
              className="border border-gray-300 p-2 print:border-black print:break-inside-avoid"
              style={{
                width: labelDimensions.width,
                height: labelDimensions.height,
                fontSize: labelDimensions.fontSize,
              }}
            >
              {/* Nombre del producto (truncado) */}
              <div className="font-semibold text-center mb-1 overflow-hidden text-ellipsis whitespace-nowrap">
                {product.name.substring(0, labelSize === '40x30' ? 15 : labelSize === '50x40' ? 20 : 30)}
              </div>

              {/* Código de barras */}
              <div className="flex justify-center items-center">
                <canvas className="barcode-canvas" />
              </div>

              {/* Información adicional */}
              <div className="mt-1 text-center space-y-0.5">
                {showPrice && product.precio_venta && (
                  <div className="font-bold text-lg">
                    €{product.precio_venta.toFixed(2)}
                  </div>
                )}

                {showCategory && product.categoria && labelSize !== '40x30' && (
                  <div className="text-xs text-gray-600 uppercase truncate">
                    {product.categoria}
                  </div>
                )}

                {/* SKU (solo en etiqueta grande) */}
                {labelSize === '70x50' && (
                  <div className="text-xs text-gray-500">
                    SKU: {product.sku}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Estilos de impresión */}
      <style>{`
        @media print {
          body {
            margin: 0;
            padding: 0;
          }
          @page {
            margin: 5mm;
            size: auto;
          }
        }
      `}</style>
    </div>
  )
}

/**
 * Hook para usar el componente de impresión
 */
export function usePrintBarcodeLabels() {
  const [isOpen, setIsOpen] = useState(false)
  const [products, setProducts] = useState<ProductLabel[]>([])
  const [config, setConfig] = useState({
    labelSize: '50x40' as LabelSize,
    showPrice: true,
    showCategory: false,
    copies: 1,
  })

  const open = (productsData: ProductLabel[], options?: Partial<typeof config>) => {
    setProducts(productsData)
    if (options) {
      setConfig({ ...config, ...options })
    }
    setIsOpen(true)
  }

  const close = () => {
    setIsOpen(false)
    setProducts([])
  }

  const PrintModal = isOpen ? (
    <PrintBarcodeLabels
      products={products}
      {...config}
      onClose={close}
    />
  ) : null

  return { open, close, PrintModal }
}
