/**
 * Barcode label printing component
 *
 * Layout: config a la izquierda (scrollable) · preview a la derecha (sticky)
 * Modo: Navegador (window.print) o Agente (ESC/POS via API)
 */

import React, { useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useCurrency } from '../../../hooks/useCurrency'

// ─── Public types ─────────────────────────────────────────────────────────────

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
  columns: number
  columnGapMm: number
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

export type PrintModalExtras = {
  printers?: PrinterInfo[]
  selectedPrinter?: PrinterInfo | null
  savedConfigs?: SavedPrinterConfig[]
  selectedConfigId?: string | null
  onSelectSavedConfig?: (configId: string | null) => void
  onSelectPrinter?: (port: string) => void
  printerSaving?: boolean
  configsLoading?: boolean
  onSaveConfig?: () => void
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: PrintConfig = {
  widthMm: 50,
  heightMm: 40,
  gapMm: 3,
  columns: 1,
  columnGapMm: 2,
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

const SIZE_PRESETS: Array<{ label: string; widthMm: number; heightMm: number }> = [
  { label: '30×20', widthMm: 30, heightMm: 20 },
  { label: '40×30', widthMm: 40, heightMm: 30 },
  { label: '50×40', widthMm: 50, heightMm: 40 },
  { label: '60×50', widthMm: 60, heightMm: 50 },
]

// ─── Utilities ────────────────────────────────────────────────────────────────

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)
const mmToPx = (value: number) => (value / 25.4) * 96

function detectBarcodeFormat(barcode: string): string {
  if (/^\d{13}$/.test(barcode)) return 'EAN13'
  if (/^\d{8}$/.test(barcode)) return 'EAN8'
  if (/^\d{12}$/.test(barcode)) return 'UPC'
  return 'CODE128'
}

// ─── Props ───────────────────────────────────────────────────────────────────

type PrintBarcodeLabelsProps = {
  products: ProductLabel[]
  defaultConfig?: PrintConfig
  onClose?: () => void
  onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
  printMode?: 'browser' | 'agent'
  onChangePrintMode?: (mode: 'browser' | 'agent') => void
  printers?: PrinterInfo[]
  selectedPrinter?: PrinterInfo | null
  onSelectPrinter?: (port: string) => void
  printerSaving?: boolean
  modalExtras?: PrintModalExtras
  currencySymbol?: string
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function PrintBarcodeLabels({
  products,
  defaultConfig,
  onClose,
  onPrint,
  printMode,
  onChangePrintMode,
  printers,
  selectedPrinter,
  onSelectPrinter,
  printerSaving,
  modalExtras,
  currencySymbol = '',
}: PrintBarcodeLabelsProps) {
  const { t } = useTranslation(['importer'])
  const printRef = useRef<HTMLDivElement>(null)
  const barcodeRendererRef = useRef<null | ((element: HTMLCanvasElement, text: string, options?: object) => void)>(null)

  const [localConfig, setLocalConfig] = useState<PrintConfig>(defaultConfig ?? DEFAULT_CONFIG)
  const [internalMode, setInternalMode] = useState<'browser' | 'agent'>(printMode ?? 'browser')
  const [perProductCopies, setPerProductCopies] = useState<Record<string, number>>({})
  const [generating, setGenerating] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [customSize, setCustomSize] = useState(false)

  // Sync props
  React.useEffect(() => { if (printMode) setInternalMode(printMode) }, [printMode])
  React.useEffect(() => { setLocalConfig(defaultConfig ?? DEFAULT_CONFIG) }, [defaultConfig])
  React.useEffect(() => {
    if (!modalExtras?.selectedConfigId) return
    const sel = (modalExtras.savedConfigs ?? []).find((c) => c.id === modalExtras.selectedConfigId)
    if (sel) setLocalConfig((prev) => ({ ...prev, ...sel }))
  }, [modalExtras?.savedConfigs, modalExtras?.selectedConfigId])

  const effectiveMode = printMode ?? internalMode

  // Expanded labels respecting copies per product
  const labels = useMemo(() => {
    const result: ProductLabel[] = []
    products.forEach((p) => {
      const n = perProductCopies[p.id] ?? Math.max(1, localConfig.copies)
      for (let i = 0; i < n; i++) result.push(p)
    })
    return result
  }, [products, localConfig.copies, perProductCopies])

  const totalLabels = labels.length

  // Grid dimensions
  const labelDimensions = {
    width: `${localConfig.widthMm}mm`,
    height: `${localConfig.heightMm}mm`,
    fontSize: clamp(localConfig.heightMm <= 40 ? 8 : localConfig.heightMm <= 50 ? 9 : 10, 7, 12) + 'px',
  }

  const gridStyle: React.CSSProperties = {
    marginLeft: `${mmToPx(localConfig.offsetXmm)}px`,
    marginTop: `${mmToPx(localConfig.offsetYmm)}px`,
    gridTemplateColumns: `repeat(${Math.max(1, localConfig.columns)}, ${labelDimensions.width})`,
    columnGap: `${mmToPx(Math.max(0, localConfig.columnGapMm))}px`,
    rowGap: `${mmToPx(Math.max(0, localConfig.gapMm))}px`,
  }

  // Regenerate barcodes when any visual setting changes
  React.useEffect(() => {
    let cancelled = false
    setGenerating(true)
    const tid = setTimeout(() => {
      void (async () => {
        if (!printRef.current) {
          if (!cancelled) setGenerating(false)
          return
        }

        const renderBarcode = barcodeRendererRef.current ?? (await import('jsbarcode')).default
        barcodeRendererRef.current = renderBarcode

        if (cancelled || !printRef.current) {
          if (!cancelled) setGenerating(false)
          return
        }

        const canvases = printRef.current.querySelectorAll<HTMLCanvasElement>('.barcode-canvas')
        let idx = 0
        products.forEach((product) => {
          const n = perProductCopies[product.id] ?? Math.max(1, localConfig.copies)
          for (let i = 0; i < n; i++) {
            const canvas = canvases[idx++]
            if (!canvas) continue
            try {
              renderBarcode(canvas, product.codigo_barras, {
                format: detectBarcodeFormat(product.codigo_barras),
                width: clamp(localConfig.barcodeWidth, 1, 5),
                height: clamp(localConfig.heightMm * 1.2, 35, 80),
                displayValue: true,
                fontSize: 12,
                margin: 5,
              })
            } catch {
              // Invalid barcode; the canvas stays empty
            }
          }
        })

        if (!cancelled) setGenerating(false)
      })().catch(() => {
        if (!cancelled) setGenerating(false)
      })
    }, 80)
    return () => {
      cancelled = true
      clearTimeout(tid)
    }
  }, [products, localConfig.copies, localConfig.heightMm, localConfig.barcodeWidth, perProductCopies])

  // Config helpers
  const update = (partial: Partial<PrintConfig>) => {
    modalExtras?.onSelectSavedConfig?.(null)
    setLocalConfig((prev) => ({ ...prev, ...partial }))
  }

  const setAllCopies = (n: number) => {
    const map: Record<string, number> = {}
    products.forEach((p) => { map[p.id] = n })
    setPerProductCopies(map)
    update({ copies: n })
  }

  const applyPreset = (preset: typeof SIZE_PRESETS[0]) => {
    setCustomSize(false)
    update({ widthMm: preset.widthMm, heightMm: preset.heightMm })
  }

  const activePreset = !customSize
    ? SIZE_PRESETS.find((p) => p.widthMm === localConfig.widthMm && p.heightMm === localConfig.heightMm)
    : null

  const handlePrint = () => {
    if (generating) return
    const printConfig = { ...localConfig, copies: Math.max(1, localConfig.copies) }
    if (effectiveMode === 'browser') {
      window.print()
      onClose?.()
      return
    }
    if (onPrint) {
      setGenerating(true)
      onPrint(labels, printConfig)
        .then(() => { setGenerating(false); onClose?.() })
        .catch(() => setGenerating(false))
      return
    }
    window.print()
  }

  const handleSavedConfigChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value || null
    if (id) {
      const sel = (modalExtras?.savedConfigs ?? []).find((c) => c.id === id)
      if (sel) setLocalConfig((prev) => ({ ...prev, ...sel }))
    }
    modalExtras?.onSelectSavedConfig?.(id)
  }

  const savedConfigs = modalExtras?.savedConfigs ?? []
  const configsLoading = modalExtras?.configsLoading ?? false
  const nameLimit = clamp(Math.round(localConfig.widthMm * 0.7), 12, 30)
  const showCategory = localConfig.showCategory && localConfig.heightMm >= 35
  const priceAlignClass =
    localConfig.priceAlignment === 'right' ? 'text-right'
    : localConfig.priceAlignment === 'left' ? 'text-left'
    : 'text-center'

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-white">

      {/* ── Sticky header ───────────────────────────────────────────────────── */}
      <div className="print:hidden shrink-0 bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Print labels
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
              {totalLabels} total
            </span>
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            {products.length} product{products.length !== 1 ? 's' : ''} · {localConfig.widthMm}×{localConfig.heightMm} mm
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handlePrint}
            disabled={generating || (effectiveMode === 'agent' && !selectedPrinter?.port)}
            className="px-4 py-1.5 text-sm font-semibold bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {generating ? 'Generating…' : effectiveMode === 'browser' ? 'Print' : 'Send to printer'}
          </button>
        </div>
      </div>

      {/* ── Body: config left · preview right ───────────────────────────────── */}
      <div className="flex-1 overflow-hidden flex print:block">

        {/* ── Configuration panel (left) ─────────────────────────────────────── */}
        <div className="print:hidden w-full lg:w-[400px] shrink-0 overflow-y-auto border-r border-gray-200 bg-gray-50 p-4 space-y-3">

          {/* Print mode */}
          <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Modo</h3>
            <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm font-medium">
              {(['browser', 'agent'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => { setInternalMode(mode); onChangePrintMode?.(mode) }}
                  className={`flex-1 py-2 transition-colors ${
                    effectiveMode === mode
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {mode === 'browser' ? 'Browser' : 'Agent / Port'}
                </button>
              ))}
            </div>

            {effectiveMode === 'agent' && (
              <div className="space-y-2">
                <select
                  value={selectedPrinter?.port || ''}
                  onChange={(e) => onSelectPrinter?.(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
          <option value="">Select a printer…</option>
                  {(printers ?? []).map((p) => (
                    <option key={p.port} value={p.port}>
                      {p.name || p.description || p.port}
                    </option>
                  ))}
                </select>
                {savedConfigs.length > 0 && (
                  <select
                    value={modalExtras?.selectedConfigId ?? ''}
                    onChange={handleSavedConfigChange}
                    disabled={configsLoading}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="">Saved profile…</option>
                    {savedConfigs.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {effectiveMode === 'browser' && (
              <p className="text-xs text-gray-400">
                Use printers installed via Wi-Fi/Bluetooth/USB. Set margins to 0 in the browser dialog.
              </p>
            )}

            {modalExtras?.onSaveConfig && (
              <button
                type="button"
                onClick={() => modalExtras.onSaveConfig?.()}
                disabled={printerSaving}
                className="w-full py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-50"
              >
                {printerSaving ? 'Saving…' : 'Save current configuration'}
              </button>
            )}
          </section>

          {/* Quantities per product */}
          <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Quantities</h3>
              <span className="text-xs font-bold text-blue-600">{totalLabels} etiquetas</span>
            </div>

            {/* Quick buttons */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-gray-400">All:</span>
              {[1, 2, 3, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setAllCopies(n)}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md border transition-colors ${
                    Object.values(perProductCopies).every((v) => v === n) && Object.keys(perProductCopies).length === products.length
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  ×{n}
                </button>
              ))}
            </div>

            {/* Product table */}
            <div className="max-h-48 overflow-y-auto rounded-lg border border-gray-100">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-1.5 text-xs font-medium text-gray-400">Product</th>
                    <th className="text-center px-2 py-1.5 text-xs font-medium text-gray-400 w-16">Copies</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {products.map((p) => (
                    <tr key={p.id} className="hover:bg-gray-50">
                      <td className="px-3 py-1.5">
                        <div className="text-gray-800 truncate max-w-[230px] text-sm">{p.name}</div>
                        <div className="text-gray-400 font-mono text-xs">{p.sku}</div>
                      </td>
                      <td className="px-2 py-1.5 text-center">
                        <input
                          type="number"
                          min={0}
                          value={perProductCopies[p.id] ?? localConfig.copies}
                          onChange={(e) => {
                            const n = Math.max(0, Number(e.target.value))
                            setPerProductCopies((prev) => ({ ...prev, [p.id]: n }))
                          }}
                          className="w-14 border border-gray-200 rounded-md px-1.5 py-1 text-sm text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Label size */}
          <section className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Size</h3>

            {/* Presets */}
            <div className="grid grid-cols-4 gap-1.5">
              {SIZE_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  onClick={() => applyPreset(preset)}
                  className={`py-2 text-xs font-medium rounded-lg border transition-colors ${
                    activePreset?.label === preset.label
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>

            {/* Custom toggle */}
            <button
              type="button"
              onClick={() => setCustomSize(!customSize)}
              className="text-xs text-blue-600 hover:underline"
            >
              {customSize ? '▲ Hide measurements' : '▼ Custom size'}
            </button>

            {customSize && (
              <div className="grid grid-cols-2 gap-3">
                <label className="text-xs text-gray-500">
                  Ancho (mm)
                  <input
                    type="number" min={10} step={1} value={localConfig.widthMm}
                    onChange={(e) => update({ widthMm: Number(e.target.value) })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <label className="text-xs text-gray-500">
                  Alto (mm)
                  <input
                    type="number" min={15} step={1} value={localConfig.heightMm}
                    onChange={(e) => update({ heightMm: Number(e.target.value) })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
              </div>
            )}

            {/* Columns */}
            <div className="grid grid-cols-2 gap-3">
              <label className="text-xs text-gray-500">
                Columns per row
                <input
                  type="number" min={1} max={6} step={1} value={localConfig.columns}
                  onChange={(e) => update({ columns: Math.max(1, Number(e.target.value)) })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                />
              </label>
              <label className="text-xs text-gray-500">
                Gap (mm)
                <input
                  type="number" min={0} step={0.5} value={localConfig.gapMm}
                  onChange={(e) => update({ gapMm: Number(e.target.value) })}
                  className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                />
              </label>
            </div>

            {/* What to show */}
            <div className="flex gap-4 text-sm text-gray-700">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox" checked={localConfig.showPrice}
                  onChange={(e) => update({ showPrice: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Precio
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox" checked={localConfig.showCategory}
                  onChange={(e) => update({ showCategory: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Category
              </label>
            </div>
          </section>

          {/* Advanced options */}
          <section className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full flex items-center justify-between px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hover:bg-gray-50"
            >
              <span>Advanced options</span>
              <span>{showAdvanced ? '▲' : '▼'}</span>
            </button>

            {showAdvanced && (
              <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
                <div className="grid grid-cols-2 gap-3 pt-3">
                  <label className="text-xs text-gray-500">
                    Offset horizontal (mm)
                    <input
                      type="number" min={-30} max={30} step={0.5} value={localConfig.offsetXmm}
                      onChange={(e) => update({ offsetXmm: Number(e.target.value) })}
                      className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="text-xs text-gray-500">
                    Offset vertical (mm)
                    <input
                      type="number" min={-30} max={30} step={0.5} value={localConfig.offsetYmm}
                      onChange={(e) => update({ offsetYmm: Number(e.target.value) })}
                      className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <label className="text-xs text-gray-500">
                    Grosor barcode
                    <input
                      type="number" min={1} max={5} step={0.1} value={localConfig.barcodeWidth}
                      onChange={(e) => update({ barcodeWidth: Number(e.target.value) })}
                      className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="text-xs text-gray-500">
                    Column gap
                    <input
                      type="number" min={0} step={0.5} value={localConfig.columnGapMm}
                      onChange={(e) => update({ columnGapMm: Number(e.target.value) })}
                      className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                </div>
                <label className="text-xs text-gray-500 block">
                  Price alignment
                  <select
                    value={localConfig.priceAlignment}
                    onChange={(e) => update({ priceAlignment: e.target.value as PrintConfig['priceAlignment'] })}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="left">Izquierda</option>
                    <option value="center">Centrada</option>
                    <option value="right">Derecha</option>
                  </select>
                </label>
                <label className="text-xs text-gray-500 block">
                  Encabezado
                  <input
                    type="text" value={localConfig.headerText}
                    onChange={(e) => update({ headerText: e.target.value })}
                    placeholder="Text above the item"
                    className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
                <label className="text-xs text-gray-500 block">
                  Pie de etiqueta
                  <input
                    type="text" value={localConfig.footerText}
                    onChange={(e) => update({ footerText: e.target.value })}
                    placeholder={t('importer:barcode.textBelowPrice')}
                    className="mt-1 w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:ring-2 focus:ring-blue-500"
                  />
                </label>
              </div>
            )}
          </section>

        </div>

        {/* ── Preview (right) ───────────────────────────────────────────────── */}
        <div className="flex-1 overflow-auto bg-gray-100 p-6 print:p-0 print:bg-white">
          {generating && (
            <div className="print:hidden flex items-center gap-2 text-xs text-gray-400 mb-3">
              <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating barcodes…
            </div>
          )}

          <div ref={printRef} className="print:p-0 inline-block">
            <div className="grid print:gap-0" style={gridStyle}>
              {labels.map((product, index) => (
                <div
                  key={`${product.id}-${index}`}
                  className="border border-gray-300 bg-white p-1.5 print:border-black print:break-inside-avoid flex flex-col items-center justify-center text-center gap-0.5"
                  style={{ width: labelDimensions.width, height: labelDimensions.height, fontSize: labelDimensions.fontSize }}
                >
                  {localConfig.headerText && (
                    <div className="text-[9px] uppercase tracking-wide text-gray-400 w-full text-center">
                      {localConfig.headerText}
                    </div>
                  )}
                  <div className="font-semibold overflow-hidden text-ellipsis whitespace-nowrap w-full leading-tight">
                    {product.name.substring(0, nameLimit)}
                  </div>
                  <div className="flex justify-center items-center py-0.5">
                    <canvas className="barcode-canvas" />
                  </div>
                  <div className="flex flex-col items-center gap-0">
                    {localConfig.showPrice && typeof product.precio_venta === 'number' && (
                      <div className={`font-bold text-base w-full leading-tight ${priceAlignClass}`}>
                        {currencySymbol}{product.precio_venta.toFixed(2)}
                      </div>
                    )}
                    {showCategory && product.categoria && (
                      <div className="text-[9px] text-gray-500 uppercase truncate">
                        {product.categoria}
                      </div>
                    )}
                    {localConfig.heightMm >= 50 && (
                      <div className="text-[9px] text-gray-400">
                        SKU: {product.sku}
                      </div>
                    )}
                    {localConfig.footerText && (
                      <div className="text-[9px] text-gray-400 uppercase tracking-wide">
                        {localConfig.footerText}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @media print {
          body { margin: 0; padding: 0; }
          @page { margin: 5mm; size: auto; }
          .print\\:hidden { display: none !important; }
        }
      `}</style>
    </div>
  )
}

// ─── Hook ────────────────────────────────────────────────────────────────────

type PrintOptions = {
  defaultConfig?: PrintConfig
  onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
  printMode?: 'browser' | 'agent'
  onChangePrintMode?: (mode: 'browser' | 'agent') => void
  modalExtras?: PrintModalExtras
  currencySymbol?: string
}

type PrintStateConfig = {
  printConfig: PrintConfig
  onPrint?: (labels: ProductLabel[], config: PrintConfig) => Promise<void>
  printMode: 'browser' | 'agent'
  onChangePrintMode?: (mode: 'browser' | 'agent') => void
  modalExtras?: PrintModalExtras
  currencySymbol: string
}

export function usePrintBarcodeLabels() {
  const { symbol: tenantSymbol } = useCurrency()
  const [isOpen, setIsOpen] = useState(false)
  const [products, setProducts] = useState<ProductLabel[]>([])
  const [config, setConfig] = useState<PrintStateConfig>({
    printConfig: DEFAULT_CONFIG,
    printMode: 'browser',
    currencySymbol: '',
  })

  const open = (productsData: ProductLabel[], options?: PrintOptions) => {
    setProducts(productsData)
    setConfig((prev) => ({
      ...prev,
      printConfig: { ...prev.printConfig, ...(options?.defaultConfig ?? {}) },
      onPrint: options?.onPrint,
      printMode: options?.printMode ?? prev.printMode ?? 'browser',
      onChangePrintMode: options?.onChangePrintMode,
      modalExtras: options?.modalExtras,
      currencySymbol: options?.currencySymbol ?? tenantSymbol ?? '',
    }))
    setIsOpen(true)
  }

  const close = () => { setIsOpen(false); setProducts([]) }

  const updateModalExtras = (modalExtras?: PrintModalExtras) => {
    setConfig((prev) => ({ ...prev, modalExtras }))
  }

  const PrintModal = isOpen ? (
    <PrintBarcodeLabels
      products={products}
      defaultConfig={config.printConfig}
      onClose={close}
      onPrint={config.onPrint}
      printMode={config.printMode}
      onChangePrintMode={(mode) => {
        setConfig((prev) => ({ ...prev, printMode: mode }))
        config.onChangePrintMode?.(mode)
      }}
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
