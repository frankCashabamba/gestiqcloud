/**
 * Componente de impresión de etiquetas con códigos de barras
 *
 * Permite configurar formato (ancho, alto, separación), controlar copias, y decidir qué campos se muestran.
 * Incluye un modal de impresión para seleccionar la impresora, guardar la configuración y lanzar la tirada.
 */
import React, { useMemo, useRef, useState } from 'react'
import JsBarcode from 'jsbarcode'

export type ProductLabel = {
  id: string
  sku: string
  name: string
  codigo_barras: string
  precio_venta?: number
  categoria?: string
}

export type PrintConfig = {
  widthMm: number
  heightMm: number
  gapMm: number
  showPrice: boolean
  showCategory: boolean
  copies: number
  headerText: string
  footerText: string
  offsetXmm: number
  offsetYmm: number
  barcodeWidth: number
  priceAlignment: 'left' | 'center' | 'right'
}

export type SavedPrinterConfig = PrintConfig & {
  id: string
  name: string
  printerPort: string
  createdAt: string
}

export type PrinterInfo = {
  port: string
  name?: string
  description?: string
  hwid?: string
}

type PrintBarcodeLabelsProps = {
  products: ProductLabel[]
  defaultConfig?: PrintConfig
  onClose?: () => void
  onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
  printers?: PrinterInfo[]
  selectedPrinter?: PrinterInfo | null
  onSelectPrinter?: (port: string) => void
  printerSaving?: boolean
  modalExtras?: PrintModalExtras
  currencySymbol?: string
}

const DEFAULT_CONFIG: PrintConfig = {
  widthMm: 50,
  heightMm: 40,
  gapMm: 3,
  showPrice: true,
  showCategory: false,
  copies: 1,
  headerText: '',
  footerText: '',
  offsetXmm: 0,
  offsetYmm: 0,
  barcodeWidth: 2,
  priceAlignment: 'center',
}

const clamp = (value: number, min: number, max: number) =>
  Math.min(Math.max(value, min), max)

const mmToPx = (value: number) => (value / 25.4) * 96

export default function PrintBarcodeLabels({
  products,
  defaultConfig,
  onClose,
  onPrint,
  printers,
  selectedPrinter,
  onSelectPrinter,
  printerSaving,
  modalExtras,
  currencySymbol = '$',
}: PrintBarcodeLabelsProps) {
  const [generating, setGenerating] = useState(false)
  const printRef = useRef<HTMLDivElement>(null)
  const [localConfig, setLocalConfig] = useState<PrintConfig>(defaultConfig ?? DEFAULT_CONFIG)

  React.useEffect(() => {
    setLocalConfig(defaultConfig ?? DEFAULT_CONFIG)
  }, [defaultConfig])

  const labels = React.useMemo(() => {
    const result: ProductLabel[] = []
    products.forEach((product) => {
      for (let i = 0; i < Math.max(1, localConfig.copies); i++) {
        result.push(product)
      }
    })
    return result
  }, [products, localConfig.copies])

  const labelDimensions = {
    width: `${localConfig.widthMm}mm`,
    height: `${localConfig.heightMm}mm`,
    fontSize: clamp(localConfig.heightMm <= 40 ? 8 : localConfig.heightMm <= 50 ? 9 : 10, 7, 12) + 'px',
  }

  const gridOffsetStyle = {
    marginLeft: `${mmToPx(localConfig.offsetXmm)}px`,
    marginTop: `${mmToPx(localConfig.offsetYmm)}px`,
  }

  const generateBarcodes = () => {
    setGenerating(true)
    setTimeout(() => {
      if (!printRef.current) return
      const barcodes = printRef.current.querySelectorAll<HTMLCanvasElement>('.barcode-canvas')
      barcodes.forEach((canvas, index) => {
        const target = products[Math.floor(index / Math.max(1, localConfig.copies))]
        if (!target) return

        try {
          JsBarcode(canvas, target.codigo_barras, {
            format: detectFormat(target.codigo_barras),
          width: clamp(localConfig.barcodeWidth, 1, 5),
            height: clamp(localConfig.heightMm * 1.2, 35, 80),
            displayValue: true,
            fontSize: 12,
            margin: 5,
          })
        } catch (error) {
          console.error('Error generating barcode:', target.codigo_barras, error)
        }
      })
      setGenerating(false)
    }, 100)
  }

  const detectFormat = (barcode: string): string => {
    if (/^\d{13}$/.test(barcode)) return 'EAN13'
    if (/^\d{8}$/.test(barcode)) return 'EAN8'
    if (/^\d{12}$/.test(barcode)) return 'UPC'
    return 'CODE128'
  }

  React.useEffect(() => {
    generateBarcodes()
  }, [products, localConfig.copies, localConfig.heightMm])

  const handlePrint = () => {
    if (generating) return
    const printConfig = { ...localConfig, copies: Math.max(1, localConfig.copies) }
    if (onPrint) {
      setGenerating(true)
      onPrint(labels, printConfig)
        .then(() => {
          setGenerating(false)
          onClose?.()
        })
        .catch((err) => {
          setGenerating(false)
          console.error('Error printing labels:', err)
        })
      return
    }
    window.print()
  }

  const handleSavedConfigChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const configId = event.target.value || null
    if (configId) {
      const selection = savedConfigs.find((config) => config.id === configId)
      if (selection) {
        setLocalConfig((prev) => ({ ...prev, ...selection }))
      }
    }
    modalExtras?.onSelectSavedConfig?.(configId)
  }

  const updateConfig = (partial: Partial<PrintConfig>) => {
    setLocalConfig((prev) => ({ ...prev, ...partial }))
  }

  const updateConfigAndResetSelection = (partial: Partial<PrintConfig>) => {
    modalExtras?.onSelectSavedConfig?.(null)
    updateConfig(partial)
  }

  const savedConfigs = modalExtras?.savedConfigs ?? []
  const selectedConfigId = modalExtras?.selectedConfigId ?? null
  const configsLoading = modalExtras?.configsLoading ?? false

  const nameLimit = clamp(Math.round(localConfig.widthMm * 0.7), 12, 30)
  const showCategory = localConfig.showCategory && localConfig.heightMm >= 35
  const priceAlignClass =
    localConfig.priceAlignment === 'right'
      ? 'text-right'
      : localConfig.priceAlignment === 'left'
        ? 'text-left'
        : 'text-center'

  React.useEffect(() => {
    if (!selectedConfigId) return
    const selection = savedConfigs.find((config) => config.id === selectedConfigId)
    if (!selection) return
    setLocalConfig((prev) => ({ ...prev, ...selection }))
  }, [savedConfigs, selectedConfigId])

  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-white">
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Imprimir etiquetas ({labels.length} total)
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            {products.length} productos × {Math.max(1, localConfig.copies)} copia(s) = {labels.length} etiquetas
          </p>
        </div>
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Cancelar
        </button>
      </div>

      <div className="print:hidden px-6 py-4 bg-gray-50 space-y-4">
        {printers && printers.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <div className="flex flex-col md:flex-row gap-4 md:items-end md:justify-between">
              <div className="flex-1 min-w-[220px]">
                <label className="block text-sm font-semibold text-gray-700 mb-1">Impresora</label>
                <select
                  value={selectedPrinter?.port || ''}
                  onChange={(event) => onSelectPrinter?.(event.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Selecciona una impresora</option>
                  {printers.map((printer) => (
                    <option key={printer.port} value={printer.port}>
                      {printer.name || printer.description || printer.port}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex-1 min-w-[220px]">
                <label className="block text-sm font-semibold text-gray-700 mb-1">Configuraciones guardadas</label>
                <select
                  value={selectedConfigId ?? ''}
                  onChange={handleSavedConfigChange}
                  disabled={configsLoading || savedConfigs.length === 0}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">
                    {savedConfigs.length === 0
                      ? configsLoading
                        ? 'Cargando…'
                        : 'No hay configuraciones guardadas'
                      : 'Selecciona un perfil'}
                  </option>
                  {savedConfigs.map((config) => (
                    <option key={config.id} value={config.id}>
                      {config.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={handlePrint}
                  disabled={!selectedPrinter?.port || generating}
                  className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-60"
                >
                  {generating ? 'Generando...' : 'Imprimir ahora'}
                </button>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {selectedPrinter
                ? `Impresora activa: ${selectedPrinter.name || selectedPrinter.port}`
                : 'Selecciona e imprime en tu impresora configurada.'}
            </p>
          </div>
        )}

        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm space-y-4">
          <h3 className="text-sm font-semibold text-gray-700">Formato de etiqueta</h3>
          <div className="grid gap-4 sm:grid-cols-3">
            <label className="text-xs text-gray-500">
              Ancho (mm)
              <input
                type="number"
                min={10}
                step={1}
                value={localConfig.widthMm}
                onChange={(event) => updateConfigAndResetSelection({ widthMm: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
            <label className="text-xs text-gray-500">
              Alto (mm)
              <input
                type="number"
                min={15}
                step={1}
                value={localConfig.heightMm}
                onChange={(event) => updateConfigAndResetSelection({ heightMm: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
            <label className="text-xs text-gray-500">
              Separación (mm)
              <input
                type="number"
                min={1}
                step={0.5}
                value={localConfig.gapMm}
                onChange={(event) => updateConfigAndResetSelection({ gapMm: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>
          <label className="text-xs text-gray-500 block">
            Copias por producto
            <input
              type="number"
              min={1}
              value={localConfig.copies}
                onChange={(event) =>
                  updateConfigAndResetSelection({ copies: Math.max(1, Number(event.target.value)) })
                }
              className="mt-1 w-32 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs text-gray-500">
              Offset horizontal (mm)
              <input
                type="number"
                min={-30}
                max={30}
                step={0.5}
                value={localConfig.offsetXmm}
                onChange={(event) => updateConfigAndResetSelection({ offsetXmm: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
            <label className="text-xs text-gray-500">
              Offset vertical (mm)
              <input
                type="number"
                min={-30}
                max={30}
                step={0.5}
                value={localConfig.offsetYmm}
                onChange={(event) => updateConfigAndResetSelection({ offsetYmm: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-xs text-gray-500">
              Ancho del código de barras
              <input
                type="number"
                min={1}
                max={5}
                step={0.1}
                value={localConfig.barcodeWidth}
                onChange={(event) => updateConfigAndResetSelection({ barcodeWidth: Number(event.target.value) })}
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </label>
            <label className="text-xs text-gray-500">
              Alineación del precio
              <select
                value={localConfig.priceAlignment}
                onChange={(event) =>
                  updateConfigAndResetSelection({
                    priceAlignment: event.target.value as PrintConfig['priceAlignment'],
                  })
                }
                className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="left">Izquierda</option>
                <option value="center">Centrada</option>
                <option value="right">Derecha</option>
              </select>
            </label>
          </div>
          <p className="text-xs text-gray-500">
            Usa valores negativos para mover el bloque hacia la izquierda o arriba; positivos para desplazarte a la derecha o abajo.
          </p>
          <label className="text-xs text-gray-500 block">
            Encabezado libre
            <input
              type="text"
              value={localConfig.headerText}
              onChange={(event) => updateConfigAndResetSelection({ headerText: event.target.value })}
              className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Texto que aparece arriba del artículo"
            />
          </label>
          <label className="text-xs text-gray-500 block">
            Pie de etiqueta
            <input
              type="text"
              value={localConfig.footerText}
              onChange={(event) => updateConfigAndResetSelection({ footerText: event.target.value })}
              className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Texto que aparece debajo del precio"
            />
          </label>
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2 text-gray-700">
              <input
                type="checkbox"
                checked={localConfig.showPrice}
                onChange={(event) => updateConfigAndResetSelection({ showPrice: event.target.checked })}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              Mostrar precio
            </label>
            <label className="flex items-center gap-2 text-gray-700">
              <input
                type="checkbox"
                checked={localConfig.showCategory}
                onChange={(event) => updateConfigAndResetSelection({ showCategory: event.target.checked })}
                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              Mostrar categoría
            </label>
          </div>
        </div>

        <div className="text-sm text-gray-600 space-y-1">
          <p>{`${products.length} productos × ${Math.max(1, localConfig.copies)} copia(s) = ${labels.length} etiquetas`}</p>
          <p>Tamaño actual: <strong>{`${localConfig.widthMm}×${localConfig.heightMm} mm`}</strong></p>
          <p>Precio visible: <strong>{localConfig.showPrice ? 'Sí' : 'No'}</strong></p>
          <p>Categoría visible: <strong>{localConfig.showCategory ? 'Sí' : 'No'}</strong></p>
        </div>
      </div>

      <div ref={printRef} className="p-6 print:p-0">
        <div
          className="grid grid-cols-3 gap-2 print:gap-1"
          style={gridOffsetStyle}
        >
          {labels.map((product, index) => (
          <div
            key={`${product.id}-${index}`}
            className="border border-gray-300 p-2 print:border-black print:break-inside-avoid flex flex-col items-center justify-center text-center gap-1"
            style={{
              width: labelDimensions.width,
              height: labelDimensions.height,
              fontSize: labelDimensions.fontSize,
            }}
          >
            {localConfig.headerText && (
              <div className="text-xs uppercase tracking-wide text-gray-500 text-center w-full">
                {localConfig.headerText}
              </div>
            )}
            <div className="font-semibold overflow-hidden text-ellipsis whitespace-nowrap w-full">
              {product.name.substring(0, nameLimit)}
            </div>
            <div className="flex justify-center items-center py-1">
              <canvas className="barcode-canvas" />
            </div>
            <div className="flex flex-col items-center gap-0.5">
              {localConfig.showPrice && typeof product.precio_venta === 'number' && (
                <div className={`font-bold text-lg w-full ${priceAlignClass}`}>
                  {currencySymbol}
                  {product.precio_venta.toFixed(2)}
                </div>
              )}
              {showCategory && product.categoria && (
                <div className="text-xs text-gray-600 uppercase truncate">
                  {product.categoria}
                </div>
              )}
              {localConfig.heightMm >= 50 && (
                <div className="text-xs text-gray-500">
                  SKU: {product.sku}
                </div>
              )}
              {localConfig.footerText && (
                <div className="text-xs text-gray-500 uppercase tracking-wide">
                  {localConfig.footerText}
                </div>
              )}
            </div>
          </div>
          ))}
        </div>
      </div>

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

type PrintOptions = {
  defaultConfig?: PrintConfig
  onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
  modalExtras?: PrintModalExtras
  currencySymbol?: string
}

export type PrintModalExtras = {
  printers?: PrinterInfo[]
  selectedPrinter?: PrinterInfo | null
  savedConfigs?: SavedPrinterConfig[]
  selectedConfigId?: string | null
  onSelectSavedConfig?: (configId: string | null) => void
  onSelectPrinter?: (port: string) => void
  printerSaving?: boolean
  configsLoading?: boolean
}

export function usePrintBarcodeLabels() {
  const [isOpen, setIsOpen] = useState(false)
  const [products, setProducts] = useState<ProductLabel[]>([])
  const [config, setConfig] = useState<{
    printConfig: PrintConfig
    onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
    modalExtras?: PrintModalExtras
    currencySymbol: string
  }>({
    printConfig: DEFAULT_CONFIG,
    currencySymbol: '$',
  })

  const open = (productsData: ProductLabel[], options?: PrintOptions) => {
    setProducts(productsData)
    setConfig((prev) => ({
      ...prev,
      printConfig: {
        ...prev.printConfig,
        ...(options?.defaultConfig ?? {}),
      },
      onPrint: options?.onPrint,
      modalExtras: options?.modalExtras,
      currencySymbol: options?.currencySymbol ?? prev.currencySymbol,
    }))
    setIsOpen(true)
  }

  const close = () => {
    setIsOpen(false)
    setProducts([])
  }

  const updateModalExtras = (modalExtras?: PrintModalExtras) => {
    setConfig((prev) => ({ ...prev, modalExtras }))
  }

  const PrintModal = isOpen ? (
    <PrintBarcodeLabels
      products={products}
      defaultConfig={config.printConfig}
      onClose={close}
      onPrint={config.onPrint}
      printers={config.modalExtras?.printers}
      selectedPrinter={config.modalExtras?.selectedPrinter}
      onSelectPrinter={config.modalExtras?.onSelectPrinter}
      printerSaving={config.modalExtras?.printerSaving}
      modalExtras={config.modalExtras}
      currencySymbol={config.currencySymbol}
    />
  ) : null

  return { open, close, PrintModal, updateModalExtras }
}
