// apps/tenant/src/modules/productos/List.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  listProductos,
  removeProducto,
  purgeProductos,
  bulkSetActive,
  bulkAssignCategory,
  listCategorias,
  type Producto,
} from './productsApi'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import CategoriasModal from './CategoriesModal'
import { useCurrency } from '../../hooks/useCurrency'
import {
  useSectorFeaturesFromConfig,
  useCompanySector,
} from '../../contexts/CompanyConfigContext'
import {
  usePrintBarcodeLabels,
  type ProductLabel,
  type PrinterInfo,
  type PrintModalExtras,
  type PrintConfig,
  type SavedPrinterConfig,
} from '../importer/components/PrintBarcodeLabels'
import { apiFetch } from '../../lib/http'

type RawPrinterLabelConfig = {
  id: string
  name: string
  printer_port: string
  width_mm?: number
  height_mm?: number
  gap_mm?: number
  columns?: number
  column_gap_mm?: number
  copies?: number
  show_price?: boolean
  show_category?: boolean
  header_text?: string
  footer_text?: string
  offset_xmm?: number
  offset_ymm?: number
  barcode_width?: number
  price_alignment?: PrintConfig['priceAlignment']
  created_at: string
  updated_at: string
}

const clampValue = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

export default function ProductosList() {
  const [items, setItems] = useState<Producto[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { empresa } = useParams()
  const { success, error: toastError } = useToast()
  const { symbol: currencySymbol } = useCurrency()
  const sector = useCompanySector()
  const sectorFeatures = useSectorFeaturesFromConfig()
  const [q, setQ] = useState('')
  const [filterActivo, setFilterActivo] = useState<'all' | 'activo' | 'inactivo'>('all')
  const [filterCategoria, setFilterCategoria] = useState<string>('all')
  const [showCategoriesModal, setShowCategoriesModal] = useState(false)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [categorias, setCategorias] = useState<Array<{ id: string; name: string }>>([])
  const { open: openPrintLabels, PrintModal, updateModalExtras } = usePrintBarcodeLabels()
  const [printers, setPrinters] = useState<PrinterInfo[]>([])
  const [selectedPrinter, setSelectedPrinter] = useState<PrinterInfo | null>(null)
  const selectedPrinterRef = useRef<PrinterInfo | null>(null)
  const [printerSaving, setPrinterSaving] = useState(false)
  const [defaultPrintConfig, setDefaultPrintConfig] = useState<PrintConfig>({
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
  })
  const [savedConfigs, setSavedConfigs] = useState<SavedPrinterConfig[]>([])
  const [selectedSavedConfigId, setSelectedSavedConfigId] = useState<string | null>(null)
  const [configsLoading, setConfigsLoading] = useState(false)
  const selectedSavedConfigIdRef = useRef<string | null>(null)
  const fetchPrinters = useCallback(async (): Promise<PrinterInfo[]> => {
    try {
      const data = await apiFetch<PrinterInfo[]>('v1/tenant/printing/printers')
      setPrinters(data)
      return data
    } catch (err) {
      console.error('Error cargando impresoras:', err)
      return []
    }
  }, [])

  const normalizeSavedConfig = useCallback(
    (config: RawPrinterLabelConfig): SavedPrinterConfig => ({
      id: config.id,
      name: config.name,
      printerPort: config.printer_port,
      widthMm: config.width_mm ?? defaultPrintConfig.widthMm,
      heightMm: config.height_mm ?? defaultPrintConfig.heightMm,
      gapMm: config.gap_mm ?? defaultPrintConfig.gapMm,
      columns: config.columns ?? defaultPrintConfig.columns,
      columnGapMm: config.column_gap_mm ?? defaultPrintConfig.columnGapMm,
      copies: config.copies ?? defaultPrintConfig.copies,
      showPrice: config.show_price ?? defaultPrintConfig.showPrice,
      showCategory: config.show_category ?? defaultPrintConfig.showCategory,
      headerText: config.header_text ?? defaultPrintConfig.headerText,
      footerText: config.footer_text ?? defaultPrintConfig.footerText,
      offsetXmm: config.offset_xmm ?? defaultPrintConfig.offsetXmm,
      offsetYmm: config.offset_ymm ?? defaultPrintConfig.offsetYmm,
      barcodeWidth: config.barcode_width ?? defaultPrintConfig.barcodeWidth,
      priceAlignment: config.price_alignment ?? defaultPrintConfig.priceAlignment,
      createdAt: config.created_at,
    }),
    [defaultPrintConfig],
  )

  const fetchSavedConfigsForPrinter = useCallback(
    async (port: string | null, resetSelection = true) => {
      if (!port) {
        setSavedConfigs([])
        if (resetSelection) {
          setSelectedSavedConfigId(null)
        }
        return
      }

      if (resetSelection) {
        setSelectedSavedConfigId(null)
      }
      setConfigsLoading(true)

      try {
        const rawConfigs = await apiFetch<RawPrinterLabelConfig[]>(
          `/v1/tenant/printing/configurations?port=${encodeURIComponent(port)}`
        )
        const normalizedConfigs = rawConfigs.map((config) => normalizeSavedConfig(config))
        setSavedConfigs(normalizedConfigs)
      } catch (err) {
        console.error('Error cargando configuraciones guardadas:', err)
      } finally {
        setConfigsLoading(false)
      }
    },
    [normalizeSavedConfig],
  )

  const handlePrinterSelect = useCallback(
    (port: string) => {
      if (!port) {
        setSelectedPrinter(null)
        void fetchSavedConfigsForPrinter(null)
        return
      }
      const match = printers.find((printer) => printer.port === port)
      const selected = match ? match : { port, name: port }
      setSelectedPrinter(selected)
      void fetchSavedConfigsForPrinter(port)
    },
    [printers, fetchSavedConfigsForPrinter],
  )

  const handleSavedConfigSelect = useCallback((configId: string | null) => {
    setSelectedSavedConfigId(configId)
  }, [])

  const buildModalExtras = useCallback(
    (
      selected: PrinterInfo | null,
      overrides?: {
        savedConfigs?: SavedPrinterConfig[]
        selectedConfigId?: string | null
      },
    ): PrintModalExtras => {
      const currentSavedConfigs = overrides?.savedConfigs ?? savedConfigs
      const currentSelectedConfigId = overrides?.selectedConfigId ?? selectedSavedConfigId
      return {
        printers,
        selectedPrinter: selected,
        savedConfigs: currentSavedConfigs,
        selectedConfigId: currentSelectedConfigId,
        onSelectPrinter: handlePrinterSelect,
        onSelectSavedConfig: handleSavedConfigSelect,
        printerSaving,
        configsLoading,
      }
    },
    [
      printers,
      savedConfigs,
      selectedSavedConfigId,
      handlePrinterSelect,
      handleSavedConfigSelect,
      printerSaving,
      configsLoading,
    ],
  )

  const loadPrinterSettings = useCallback(
    async (available: PrinterInfo[]) => {
      try {
        const settings = await apiFetch<{
          port?: string
          name?: string
          label_config?: {
            width_mm?: number
            height_mm?: number
            gap_mm?: number
            columns?: number
            column_gap_mm?: number
            show_price?: boolean
            show_category?: boolean
            copies?: number
            header_text?: string
            footer_text?: string
            offset_xmm?: number
            offset_ymm?: number
            barcode_width?: number
            price_alignment?: PrintConfig['priceAlignment']
          }
        } | null>('/v1/tenant/printing/settings')
        if (settings?.label_config) {
            setDefaultPrintConfig((prev) => ({
              ...prev,
              widthMm: settings.label_config?.width_mm ?? prev.widthMm,
              heightMm: settings.label_config?.height_mm ?? prev.heightMm,
              gapMm: settings.label_config?.gap_mm ?? prev.gapMm,
              columns: settings.label_config?.columns ?? prev.columns,
              columnGapMm: settings.label_config?.column_gap_mm ?? prev.columnGapMm,
              showPrice: settings.label_config?.show_price ?? prev.showPrice,
              showCategory: settings.label_config?.show_category ?? prev.showCategory,
              copies: settings.label_config?.copies ?? prev.copies,
              headerText: settings.label_config?.header_text ?? prev.headerText,
              footerText: settings.label_config?.footer_text ?? prev.footerText,
              offsetXmm: settings.label_config?.offset_xmm ?? prev.offsetXmm,
              offsetYmm: settings.label_config?.offset_ymm ?? prev.offsetYmm,
              barcodeWidth: settings.label_config?.barcode_width ?? prev.barcodeWidth,
              priceAlignment: settings.label_config?.price_alignment ?? prev.priceAlignment,
            }))
        }
        if (!settings?.port) {
          setSelectedPrinter(null)
          await fetchSavedConfigsForPrinter(null)
          return
        }
        const match = available.find((printer) => printer.port === settings.port)
        if (match) {
          setSelectedPrinter(match)
        } else {
          setSelectedPrinter({ port: settings.port, name: settings.name || settings.port })
        }
        await fetchSavedConfigsForPrinter(settings.port)
      } catch (err) {
        console.error('Error cargando configuraciön de impresora:', err)
      }
    },
    [fetchSavedConfigsForPrinter],
  )

  const extrasSignature = useMemo(
    () =>
      [
        selectedPrinter?.port ?? '',
        selectedSavedConfigId ?? '',
        savedConfigs.map((config) => config.id).join(','),
        printerSaving ? 'saving' : 'idle',
        configsLoading ? 'loading' : 'ready',
      ].join('|'),
    [selectedPrinter?.port, selectedSavedConfigId, savedConfigs, printerSaving, configsLoading],
  )

  const extrasRef = useRef<string | null>(null)

  useEffect(() => {
    const signature = extrasSignature
    if (extrasRef.current === signature) {
      return
    }
    extrasRef.current = signature
    updateModalExtras?.(buildModalExtras(selectedPrinter))
  }, [buildModalExtras, extrasSignature, selectedPrinter, updateModalExtras])

  const promptToSaveLabelConfig = useCallback(
    async (printConfig: PrintConfig) => {
      const printer = selectedPrinterRef.current || selectedPrinter
      if (!printer?.port) {
        return
      }
      const shouldSave = window.confirm(
        '¿Deseas guardar esta configuración para la impresora seleccionada?'
      )
      if (!shouldSave) {
        return
      }
      const suggestedName = `Etiqueta ${printConfig.widthMm}×${printConfig.heightMm} mm`
      const name = window.prompt('Nombre de la configuración', suggestedName)
      if (!name?.trim()) {
        toastError('Debes indicar un nombre válido para guardar la configuración.')
        return
      }
      try {
        const saved = await apiFetch<RawPrinterLabelConfig>('/v1/tenant/printing/configurations', {
          method: 'POST',
          body: JSON.stringify({
            printer_port: printer.port,
            name: name.trim(),
            label_config: {
              width_mm: printConfig.widthMm,
              height_mm: printConfig.heightMm,
              gap_mm: printConfig.gapMm,
              columns: printConfig.columns,
              column_gap_mm: printConfig.columnGapMm,
              copies: Math.max(1, printConfig.copies),
              show_price: printConfig.showPrice,
              show_category: printConfig.showCategory,
              header_text: printConfig.headerText || undefined,
              footer_text: printConfig.footerText || undefined,
              offset_xmm: clampValue(printConfig.offsetXmm, -30, 30),
              offset_ymm: clampValue(printConfig.offsetYmm, -30, 30),
              barcode_width: clampValue(printConfig.barcodeWidth, 1, 5),
              price_alignment: printConfig.priceAlignment,
            },
          }),
        })
        await fetchSavedConfigsForPrinter(printer.port, false)
        setSelectedSavedConfigId(saved.id)
        success('Configuración guardada.')
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Error guardando la configuración'
        toastError(message)
      }
    },
    [fetchSavedConfigsForPrinter, selectedPrinter, success, toastError],
  )

  useEffect(() => {
    let mounted = true
    ;(async () => {
      const available = await fetchPrinters()
      if (!mounted) return
      await loadPrinterSettings(available)
    })()
    return () => {
      mounted = false
    }
  }, [fetchPrinters, loadPrinterSettings])

  useEffect(() => {
    selectedPrinterRef.current = selectedPrinter
  }, [selectedPrinter])

  useEffect(() => {
    selectedSavedConfigIdRef.current = selectedSavedConfigId
  }, [selectedSavedConfigId])

  // Cargar categorías para el filtro
  useEffect(() => {
    ;(async () => {
      try {
        const cats = await listCategorias()
        setCategorias(cats)
      } catch (e) {
        console.error('Error cargando categorías:', e)
      }
    })()
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setLoading(true)
        setItems(await listProductos())
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const [sortKey, setSortKey] = useState<'name' | 'sku' | 'price'>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [per, setPer] = useState(10)

  const filtered = useMemo(() => {
    let result = items.filter(
      (p) =>
        (p.name || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.sku || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.product_metadata?.Código_barras || '').toLowerCase().includes(q.toLowerCase()) ||
        (p.product_metadata?.marca || '').toLowerCase().includes(q.toLowerCase())
    )

    if (filterActivo === 'activo') {
      result = result.filter((p) => p.active)
    } else if (filterActivo === 'inactivo') {
      result = result.filter((p) => !p.active)
    }

    if (filterCategoria !== 'all') {
      result = result.filter((p) => p.categoria === filterCategoria)
    }

    return result
  }, [items, q, filterActivo, filterCategoria])

  const sorted = useMemo(() => {
    const dir = sortDir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const av = ((a as any)[sortKey] || '').toString().toLowerCase()
      const bv = ((b as any)[sortKey] || '').toString().toLowerCase()
      return av < bv ? -1 * dir : av > bv ? 1 * dir : 0
    })
  }, [filtered, sortKey, sortDir])

  const { page, setPage, totalPages, view, perPage, setPerPage } = usePagination(sorted, per)
  useEffect(() => setPerPage(per), [per, setPerPage])

  const buildLabelFromProduct = (product: Producto): ProductLabel => {
    const metadata = product.product_metadata || {}
    const metadataBarcode =
      metadata.codigo_barras ||
      metadata.codigo ||
      metadata['Codigo_barras'] ||
      metadata['Código_barras']

    const codigo = (metadataBarcode || product.sku || product.id).toString()

    return {
      id: product.id,
      sku: product.sku || product.id,
      name: product.name,
      codigo_barras: codigo,
      precio_venta: product.price,
      categoria: product.categoria || undefined,
    }
  }

  const formatPriceLabel = (value?: number) =>
    value !== undefined && value !== null ? `${value.toFixed(2)} ${currencySymbol}` : undefined

  const handleSendToPrinter = async (labels: ProductLabel[], printConfig: PrintConfig) => {
    if (labels.length === 0) {
      const error = new Error('Selecciona al menos un producto para imprimir.')
      toastError(error.message)
      throw error
    }

    const printerToUse = selectedPrinterRef.current || selectedPrinter
    if (!printerToUse?.port) {
      const error = new Error('Selecciona una impresora antes de imprimir.')
      toastError(error.message)
      throw error
    }

    const normalizedConfig = {
      ...printConfig,
      copies: Math.max(1, printConfig.copies),
      columns: Math.max(1, Math.min(6, Math.round(printConfig.columns))),
      columnGapMm: clampValue(printConfig.columnGapMm, 0, 20),
      offsetXmm: clampValue(printConfig.offsetXmm, -30, 30),
      offsetYmm: clampValue(printConfig.offsetYmm, -30, 30),
      barcodeWidth: clampValue(printConfig.barcodeWidth, 1, 5),
    }

    try {
      const payload = {
        labels: labels.map((label) => ({
          name: label.name,
          barcode: label.codigo_barras,
          price: normalizedConfig.showPrice ? formatPriceLabel(label.precio_venta) : undefined,
          copies: 1,
        })),
        port: printerToUse.port,
        width_mm: normalizedConfig.widthMm,
        height_mm: normalizedConfig.heightMm,
        gap_mm: normalizedConfig.gapMm,
        columns: normalizedConfig.columns,
        column_gap_mm: normalizedConfig.columnGapMm,
        header_text: normalizedConfig.headerText || undefined,
        footer_text: normalizedConfig.footerText || undefined,
        offset_xmm: normalizedConfig.offsetXmm,
        offset_ymm: normalizedConfig.offsetYmm,
        barcode_width: normalizedConfig.barcodeWidth,
        price_alignment: normalizedConfig.priceAlignment,
      }

      await apiFetch('v1/tenant/printing/labels/batch', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      success(
        `Impresi?n enviada a ${printerToUse.name || printerToUse.port}.`
      )
      if (!selectedSavedConfigIdRef.current) {
        await promptToSaveLabelConfig(normalizedConfig)
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error enviando a la impresora'
      toastError(message)
      throw err
    }
  }

  const handlePrintLabels = () => {
    const sourceProducts =
      selectedIds.length > 0 ? items.filter((p) => selectedIds.includes(p.id)) : view

    if (sourceProducts.length === 0) {
      toastError('Selecciona al menos un producto para imprimir etiquetas.')
      return
    }

    const extras = buildModalExtras(selectedPrinter)
    openPrintLabels(
      sourceProducts.map((product) => buildLabelFromProduct(product)),
      {
        defaultConfig: defaultPrintConfig,
        onPrint: handleSendToPrinter,
        modalExtras: extras,
        currencySymbol,
      },
    )
    updateModalExtras?.(extras)
  }

  const exportCSV = () => {
    const headers = ['Code', 'Nombre', 'Precio', 'IVA', 'Status']
    const rows = sorted.map((p) => [p.sku || '', p.name, p.price?.toFixed(2) || '0', `${p.iva_tasa || 0}%`, p.active ? 'Activo' : 'Inactivo'])

    const csv = [headers, ...rows].map((row) => row.join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `productos-${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Productos</h1>
          <p className="mt-1 text-sm text-gray-500">Catálogo de productos y servicios</p>
        </div>
        <div className="flex gap-2">
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={() => setShowCategoriesModal(true)}
            title="Gestionar categorías"
          >
            🏷️ categorías
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={exportCSV}
            title="Exportar a CSV"
          >
            📥 Exportar
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            onClick={handlePrintLabels}
            title="Imprimir etiquetas (c?digo y precio)"
          >
            Imprimir etiquetas
          </button>
                    {items.length > 0 && (<button
                      className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors font-medium"
                                  onClick={async () => {
                                    if (prompt('Para confirmar la eliminación de todos los productos, escriba PURGE') === 'PURGE') {
                                      try {
                                        await purgeProductos();
                                        setItems([]);
                                        success('Todos los productos han sido eliminados.');
                                      } catch (e) {
                                        toastError(getErrorMessage(e));
                                      }
                                    }
                                  }}                      title="Eliminar todos los productos"
                    >
                      🗑️ Eliminar todo
                    </button>)}

                    <button
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
            onClick={() => nav('nuevo')}
          >
            <span className="text-lg">➕</span> Nuevo producto
          </button>
        </div>
      </div>

      {/* Acciones masivas sobre productos SELECCIONADOS */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-medium text-blue-900">{selectedIds.length} producto(s) seleccionado(s)</span>
            <button
              onClick={() => setSelectedIds([])}
              className="text-sm text-blue-600 hover:underline"
            >
              Deseleccionar todos
            </button>
          </div>
          <div className="flex gap-2">
            <button
              className="bg-white border border-purple-300 text-purple-700 px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors font-medium text-sm"
              onClick={async () => {
                const categoryName = prompt('Nombre de la categoría para asignar:')
                if (!categoryName || !categoryName.trim()) return

                try {
                  const result = await bulkAssignCategory(selectedIds, categoryName.trim())
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success(`${result.updated} productos actualizados${result.category_created ? ' (categoría creada)' : ''}`)
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              🏷️ Asignar categoría
            </button>
            <button
              className="bg-white border border-green-300 text-green-700 px-4 py-2 rounded-lg hover:bg-green-50 transition-colors font-medium text-sm"
              onClick={async () => {
                try {
                  await bulkSetActive(selectedIds, true)
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success('Productos activados')
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              ✓ Activar
            </button>
            <button
              className="bg-white border border-yellow-300 text-yellow-700 px-4 py-2 rounded-lg hover:bg-yellow-50 transition-colors font-medium text-sm"
              onClick={async () => {
                try {
                  await bulkSetActive(selectedIds, false)
                  await (async () => {
                    setItems(await listProductos())
                  })()
                  setSelectedIds([])
                  success('Productos desactivados')
                } catch (e: any) {
                  toastError(getErrorMessage(e))
                }
              }}
            >
              ✗ Desactivar
            </button>
          </div>
        </div>
      )}

      <div className="bg-white shadow-sm rounded-lg p-4 mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por nombre, Código, EAN o marca..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label="Buscar productos"
          />
          <select
            value={filterCategoria}
            onChange={(e) => setFilterCategoria(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">Todas las categorías</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.name}>
                {cat.name}
              </option>
            ))}
          </select>
          <select
            value={filterActivo}
            onChange={(e) => setFilterActivo(e.target.value as any)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">Todos los estados</option>
            <option value="activo">Solo activos</option>
            <option value="inactivo">Solo inactivos</option>
          </select>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <label className="text-gray-600">Por página:</label>
            <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border border-gray-300 px-3 py-1 rounded">
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="text-gray-600">
            <span className="font-medium">{filtered.length}</span> productos encontrados
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      )}

      {errMsg && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <strong className="font-medium">Error:</strong> {errMsg}
        </div>
      )}

      {!loading && (
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-center w-12">
                    <input
                      type="checkbox"
                      checked={view.length > 0 && selectedIds.length === view.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds(view.map(p => p.id))
                        } else {
                          setSelectedIds([])
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('sku')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Código {sortKey === 'sku' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('name')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Nombre {sortKey === 'name' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Categoría</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">EAN</th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('price')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      Precio {sortKey === 'price' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">IVA</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Estado</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {view.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(p.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIds([...selectedIds, p.id])
                        } else {
                          setSelectedIds(selectedIds.filter(id => id !== p.id))
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="font-mono text-xs text-gray-900 font-medium">{p.sku || '—'}</span>
                  </td>
                  <td className="px-4 py-3">
                  <div className="text-sm font-medium text-gray-900">{p.name}</div>
                  {p.description && <div className="text-xs text-gray-500 truncate max-w-xs">{p.description}</div>}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  {p.categoria ? (
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                          {p.categoria}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-gray-600">{p.product_metadata?.Código_barras || '—'}</span>
                    </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm font-semibold text-gray-900">{p.price?.toFixed(2) || '0.00'} {currencySymbol}</span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-600">{p.iva_tasa || 0}%</span>
                  </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          p.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {p.active ? '✓ Activo' : '✗ Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                      <Link to={`${p.id}/editar`} className="text-blue-600 hover:text-blue-900 mr-4">
                        Editar
                      </Link>
                      {(sectorFeatures?.recipes ||
                        sector.features?.recipes ||
                        sector.plantilla?.toLowerCase().includes('panaderia') ||
                        sector.plantilla?.toLowerCase().includes('bakery')) && (
                        <button
                          className="text-amber-600 hover:text-amber-800 mr-4"
                          title="Crear receta desde este producto"
                          onClick={() =>
                            nav(
                              `/${empresa || ''}/produccion/recetas/nueva?productId=${encodeURIComponent(
                                p.id
                              )}`
                            )
                          }
                        >
                          Crear receta
                        </button>
                      )}
                      <button
                        className="text-red-600 hover:text-red-900"
                        onClick={async () => {
                          if (!confirm(`¿Eliminar "${p.name}"?`)) return
                          try {
                            await removeProducto(p.id)
                            setItems((prev) => prev.filter((x) => x.id !== p.id))
                            success('Producto eliminado')
                          } catch (e: any) {
                            toastError(getErrorMessage(e))
                          }
                        }}
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <div className="text-gray-400 text-4xl mb-3">📦</div>
                      <p className="text-gray-500 mb-2">No hay productos registrados</p>
                      <button className="text-blue-600 hover:underline font-medium" onClick={() => nav('nuevo')}>
                        Crear el primer producto
                      </button>
                    </td>
                  </tr>
                )}
                {!loading && items.length > 0 && view.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <p className="text-gray-500">No se encontraron productos con esos filtros</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-gray-200">
              <Pagination page={page} setPage={setPage} totalPages={totalPages} />
            </div>
          )}
        </div>
      )}

      {/* Modal de categorías */}
      {showCategoriesModal && (
        <CategoriasModal
          onClose={() => setShowCategoriesModal(false)}
          onCategoryCreated={() => {
            // Recargar productos para ver nuevas categorías
            setLoading(true)
            listProductos()
              .then((data) => setItems(data))
              .finally(() => setLoading(false))
          }}
        />
      )}
      {PrintModal}
    </div>
  )
}
