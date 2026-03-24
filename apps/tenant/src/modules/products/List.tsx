// apps/tenant/src/modules/products/List.tsx
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { BackButton } from '@ui'
import {
  listProductos,
  removeProducto,
  purgeProductos,
  bulkSetActive,
  bulkAssignCategory,
  bulkGenerateMissingSkus,
  listCategorias,
  updateProducto,
  type Producto,
} from './productsApi'
import SimilarProductsMergeModal from './SimilarProductsMergeModal'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useTranslation } from 'react-i18next'
import { usePagination, Pagination } from '../../shared/pagination'
import CategoriasModal from './CategoriesModal'
import { useCurrency } from '../../hooks/useCurrency'
import {
  useSectorFeaturesFromConfig,
  useCompanySector,
} from '../../contexts/CompanyConfigContext'
import { listRecipes } from '../../services/api/recetas'
import {
  usePrintBarcodeLabels,
  type ProductLabel,
  type PrinterInfo,
  type PrintModalExtras,
  type PrintConfig,
  type SavedPrinterConfig,
} from '../importador/components/PrintBarcodeLabels'
import { apiFetch } from '../../lib/http'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'
import PermissionDenied from '../../components/PermissionDenied'

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
  const { t } = useTranslation(['products', 'common'])
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
  const [showMergeModal, setShowMergeModal] = useState(false)
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
  const [recipeByProduct, setRecipeByProduct] = useState<Map<string, string>>(new Map())
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null)
  const [editingPriceValue, setEditingPriceValue] = useState<string>('')
  const [deleteTarget, setDeleteTarget] = useState<Producto | null>(null)
  const [generateAllCodesPending, setGenerateAllCodesPending] = useState<number | null>(null)
  const [generateSelectedSkuPending, setGenerateSelectedSkuPending] = useState<Producto[] | null>(null)
  const [saveLabelConfigModal, setSaveLabelConfigModal] = useState<{ config: PrintConfig; name: string } | null>(null)
  const [saveLabelConfigName, setSaveLabelConfigName] = useState('')
  const [assignCategoryModal, setAssignCategoryModal] = useState(false)
  const [assignCategoryName, setAssignCategoryName] = useState('')
  const [purgeModal, setPurgeModal] = useState(false)
  const [purgeConfirmText, setPurgeConfirmText] = useState('')
  const can = usePermission()
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
    (printConfig: PrintConfig) => {
      const printer = selectedPrinterRef.current || selectedPrinter
      if (!printer?.port) {
        return
      }
      const suggestedName = `Etiqueta ${printConfig.widthMm}×${printConfig.heightMm} mm`
      setSaveLabelConfigName(suggestedName)
      setSaveLabelConfigModal({ config: printConfig, name: suggestedName })
    },
    [selectedPrinter],
  )

  const doSaveLabelConfig = async () => {
    const printer = selectedPrinterRef.current || selectedPrinter
    if (!printer?.port || !saveLabelConfigModal) return
    if (!saveLabelConfigName.trim()) {
      toastError(t('products:list.configNameRequired', { defaultValue: 'Debes indicar un nombre válido.' }))
      return
    }
    try {
      const printConfig = saveLabelConfigModal.config
      setPrinterSaving(true)
      const saved = await apiFetch<RawPrinterLabelConfig>('/v1/tenant/printing/configurations', {
        method: 'POST',
        body: JSON.stringify({
          printer_port: printer.port,
          name: saveLabelConfigName.trim(),
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
      success(t('products:list.configSaved', { defaultValue: 'Configuración guardada.' }))
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : t('products:list.errorSavingConfig')
      toastError(message)
    } finally {
      setPrinterSaving(false)
      setSaveLabelConfigModal(null)
    }
  }

  const doGenerateAllCodes = async () => {
    try {
      const res = await bulkGenerateMissingSkus()
      success(`${res.updated} producto(s) actualizados con código.`)
      const updated = await listProductos()
      setItems(updated)
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setGenerateAllCodesPending(null)
    }
  }

  const doGenerateSelectedSku = async () => {
    if (!generateSelectedSkuPending) return
    try {
      const withoutSku = generateSelectedSkuPending
      const usedSkus = new Set(items.map(p => p.sku).filter(Boolean))
      const updates: Promise<any>[] = withoutSku.map(p => {
        const prefix = p.category ? p.category.substring(0, 3).toUpperCase() : 'PRO'
        let sku: string
        do { sku = `${prefix}-${Math.floor(Math.random() * 90000 + 10000)}` } while (usedSkus.has(sku))
        usedSkus.add(sku)
        return updateProducto(p.id, { sku })
      })
      await Promise.all(updates)
      setItems(await listProductos())
      setSelectedIds([])
      success(`SKU generado para ${withoutSku.length} producto(s)`)
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setGenerateSelectedSkuPending(null)
    }
  }

  const doAssignCategory = async () => {
    if (!assignCategoryName.trim()) {
      toastError(t('products:bulkAssignCategoryPrompt', { defaultValue: 'Indica el nombre de la categoría.' }))
      return
    }
    try {
      const result = await bulkAssignCategory(selectedIds, assignCategoryName.trim())
      setItems(await listProductos())
      setSelectedIds([])
      const created = result.category_created ? t('products:bulkAssignCategoryCreated') : ''
      success(t('products:bulkAssignCategoryResult', { updated: result.updated, created }))
      setAssignCategoryModal(false)
      setAssignCategoryName('')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const doDeleteProduct = async () => {
    if (!deleteTarget) return
    try {
      await removeProducto(deleteTarget.id)
      setItems(prev => prev.filter(x => x.id !== deleteTarget.id))
      success(t('products:deleteOne'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setDeleteTarget(null)
    }
  }

  const doPurge = async () => {
    if (purgeConfirmText !== 'PURGE') return
    try {
      await purgeProductos()
      setItems([])
      success(t('products:deleteAll'))
    } catch (e) {
      toastError(getErrorMessage(e))
    } finally {
      setPurgeModal(false)
      setPurgeConfirmText('')
    }
  }

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

  const reloadProducts = useCallback(async () => {
    try {
      setLoading(true)
      const [prods, recipes] = await Promise.all([
        listProductos(),
        listRecipes({ limit: 5000 }).catch(() => []),
      ])
      setItems(prods)
      const map = new Map<string, string>()
      for (const r of recipes) {
        if (r.product_id) map.set(r.product_id, r.id)
      }
      setRecipeByProduct(map)
    } catch (e: any) {
      const m = getErrorMessage(e)
      setErrMsg(m)
      toastError(m)
    } finally {
      setLoading(false)
    }
  }, [toastError])

  useEffect(() => {
    void reloadProducts()
  }, [reloadProducts])

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
      result = result.filter((p) => p.category === filterCategoria)
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
      categoria: product.category || undefined,
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
    const headers = [t('products:code'), t('products:name'), t('products:price'), t('products:tax'), t('products:status')]
    const rows = sorted.map((p) => [p.sku || '', p.name, p.price?.toFixed(2) || '0', `${p.tax_rate || 0}%`, p.active ? t('products:list.active') : t('products:list.inactive')])

    const csv = [headers, ...rows].map((row) => row.join(';')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `products-${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  return (
    <div className="p-6">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('products:title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('products:subtitle')}</p>
        </div>
        <div className="flex gap-2">
          {can('products:update') && (
            <ProtectedButton
              permission="products:update"
              className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              onClick={() => setShowCategoriesModal(true)}
              title={t('products:categories')}
            >
              🏷️ {t('products:categories')}
            </ProtectedButton>
          )}
          {can('products:read') && (
            <ProtectedButton
              permission="products:read"
              className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              onClick={exportCSV}
              title={t('products:export')}
            >
              📥 {t('products:export')}
            </ProtectedButton>
          )}
          {can('products:read') && (
            <ProtectedButton
              permission="products:read"
              className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium"
              onClick={handlePrintLabels}
              title={t('products:printLabelsTitle')}
            >
              {t('products:printLabels')}
            </ProtectedButton>
          )}
          {can('products:update') && items.some(p => !p.sku?.trim()) && (
            <ProtectedButton
              permission="products:update"
              className="bg-white border border-amber-400 text-amber-700 px-4 py-2 rounded-lg hover:bg-amber-50 transition-colors font-medium"
              onClick={() => {
                const count = items.filter(p => !p.sku?.trim()).length
                setGenerateAllCodesPending(count)
              }}
              title="Generar códigos para productos sin código"
            >
              ⚡ Generar códigos faltantes
            </ProtectedButton>
          )}
          {can('products:update') && (
            <ProtectedButton
              permission="products:update"
              className="bg-white border border-indigo-300 text-indigo-700 px-4 py-2 rounded-lg hover:bg-indigo-50 transition-colors font-medium"
              onClick={() => setShowMergeModal(true)}
              title={t('products:mergeDuplicates.open')}
            >
              {t('products:mergeDuplicates.open')}
            </ProtectedButton>
          )}
          {items.length > 0 && can('products:delete') && (
            <ProtectedButton
              permission="products:delete"
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors font-medium"
              onClick={() => { setPurgeConfirmText(''); setPurgeModal(true) }}
              title={t('products:deleteAll')}
            >
              🗑️ {t('products:deleteAll')}
            </ProtectedButton>
          )}

                    {can('products:create') && (
                      <ProtectedButton
                        permission="products:create"
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
                        onClick={() => nav('nuevo')}
                      >
            <span className="text-lg">➕</span> {t('products:new')}
          </ProtectedButton>
        )}
        </div>
      </div>

      {/* Acciones masivas sobre productos SELECCIONADOS */}
      {selectedIds.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="font-medium text-blue-900">{t('products:bulkSelected', { count: selectedIds.length })}</span>
            <button
              onClick={() => setSelectedIds([])}
              className="text-sm text-blue-600 hover:underline"
            >
              {t('products:bulkClear')}
            </button>
          </div>
          <div className="flex gap-2">
            {can('products:update') && (
              <ProtectedButton
                permission="products:update"
                className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors font-medium text-sm"
                onClick={() => {
                  const withoutSku = items.filter(p => selectedIds.includes(p.id) && !p.sku?.trim())
                  if (withoutSku.length === 0) {
                    success(t('products:bulkSkuAllHave', { defaultValue: 'Todos los seleccionados ya tienen código SKU' }))
                    return
                  }
                  setGenerateSelectedSkuPending(withoutSku)
                }}
              >
                # {t('products:bulkGenerateSku', { defaultValue: 'Generar SKU' })}
              </ProtectedButton>
            )}
            {can('products:update') && (
              <ProtectedButton
                permission="products:update"
                className="bg-white border border-purple-300 text-purple-700 px-4 py-2 rounded-lg hover:bg-purple-50 transition-colors font-medium text-sm"
                onClick={() => {
                  setAssignCategoryModal(true)
                }}
              >
                🏷️ {t('products:bulkAssignCategory')}
              </ProtectedButton>
            )}
            {can('products:update') && (
              <ProtectedButton
                permission="products:update"
                className="bg-white border border-green-300 text-green-700 px-4 py-2 rounded-lg hover:bg-green-50 transition-colors font-medium text-sm"
                onClick={async () => {
                  try {
                    await bulkSetActive(selectedIds, true)
                    setItems(await listProductos())
                    setSelectedIds([])
                    success(t('products:bulkActivated'))
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
              >
                ✓ {t('products:bulkActivate')}
              </ProtectedButton>
            )}
            {can('products:update') && (
              <ProtectedButton
                permission="products:update"
                className="bg-white border border-yellow-300 text-yellow-700 px-4 py-2 rounded-lg hover:bg-yellow-50 transition-colors font-medium text-sm"
                onClick={async () => {
                  try {
                    await bulkSetActive(selectedIds, false)
                    setItems(await listProductos())
                    setSelectedIds([])
                    success(t('products:bulkDeactivated'))
                  } catch (e: any) {
                    toastError(getErrorMessage(e))
                  }
                }}
              >
                ✗ {t('products:bulkDeactivate')}
              </ProtectedButton>
            )}
          </div>
        </div>
      )}

      <div className="bg-white shadow-sm rounded-lg p-4 mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('products:searchPlaceholder')}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            aria-label={t('products:searchPlaceholder')}
          />
          <select
            value={filterCategoria}
            onChange={(e) => setFilterCategoria(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">{t('products:category')} ({t('common:all')})</option>
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
            <option value="all">{t('common:all')}</option>
            <option value="activo">{t('products:active')}</option>
            <option value="inactivo">{t('products:inactive')}</option>
          </select>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <label className="text-gray-600">{t('products:perPage')}:</label>
            <select value={per} onChange={(e) => setPer(Number(e.target.value))} className="border border-gray-300 px-3 py-1 rounded">
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
          <div className="text-gray-600">
            {t('products:found', { count: filtered.length })}
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
                      {t('products:code')} {sortKey === 'sku' && (sortDir === 'asc' ? '▲' : '▼')}
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
                      {t('products:name')} {sortKey === 'name' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('products:category')}</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('products:ean')}</th>
                  <th className="px-4 py-3 text-left">
                    <button
                      className="text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-900 flex items-center gap-1"
                      onClick={() => {
                        setSortKey('price')
                        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
                      }}
                    >
                      {t('products:price')} {sortKey === 'price' && (sortDir === 'asc' ? '▲' : '▼')}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('products:tax')}</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('products:status')}</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">{t('products:actions')}</th>
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
                  {p.category ? (
                      <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                          {p.category}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="font-mono text-xs text-gray-600">{p.product_metadata?.Código_barras || '—'}</span>
                    </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {can('products:update') && editingPriceId === p.id ? (
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        autoFocus
                        className="w-24 text-sm font-semibold text-gray-900 border border-blue-400 rounded px-1 py-0.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        value={editingPriceValue}
                        onChange={(e) => setEditingPriceValue(e.target.value)}
                        onKeyDown={async (e) => {
                          if (e.key === 'Enter') {
                            const newPrice = parseFloat(editingPriceValue)
                            if (!isNaN(newPrice) && newPrice >= 0) {
                              try {
                                await updateProducto(p.id, { price: newPrice })
                                setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, price: newPrice } : x))
                              } catch (err: any) {
                                toastError(getErrorMessage(err))
                              }
                            }
                            setEditingPriceId(null)
                          } else if (e.key === 'Escape') {
                            setEditingPriceId(null)
                          }
                        }}
                        onBlur={async () => {
                          const newPrice = parseFloat(editingPriceValue)
                          if (!isNaN(newPrice) && newPrice >= 0) {
                            try {
                              await updateProducto(p.id, { price: newPrice })
                              setItems((prev) => prev.map((x) => x.id === p.id ? { ...x, price: newPrice } : x))
                            } catch (err: any) {
                              toastError(getErrorMessage(err))
                            }
                          }
                          setEditingPriceId(null)
                        }}
                      />
                    ) : (
                      <span
                        className={`text-sm font-semibold text-gray-900 ${can('products:update') ? 'cursor-pointer hover:text-blue-600 hover:underline' : ''}`}
                        title={can('products:update') ? 'Click para editar precio' : undefined}
                        onClick={() => {
                          if (!can('products:update')) return
                          setEditingPriceId(p.id)
                          setEditingPriceValue(String(p.price ?? 0))
                        }}
                      >
                        {p.price?.toFixed(2) || '0.00'} {currencySymbol}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                  <span className="text-sm text-gray-600">{p.tax_rate || 0}%</span>
                  </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          p.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {p.active ? `✓ ${t('products:active')}` : `✗ ${t('products:inactive')}`}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                      {can('products:update') && (
                        <Link to={`${p.id}/editar`} className="text-blue-600 hover:text-blue-900 mr-4">
                          {t('common:edit')}
                        </Link>
                      )}
                      {(sectorFeatures?.recipes ||
                        sector.features?.recipes ||
                        sector.plantilla?.toLowerCase().includes('panaderia') ||
                        sector.plantilla?.toLowerCase().includes('bakery')) &&
                        recipeByProduct.has(p.id) && (
                          <Link
                            to={`/${empresa || ''}/manufacturing/recetas/${recipeByProduct.get(p.id)}`}
                            className="text-green-600 hover:text-green-800 mr-4"
                            title={t('products:list.viewRecipe')}
                          >
                            {t('products:list.viewRecipe')}
                          </Link>
                        )}
                      {can('products:delete') && (
                        <ProtectedButton
                          permission="products:delete"
                          variant="ghost"
                          onClick={() => setDeleteTarget(p)}
                        >
                          {t('products:deleteOne')}
                        </ProtectedButton>
                      )}
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <div className="text-gray-400 text-4xl mb-3">📦</div>
                      <p className="text-gray-500 mb-2">{t('products:emptyTitle')}</p>
                      {can('products:create') && (
                        <ProtectedButton
                          permission="products:create"
                          className="text-blue-600 hover:underline font-medium"
                          onClick={() => nav('nuevo')}
                          variant="secondary"
                        >
                          {t('products:emptyCta')}
                        </ProtectedButton>
                      )}
                    </td>
                  </tr>
                )}
                {!loading && items.length > 0 && view.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center">
                      <p className="text-gray-500">{t('products:noResults')}</p>
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
      {/* Modal: purgar todos los productos */}
      {purgeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('products:deleteAll')}</h3>
            <p className="text-sm text-slate-600 mb-3">{t('products:deleteAllConfirm')}</p>
            <input
              type="text"
              value={purgeConfirmText}
              onChange={e => setPurgeConfirmText(e.target.value)}
              placeholder="PURGE"
              className="gc-input w-full mb-4"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && doPurge()}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setPurgeModal(false); setPurgeConfirmText('') }} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doPurge} disabled={purgeConfirmText !== 'PURGE'} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm disabled:opacity-50">{t('common:delete')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: eliminar producto */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('products:deleteOneConfirm', { name: deleteTarget.name })}</h3>
            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doDeleteProduct} className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 text-sm">{t('common:delete')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: generar códigos para todos sin SKU */}
      {generateAllCodesPending !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('products:generateCodesConfirm', { count: generateAllCodesPending, defaultValue: `¿Generar código para ${generateAllCodesPending} producto(s) sin código?` })}</h3>
            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setGenerateAllCodesPending(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doGenerateAllCodes} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">{t('common:confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: generar SKU para seleccionados */}
      {generateSelectedSkuPending !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-2">{t('products:generateSkuConfirm', { count: generateSelectedSkuPending.length, defaultValue: `¿Generar SKU para ${generateSelectedSkuPending.length} producto(s)?` })}</h3>
            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setGenerateSelectedSkuPending(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doGenerateSelectedSku} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">{t('common:confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: guardar configuración de etiqueta */}
      {saveLabelConfigModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-3">{t('products:list.saveConfig', { defaultValue: 'Guardar configuración de etiqueta' })}</h3>
            <p className="text-sm text-slate-600 mb-3">{t('products:list.saveConfigSubtitle', { defaultValue: '¿Deseas guardar esta configuración para la impresora seleccionada?' })}</p>
            <label className="text-sm font-medium text-slate-700 block mb-1">{t('products:list.configName', { defaultValue: 'Nombre de la configuración' })}</label>
            <input
              type="text"
              value={saveLabelConfigName}
              onChange={e => setSaveLabelConfigName(e.target.value)}
              className="gc-input w-full mb-4"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && doSaveLabelConfig()}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setSaveLabelConfigModal(null)} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doSaveLabelConfig} disabled={printerSaving} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm disabled:opacity-50">{printerSaving ? t('common:saving', { defaultValue: 'Guardando...' }) : t('common:save')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: asignar categoría masiva */}
      {assignCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-base mb-3">🏷️ {t('products:bulkAssignCategory')}</h3>
            <label className="text-sm font-medium text-slate-700 block mb-1">{t('products:bulkAssignCategoryPrompt', { defaultValue: 'Nombre de la categoría' })}</label>
            <input
              type="text"
              value={assignCategoryName}
              onChange={e => setAssignCategoryName(e.target.value)}
              className="gc-input w-full mb-4"
              autoFocus
              onKeyDown={e => e.key === 'Enter' && doAssignCategory()}
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => { setAssignCategoryModal(false); setAssignCategoryName('') }} className="px-4 py-2 rounded bg-slate-200 hover:bg-slate-300 text-sm">{t('common:cancel')}</button>
              <button onClick={doAssignCategory} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 text-sm">{t('common:confirm')}</button>
            </div>
          </div>
        </div>
      )}

      {PrintModal}
      <SimilarProductsMergeModal
        open={showMergeModal}
        onClose={() => setShowMergeModal(false)}
        onMerged={reloadProducts}
      />
    </div>
  )
}
