/**
 * usePOSActions — Lógica de negocio del terminal POS.
 *
 * Recibe el estado centralizado (usePOSState) y expone todas las acciones:
 * carga de datos, gestión del carrito, checkout, impresión, tickets retenidos, etc.
 *
 * Los hooks de plataforma (useTranslation, useToast, etc.) se consumen aquí
 * para evitar que POSView deba importarlos directamente.
 */
import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useDocumentIDTypes } from '../../../hooks/useDocumentIDTypes'
import { useToast } from '../../../shared/toast'
import { useAuth } from '../../../auth/AuthContext'
import useOfflineSync from './useOfflineSync'
import {
    listRegisters,
    createRegister,
    createReceipt,
    deleteReceipt,
    payReceipt,
    printReceipt,
    addToOutbox,
    issueDocument,
    renderDocumentWithFormat,
    type CheckoutResponse,
    type QueuedPOSCreateAndCheckout,
    type ReceiptTotals,
    type SaleDraft,
} from '../services'
import {
    createProducto as createProduct,
    listProductos as listProducts,
    searchProductos as searchProducts,
    updateProducto as updateProduct,
} from '../../products/productsApi'
import { getCompanySettings, getDefaultReorderPoint, getDefaultTaxRate, formatCurrency, savePosTheme, shouldCreateInvoice } from '../../../services/companySettings'
import { listWarehouses, adjustStock } from '../../inventory/services'
import { listUsuarios } from '../../users/services'
import { createCliente as createCustomer, listClientes as listCustomers } from '../../customers/services'
import type { Cliente as Customer } from '../../customers/services'
import type { Producto as Product } from '../../products/productsApi'
import type { POSPayment } from '../../../types/pos'
import { POS_DRAFT_KEY } from '../../../constants/storage'
import { POS_THEME_KEY, normalizePosTheme, type CartItem, type POSState } from './usePOSState'
import { createOfflineTempId, isNetworkIssue } from '../../../lib/offlineHttp'
import {
    getBulkPricingShortcutItems,
    normalizeBakeryShortcutLetter,
    sanitizeBulkPricingItem,
    type BulkPricingItem,
} from '../bakeryShortcuts'
import { computeLineTotal, roundMoney } from '../utils/money'

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePOSActions(state: POSState, isCompanyAdmin: boolean) {
    const { t } = useTranslation(['pos', 'common'])
    const toast = useToast()
    const { profile } = useAuth()
    const { isOnline } = useOfflineSync()
    const { data: documentIdTypes } = useDocumentIDTypes()

    const {
        // Registers / Shifts
        setRegisters, setSelectedRegister,
        // Products
        products, setProducts, defaultTaxPct, setDefaultTaxPct,
        setInventoryConfig, selectedCategory,
        // Cart
        cart, setCart, globalDiscountPct, setGlobalDiscountPct,
        ticketNotes, setTicketNotes, setCurrentReceiptId, currentReceiptId, paymentDraftContext, setPaymentDraftContext,
        heldTickets, setHeldTickets,
        // Buyer
        buyerMode, setBuyerMode, buyerIdType, setBuyerIdType,
        buyerIdNumber, buyerName, buyerEmail, isWholesaleCustomer,
        setSelectedClient, selectedClient, clients, setClients,
        setClientsLoading, clientsLoading, setClientsLoadError,
        clientsLoadAttemptedRef,
        // Modals
        setShowPaymentModal, setShowBuyerModal, showBuyerModal,
        setShowInvoiceModal, setShowDiscountModal, setShowResumeTicketModal,
        setShowCreateProductModal, showCreateProductModal,
        setShowPendingModal, setShowPrintPreview,
        quickInputState, setQuickInputState,
        // Print
        setAndPersistLastPrintJob, setPrintHtml, docPrintFormat,
        setSkipPrint, skipPrint,
        // Settings
        setCompanySettings, companySettings, setDocumentConfig, documentConfig,
        setAutoCreateInvoice, setPosTheme,
        // Cashiers
        setCashiers, selectedCashierId,
        // Warehouses
        warehouses, setWarehouses, headerWarehouseId, setHeaderWarehouseId,
        // UI
        setLoading, loading, setCreatingProduct, creatingProduct,
        setCreateProductForm, createProductForm, setBarcodeInput,
        // Refs
        pendingSaleRef, buyerAlertRef, buyerContinueRef,
        barcodeBufferRef, barcodeTimerRef,
        createProductNameInputRef,
    } = state

    // ------------------------------------------------------------------
    // Totals (calculados localmente — sin HTTP por keypress)
    // ------------------------------------------------------------------
    const [totals, setTotals] = useState<ReceiptTotals>({
        subtotal: 0,
        line_discounts: 0,
        global_discount: 0,
        base_after_discounts: 0,
        tax: 0,
        total: 0,
    })

    const bulkPricingItems = useMemo(
        () =>
            (((companySettings?.pos_config as any)?.bulk_pricing_items || []) as BulkPricingItem[]).map(
                sanitizeBulkPricingItem
            ),
        [companySettings]
    )

    const bulkShortcutItems = useMemo(
        () => getBulkPricingShortcutItems(bulkPricingItems),
        [bulkPricingItems]
    )

    // Cálculo local determinista — item.price ya incluye bulk pricing blended
    // Todos los cálculos pasan por roundMoney() para evitar arrastre de error
    // de IEEE 754 al sumar muchas líneas / pagos.
    useEffect(() => {
        if (cart.length === 0) {
            setTotals({ subtotal: 0, line_discounts: 0, global_discount: 0, base_after_discounts: 0, tax: 0, total: 0 })
            return
        }
        const subtotal = cart.reduce((sum, item) => sum + roundMoney(item.price * item.qty), 0)
        const lineDiscounts = cart.reduce((sum, item) => sum + roundMoney(item.price * item.qty * (item.discount_pct / 100)), 0)
        const baseAfterLineDisc = roundMoney(subtotal - lineDiscounts)
        const globalDisc = roundMoney(baseAfterLineDisc * (globalDiscountPct / 100))
        const base = roundMoney(baseAfterLineDisc - globalDisc)
        const tax = roundMoney(cart.reduce((sum, item) => {
            const lineBase = roundMoney(item.price * item.qty * (1 - item.discount_pct / 100))
            return sum + roundMoney(lineBase * (item.iva_tasa / 100))
        }, 0))
        setTotals({
            subtotal: roundMoney(subtotal),
            line_discounts: roundMoney(lineDiscounts),
            global_discount: globalDisc,
            base_after_discounts: base,
            tax,
            total: roundMoney(base + tax),
        })
    }, [cart, globalDiscountPct])

    // ------------------------------------------------------------------
    // Tipos de identificación y política de comprador
    // ------------------------------------------------------------------
    const idTypeOptions = useMemo(() => {
        const raw = documentConfig?.id_types || documentConfig?.idTypes || []
        if (!Array.isArray(raw)) return []
        return raw.map((value: any) => String(value)).filter((value: string) => value.trim())
    }, [documentConfig])

    const apiIdTypeOptions = useMemo(() => {
        return documentIdTypes
            .map((item) => String(item.code || '').trim())
            .filter((value) => value && value.toUpperCase() !== 'NONE')
    }, [documentIdTypes])

    const allowedIdTypes = useMemo(() => {
        const sanitized = idTypeOptions.map((v) => v.trim()).filter((v) => v && v.toUpperCase() !== 'NONE')
        return sanitized.length > 0 ? sanitized : apiIdTypeOptions
    }, [idTypeOptions, apiIdTypeOptions])

    const buyerPolicy = useMemo(() => {
        const raw = (documentConfig?.buyer_policy || documentConfig?.buyerPolicy || {}) as any
        return {
            consumerFinalEnabled: raw.consumerFinalEnabled ?? raw.consumer_final_enabled ?? true,
            consumerFinalMaxTotal: Number(raw.consumerFinalMaxTotal ?? raw.consumer_final_max_total ?? 0),
            requireBuyerAboveAmount: raw.requireBuyerAboveAmount ?? raw.require_buyer_above_amount ?? false,
        }
    }, [documentConfig])

    const canUseConsumerFinal = useMemo(() => {
        if (buyerPolicy.consumerFinalEnabled === false) return false
        if (buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0) {
            return totals.total <= buyerPolicy.consumerFinalMaxTotal
        }
        return true
    }, [buyerPolicy, totals.total])

    // Sincronizar docPrintFormat con configuración
    useEffect(() => {
        const raw = (documentConfig as any)?.render_format_default || (documentConfig as any)?.renderFormatDefault
        if (raw === 'A4_PDF') state.setDocPrintFormat('A4_PDF')
        else if (raw === 'THERMAL_80MM') state.setDocPrintFormat('THERMAL_80MM')
    }, [documentConfig])

    // Normalizar buyerIdType cuando cambian allowedIdTypes
    useEffect(() => {
        if (!buyerIdType) {
            setBuyerIdType(allowedIdTypes[0] || '')
            return
        }
        const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
        if (normalized && normalized !== buyerIdType) setBuyerIdType(normalized)
    }, [buyerIdType, allowedIdTypes])

    // Forzar IDENTIFIED si consumer final está deshabilitado
    useEffect(() => {
        if (buyerPolicy.consumerFinalEnabled === false && buyerMode === 'CONSUMER_FINAL') {
            setBuyerMode('IDENTIFIED')
        }
    }, [buyerMode, buyerPolicy.consumerFinalEnabled])

    // Alerta cuando supera el límite de consumidor final
    useEffect(() => {
        if (!showBuyerModal) { buyerAlertRef.current = false; return }
        if (buyerMode !== 'CONSUMER_FINAL') { buyerAlertRef.current = false; return }
        if (!canUseConsumerFinal && !buyerAlertRef.current) {
            buyerAlertRef.current = true
            toast.warning(t('pos:errors.totalExceedsLimit'))
            setBuyerMode('IDENTIFIED')
        }
        if (canUseConsumerFinal) buyerAlertRef.current = false
    }, [buyerMode, canUseConsumerFinal, showBuyerModal])

    useEffect(() => {
        if (showBuyerModal) buyerContinueRef.current = false
    }, [showBuyerModal])

    // ------------------------------------------------------------------
    // Helpers internos
    // ------------------------------------------------------------------
    const normalizeIdType = (value: string, options: string[]) => {
        const norm = (input: string) =>
            input.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9]+/g, '').trim().toUpperCase()
        const target = norm(value || '')
        if (!target) return ''
        return options.find((opt) => norm(opt) === target) || ''
    }

    const normalizeCode = (value?: string | null) =>
        (value || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9]+/g, '').trim().toUpperCase()

    const normalizeText = (value?: string | null) =>
        (value || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^A-Za-z0-9]+/g, '').trim().toUpperCase()

    // Mantenido como alias local para compatibilidad con llamadas existentes.
    // Nuevos cálculos deben usar roundMoney() de utils/money directamente.
    const round2 = roundMoney

    const normalizeCurrencyCode = (raw?: string): string => {
        const code = (raw || '').trim().toUpperCase()
        const aliases: Record<string, string> = { US: 'USD', USA: 'USD' }
        return aliases[code] || code
    }

    const mapPaymentMethod = (method: POSPayment['method']): SaleDraft['payments'][number]['method'] => {
        switch (method) {
            case 'cash': return 'CASH'
            case 'card': return 'CARD'
            case 'link': return 'TRANSFER'
            default: return 'OTHER'
        }
    }

    const extractDocumentConfig = (settings: any) => {
        if (!settings || typeof settings !== 'object') return {}
        const docs = (settings.settings && (settings.settings as any).documents) || {}
        if (docs && typeof docs === 'object') return docs
        const invoiceCfg = (settings as any).invoice_config
        return invoiceCfg && typeof invoiceCfg === 'object' ? invoiceCfg : {}
    }

    // ------------------------------------------------------------------
    // Pricing helpers
    // ------------------------------------------------------------------
    const getReorderPoint = (product: Product) => {
        const point = Number(product.product_metadata?.reorder_point ?? state.inventoryConfig.reorderPoint ?? 0)
        return Number.isFinite(point) ? point : 0
    }

    const violatesStockPolicy = (product: Product, desiredQty: number, opts?: { ignoreReorder?: boolean }) => {
        const stock = Number(product.stock ?? 0)
        const remaining = stock - desiredQty
        if (!state.inventoryConfig.allowNegative && remaining < 0) {
            toast.warning(t('pos:errors.insufficientStockAmount', { stock: String(stock) }))
            return true
        }
        if (!opts?.ignoreReorder) {
            const reorderPoint = getReorderPoint(product)
            if (reorderPoint > 0 && remaining < reorderPoint) {
                toast.warning(t('pos:errors.lowStockMinimumAmount', { minimum: String(reorderPoint) }))
                return true
            }
        }
        return false
    }

    const getWholesaleConfig = (product: Product) => {
        const meta = (product.product_metadata || {}) as any
        const raw = (meta.wholesale || {}) as any
        if (!raw || raw.enabled === false) return null
        const price = Number(raw.price)
        if (!Number.isFinite(price) || price <= 0) return null
        return {
            price,
            min_qty_units: Number(raw.min_qty_units ?? 0) || 0,
            min_qty_by_pack: (raw.min_qty_by_pack || {}) as Record<string, number>,
            apply_mode: raw.apply_mode === 'excess' ? 'excess' : 'all',
        }
    }

    const resolveWholesaleThreshold = (cfg: any, packKey: string) => {
        const minUnits = Number(cfg.min_qty_units ?? 0) || 0
        const minPack = Number(cfg.min_qty_by_pack?.[packKey] ?? 0) || 0
        const candidates = [minUnits, minPack].filter((n) => n > 0)
        return candidates.length ? Math.min(...candidates) : 0
    }

    const getPricingForProduct = (product: Product, qty: number, packKey = 'unit') => {
        const basePrice = Number(product.price ?? 0) || 0
        const bulkCfg = bulkPricingItems.find((b) => b.product_id === product.id)
        if (bulkCfg && bulkCfg.quantity > 0) {
            const bulkQty = Number(bulkCfg.quantity)
            const bulkPrice = Number(bulkCfg.unit_price)
            const fullSets = Math.floor(qty / bulkQty)
            const remainder = qty % bulkQty
            if (fullSets > 0) {
                const total = fullSets * bulkPrice + remainder * basePrice
                return { unitPrice: total / qty, source: 'wholesale' as const, note: `${fullSets}×${bulkQty} = $${(fullSets * bulkPrice).toFixed(2)}${remainder > 0 ? ` + ${remainder} und` : ''}` }
            }
        }

        const cfg = getWholesaleConfig(product)
        if (!cfg) return { unitPrice: basePrice, source: 'retail' as const }

        const reorderPoint = getReorderPoint(product)
        const stock = Number(product.stock ?? 0)
        if (reorderPoint > 0 && stock < reorderPoint) return { unitPrice: basePrice, source: 'retail' as const }

        const minUnits = Number(cfg.min_qty_units ?? 0) || 0
        const meetsMin = (minUnits > 0 && qty >= minUnits) || false
        const isActive = isWholesaleCustomer || meetsMin
        if (!isActive) return { unitPrice: basePrice, source: 'retail' as const }

        if (cfg.apply_mode !== 'excess') {
            return { unitPrice: cfg.price, source: 'wholesale' as const, note: t('pos:messages.wholesale', { defaultValue: 'Wholesale' }) }
        }

        const threshold = resolveWholesaleThreshold(cfg, packKey)
        if (threshold <= 0) return { unitPrice: cfg.price, source: 'wholesale' as const, note: t('pos:messages.wholesale', { defaultValue: 'Wholesale' }) }
        if (qty <= threshold) return { unitPrice: basePrice, source: 'retail' as const }

        const mixedTotal = basePrice * threshold + cfg.price * (qty - threshold)
        return {
            unitPrice: mixedTotal / qty,
            source: 'wholesale_mixed' as const,
            note: t('pos:messages.partialWholesaleFrom', { threshold: String(threshold), defaultValue: 'Partial wholesale from {{threshold}}' }),
        }
    }

    const applyPricingToCartItem = (item: CartItem, product: Product, qty: number) => {
        const pricing = getPricingForProduct(product, qty)
        return { ...item, qty, price: pricing.unitPrice, price_source: pricing.source, pricing_note: pricing.note }
    }

    // Actualizar precios al cambiar modo wholesale
    useEffect(() => {
        if (cart.length === 0) return
        setCart((prev) =>
            prev.map((item) => {
                const product = products.find((p) => p.id === item.product_id)
                if (!product) return item
                const priced = applyPricingToCartItem(item, product, item.qty)
                if (priced.price === item.price && priced.pricing_note === item.pricing_note && priced.price_source === item.price_source) return item
                return priced
            })
        )
    }, [isWholesaleCustomer, products])

    // ------------------------------------------------------------------
    // Búsqueda de producto por código
    // ------------------------------------------------------------------
    const findProductByCode = useCallback((code: string) => {
        const normalized = normalizeCode(code)
        if (!normalized) return null
        return products.find(
            (p) =>
                normalizeCode(p.sku) === normalized ||
                normalizeCode(p.product_metadata?.codigo_barras as string) === normalized ||
                normalizeCode(p.product_metadata?.codigo as string) === normalized ||
                normalizeCode(p.product_metadata?.barcode as string) === normalized ||
                normalizeCode(p.product_metadata?.ean as string) === normalized ||
                normalizeCode(p.product_metadata?.upc as string) === normalized
        ) || null
    }, [products])

    // ------------------------------------------------------------------
    // Carrito
    // ------------------------------------------------------------------
    const openQuickInput = (options: {
        title: string
        value?: string
        placeholder?: string
        type?: 'text' | 'number'
        multiline?: boolean
        onConfirm: (value: string) => void
    }) => {
        setQuickInputState({
            open: true,
            title: options.title,
            value: options.value ?? '',
            placeholder: options.placeholder,
            type: options.type ?? 'text',
            multiline: options.multiline ?? false,
            onConfirm: options.onConfirm,
        })
    }

    const closeQuickInput = () => {
        setQuickInputState((prev) => ({ ...prev, open: false, onConfirm: undefined, multiline: false }))
    }

    const addUnitsToCart = useCallback((product: Product, unitsToAdd = 1, opts?: { ignoreReorder?: boolean }) => {
        const normalizedUnits = Math.max(1, Math.floor(Number(unitsToAdd) || 1))
        const existing = cart.find((item) => item.product_id === product.id)
        let basePrice = Number(product.price ?? 0)
        if ((!Number.isFinite(basePrice) || basePrice <= 0) && existing && existing.price > 0) basePrice = existing.price

        if (!Number.isFinite(basePrice) || basePrice <= 0) {
            openQuickInput({
                title: t('pos:prompts.enterPriceForProduct', { defaultValue: `Price for ${product.name}`, name: product.name }),
                value: '',
                placeholder: '0.00',
                type: 'number',
                onConfirm: async (value) => {
                    const enteredPrice = Number.parseFloat(value)
                    if (!Number.isFinite(enteredPrice) || enteredPrice <= 0) {
                        toast.error(t('pos:errors.invalidPrice'))
                        return
                    }
                    closeQuickInput()
                    const pricedProduct = { ...product, price: enteredPrice }
                    setProducts((prev) => prev.map((p) => (p.id === product.id ? { ...p, price: enteredPrice } : p)))
                    addUnitsToCart(pricedProduct, normalizedUnits, opts)
                    toast.info(t('pos:messages.priceEnteredForSale', { defaultValue: 'Price applied for this sale' }), {
                        action: {
                            label: t('common:save', { defaultValue: 'Save' }),
                            onClick: async () => {
                                try {
                                    await updateProduct(product.id, { price: enteredPrice })
                                    setProducts((prev) => prev.map((p) => (p.id === product.id ? { ...p, price: enteredPrice } : p)))
                                    toast.success(t('pos:messages.priceSavedInProduct', { defaultValue: 'Price saved on product' }))
                                } catch {
                                    toast.error(t('pos:errors.savePriceFailed', { defaultValue: 'Could not save price' }))
                                }
                            },
                        },
                    })
                },
            })
            return
        }

        const productWithPrice = { ...product, price: basePrice }
        setCart((prev) => {
            const existingItem = prev.find((item) => item.product_id === product.id)
            const nextQty = existingItem ? existingItem.qty + normalizedUnits : normalizedUnits
            if (violatesStockPolicy(productWithPrice, nextQty, opts)) return prev

            if (existingItem) {
                return prev.map((item) =>
                    item.product_id === product.id ? applyPricingToCartItem(item, productWithPrice, nextQty) : item
                )
            }

            const baseItem: CartItem = {
                product_id: product.id,
                sku: product.sku || '',
                name: product.name,
                price: basePrice,
                iva_tasa: (productWithPrice as any).iva_tasa ?? defaultTaxPct,
                qty: normalizedUnits,
                discount_pct: 0,
                categoria: productWithPrice.category || (productWithPrice.product_metadata?.categoria as any),
            }
            return [...prev, applyPricingToCartItem(baseItem, productWithPrice, normalizedUnits)]
        })
    }, [cart, defaultTaxPct, applyPricingToCartItem, t, toast])

    const addToCart = useCallback((product: Product, opts?: { ignoreReorder?: boolean }) => {
        addUnitsToCart(product, 1, opts)
    }, [addUnitsToCart])

    const updateQty = (index: number, delta: number) => {
        setCart(cart.map((item, i) => {
            if (i !== index) return item
            const newQty = Math.max(1, item.qty + delta)
            const product = products.find((p) => p.id === item.product_id)
            if (delta > 0 && product && violatesStockPolicy(product, newQty)) return item
            if (!product) return { ...item, qty: newQty }
            return applyPricingToCartItem(item, product, newQty)
        }))
    }

    const removeItem = (index: number) => {
        const removed = cart[index]
        setCart(cart.filter((_, i) => i !== index))
        if (!removed) return
        toast.info(t('pos:messages.itemRemoved', { defaultValue: 'Product removed' }), {
            action: {
                label: t('pos:common.undo', { defaultValue: 'Undo' }),
                onClick: () => {
                    setCart((prev) => {
                        const next = [...prev]
                        next.splice(index, 0, removed)
                        return next
                    })
                },
            },
        })
    }

    const setLineDiscount = (index: number) => {
        openQuickInput({
            title: t('pos:prompts.lineDiscountPercent'),
            value: String(cart[index].discount_pct),
            type: 'number',
            onConfirm: (value) => {
                const pct = Math.min(100, Math.max(0, parseFloat(value) || 0))
                setCart((prev) => prev.map((item, i) => (i === index ? { ...item, discount_pct: pct } : item)))
                closeQuickInput()
            },
        })
    }

    const setLineNote = (index: number) => {
        openQuickInput({
            title: t('pos:prompts.lineNotes'),
            value: cart[index].notes || '',
            multiline: true,
            placeholder: t('pos:prompts.lineNotes', { defaultValue: 'Line notes' }),
            onConfirm: (value) => {
                setCart((prev) => prev.map((item, i) => (i === index ? { ...item, notes: value } : item)))
                closeQuickInput()
            },
        })
    }

    // Pre-cargar productos de shortcuts al montar/cambiar config — shortcut nunca hace fetch en tiempo real
    useEffect(() => {
        if (bulkShortcutItems.length === 0) return
        bulkShortcutItems.forEach(async (item) => {
            const cached = products.find((p) => String(p.id) === String(item.product_id))
            if (cached) return
            try {
                const results = await searchProducts(String(item.product_name || item.product_id))
                const found =
                    results.find((p: any) => String(p.id) === String(item.product_id)) ||
                    results.find((p: any) => normalizeText(p.name) === normalizeText(item.product_name)) ||
                    results[0]
                if (found) setProducts((prev) => prev.some((p) => p.id === found.id) ? prev : [found, ...prev])
            } catch { /* silencioso — se reintenta al presionar la tecla */ }
        })
    }, [bulkShortcutItems.length])

    const resolveBakeryShortcutProduct = useCallback(async (item: BulkPricingItem) => {
        const byId = products.find((entry) => String(entry.id) === String(item.product_id))
        if (byId) return byId

        const targetName = normalizeText(item.product_name)
        if (targetName) {
            const localByName = products.find((entry) => normalizeText(entry.name) === targetName)
            if (localByName) return localByName
        }

        const query = String(item.product_name || item.product_id || '').trim()
        if (!query) return null

        try {
            const remoteMatches = await searchProducts(query)
            const remoteExact =
                remoteMatches.find((entry) => String(entry.id) === String(item.product_id)) ||
                remoteMatches.find((entry) => normalizeText(entry.name) === targetName) ||
                remoteMatches[0]
            if (!remoteExact) return null

            setProducts((prev) => {
                const exists = prev.some((entry) => String(entry.id) === String(remoteExact.id))
                return exists ? prev : [remoteExact, ...prev]
            })
            return remoteExact
        } catch {
            return null
        }
    }, [products])

    const applyBakeryShortcut = useCallback(async (shortcutLetter: string, multiplier: number) => {
        const item = bulkShortcutItems.find((entry) => entry.shortcut_letter === shortcutLetter)
        if (!item || item.quantity <= 0) return false
        const product = await resolveBakeryShortcutProduct(item)
        if (!product) {
            toast.warning(`Producto no disponible para el atajo ${shortcutLetter}: ${item.product_name || item.product_id}`)
            return false
        }
        addUnitsToCart(product, item.quantity * multiplier)
        return true
    }, [bulkShortcutItems, resolveBakeryShortcutProduct, addUnitsToCart, toast])

    // ------------------------------------------------------------------
    // Barcode handlers
    // ------------------------------------------------------------------
    const handleBarcodeEnter = (e: React.KeyboardEvent) => {
        if (e.key !== 'Enter') return
        const product = findProductByCode(state.barcodeInput)
        if (product) {
            addToCart(product)
            setBarcodeInput('')
        } else {
            const code = normalizeCode(state.barcodeInput)
            if (code) {
                toast.warning(`${t('pos:errors.productNotFound')}: ${code}`, {
                    duration: 0,
                    action: {
                        label: t('common:create', { defaultValue: 'Create' }),
                        onClick: () => {
                            setCreateProductForm({ sku: code, name: '', price: 0, stock: 1, tax_rate: defaultTaxPct, category: selectedCategory !== '*' ? selectedCategory : '' })
                            setShowCreateProductModal(true)
                        },
                    },
                })
            }
        }
    }

    const handleSearchEnter = (e: React.KeyboardEvent) => {
        if (e.key !== 'Enter') return
        const product = findProductByCode(state.searchQuery)
        if (product) {
            addToCart(product)
            state.setSearchQuery('')
        } else {
            const code = normalizeCode(state.searchQuery)
            if (code) {
                toast.warning(`${t('pos:errors.productNotFound')}: ${code}`, {
                    duration: 0,
                    action: {
                        label: t('common:create', { defaultValue: 'Create' }),
                        onClick: () => {
                            setCreateProductForm({ sku: code, name: '', price: 0, stock: 1, tax_rate: defaultTaxPct, category: selectedCategory !== '*' ? selectedCategory : '' })
                            setShowCreateProductModal(true)
                        },
                    },
                })
            }
        }
    }

    useEffect(() => {
        if (
            bulkShortcutItems.length === 0 ||
            state.showPaymentModal ||
            showBuyerModal ||
            state.showInvoiceModal ||
            state.showDiscountModal ||
            state.showResumeTicketModal ||
            showCreateProductModal ||
            quickInputState.open
        ) {
            return
        }

        const handler = (e: KeyboardEvent) => {
            if (e.defaultPrevented) return
            const target = e.target as HTMLElement | null
            const tag = target?.tagName?.toLowerCase()
            const isSearchInput = target === state.searchInputRef.current
            if ((!isSearchInput && tag === 'input') || tag === 'textarea' || target?.isContentEditable) return
            if (e.ctrlKey || e.altKey || e.metaKey) return

            if (e.key.length !== 1) return
            const shortcutLetter = normalizeBakeryShortcutLetter(e.key)
            if (!shortcutLetter) return
            const hasShortcut = bulkShortcutItems.some((item) => item.shortcut_letter === shortcutLetter)
            if (!hasShortcut) return

            e.preventDefault()
            e.stopImmediatePropagation()
            void applyBakeryShortcut(shortcutLetter, 1)
        }

        window.addEventListener('keydown', handler)
        return () => {
            window.removeEventListener('keydown', handler)
        }
    }, [
        applyBakeryShortcut,
        bulkShortcutItems,
        quickInputState.open,
        showBuyerModal,
        showCreateProductModal,
        state.showDiscountModal,
        state.showInvoiceModal,
        state.showPaymentModal,
        state.showResumeTicketModal,
    ])

    // Listener global de lector de barras (hardware)
    // Corre en fase CAPTURE para interceptar antes que useKeyboardShortcuts,
    // que registra su handler también en capture y llama e.preventDefault() en Enter.
    //
    // Estrategia:
    //  - Sin input enfocado (body/botón): cualquier char viene del lector → acumular siempre.
    //  - Buscador enfocado: chars del lector llegan < 100 ms entre sí → isBarcodeMode.
    //  - Otro input (modales, formularios): ignorar completamente.
    useEffect(() => {
        const BARCODE_SPEED_MS = 100   // lectores USB/BT emiten < 100 ms entre chars
        const BARCODE_MIN_LENGTH = 3
        let lastKeyAt = 0
        let isBarcodeMode = false

        const resetBuffer = () => {
            barcodeBufferRef.current = ''
            isBarcodeMode = false
            if (barcodeTimerRef.current) { window.clearTimeout(barcodeTimerRef.current); barcodeTimerRef.current = null }
        }

        const processBarcode = (code: string) => {
            const product = findProductByCode(code)
            if (product) {
                addToCart(product)
            } else {
                toast.warning(`${t('pos:errors.productNotFound')}: ${code}`, {
                    duration: 0,
                    action: {
                        label: t('common:create', { defaultValue: 'Create' }),
                        onClick: () => {
                            setCreateProductForm({ sku: code, name: '', price: 0, stock: 1, tax_rate: defaultTaxPct, category: selectedCategory !== '*' ? selectedCategory : '' })
                            setShowCreateProductModal(true)
                        },
                    },
                })
            }
            state.setSearchQuery('')
        }

        const handler = (e: KeyboardEvent) => {
            if (e.ctrlKey || e.altKey || e.metaKey) return

            const target = e.target as HTMLElement | null
            const tag = target?.tagName?.toLowerCase()
            // searchInputRef es un useRef estable — .current siempre refleja el DOM actual
            const isSearchInput = target === state.searchInputRef.current
            const isOtherInput = (tag === 'input' || tag === 'textarea' || !!target?.isContentEditable) && !isSearchInput
            const noInputFocused = tag !== 'input' && tag !== 'textarea' && !target?.isContentEditable

            if (e.key === 'Enter') {
                if (isOtherInput) {
                    // Modal / formulario: limpiar buffer y dejar pasar el Enter normalmente
                    resetBuffer()
                    return
                }
                const code = barcodeBufferRef.current.trim()
                // Procesar si: sin input enfocado (siempre del lector) O buscador con modo barcode
                if (code.length >= BARCODE_MIN_LENGTH && (noInputFocused || isBarcodeMode)) {
                    e.stopImmediatePropagation()
                    e.preventDefault()
                    processBarcode(code)
                }
                resetBuffer()
                return
            }

            if (e.key.length !== 1) return

            // Ignorar chars de inputs que no son el buscador
            if (isOtherInput) return

            const now = Date.now()
            const timeSinceLast = now - lastKeyAt
            lastKeyAt = now

            if (noInputFocused) {
                // Sin input enfocado: siempre es el lector → acumular sin verificar velocidad
                isBarcodeMode = true
            } else if (barcodeBufferRef.current.length > 0 && timeSinceLast <= BARCODE_SPEED_MS) {
                // Buscador enfocado: activar modo barcode si chars llegan rápido
                isBarcodeMode = true
            }

            barcodeBufferRef.current += e.key
            if (barcodeTimerRef.current) window.clearTimeout(barcodeTimerRef.current)
            barcodeTimerRef.current = window.setTimeout(() => {
                resetBuffer()
            }, 500)
        }

        // useCapture=true: corre antes que useKeyboardShortcuts y antes del bubble phase
        window.addEventListener('keydown', handler, true)
        return () => {
            window.removeEventListener('keydown', handler, true)
            if (barcodeTimerRef.current) { window.clearTimeout(barcodeTimerRef.current); barcodeTimerRef.current = null }
        }
    }, [findProductByCode, addToCart])

    // ------------------------------------------------------------------
    // Clientes
    // ------------------------------------------------------------------
    const handleSelectClient = (client: Customer) => {
        setSelectedClient(client)
        state.setBuyerName(client.name || '')
        const doc = (client.identificacion || client.tax_id || '').toString()
        if (doc) state.setBuyerIdNumber(doc)
        if (client.email) state.setBuyerEmail(client.email)
        if ((client as any).identificacion_tipo) setBuyerIdType(String((client as any).identificacion_tipo))
    }

    const clearSelectedClient = () => {
        setSelectedClient(null)
        state.setClientQuery('')
        state.setIsWholesaleCustomer(false)
    }

    const loadClients = async () => {
        if (clientsLoading) return
        try {
            setClientsLoading(true)
            setClientsLoadError(null)
            setClients(await listCustomers())
        } catch (error) {
            const status = (error as any)?.response?.status
            setClientsLoadError(status === 429 ? t('pos:errors.tooManyRequests') : 'No se pudieron cargar los clientes. Reintenta.')
        } finally {
            setClientsLoading(false)
        }
    }

    // Cargar clientes cuando se abre el modal de buyer
    useEffect(() => {
        if (!showBuyerModal || buyerMode !== 'IDENTIFIED') return
        if (clients.length > 0 || clientsLoading) return
        if (clientsLoadAttemptedRef.current) return
        clientsLoadAttemptedRef.current = true
        loadClients()
    }, [showBuyerModal, buyerMode, clients.length, clientsLoading])

    const maybeSaveBuyerAsClient = async () => {
        if (buyerMode !== 'IDENTIFIED') return
        if (!state.saveBuyerAsClient) return
        if (selectedClient) return
        const idNumber = state.buyerIdNumber.trim()
        const name = state.buyerName.trim()
        if (!idNumber || !name) return

        const norm = (v: string) => (v || '').toString().replace(/[^A-Za-z0-9]+/g, '').trim().toUpperCase()
        const existing = clients.find((c) => { const doc = String(c.identificacion || c.tax_id || ''); return norm(doc) && norm(doc) === norm(idNumber) })
        if (existing) { setSelectedClient(existing); return }

        try {
            const created = await createCustomer({
                name,
                identificacion: idNumber,
                identificacion_tipo: normalizeIdType(state.buyerIdType, allowedIdTypes) || state.buyerIdType || undefined,
                email: state.buyerEmail.trim() || undefined,
                is_wholesale: isWholesaleCustomer || undefined,
            } as any)
            setClients((prev) => [created, ...prev])
            setSelectedClient(created)
        } catch (err) {
            console.error('Could not save customer:', err)
        }
    }

    // ------------------------------------------------------------------
    // Carga de datos
    // ------------------------------------------------------------------
    const loadRegisters = async () => {
        try {
            const data = await listRegisters()
            setRegisters(data.filter((r: any) => r.active))
            if (data.length > 0) setSelectedRegister(data[0])
        } catch (error) {
            console.error('Error loading registers:', error)
        }
    }

    const loadSettings = async () => {
        try {
            const settings = await getCompanySettings()
            const defaultTaxRate = getDefaultTaxRate(settings, 0)
            setCompanySettings(settings)
            setDocumentConfig(extractDocumentConfig(settings))
            try {
                const hasLocalTheme = !!localStorage.getItem(POS_THEME_KEY)
                if (!hasLocalTheme) {
                    const s = settings as any
                    const themeFromSettings = s?.pos_config?.theme || s?.settings?.pos_theme || s?.ui?.pos_theme || s?.branding?.pos_theme
                    setPosTheme(normalizePosTheme(themeFromSettings))
                }
            } catch { }
            setInventoryConfig({
                reorderPoint: getDefaultReorderPoint(settings),
                allowNegative: !!(settings?.inventory?.allow_negative || settings?.inventory?.allow_negative_stock || settings?.pos_config?.allow_negative),
            })
            if (typeof defaultTaxRate === 'number' && Number.isFinite(defaultTaxRate)) {
                setDefaultTaxPct(Math.max(0, defaultTaxRate * 100))
            }
            if (shouldCreateInvoice && typeof (shouldCreateInvoice as any) === 'function') {
                setAutoCreateInvoice(!!(settings as any)?.pos_config?.auto_create_invoice)
            }
        } catch (error) {
            console.error('Error loading settings:', error)
        }
    }

    const loadProducts = async () => {
        try {
            setProducts(await listProducts(true, true))
        } catch (error) {
            console.error('Error loading products:', error)
        }
    }

    const resolveWarehouseForStock = async () => {
        if (headerWarehouseId) return headerWarehouseId
        if (warehouses.length > 0) return String(warehouses[0].id)
        try {
            const fetched = await listWarehouses()
            if (Array.isArray(fetched) && fetched.length > 0) {
                const actives = fetched.filter((w) => w.is_active)
                const candidates = actives.length ? actives : fetched
                setWarehouses(candidates)
                if (!headerWarehouseId && candidates.length === 1) setHeaderWarehouseId(String(candidates[0].id))
                return String(candidates[0].id)
            }
        } catch (err) {
            console.error('Could not resolve default warehouse', err)
        }
        return null
    }

    // ------------------------------------------------------------------
    // Checkout
    // ------------------------------------------------------------------
    const buildReceiptLines = () => cart.map((item) => ({
        product_id: item.product_id,
        qty: item.qty,
        unit_price: item.price,
        tax_rate: item.iva_tasa / 100,
        discount_pct: item.discount_pct,
        uom: 'unit',
        line_total: computeLineTotal(item.qty, item.price, item.discount_pct),
    }))

    const createClientRequestId = () => createOfflineTempId('receipt-request')

    const buildReceiptPayload = (clientRequestId = createClientRequestId()) => ({
        register_id: state.selectedRegister.id,
        shift_id: state.currentShift.id,
        cashier_id: isCompanyAdmin ? selectedCashierId || undefined : undefined,
        customer_id: selectedClient ? String(selectedClient.id) : undefined,
        client_request_id: clientRequestId,
        lines: buildReceiptLines(),
        metadata: { notes: ticketNotes },
    })

    const buildPaymentDraftContext = (clientRequestId = createClientRequestId()) => ({
        draftLines: cart.map((item, index) => ({
            id: `draft-${index}`,
            product_id: item.product_id,
            product_name: item.name,
            product_code: item.sku || undefined,
            qty: item.qty,
            uom: 'unit',
            unit_price: item.price,
            tax_rate: item.iva_tasa / 100,
            discount_pct: item.discount_pct,
            line_total: computeLineTotal(item.qty, item.price, item.discount_pct),
        })),
        createPayload: buildReceiptPayload(clientRequestId),
    })

    const buildSaleDraft = (payments: POSPayment[] = []): SaleDraft => {
        const tenantId = profile?.tenant_id ? String(profile.tenant_id) : ''
        const country = documentConfig?.country || (companySettings?.settings as any)?.pais || (companySettings as any)?.settings?.country || 'EC'
        const currency = normalizeCurrencyCode(companySettings?.currency || (companySettings as any)?.settings?.currency)
        const posId = state.selectedRegister?.id ? String(state.selectedRegister.id) : 'pos'
        if (!currency) throw new Error('currency_not_configured')

        const buyer = buyerMode === 'CONSUMER_FINAL'
            ? { mode: 'CONSUMER_FINAL' as const, idType: 'NONE', idNumber: '', name: state.buyerName.trim() || 'CONSUMIDOR FINAL', email: state.buyerEmail.trim() || undefined }
            : { mode: 'IDENTIFIED' as const, idType: normalizeIdType(state.buyerIdType, allowedIdTypes), idNumber: state.buyerIdNumber.trim(), name: state.buyerName.trim(), email: state.buyerEmail.trim() || undefined }

        return {
            tenantId, country, posId, currency, buyer,
            items: cart.map((item) => ({
                sku: item.sku || '',
                name: item.name,
                qty: item.qty,
                unitPrice: item.price,
                discount: round2(item.price * item.qty * (item.discount_pct / 100)),
                taxCategory: item.categoria || 'DEFAULT',
            })),
            payments: payments.map((payment) => ({ method: mapPaymentMethod(payment.method), amount: payment.amount })),
            meta: { notes: ticketNotes, cashier: selectedCashierId || profile?.user_id || undefined },
        }
    }

    const buildOfflineCreateAndCheckoutPayload = (
        payments: POSPayment[],
        warehouseId?: string | null,
        clientRequestId = createClientRequestId(),
    ): QueuedPOSCreateAndCheckout => ({
        _queueAction: 'create_and_checkout',
        ...buildReceiptPayload(clientRequestId),
        metadata: {
            notes: ticketNotes,
            queued_from: 'pos_actions',
            queued_offline_at: new Date().toISOString(),
        },
        payments: payments.map((payment) => ({
            ...payment,
            receipt_id: payment.receipt_id || 'offline-receipt',
        })),
        document_issue: buildSaleDraft(payments),
        ...(warehouseId ? { warehouse_id: warehouseId } : {}),
    })

    const startCheckout = async () => {
        const paymentDraft = buildPaymentDraftContext()
        try {
            setLoading(true)
            pendingSaleRef.current = buildSaleDraft([])
            const receipt = await createReceipt(paymentDraft.createPayload as any)
            setPaymentDraftContext(null)
            setCurrentReceiptId(receipt.id ?? null)
            setShowPaymentModal(true)
        } catch (e) {
            const msg = String((e as any)?.message || '')
            if (msg.includes('currency_not_configured')) {
                toast.error(t('pos:errors.currencyNotConfigured'))
            } else if (isNetworkIssue(e)) {
                setPaymentDraftContext(paymentDraft)
                setCurrentReceiptId(createOfflineTempId('receipt'))
                setShowPaymentModal(true)
                toast.warning(t('pos:errors.offlineSync'))
            } else {
                toast.error(t('pos:errors.preparePaymentFailed'))
            }
        } finally {
            setLoading(false)
        }
    }

    const handleBuyerContinue = async (nextMode?: 'CONSUMER_FINAL' | 'IDENTIFIED') => {
        const mode = nextMode ?? buyerMode
        if (nextMode) setBuyerMode(nextMode)
        if (mode === 'CONSUMER_FINAL' && !canUseConsumerFinal) {
            toast.warning(t('pos:errors.requiresBuyerData'))
            return
        }
        if (mode === 'IDENTIFIED') {
            const normalized = normalizeIdType(state.buyerIdType, allowedIdTypes)
            if (!normalized) { toast.warning(t('pos:errors.selectIdentificationType')); return }
            if (!state.buyerIdNumber.trim() || !state.buyerName.trim()) { toast.warning(t('pos:errors.completeIdentification')); return }
            await maybeSaveBuyerAsClient()
        }
        setShowBuyerModal(false)
        await startCheckout()
    }

    // Enter en modal de buyer
    useEffect(() => {
        if (!showBuyerModal) return
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') { e.preventDefault(); setShowBuyerModal(false); return }
            if (e.key === 'Enter') {
                const tag = (e.target as HTMLElement | null)?.tagName?.toLowerCase()
                if (tag === 'textarea') return
                e.preventDefault()
                void handleBuyerContinue()
            }
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [showBuyerModal, handleBuyerContinue])

    const canStartCheckout = () => {
        if (cart.length === 0) { toast.warning(t('pos:errors.emptyCart')); return false }
        if (!state.currentShift) { toast.warning(t('pos:errors.noShiftOpen')); return false }
        const invalidLine = cart.find((item) => !item.product_id || item.qty <= 0)
        if (invalidLine) { toast.warning(t('pos:errors.invalidCartLine')); return false }
        if (totals.total < 0) { toast.warning(t('pos:errors.negativeTotalNotAllowed')); return false }
        return true
    }

    const handlePaymentCancel = useCallback(async () => {
        const id = currentReceiptId
        setShowPaymentModal(false)
        setCurrentReceiptId(null)
        setPaymentDraftContext(null)
        if (id && !paymentDraftContext) {
            try { await deleteReceipt(id) } catch { /* no-op: ya pudo haber sido pagado */ }
        }
    }, [currentReceiptId, paymentDraftContext, setShowPaymentModal, setCurrentReceiptId, setPaymentDraftContext])

    const beginCheckout = (opts?: { skipPrint?: boolean }) => {
        if (!canStartCheckout()) return
        setSkipPrint(!!opts?.skipPrint)
        setShowBuyerModal(true)
    }

    const handleCheckout = () => beginCheckout({ skipPrint: false })

    const handleQuickConsumerFinal = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(false)
        if (!canUseConsumerFinal) { setBuyerMode('IDENTIFIED'); setShowBuyerModal(true); toast.warning(t('pos:errors.requiresBuyerData')); return }
        await handleBuyerContinue('CONSUMER_FINAL')
    }

    const handleQuickNoTicket = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(true)
        if (!canUseConsumerFinal) { setBuyerMode('IDENTIFIED'); setShowBuyerModal(true); toast.warning(t('pos:errors.requiresBuyerData')); return }
        await handleBuyerContinue('CONSUMER_FINAL')
    }

    const handleQuickInvoice = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(false)
        const normalized = normalizeIdType(state.buyerIdType, allowedIdTypes)
        const hasBuyerData = !!normalized && !!state.buyerIdNumber.trim() && !!state.buyerName.trim()
        if (!hasBuyerData) {
            setBuyerMode('IDENTIFIED')
            setShowBuyerModal(true)
            toast.info(t('pos:messages.completeBuyerDataQuick', { defaultValue: 'Complete customer data to issue invoice quickly' }))
            return
        }
        await handleBuyerContinue('IDENTIFIED')
    }

    const resetSaleState = () => {
        setCart([])
        setGlobalDiscountPct(0)
        setTicketNotes('')
        setBuyerMode('CONSUMER_FINAL')
        setBuyerIdType('')
        state.setBuyerIdNumber('')
        state.setBuyerName('')
        state.setBuyerEmail('')
        setSkipPrint(false)
        localStorage.removeItem(POS_DRAFT_KEY)
        setShowPaymentModal(false)
        setPaymentDraftContext(null)
        pendingSaleRef.current = null
    }

    const handlePaymentSuccess = async (payments: POSPayment[], checkoutResponse?: CheckoutResponse) => {
        try {
            setLoading(true)
            if (checkoutResponse?.status === 'queued_offline') {
                resetSaleState()
                setCurrentReceiptId(null)
                toast.warning(t('pos:errors.offlineSync'))
                return
            }
            if (!currentReceiptId) { setLoading(false); return }

            let docPrinted = false
            const baseDraft = pendingSaleRef.current || buildSaleDraft([])
            const isCreditSale = payments.some((p) => p.ref === 'credit_sale')
            const saleDraft = {
                ...baseDraft,
                payments: payments.map((p) => ({ method: mapPaymentMethod(p.method), amount: p.amount })),
                meta: isCreditSale ? { ...(baseDraft.meta || {}), credit_sale: true } : baseDraft.meta,
            }

            if (isOnline) {
                try {
                    const issued = await issueDocument(saleDraft)
                    const docId = issued?.document?.id
                    if (docId && !skipPrint) {
                        const html = await renderDocumentWithFormat(docId, docPrintFormat)
                        setPrintHtml(html)
                        setShowPrintPreview(true)
                        docPrinted = true
                        setAndPersistLastPrintJob({ kind: 'document', documentId: docId, format: docPrintFormat })
                    }
                } catch (err) {
                    if (isNetworkIssue(err) && currentReceiptId) {
                        await addToOutbox({
                            _queueAction: 'issue_document',
                            receipt_id: currentReceiptId,
                            sale_draft: saleDraft,
                        })
                        toast.warning(t('pos:errors.offlineSync'))
                    } else if (buyerMode === 'IDENTIFIED') {
                        const detail = (err as any)?.response?.data?.detail ?? (err as any)?.response?.data
                        const msg = detail ? `\n\nDetalle:\n${typeof detail === 'string' ? detail : JSON.stringify(detail, null, 2)}` : ''
                        toast.error(`${t('pos:errors.documentIssueFailed')} ${msg}`)
                    }
                }
            }

            if (!docPrinted && !skipPrint) {
                const html = await printReceipt(currentReceiptId, '58mm')
                setPrintHtml(html)
                setShowPrintPreview(true)
                setAndPersistLastPrintJob({ kind: 'receipt', receiptId: currentReceiptId, width: '58mm' })
            }

            const needsInvoice = shouldCreateInvoice(totals.total, isWholesaleCustomer, companySettings)
            const receiptIdForInvoice = currentReceiptId

            resetSaleState()

            if (needsInvoice && receiptIdForInvoice) {
                setAutoCreateInvoice(true)
                setShowInvoiceModal(true)
                toast.success(t('pos:messages.invoiceCreation'))
            } else {
                toast.success(t('pos:messages.saleSupervisor'))
            }
        } catch (error: any) {
            if (!isOnline || isNetworkIssue(error)) {
                resetSaleState()
                setCurrentReceiptId(null)
                toast.warning(t('pos:errors.offlineSync'))
            } else {
                toast.error(error.response?.data?.detail || t('pos:errors.createTicketFailed'))
            }
        } finally {
            setLoading(false)
        }
    }

    // ------------------------------------------------------------------
    // Tickets retenidos
    // ------------------------------------------------------------------
    const handleHoldTicket = () => {
        if (cart.length === 0) { toast.warning(t('pos:errors.emptyCart')); return }
        const id = `T${String(Date.now()).slice(-6)}`
        const snapshot = { id, cart: JSON.parse(JSON.stringify(cart)), globalDiscountPct, ticketNotes }
        setHeldTickets((prev) => [...prev, snapshot])
        setCart([])
        setGlobalDiscountPct(0)
        setTicketNotes('')
        setCurrentReceiptId(null)
        toast.success(t('pos:messages.heldTicketInfo', { id }), {
            action: {
                label: t('pos:common.undo'),
                onClick: () => {
                    setCart(snapshot.cart)
                    setGlobalDiscountPct(snapshot.globalDiscountPct)
                    setTicketNotes(snapshot.ticketNotes || '')
                    setHeldTickets((prev) => prev.filter((t) => t.id !== id))
                },
            },
        })
    }

    const handleResumeTicketConfirm = (ticketId: string) => {
        const idx = heldTickets.findIndex((t) => t.id === ticketId)
        if (idx < 0) { toast.error(t('pos:errors.idNotFound')); return }
        const ticket = heldTickets[idx]
        setHeldTickets([...heldTickets.slice(0, idx), ...heldTickets.slice(idx + 1)])
        setCart(ticket.cart)
        setGlobalDiscountPct(ticket.globalDiscountPct || 0)
        setTicketNotes(ticket.ticketNotes || '')
        setCurrentReceiptId(null)
        setShowResumeTicketModal(false)
        toast.success(t('pos:messages.ticketRecovered', { ticketId }))
    }

    // ------------------------------------------------------------------
    // Impresión
    // ------------------------------------------------------------------
    const handleReprintLast = async () => {
        if (!state.lastPrintJob) { toast.info(t('pos:errors.nothingToReprint')); return }
        try {
            setLoading(true)
            const html = state.lastPrintJob.kind === 'document'
                ? await renderDocumentWithFormat(state.lastPrintJob.documentId, state.lastPrintJob.format)
                : await printReceipt(state.lastPrintJob.receiptId, state.lastPrintJob.width)
            setPrintHtml(html)
            setShowPrintPreview(true)
        } catch {
            toast.error(t('pos:errors.reprintFailed'))
        } finally {
            setLoading(false)
        }
    }

    // ------------------------------------------------------------------
    // Proforma / Cotización sin pago
    // ------------------------------------------------------------------
    const handlePrintQuote = useCallback(() => {
        if (cart.length === 0) { toast.warning(t('pos:errors.emptyCart')); return }

        const empresa = companySettings?.settings?.empresa_nombre || ''
        const widthPx = companySettings?.pos_config?.receipt?.width_mm === 80 ? '302px' : '220px'
        const now = new Date()
        const fecha = now.toLocaleDateString('es', { day: '2-digit', month: '2-digit', year: 'numeric' })
        const hora = now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })
        const fmt = (n: number) => formatCurrency(n, companySettings || undefined)

        const lineRows = cart.map((item) => {
            const lineTotal = item.qty * item.price * (1 - item.discount_pct / 100)
            return `
                <tr><td colspan="3" style="padding-top:5px;font-weight:bold">${item.name}</td></tr>
                <tr>
                    <td>${item.qty} × ${fmt(item.price)}</td>
                    <td style="text-align:center">${item.discount_pct ? `-${item.discount_pct}%` : ''}</td>
                    <td style="text-align:right">${fmt(lineTotal)}</td>
                </tr>`
        }).join('')

        const discountTotal = totals.line_discounts + totals.global_discount
        const discountRow = discountTotal > 0
            ? `<tr><td colspan="2">Descuentos</td><td style="text-align:right">-${fmt(discountTotal)}</td></tr>`
            : ''
        const taxRow = totals.tax > 0
            ? `<tr><td colspan="2">IVA</td><td style="text-align:right">${fmt(totals.tax)}</td></tr>`
            : ''

        const html = `<!DOCTYPE html><html><head><meta charset="utf-8"/>
        <style>
            body{font-family:monospace;font-size:12px;width:${widthPx};margin:0;padding:8px}
            h2,h3,p{margin:2px 0;text-align:center}
            table{width:100%;border-collapse:collapse}
            td{vertical-align:top;font-size:11px;padding:1px 2px}
            .sep{border-top:1px dashed #000;margin:6px 0}
            .proforma{font-size:10px;text-align:center;border:1px dashed #000;padding:3px;margin:4px 0}
            .total td{font-weight:bold;font-size:13px;padding-top:4px}
        </style></head><body>
            ${empresa ? `<h2>${empresa}</h2>` : ''}
            <h3>PROFORMA</h3>
            <div class="proforma">NO ES UN COMPROBANTE DE VENTA</div>
            <p>${fecha} &nbsp; ${hora}</p>
            <div class="sep"></div>
            <table>${lineRows}</table>
            <div class="sep"></div>
            <table>
                <tr><td colspan="2">Subtotal</td><td style="text-align:right">${fmt(totals.subtotal)}</td></tr>
                ${discountRow}${taxRow}
                <tr class="total"><td colspan="2">TOTAL</td><td style="text-align:right">${fmt(totals.total)}</td></tr>
            </table>
            <div class="sep"></div>
            <p style="font-size:10px">Válido por 24 horas</p>
        </body></html>`

        setPrintHtml(html)
        setShowPrintPreview(true)
    }, [cart, totals, companySettings, t, toast, setPrintHtml, setShowPrintPreview])

    // ------------------------------------------------------------------
    // Cobro express en efectivo — sin modal, sin pasos intermedios
    // F10 = sin ticket | F11 = con ticket
    // ------------------------------------------------------------------
    const handleExpressCash = useCallback(async (opts: { printTicket?: boolean } = {}) => {
        if (!canStartCheckout()) return
        if (!canUseConsumerFinal) {
            setBuyerMode('IDENTIFIED')
            setShowBuyerModal(true)
            toast.warning(t('pos:errors.requiresBuyerData'))
            return
        }
        let createdReceiptId: string | null = null
        const expressCreatePayload = buildReceiptPayload()
        try {
            setLoading(true)
            const receipt = await createReceipt(expressCreatePayload as any)

            const receiptId = receipt.id
            if (!receiptId) throw new Error('no_receipt_id')
            createdReceiptId = String(receiptId)

            const warehouseId = await resolveWarehouseForStock()
            await payReceipt(receiptId, [{ receipt_id: receiptId, method: 'cash', amount: totals.total }], warehouseId ? { warehouse_id: warehouseId } : undefined)

            if (isOnline) {
                const expressSaleDraft = buildSaleDraft([{ receipt_id: receiptId, method: 'cash', amount: totals.total }])
                try {
                    await issueDocument(expressSaleDraft)
                } catch (err) {
                    if (isNetworkIssue(err)) {
                        await addToOutbox({
                            _queueAction: 'issue_document',
                            receipt_id: receiptId,
                            sale_draft: expressSaleDraft,
                        })
                    } else {
                        console.warn('Express cash: issue document failed (non-fatal)', err)
                    }
                }
            }

            if (opts.printTicket) {
                try {
                    const width = companySettings?.pos_config?.receipt?.width_mm === 80 ? '80mm' : '58mm'
                    const html = await printReceipt(receiptId, width)
                    setPrintHtml(html)
                    setShowPrintPreview(true)
                    setAndPersistLastPrintJob({ kind: 'receipt', receiptId, width })
                } catch (err) {
                    console.warn('Express cash: print failed (non-fatal)', err)
                }
            }

            // Limpieza idéntica a handlePaymentSuccess
            resetSaleState()
            setCurrentReceiptId(null)

            toast.success(t('pos:messages.saleSupervisor'))
        } catch (error: any) {
            if (!isOnline || isNetworkIssue(error)) {
                const warehouseId = await resolveWarehouseForStock()
                if (createdReceiptId) {
                    await addToOutbox({
                        _queueAction: 'checkout_existing',
                        receipt_id: createdReceiptId,
                        payments: [{ receipt_id: createdReceiptId, method: 'cash', amount: totals.total }],
                        document_issue: buildSaleDraft([{ receipt_id: createdReceiptId, method: 'cash', amount: totals.total }]),
                        ...(warehouseId ? { warehouse_id: warehouseId } : {}),
                        metadata: {
                            queued_from: 'express_cash',
                            queued_offline_at: new Date().toISOString(),
                        },
                    })
                } else {
                    await addToOutbox(
                        buildOfflineCreateAndCheckoutPayload(
                            [{ receipt_id: 'offline-receipt', method: 'cash', amount: totals.total }],
                            warehouseId,
                            expressCreatePayload.client_request_id,
                        ),
                    )
                }
                resetSaleState()
                setCurrentReceiptId(null)
                toast.warning(t('pos:errors.offlineSync'))
            } else {
                toast.error(error.response?.data?.detail || t('pos:errors.createTicketFailed'))
            }
        } finally {
            setLoading(false)
        }
    }, [
        canStartCheckout, canUseConsumerFinal, cart, totals, isOnline, isCompanyAdmin,
        selectedCashierId, selectedClient, ticketNotes, companySettings,
        state, buildReceiptPayload, buildSaleDraft, buildOfflineCreateAndCheckoutPayload, resetSaleState, t, toast, resolveWarehouseForStock,
        setBuyerMode, setShowBuyerModal, setLoading, setCart, setGlobalDiscountPct,
        setTicketNotes, setBuyerIdType, setPrintHtml, setShowPrintPreview,
        setAndPersistLastPrintJob, pendingSaleRef,
    ])

    // ------------------------------------------------------------------
    // Merma / Regalo / Muestra
    // ------------------------------------------------------------------
    const handleWasteAdjust = useCallback(async (payload: {
        product: { id: string | number; name?: string }
        qty: number
        reason: 'merma' | 'regalo' | 'muestra'
        note: string
    }) => {
        try {
            const warehouseId = await resolveWarehouseForStock()
            if (!warehouseId) { toast.error(t('pos:errors.noWarehouse', { defaultValue: 'No warehouse configured' })); return }
            await adjustStock({
                warehouse_id: warehouseId,
                product_id: String(payload.product.id),
                delta: -Math.abs(payload.qty),
                reason: payload.note
                    ? `${payload.reason}: ${payload.note}`
                    : payload.reason,
            })
            toast.success(t('pos:waste.success', {
                defaultValue: 'Registered: {{qty}} {{name}}',
                qty: payload.qty,
                name: payload.product.name || '',
            }))
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || t('pos:waste.error', { defaultValue: 'Error registering adjustment' }))
        }
    }, [resolveWarehouseForStock, adjustStock, t, toast])

    // ------------------------------------------------------------------
    // Pendientes / Caja
    // ------------------------------------------------------------------
    const handlePayPending = async () => {
        if (!state.currentShift) { toast.warning(t('pos:errors.noShiftOpen')); return }
        setShowPendingModal(true)
    }

    // ------------------------------------------------------------------
    // Crear producto rápido
    // ------------------------------------------------------------------
    const handleCreateProductQuickSave = useCallback(async () => {
        if (!createProductForm.name.trim()) return
        try {
            setCreatingProduct(true)
            const skuValue = createProductForm.sku.trim()
            if (skuValue) {
                const existing = findProductByCode(skuValue)
                if (existing) {
                    addToCart(existing)
                    setBarcodeInput('')
                    setShowCreateProductModal(false)
                    toast.success(t('pos:createProduct.existingAdded'))
                    return
                }
                const remoteMatches = await searchProducts(skuValue)
                const remoteProduct = Array.isArray(remoteMatches)
                    ? remoteMatches.find((p) =>
                        normalizeCode(p.sku) === normalizeCode(skuValue) ||
                        normalizeCode(p.product_metadata?.codigo_barras as string) === normalizeCode(skuValue)
                    )
                    : null
                if (remoteProduct) {
                    setProducts((prev) => [remoteProduct, ...prev])
                    addToCart(remoteProduct)
                    setBarcodeInput('')
                    setShowCreateProductModal(false)
                    toast.success(t('pos:createProduct.existingAdded'))
                    return
                }
            }
            const created = await createProduct({
                sku: skuValue || undefined,
                name: createProductForm.name.trim(),
                price: parseFloat(String(createProductForm.price).replace(',', '.')) || 0,
                stock: Number(createProductForm.stock) || 0,
                tax_rate: Number(createProductForm.tax_rate) || 0,
                category: createProductForm.category.trim() || (selectedCategory !== '*' ? selectedCategory : undefined),
                unit: 'unit',
                active: true,
            })
            const stockQty = Number(createProductForm.stock) || 0
            if (stockQty > 0) {
                const warehouseId = await resolveWarehouseForStock()
                if (warehouseId) {
                    try { await adjustStock({ warehouse_id: warehouseId, product_id: created.id, delta: stockQty, reason: 'POS quick add' }) }
                    catch (err) { console.error('Could not adjust stock', err) }
                }
            }
            const enrichedProduct: Product = { ...created, stock: stockQty > 0 ? stockQty : Number(created.stock ?? 0) }
            setProducts((prev) => [enrichedProduct, ...prev])
            addToCart(enrichedProduct, { ignoreReorder: true })
            setBarcodeInput('')
            setShowCreateProductModal(false)
        } catch {
            toast.error(t('pos:createProduct.creationFailed'))
        } finally {
            setCreatingProduct(false)
        }
    }, [addToCart, createProductForm, resolveWarehouseForStock, selectedCategory, t, toast])

    // Foco al abrir el modal — efecto separado para no re-ejecutarse al cambiar el formulario
    useEffect(() => {
        if (!showCreateProductModal) return
        const focusTimer = window.setTimeout(() => {
            createProductNameInputRef.current?.focus()
            createProductNameInputRef.current?.select()
        }, 20)
        return () => window.clearTimeout(focusTimer)
    }, [showCreateProductModal])

    // Teclado en modal crear producto (Escape / Enter)
    useEffect(() => {
        if (!showCreateProductModal) return
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') { e.preventDefault(); return } // Escape bloqueado — cerrar solo con Cancelar/Guardar
            if (e.key === 'Enter' && !creatingProduct) {
                if ((e.target as HTMLElement | null)?.tagName?.toLowerCase() === 'textarea') return
                e.preventDefault()
                void handleCreateProductQuickSave()
            }
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [showCreateProductModal, creatingProduct, handleCreateProductQuickSave])

    // ------------------------------------------------------------------
    // Carga inicial
    // ------------------------------------------------------------------
    useEffect(() => {
        loadRegisters()
        loadSettings()
        loadProducts()
        loadClients().catch(() => { })
            ; (async () => {
                try {
                    const items = await listWarehouses()
                    const actives = items.filter((w) => w.is_active)
                    setWarehouses(actives)
                    if (actives.length === 1) setHeaderWarehouseId(String(actives[0].id))
                } catch { }
            })()
    }, [])

    useEffect(() => {
        if (!state.selectedCashierId && profile?.user_id) state.setSelectedCashierId(String(profile.user_id))
    }, [profile, state.selectedCashierId])

    useEffect(() => {
        if (!isCompanyAdmin) return
            ; (async () => {
                try {
                    const users = await listUsuarios()
                    setCashiers(users.filter((u) => u.active))
                } catch { }
            })()
    }, [isCompanyAdmin])

    // ------------------------------------------------------------------
    // Return
    // ------------------------------------------------------------------
    return {
        // Totals & derived
        totals,
        allowedIdTypes,
        buyerPolicy,
        canUseConsumerFinal,
        normalizeIdType,
        normalizeCode,

        // Data loading
        loadRegisters,
        loadSettings,
        loadProducts,
        loadClients,
        resolveWarehouseForStock,

        // Pricing
        getPricingForProduct,
        getWholesaleConfig,
        getReorderPoint,
        violatesStockPolicy,
        applyPricingToCartItem,

        // Cart
        addToCart,
        updateQty,
        removeItem,
        setLineDiscount,
        setLineNote,
        openQuickInput,
        closeQuickInput,
        findProductByCode,

        // Barcode
        handleBarcodeEnter,
        handleSearchEnter,

        // Clients
        handleSelectClient,
        clearSelectedClient,
        maybeSaveBuyerAsClient,

        // Checkout
        buildSaleDraft,
        startCheckout,
        handleBuyerContinue,
        beginCheckout,
        canStartCheckout,
        handleCheckout,
        handleQuickConsumerFinal,
        handleQuickNoTicket,
        handleQuickInvoice,
        handlePaymentSuccess,
        handlePaymentCancel,

        // Tickets retenidos
        handleHoldTicket,
        handleResumeTicketConfirm,

        // Impresión
        handleReprintLast,
        handlePrintQuote,
        handleExpressCash,

        // Merma / Regalo / Muestra
        handleWasteAdjust,

        // Pendientes
        handlePayPending,

        // Producto rápido
        handleCreateProductQuickSave,
    }
}

export type POSActions = ReturnType<typeof usePOSActions>
