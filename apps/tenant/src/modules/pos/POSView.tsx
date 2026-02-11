/**
 * POSView - Professional Point of Sale terminal
 * Layout based on tpv_pro.html with full backend integration
 */
import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import ShiftManager, { type ShiftManagerHandle } from './components/ShiftManager'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import useOfflineSync from './hooks/useOfflineSync'
import { useCurrency } from '../../hooks/useCurrency'
import { useAuth } from '../../auth/AuthContext'
import { POS_DRAFT_KEY } from '../../constants/storage'
import { POS_DEFAULTS } from '../../constants/defaults'
import { listWarehouses, adjustStock, type Warehouse } from '../inventory/services'
import { listUsuarios } from '../usuarios/services'
import type { Usuario } from '../usuarios/types'
import { createCliente, listClientes, type Cliente } from '../customers/services'
import {
    listRegisters,
    createRegister,
    createReceipt,
    printReceipt,
    addToOutbox,
    calculateReceiptTotals,
    issueDocument,
    renderDocumentWithFormat,
    type ReceiptTotals,
    type SaleDraft,
} from './services'
import { createProducto, listProductos, searchProductos, type Producto } from '../products/services'
import { getCompanySettings, getDefaultReorderPoint, getDefaultTaxRate, shouldCreateInvoice } from '../../services/companySettings'
import './pos-styles.css'
import PendingReceiptsModal from './components/PendingReceiptsModal'
import type { POSPayment } from '../../types/pos'

type CartItem = {
    product_id: string
    sku: string
    name: string
    price: number
    iva_tasa: number
    qty: number
    discount_pct: number
    notes?: string
    categoria?: string
    price_source?: 'retail' | 'wholesale' | 'wholesale_mixed'
    pricing_note?: string
}

type HeldTicket = {
    id: string
    cart: CartItem[]
    globalDiscountPct: number
    ticketNotes?: string
}

type LastPrintJob =
    | { kind: 'document'; documentId: string; format: 'THERMAL_80MM' | 'A4_PDF' }
    | { kind: 'receipt'; receiptId: string; width: '58mm' | '80mm' }

type PosDraftState = {
    cart: CartItem[]
    globalDiscountPct: number
    ticketNotes: string
    buyerMode: 'CONSUMER_FINAL' | 'IDENTIFIED'
    buyerIdType: string
    buyerIdNumber: string
    buyerName: string
    buyerEmail: string
    isWholesaleCustomer: boolean
    selectedCustomerId: string | null
    selectedCustomerName: string | null
}

const DEFAULT_ID_TYPES = ['CEDULA', 'RUC', 'PASSPORT']

export default function POSView() {
    const navigate = useNavigate()
    const can = usePermission()
    const { t } = useTranslation(['pos', 'common'])
    const { symbol: currencySymbol } = useCurrency()
    const { profile } = useAuth()
    const esAdminEmpresa = !!(profile?.es_admin_empresa || (profile as any)?.is_company_admin)
    const [registers, setRegisters] = useState<any[]>([])
    const [selectedRegister, setSelectedRegister] = useState<any>(null)
    const [currentShift, setCurrentShift] = useState<any>(null)
    const [products, setProducts] = useState<Producto[]>([])
    const [cart, setCart] = useState<CartItem[]>([])
    const [defaultTaxPct, setDefaultTaxPct] = useState<number>(0) // fallback neutral hasta cargar settings
    const [searchQuery, setSearchQuery] = useState('')
    const [barcodeInput, setBarcodeInput] = useState('')
    const [searchExpanded, setSearchExpanded] = useState(false)
    const [selectedCategory, setSelectedCategory] = useState<string>('*')
    const [inventoryConfig, setInventoryConfig] = useState<{ reorderPoint: number; allowNegative: boolean }>({
        reorderPoint: 0,
        allowNegative: false,
    })
    const [viewMode, setViewMode] = useState<'categories' | 'all'>('categories')
    const [globalDiscountPct, setGlobalDiscountPct] = useState(0)
    const [ticketNotes, setTicketNotes] = useState('')
    const [currentReceiptId, setCurrentReceiptId] = useState<string | null>(null)
    const [showPaymentModal, setShowPaymentModal] = useState(false)
    const [showBuyerModal, setShowBuyerModal] = useState(false)
    const [showInvoiceModal, setShowInvoiceModal] = useState(false)
    const [autoCreateInvoice, setAutoCreateInvoice] = useState(false)
    const [showCreateProductModal, setShowCreateProductModal] = useState(false)
    const [loading, setLoading] = useState(false)
    const [creatingProduct, setCreatingProduct] = useState(false)
    const [heldTickets, setHeldTickets] = useState<HeldTicket[]>([])
    const [lastPrintJob, setLastPrintJob] = useState<LastPrintJob | null>(null)
    const [showPendingModal, setShowPendingModal] = useState(false)
    const [showPrintPreview, setShowPrintPreview] = useState(false)
    const [printHtml, setPrintHtml] = useState('')
    const printFrameRef = useRef<HTMLIFrameElement>(null)
    const [cashiers, setCashiers] = useState<Usuario[]>([])
    const [selectedCashierId, setSelectedCashierId] = useState<string | null>(null)
    const [newRegisterName, setNewRegisterName] = useState(POS_DEFAULTS.REGISTER_NAME)
    const [newRegisterCode, setNewRegisterCode] = useState(POS_DEFAULTS.REGISTER_CODE)
    const [companySettings, setCompanySettings] = useState<any | null>(null)
    const [documentConfig, setDocumentConfig] = useState<any | null>(null)
    const [buyerMode, setBuyerMode] = useState<'CONSUMER_FINAL' | 'IDENTIFIED'>('CONSUMER_FINAL')
    const [buyerIdType, setBuyerIdType] = useState('')
    const [buyerIdNumber, setBuyerIdNumber] = useState('')
    const [buyerName, setBuyerName] = useState('')
    const [buyerEmail, setBuyerEmail] = useState('')
    const [isWholesaleCustomer, setIsWholesaleCustomer] = useState(false)
    const [clients, setClients] = useState<Cliente[]>([])
    const [clientsLoading, setClientsLoading] = useState(false)
    const [clientsLoadError, setClientsLoadError] = useState<string | null>(null)
    const clientsLoadAttemptedRef = useRef(false)
    const [clientQuery, setClientQuery] = useState('')
    const [selectedClient, setSelectedClient] = useState<Cliente | null>(null)
    const [saveBuyerAsClient, setSaveBuyerAsClient] = useState(true)
    const [docPrintFormat, setDocPrintFormat] = useState<'THERMAL_80MM' | 'A4_PDF'>('THERMAL_80MM')
    const [createProductForm, setCreateProductForm] = useState({
        sku: '',
        name: '',
        price: 0,
        stock: 1,
        iva_tasa: 0,
        categoria: '',
    })
    const pendingSaleRef = useRef<SaleDraft | null>(null)
    const buyerAlertRef = useRef(false)
    const buyerContinueRef = useRef(false)

    if (!can('pos:read')) {
        return <PermissionDenied permission="pos:read" />
    }
    const shiftManagerRef = useRef<ShiftManagerHandle | null>(null)
    const barcodeBufferRef = useRef('')
    const barcodeTimerRef = useRef<number | null>(null)
    const [skipPrint, setSkipPrint] = useState(false)

    useEffect(() => {
        try {
            const raw = localStorage.getItem('POS_LAST_PRINT_JOB')
            if (!raw) return
            const parsed = JSON.parse(raw)
            if (!parsed || typeof parsed !== 'object') return
            if (parsed.kind === 'document' && parsed.documentId && parsed.format) {
                setLastPrintJob(parsed)
            } else if (parsed.kind === 'receipt' && parsed.receiptId && parsed.width) {
                setLastPrintJob(parsed)
            }
        } catch { }
    }, [])

    const setAndPersistLastPrintJob = (job: LastPrintJob | null) => {
        setLastPrintJob(job)
        try {
            if (!job) localStorage.removeItem('POS_LAST_PRINT_JOB')
            else localStorage.setItem('POS_LAST_PRINT_JOB', JSON.stringify(job))
        } catch { }
    }

    const userLabel = useMemo(() => {
        if (!profile) return ''
        const anyProf: any = profile as any
        const name = anyProf.username || anyProf.name || anyProf.full_name || anyProf.email
        return name || (profile.user_id ? `#${String(profile.user_id).slice(0, 8)}` : '')
    }, [profile])

    const roleList = useMemo(() => {
        const roles = (profile as any)?.roles
        return Array.isArray(roles) ? roles : []
    }, [profile])
    const hasRoles = roleList.length > 0
    const isAdminRole = esAdminEmpresa || roleList.includes('admin') || roleList.includes('owner')
    const canViewReports = hasRoles ? (isAdminRole || roleList.includes('manager')) : true
    const canManagePending = hasRoles ? (isAdminRole || roleList.includes('manager')) : true
    const canDiscount = hasRoles ? (isAdminRole || roleList.includes('supervisor')) : true

    const formatCashierLabel = (u: Usuario) => {
        const name = `${u.first_name || ''} ${u.last_name || ''}`.trim()
        return name || u.username || u.email || (u.id ? `#${String(u.id).slice(0, 8)}` : '')
    }

    const { isOnline, pendingCount, syncNow } = useOfflineSync()
    // Almacenes (para admins)
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [headerWarehouseId, setHeaderWarehouseId] = useState<string | null>(null)

    useEffect(() => {
        loadRegisters()
        loadSettings()
        loadProducts()
            ; (async () => {
                try {
                    const items = await listWarehouses()
                    const actives = items.filter((w) => w.is_active)
                    setWarehouses(actives)
                    if (actives.length === 1) setHeaderWarehouseId(String(actives[0].id))
                } catch (e) {
                    // silent fallback: if inventory is unavailable, POS keeps working
                }
            })()
    }, [])

    useEffect(() => {
        if (cart.length === 0) return
        setCart((prev) =>
            prev.map((item) => {
                const product = products.find((p) => p.id === item.product_id)
                if (!product) return item
                const priced = applyPricingToCartItem(item, product, item.qty)
                if (
                    priced.price === item.price &&
                    priced.pricing_note === item.pricing_note &&
                    priced.price_source === item.price_source
                ) {
                    return item
                }
                return priced
            })
        )
    }, [isWholesaleCustomer, products])

    useEffect(() => {
        if (!selectedCashierId && profile?.user_id) {
            setSelectedCashierId(String(profile.user_id))
        }
    }, [profile, selectedCashierId])

    useEffect(() => {
        if (!esAdminEmpresa) return
            ; (async () => {
                try {
                    const users = await listUsuarios()
                    const actives = users.filter((u) => u.active)
                    setCashiers(actives)
                } catch {
                    // silencioso
                }
            })()
    }, [esAdminEmpresa])

    useEffect(() => {
        if (buyerMode === 'CONSUMER_FINAL') {
            setSelectedClient(null)
            setIsWholesaleCustomer(false)
        }
    }, [buyerMode])

    useEffect(() => {
        setIsWholesaleCustomer(!!selectedClient?.is_wholesale)
    }, [selectedClient])

    // Persistir tickets en espera en localStorage para sobrevivir recargas
    useEffect(() => {
        try {
            const raw = localStorage.getItem('posHeldTickets')
            if (raw) {
                const parsed = JSON.parse(raw)
                if (Array.isArray(parsed)) setHeldTickets(parsed)
            }
        } catch { }
    }, [])

    useEffect(() => {
        try {
            const raw = localStorage.getItem(POS_DRAFT_KEY)
            if (!raw) return
            const draft = JSON.parse(raw) as Partial<PosDraftState>
            if (draft.cart && Array.isArray(draft.cart)) setCart(draft.cart)
            if (typeof draft.globalDiscountPct === 'number') setGlobalDiscountPct(draft.globalDiscountPct)
            if (typeof draft.ticketNotes === 'string') setTicketNotes(draft.ticketNotes)
            if (draft.buyerMode === 'CONSUMER_FINAL' || draft.buyerMode === 'IDENTIFIED') {
                setBuyerMode(draft.buyerMode)
            }
            if (typeof draft.buyerIdType === 'string') setBuyerIdType(draft.buyerIdType)
            if (typeof draft.buyerIdNumber === 'string') setBuyerIdNumber(draft.buyerIdNumber)
            if (typeof draft.buyerName === 'string') setBuyerName(draft.buyerName)
            if (typeof draft.buyerEmail === 'string') setBuyerEmail(draft.buyerEmail)
            if (typeof draft.isWholesaleCustomer === 'boolean') {
                setIsWholesaleCustomer(draft.isWholesaleCustomer)
            }
            if (draft.selectedCustomerId) {
                setSelectedClient({
                    id: draft.selectedCustomerId,
                    name: draft.selectedCustomerName || draft.buyerName || 'Cliente',
                    is_wholesale: !!draft.isWholesaleCustomer,
                } as Cliente)
            }
        } catch {
            // ignore corrupted draft
        }
    }, [])

    useEffect(() => {
        try {
            localStorage.setItem('posHeldTickets', JSON.stringify(heldTickets))
        } catch { }
    }, [heldTickets])

    useEffect(() => {
        try {
            const draft: PosDraftState = {
                cart,
                globalDiscountPct,
                ticketNotes,
                buyerMode,
                buyerIdType,
                buyerIdNumber,
                buyerName,
                buyerEmail,
                isWholesaleCustomer,
                selectedCustomerId: selectedClient ? String(selectedClient.id) : null,
                selectedCustomerName: selectedClient?.name || null,
            }
            if (draft.cart.length === 0 && !draft.ticketNotes) {
                localStorage.removeItem(POS_DRAFT_KEY)
                return
            }
            localStorage.setItem(POS_DRAFT_KEY, JSON.stringify(draft))
        } catch { }
    }, [
        cart,
        globalDiscountPct,
        ticketNotes,
        buyerMode,
        buyerIdType,
        buyerIdNumber,
        buyerName,
        buyerEmail,
        isWholesaleCustomer,
        selectedClient,
    ])

    const loadRegisters = async () => {
        try {
            const data = await listRegisters()
            setRegisters(data.filter((r: any) => r.active))
            if (data.length > 0) setSelectedRegister(data[0])
        } catch (error) {
            console.error('Error loading registers:', error)
        }
    }

    const extractDocumentConfig = (settings: any) => {
        if (!settings || typeof settings !== 'object') return {}
        const docs = (settings.settings && (settings.settings as any).documents) || {}
        if (docs && typeof docs === 'object') return docs
        const invoiceCfg = (settings as any).invoice_config
        return invoiceCfg && typeof invoiceCfg === 'object' ? invoiceCfg : {}
    }

    const loadSettings = async () => {
        try {
            const settings = await getCompanySettings()
            // For POS, if there is no explicit setting, prefer 0 (avoid forcing 15% by default)
            const defaultTaxRate = getDefaultTaxRate(settings, 0)
            setCompanySettings(settings)
            setDocumentConfig(extractDocumentConfig(settings))
            setInventoryConfig({
                reorderPoint: getDefaultReorderPoint(settings),
                allowNegative: !!(
                    settings?.inventory?.allow_negative ||
                    settings?.inventory?.allow_negative_stock ||
                    settings?.pos_config?.allow_negative
                ),
            })
            if (typeof defaultTaxRate === 'number' && Number.isFinite(defaultTaxRate)) {
                // defaultTaxRate viene en decimal (0.12). Convertimos a porcentaje
                setDefaultTaxPct(Math.max(0, defaultTaxRate * 100))
            }
        } catch (error) {
            console.error('Error loading settings:', error)
        }
    }

    const loadProducts = async () => {
        try {
            // Filtrar productos sin stock para POS
            const data = await listProductos(true) // hideOutOfStock = true
            setProducts(data)
        } catch (error) {
            console.error('Error loading products:', error)
        }
    }

    const loadClients = async () => {
        if (clientsLoading) return
        try {
            setClientsLoading(true)
            setClientsLoadError(null)
            const data = await listClientes()
            setClients(data)
        } catch (error) {
            console.error('Error loading clients:', error)
            const status = (error as any)?.response?.status
            if (status === 429) {
                setClientsLoadError(t('pos:errors.tooManyRequests'))
            } else {
                setClientsLoadError('No se pudieron cargar los clientes. Reintenta.')
            }
        } finally {
            setClientsLoading(false)
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
                if (!headerWarehouseId && candidates.length === 1) {
                    setHeaderWarehouseId(String(candidates[0].id))
                }
                return String(candidates[0].id)
            }
        } catch (err) {
            console.error('No se pudo resolver almacen por defecto', err)
        }
        return null
    }

    const categories = useMemo(() => {
        const cats = new Set<string>()
        products.forEach((p) => {
            if (p.categoria || p.product_metadata?.categoria) {
                cats.add(p.categoria || (p.product_metadata?.categoria as any))
            }
        })
        return ['*', ...Array.from(cats).sort()]
    }, [products])

    const filteredProducts = useMemo(() => {
        let result = products
        const globalReorderPoint = Number(inventoryConfig.reorderPoint || 0)

        // In categories view, filter by selected category
        if (viewMode === 'categories' && selectedCategory !== '*') {
            result = result.filter(
                (p) => p.categoria === selectedCategory || (p.product_metadata?.categoria || '') === selectedCategory
            )
        }

        // Ocultar productos con stock por debajo del minimo de stock
        result = result.filter((p) => {
            const min = Number((p.product_metadata?.reorder_point ?? globalReorderPoint) || 0)
            if (min > 0) {
                return Number(p.stock ?? 0) >= min
            }
            return true
        })

        // Text search always active
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase()
            result = result.filter(
                (p) =>
                    (p.name || '').toLowerCase().includes(q) ||
                    (p.sku || '').toLowerCase().includes(q) ||
                    ((p.product_metadata?.codigo_barras || '') as string).toLowerCase().includes(q)
            )
        }

        return result
    }, [products, selectedCategory, searchQuery, viewMode, inventoryConfig.reorderPoint])

    useEffect(() => {
        if (!showBuyerModal || buyerMode !== 'IDENTIFIED') return
        if (clients.length > 0 || clientsLoading) return
        if (clientsLoadAttemptedRef.current) return
        clientsLoadAttemptedRef.current = true
        loadClients()
    }, [showBuyerModal, buyerMode, clients.length, clientsLoading])

    useEffect(() => {
        if (showBuyerModal) return
        setClientQuery('')
        setSelectedClient(null)
        setClientsLoadError(null)
        clientsLoadAttemptedRef.current = false
    }, [showBuyerModal])

    const filteredClients = useMemo(() => {
        if (!clientQuery.trim()) return clients.slice(0, 8)
        const q = clientQuery.trim().toLowerCase()
        return clients
            .filter((c) => {
                const name = (c.name || '').toLowerCase()
                const tax = ((c.identificacion || c.tax_id || '') as string).toLowerCase()
                const email = (c.email || '').toLowerCase()
                return name.includes(q) || tax.includes(q) || email.includes(q)
            })
            .slice(0, 8)
    }, [clients, clientQuery])

    const getReorderPoint = (product: Producto) => {
        const point = Number(product.product_metadata?.reorder_point ?? inventoryConfig.reorderPoint ?? 0)
        return Number.isFinite(point) ? point : 0
    }

    const violatesStockPolicy = (
        product: Producto,
        desiredQty: number,
        opts?: { ignoreReorder?: boolean }
    ) => {
        const stock = Number(product.stock ?? 0)
        const remaining = stock - desiredQty

        if (!inventoryConfig.allowNegative && remaining < 0) {
            alert(t('pos:errors.insufficientStockAmount', { stock: String(stock) }))
            return true
        }

        if (!opts?.ignoreReorder) {
            const reorderPoint = getReorderPoint(product)
            if (reorderPoint > 0 && remaining < reorderPoint) {
                alert(t('pos:errors.lowStockMinimumAmount', { minimum: String(reorderPoint) }))
                return true
            }
        }
        return false
    }

    const getWholesaleConfig = (product: Producto) => {
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

    const getPricingForProduct = (product: Producto, qty: number, packKey = 'unit') => {
        const basePrice = Number(product.price ?? 0) || 0
        const cfg = getWholesaleConfig(product)
        if (!cfg) return { unitPrice: basePrice, source: 'retail' as const }

        const reorderPoint = getReorderPoint(product)
        const stock = Number(product.stock ?? 0)
        if (reorderPoint > 0 && stock < reorderPoint) {
            return { unitPrice: basePrice, source: 'retail' as const }
        }

        const minUnits = Number(cfg.min_qty_units ?? 0) || 0
        const minPack = Number(cfg.min_qty_by_pack?.[packKey] ?? 0) || 0
        const meetsMin = (minUnits > 0 && qty >= minUnits) || (minPack > 0 && qty >= minPack)
        const isActive = isWholesaleCustomer || meetsMin
        if (!isActive) return { unitPrice: basePrice, source: 'retail' as const }

        if (cfg.apply_mode !== 'excess') {
            return { unitPrice: cfg.price, source: 'wholesale' as const, note: 'Mayorista' }
        }

        const threshold = resolveWholesaleThreshold(cfg, packKey)
        if (threshold <= 0) {
            return { unitPrice: cfg.price, source: 'wholesale' as const, note: 'Mayorista' }
        }
        if (qty <= threshold) {
            return { unitPrice: basePrice, source: 'retail' as const }
        }

        const mixedTotal = basePrice * threshold + cfg.price * (qty - threshold)
        const unitPrice = mixedTotal / qty
        return {
            unitPrice,
            source: 'wholesale_mixed' as const,
            note: `Mayorista parcial desde ${threshold}`,
        }
    }

    const applyPricingToCartItem = (item: CartItem, product: Producto, qty: number) => {
        const pricing = getPricingForProduct(product, qty)
        return {
            ...item,
            qty,
            price: pricing.unitPrice,
            price_source: pricing.source,
            pricing_note: pricing.note,
        }
    }

    const addToCart = (product: Producto, opts?: { ignoreReorder?: boolean }) => {
        let basePrice = Number(product.price ?? 0)
        if (!Number.isFinite(basePrice) || basePrice <= 0) {
            const fallbackName = product.name || t('posView.prompts.unnamedProduct')
            const input = prompt(t('pos:prompts.enterPrice', { name: fallbackName })) || ''
            const normalized = input.replace(',', '.').trim()
            const parsed = Number(normalized)
            if (!normalized || !Number.isFinite(parsed) || parsed <= 0) {
                alert(t('pos:errors.invalidPrice'))
                return
            }
            basePrice = parsed
        }
        const productWithPrice = { ...product, price: basePrice }
        const existing = cart.find((item) => item.product_id === product.id)
        const nextQty = existing ? existing.qty + 1 : 1
        if (violatesStockPolicy(productWithPrice, nextQty, opts)) return

        if (existing) {
            setCart(
                cart.map((item) =>
                    item.product_id === product.id
                        ? applyPricingToCartItem(item, productWithPrice, nextQty)
                        : item
                )
            )
        } else {
            const baseItem: CartItem = {
                product_id: product.id,
                sku: product.sku || '',
                name: product.name,
                price: basePrice,
                // Preservar 0% si el producto lo tiene; solo usar fallback de configuracion cuando viene null/undefined
                iva_tasa: (productWithPrice as any).iva_tasa ?? defaultTaxPct,
                qty: 1,
                discount_pct: 0,
                categoria: productWithPrice.categoria || (productWithPrice.product_metadata?.categoria as any),
            }
            const priced = applyPricingToCartItem(baseItem, productWithPrice, 1)
            setCart([...cart, priced])
        }
    }

    const updateQty = (index: number, delta: number) => {
        setCart(
            cart.map((item, i) => {
                if (i !== index) return item
                const newQty = Math.max(1, item.qty + delta)
                const product = products.find((p) => p.id === item.product_id)
                if (delta > 0 && product && violatesStockPolicy(product, newQty)) {
                    return item
                }
                if (!product) return { ...item, qty: newQty }
                return applyPricingToCartItem(item, product, newQty)
            })
        )
    }

    const handleSelectClient = (client: Cliente) => {
        setSelectedClient(client)
        setBuyerName(client.name || '')
        const doc = (client.identificacion || client.tax_id || '').toString()
        if (doc) setBuyerIdNumber(doc)
        if (client.email) setBuyerEmail(client.email)
        if ((client as any).identificacion_tipo) setBuyerIdType(String((client as any).identificacion_tipo))
    }

    const clearSelectedClient = () => {
        setSelectedClient(null)
        setClientQuery('')
        setIsWholesaleCustomer(false)
    }

    const maybeSaveBuyerAsClient = async () => {
        if (buyerMode !== 'IDENTIFIED') return
        if (!saveBuyerAsClient) return
        if (selectedClient) return

        const idNumber = buyerIdNumber.trim()
        const name = buyerName.trim()
        if (!idNumber || !name) return

        const normalize = (v: string) =>
            (v || '')
                .toString()
                .replace(/[^A-Za-z0-9]+/g, '')
                .trim()
                .toUpperCase()

        const existing = clients.find((c) => {
            const doc = String(c.identificacion || c.tax_id || '')
            return normalize(doc) && normalize(doc) === normalize(idNumber)
        })
        if (existing) {
            setSelectedClient(existing)
            return
        }

        try {
            const created = await createCliente({
                name,
                identificacion: idNumber,
                identificacion_tipo: normalizeIdType(buyerIdType, allowedIdTypes) || buyerIdType || undefined,
                email: buyerEmail.trim() || undefined,
                is_wholesale: isWholesaleCustomer || undefined,
            } as any)
            setClients((prev) => [created, ...prev])
            setSelectedClient(created)
        } catch (err) {
            console.error('No se pudo guardar cliente:', err)
        }
    }

    const removeItem = (index: number) => {
        setCart(cart.filter((_, i) => i !== index))
    }

    const setLineDiscount = (index: number) => {
        const value = prompt(t('pos:prompts.lineDiscountPercent'), String(cart[index].discount_pct))
        if (value === null) return
        const pct = Math.min(100, Math.max(0, parseFloat(value) || 0))
        setCart(cart.map((item, i) => (i === index ? { ...item, discount_pct: pct } : item)))
    }

    const setLineNote = (index: number) => {
        const value = prompt(t('pos:prompts.lineNotes'), cart[index].notes || '')
        if (value === null) return
        setCart(cart.map((item, i) => (i === index ? { ...item, notes: value } : item)))
    }

    const normalizeCode = (value?: string | null) => {
        const normalized = (value || '').toString().trim().toLowerCase()
        return normalized.replace(/(\d)[`'’](\d)/g, '$1-$2')
    }

    const findProductByCode = (code: string) => {
        const normalized = normalizeCode(code)
        if (!normalized) return null
        return (
            products.find(
                (p) =>
                    normalizeCode(p.sku) === normalized ||
                    normalizeCode(p.product_metadata?.codigo_barras as string) === normalized ||
                    normalizeCode(p.product_metadata?.codigo as string) === normalized ||
                    normalizeCode(p.product_metadata?.barcode as string) === normalized ||
                    normalizeCode(p.product_metadata?.ean as string) === normalized ||
                    normalizeCode(p.product_metadata?.upc as string) === normalized
            ) || null
        )
    }

    const handleBarcodeEnter = (e: React.KeyboardEvent) => {
        if (e.key !== 'Enter') return
        const product = findProductByCode(barcodeInput)
        if (product) {
            addToCart(product)
            setBarcodeInput('')
        } else {
            const code = normalizeCode(barcodeInput)
            if (code) {
                const shouldCreate = confirm(`${t('pos:errors.productNotFound')}: ${code}\n${t('pos:errors.confirmCreate')}`)
                if (shouldCreate) {
                    setCreateProductForm({
                        sku: code,
                        name: '',
                        price: 0,
                        stock: 1,
                        iva_tasa: defaultTaxPct,
                        categoria: selectedCategory !== '*' ? selectedCategory : '',
                    })
                    setShowCreateProductModal(true)
                }
            }
        }
    }

    const handleSearchEnter = (e: React.KeyboardEvent) => {
        if (e.key !== 'Enter') return
        const product = findProductByCode(searchQuery)
        if (product) {
            addToCart(product)
            setSearchQuery('')
        }
    }

    // Totals calculated by backend (single source of truth)
    const [totals, setTotals] = useState<ReceiptTotals>({
        subtotal: 0,
        line_discounts: 0,
        global_discount: 0,
        base_after_discounts: 0,
        tax: 0,
        total: 0,
    })

    const buyerPolicy = useMemo(() => {
        const raw = (documentConfig?.buyer_policy || documentConfig?.buyerPolicy || {}) as any
        return {
            consumerFinalEnabled:
                raw.consumerFinalEnabled ?? raw.consumer_final_enabled ?? true,
            consumerFinalMaxTotal: Number(
                raw.consumerFinalMaxTotal ?? raw.consumer_final_max_total ?? 0
            ),
            requireBuyerAboveAmount:
                raw.requireBuyerAboveAmount ?? raw.require_buyer_above_amount ?? false,
        }
    }, [documentConfig])

    const canUseConsumerFinal = useMemo(() => {
        if (buyerPolicy.consumerFinalEnabled === false) return false
        if (buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0) {
            return totals.total <= buyerPolicy.consumerFinalMaxTotal
        }
        return true
    }, [buyerPolicy, totals.total])

    const idTypeOptions = useMemo(() => {
        const raw = documentConfig?.id_types || documentConfig?.idTypes || []
        if (!Array.isArray(raw)) return []
        return raw.map((value: any) => String(value)).filter((value: string) => value.trim())
    }, [documentConfig])

    const allowedIdTypes = useMemo(() => {
        const sanitized = idTypeOptions
            .map((value) => value.trim())
            .filter((value) => value && value.toUpperCase() !== 'NONE')
        return sanitized.length > 0 ? sanitized : DEFAULT_ID_TYPES
    }, [idTypeOptions])

    const normalizeIdType = (value: string, options: string[]) => {
        const normalize = (input: string) =>
            input
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .replace(/[^A-Za-z0-9]+/g, '') // ignore punctuation/spaces so "C.I." matches "CI"
                .trim()
                .toUpperCase()
        const target = normalize(value || '')
        if (!target) return ''
        const directMatch = options.find((opt) => normalize(opt) === target)
        if (directMatch) return directMatch
        return ''
    }

    useEffect(() => {
        if (!buyerIdType) {
            setBuyerIdType(allowedIdTypes[0] || '')
            return
        }
        const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
        if (normalized && normalized !== buyerIdType) {
            setBuyerIdType(normalized)
        }
    }, [buyerIdType, allowedIdTypes])

    useEffect(() => {
        const raw = (documentConfig as any)?.render_format_default || (documentConfig as any)?.renderFormatDefault
        if (raw === 'A4_PDF') setDocPrintFormat('A4_PDF')
        else if (raw === 'THERMAL_80MM') setDocPrintFormat('THERMAL_80MM')
    }, [documentConfig])

    useEffect(() => {
        const resetBuffer = () => {
            barcodeBufferRef.current = ''
            if (barcodeTimerRef.current) {
                window.clearTimeout(barcodeTimerRef.current)
                barcodeTimerRef.current = null
            }
        }

        const handler = (e: KeyboardEvent) => {
            const target = e.target as HTMLElement | null
            const tag = target?.tagName?.toLowerCase()
            const isEditable =
                tag === 'input' ||
                tag === 'textarea' ||
                (target as HTMLElement | null)?.isContentEditable
            if (isEditable) return
            if (e.ctrlKey || e.altKey || e.metaKey) return

            if (e.key === 'Enter') {
                const code = barcodeBufferRef.current.trim()
                if (code) {
                    const product = findProductByCode(code)
                    if (product) {
                        addToCart(product)
                    } else {
                        const shouldCreate = confirm(`${t('pos:errors.productNotFound')}: ${code}\n${t('pos:errors.confirmCreate')}`)
                        if (shouldCreate) {
                            setCreateProductForm({
                                sku: code,
                                name: '',
                                price: 0,
                                stock: 1,
                                iva_tasa: defaultTaxPct,
                                categoria: selectedCategory !== '*' ? selectedCategory : '',
                            })
                            setShowCreateProductModal(true)
                        }
                    }
                }
                resetBuffer()
                return
            }

            if (e.key.length !== 1) return
            barcodeBufferRef.current += e.key
            if (barcodeTimerRef.current) {
                window.clearTimeout(barcodeTimerRef.current)
            }
            barcodeTimerRef.current = window.setTimeout(() => {
                barcodeBufferRef.current = ''
                barcodeTimerRef.current = null
            }, 300)
        }

        window.addEventListener('keydown', handler)
        return () => {
            window.removeEventListener('keydown', handler)
            if (barcodeTimerRef.current) {
                window.clearTimeout(barcodeTimerRef.current)
                barcodeTimerRef.current = null
            }
        }
    }, [findProductByCode, addToCart])

    useEffect(() => {
        if (buyerPolicy.consumerFinalEnabled === false && buyerMode === 'CONSUMER_FINAL') {
            setBuyerMode('IDENTIFIED')
        }
    }, [buyerMode, buyerPolicy.consumerFinalEnabled])

    useEffect(() => {
        if (!showBuyerModal) {
            buyerAlertRef.current = false
            return
        }
        if (buyerMode !== 'CONSUMER_FINAL') {
            buyerAlertRef.current = false
            return
        }
        if (!canUseConsumerFinal && !buyerAlertRef.current) {
            buyerAlertRef.current = true
            alert(t('pos:errors.totalExceedsLimit'))
            setBuyerMode('IDENTIFIED')
        }
        if (canUseConsumerFinal) buyerAlertRef.current = false
    }, [buyerMode, canUseConsumerFinal, showBuyerModal])

    useEffect(() => {
        if (showBuyerModal) {
            buyerContinueRef.current = false
        }
    }, [showBuyerModal])

    // Calcular totales cuando cambia el carrito o descuento global
    useEffect(() => {
        if (cart.length === 0) {
            setTotals({
                subtotal: 0,
                line_discounts: 0,
                global_discount: 0,
                base_after_discounts: 0,
                tax: 0,
                total: 0,
            })
            return
        }

        const calculateTotals = async () => {
            try {
                const lines = cart.map((item) => ({
                    qty: item.qty,
                    unit_price: item.price,
                    tax_rate: item.iva_tasa / 100, // Convertir a decimal (15% -> 0.15)
                    discount_pct: item.discount_pct,
                }))

                const calculated = await calculateReceiptTotals({
                    lines,
                    global_discount_pct: globalDiscountPct,
                })

                setTotals(calculated)
            } catch (error) {
                console.error('Error calculando totales:', error)
                // Fallback to local calculation on network error
                const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0)
                const lineDiscounts = cart.reduce(
                    (sum, item) => sum + item.price * item.qty * (item.discount_pct / 100),
                    0
                )
                const baseAfterLineDisc = subtotal - lineDiscounts
                const globalDisc = baseAfterLineDisc * (globalDiscountPct / 100)
                const base = baseAfterLineDisc - globalDisc
                const tax = cart.reduce((sum, item) => {
                    const lineBase = item.price * item.qty * (1 - item.discount_pct / 100)
                    return sum + lineBase * (item.iva_tasa / 100)
                }, 0)
                const total = base + tax

                setTotals({
                    subtotal,
                    line_discounts: lineDiscounts,
                    global_discount: globalDisc,
                    base_after_discounts: base,
                    tax,
                    total,
                })
            }
        }

        calculateTotals()
    }, [cart, globalDiscountPct])

    const round2 = (value: number) => Math.round(value * 100) / 100

    const normalizeCurrencyCode = (raw?: string): string => {
        const code = (raw || '').trim().toUpperCase()
        if (!code) return ''
        const aliases: Record<string, string> = {
            US: 'USD',
            USA: 'USD',
        }
        return aliases[code] || code
    }

    const mapPaymentMethod = (
        method: POSPayment['method']
    ): SaleDraft['payments'][number]['method'] => {
        switch (method) {
            case 'cash':
                return 'CASH'
            case 'card':
                return 'CARD'
            case 'link':
                return 'TRANSFER'
            default:
                return 'OTHER'
        }
    }

    const buildSaleDraft = (payments: POSPayment[] = []): SaleDraft => {
        const tenantId = profile?.tenant_id ? String(profile.tenant_id) : ''
        const country =
            documentConfig?.country ||
            (companySettings?.settings as any)?.pais ||
            (companySettings as any)?.settings?.country ||
            'EC'
        const currency = normalizeCurrencyCode(
            companySettings?.currency || (companySettings as any)?.settings?.currency
        )
        const posId = selectedRegister?.id ? String(selectedRegister.id) : 'pos'
        if (!currency) {
            console.warn('[POS] currency missing in company settings', {
                currency: companySettings?.currency,
                legacyCurrency: (companySettings as any)?.settings?.currency,
                raw: companySettings,
            })
            throw new Error('currency_not_configured')
        }

        const buyer =
            buyerMode === 'CONSUMER_FINAL'
                ? {
                    mode: 'CONSUMER_FINAL' as const,
                    idType: 'NONE',
                    idNumber: '',
                    name: buyerName.trim() || 'CONSUMIDOR FINAL',
                    email: buyerEmail.trim() || undefined,
                }
                : {
                    mode: 'IDENTIFIED' as const,
                    idType: normalizeIdType(buyerIdType, allowedIdTypes),
                    idNumber: buyerIdNumber.trim(),
                    name: buyerName.trim(),
                    email: buyerEmail.trim() || undefined,
                }

        return {
            tenantId,
            country,
            posId,
            currency,
            buyer,
            items: cart.map((item) => {
                const lineSubtotal = item.price * item.qty
                const discount = round2(lineSubtotal * (item.discount_pct / 100))
                return {
                    sku: item.sku || '',
                    name: item.name,
                    qty: item.qty,
                    unitPrice: item.price,
                    discount,
                    taxCategory: item.categoria || 'DEFAULT',
                }
            }),
            payments: payments.map((payment) => ({
                method: mapPaymentMethod(payment.method),
                amount: payment.amount,
            })),
            meta: {
                notes: ticketNotes,
                cashier: selectedCashierId || profile?.user_id || undefined,
            },
        }
    }

    const startCheckout = async () => {
        try {
            setLoading(true)
            pendingSaleRef.current = buildSaleDraft([])
            const receiptData = {
                register_id: selectedRegister.id,
                shift_id: currentShift.id,
                cashier_id: esAdminEmpresa ? selectedCashierId || undefined : undefined,
                customer_id: selectedClient ? String(selectedClient.id) : undefined,
                lines: cart.map((item) => {
                    const line_total = item.price * item.qty * (1 - item.discount_pct / 100)
                    return {
                        product_id: item.product_id,
                        qty: item.qty,
                        unit_price: item.price,
                        tax_rate: item.iva_tasa / 100,
                        discount_pct: item.discount_pct,
                        uom: 'unit',
                        line_total,
                    }
                }),
                payments: [],
                notes: ticketNotes,
            }
            const receipt = await createReceipt(receiptData)
            setCurrentReceiptId(receipt.id ?? null)
            setShowPaymentModal(true)
        } catch (e) {
            console.error('Error creating receipt:', e)
            const msg = String((e as any)?.message || '')
            if (msg.includes('currency_not_configured')) {
                alert(t('pos:errors.currencyNotConfigured'))
            } else {
                alert(t('pos:errors.preparePaymentFailed'))
            }
        } finally {
            setLoading(false)
        }
    }

    const handleBuyerContinue = async (nextMode?: 'CONSUMER_FINAL' | 'IDENTIFIED') => {
        const mode = nextMode ?? buyerMode
        if (nextMode) {
            setBuyerMode(nextMode)
        }
        if (mode == 'CONSUMER_FINAL' && !canUseConsumerFinal) {
            alert(t('pos:errors.requiresBuyerData'))
            return
        }
        if (mode == 'IDENTIFIED') {
            const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
            if (!normalized) {
                alert(t('pos:errors.selectIdentificationType'))
                return
            }
            if (!buyerIdNumber.trim() || !buyerName.trim()) {
                alert(t('pos:errors.completeIdentification'))
                return
            }
        }
        if (mode == 'IDENTIFIED') {
            await maybeSaveBuyerAsClient()
        }
        setShowBuyerModal(false)
        await startCheckout()
    }


    const beginCheckout = (opts?: { skipPrint?: boolean }) => {
        if (cart.length === 0) {
            alert(t('pos:errors.emptyCart'))
            return
        }
        if (!currentShift) {
            alert(t('pos:errors.noShiftOpen'))
            return
        }
        setSkipPrint(!!opts?.skipPrint)
        setShowBuyerModal(true)
    }

    const handleCheckout = () => beginCheckout({ skipPrint: false })
    const handleCheckoutWithoutTicket = () => beginCheckout({ skipPrint: true })


    const handlePaymentSuccess = async (payments: POSPayment[]) => {
        try {
            setLoading(true)
            // Use existing receipt; do not recreate
            if (!currentReceiptId) {
                setLoading(false)
                return
            }

            let docPrinted = false
            const baseDraft = pendingSaleRef.current || buildSaleDraft([])
            const saleDraft = {
                ...baseDraft,
                payments: payments.map((payment) => ({
                    method: mapPaymentMethod(payment.method),
                    amount: payment.amount,
                })),
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
                    const detail = (err as any)?.response?.data
                    console.error('Error emitiendo documento:', err, 'Detalle:', detail)
                    if (buyerMode === 'IDENTIFIED') {
                        const msgDetail = detail?.detail ?? detail
                        const msg = msgDetail ? `\n\nDetalle:\n${typeof msgDetail === 'string' ? msgDetail : JSON.stringify(msgDetail, null, 2)}` : ''
                        alert(`${t('pos:errors.documentIssueFailed')} ${msg}`)
                    }
                }
            }

            if (!docPrinted && !skipPrint) {
                const html = await printReceipt(currentReceiptId, '58mm')
                setPrintHtml(html)
                setShowPrintPreview(true)
                setAndPersistLastPrintJob({ kind: 'receipt', receiptId: currentReceiptId, width: '58mm' })
            }

            // Calculate totals to check if invoice must be created automatically
            // Use current totals state to avoid 422 responses to calculate_totals with empty payload
            const needsInvoice = shouldCreateInvoice(totals.total, isWholesaleCustomer, companySettings)

            // Reset carrito
            setCart([])
            setGlobalDiscountPct(0)
            setTicketNotes('')
            setBuyerMode('CONSUMER_FINAL')
            setBuyerIdType('')
            setBuyerIdNumber('')
            setBuyerName('')
            setBuyerEmail('')
            setSkipPrint(false)
            localStorage.removeItem(POS_DRAFT_KEY)
            setShowPaymentModal(false)
            pendingSaleRef.current = null

            // If invoice must be created automatically, open modal
            if (needsInvoice && currentReceiptId) {
                setAutoCreateInvoice(true)
                setShowInvoiceModal(true)
            alert(t('pos:messages.invoiceCreation'))
            } else {
                alert(t('pos:messages.saleSupervisor'))
            }
        } catch (error: any) {
            if (!isOnline) {
                await addToOutbox({ type: 'receipt', data: { cart, totals } })
            alert(t('pos:errors.offlineSync'))
                setCart([])
                setShowPaymentModal(false)
            } else {
                alert(error.response?.data?.detail || t('pos:errors.createTicketFailed'))
            }
        } finally {
            setLoading(false)
        }
    }

    const handleConvertToInvoice = () => {
        if (!currentReceiptId) return
        setShowPaymentModal(false)
        setShowInvoiceModal(true)
    }

    const handleHoldTicket = () => {
        if (cart.length === 0) {
            alert(t('pos:errors.emptyCart'))
            return
        }
        const id = `T${String(Date.now()).slice(-6)}`
        const snapshot: HeldTicket = {
            id,
            cart: JSON.parse(JSON.stringify(cart)),
            globalDiscountPct,
            ticketNotes,
        }
        setHeldTickets((prev) => [...prev, snapshot])
        setCart([])
        setGlobalDiscountPct(0)
        setTicketNotes('')
        setCurrentReceiptId(null)
        alert(t('pos:messages.heldTicketInfo', { id }))
    }

    const handleResumeTicket = () => {
        if (heldTickets.length === 0) {
            alert(t('pos:errors.heldTickets'))
            return
        }
        const list = heldTickets.map((t) => t.id).join(', ')
        const pick = prompt(t('pos:messages.heldTicketPick', { list }))
        if (!pick) return
        const trimmed = pick.trim()
        const idx = heldTickets.findIndex((t) => t.id === trimmed)
        if (idx < 0) {
            alert(t('pos:errors.idNotFound'))
            return
        }
        const ticket = heldTickets[idx]
        setHeldTickets([...heldTickets.slice(0, idx), ...heldTickets.slice(idx + 1)])
        setCart(ticket.cart)
        setGlobalDiscountPct(ticket.globalDiscountPct || 0)
        setTicketNotes(ticket.ticketNotes || '')
        setCurrentReceiptId(null)
        alert(t('pos:messages.ticketRecovered', { ticketId: trimmed }))
    }

    const handleReprintLast = async () => {
        if (!lastPrintJob) {
            alert(t('pos:errors.nothingToReprint'))
            return
        }
        try {
            setLoading(true)
            if (lastPrintJob.kind === 'document') {
                const html = await renderDocumentWithFormat(lastPrintJob.documentId, lastPrintJob.format)
                setPrintHtml(html)
                setShowPrintPreview(true)
            } else {
                const html = await printReceipt(lastPrintJob.receiptId, lastPrintJob.width)
                setPrintHtml(html)
                setShowPrintPreview(true)
            }
        } catch (err) {
            console.error('Error reimprimiendo:', err)
            alert(t('pos:errors.reprintFailed'))
        } finally {
            setLoading(false)
        }
    }

    const handlePayPending = async () => {
        if (!currentShift) {
            alert(t('pos:errors.noShiftOpen'))
            return
        }
        setShowPendingModal(true)
    }

    if (!selectedRegister) {
        const crearCajaRapida = async () => {
            try {
                setLoading(true)
                // Intentar obtener almacenes activos
                let ws = warehouses
                if (!ws || ws.length === 0) {
                    try {
                        ws = (await listWarehouses()).filter((w) => w.is_active)
                        setWarehouses(ws)
                    } catch { }
                }
                const wh = ws && ws.length > 0 ? ws[0] : null
                const payload: any = {
                    code: (newRegisterCode || '').trim() || undefined,
                    name: (newRegisterName || '').trim(),
                }
                // If there is more than one warehouse and user chose one, respect it
                const chosenId = headerWarehouseId || (ws && ws.length === 1 ? wh?.id : null)
                if (chosenId) payload.default_warehouse_id = chosenId
                const reg = await createRegister(payload)
                await loadRegisters()
                setSelectedRegister(reg)
                alert(t('pos:register.createdSuccess') + `: ${payload.name}`)
            } catch (e) {
                console.error('No se pudo crear la caja', e)
                alert(t('pos:register.createdError'))
            } finally {
                setLoading(false)
            }
        }

        return (
            <div className="p-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold mb-2">{t('pos:register.noRegisters')}</h2>
                    <p className="text-sm text-gray-600 mb-4">
                        {t('pos:register.createDefault')}
                    </p>
                    {!esAdminEmpresa && (
                        <p className="text-sm text-amber-700 mb-4">
                            {t('pos:register.adminOnly')}
                        </p>
                    )}
                    <div className="mb-4 grid gap-3">
                        <div>
                            <label className="block text-sm font-medium mb-1">{t('pos:register.nameLabel')}</label>
                            <input
                                value={newRegisterName}
                                onChange={(e) => setNewRegisterName(e.target.value)}
                                className="border rounded px-3 py-2 w-full"
                                placeholder="Caja Principal"
                                disabled={!esAdminEmpresa}
                                required
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">{t('pos:register.codeLabel')}</label>
                            <input
                                value={newRegisterCode}
                                onChange={(e) => setNewRegisterCode(e.target.value)}
                                className="border rounded px-3 py-2 w-full"
                                placeholder={t('pos:register.codeDefault')}
                                disabled={!esAdminEmpresa}
                            />
                        </div>
                    </div>

                    {warehouses.length > 1 && (
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-1">{t('pos:register.warehouseLabel')}</label>
                            <select
                                value={headerWarehouseId || ''}
                                onChange={(e) => setHeaderWarehouseId(e.target.value || null)}
                                className="border rounded px-3 py-2"
                            >
                                <option value="">{t('pos:register.choose')}</option>
                                {warehouses.map((w) => (
                                    <option key={w.id} value={w.id}>
                                        {w.code} - {w.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    <ProtectedButton
                        permission="pos:create"
                        onClick={crearCajaRapida}
                        disabled={loading || !newRegisterName.trim() || (warehouses.length > 1 && !headerWarehouseId)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60"
                    >
                        {loading ? t('pos:register.creating') : t('pos:register.buttonLabel')}
                    </ProtectedButton>
                </div>
            </div>
        )
    }

    return (
        <div className={cart.length > 0 ? 'tpv' : 'tpv tpv--no-cart'}>
            {/* Top Bar */}
            <header className="top">
                <div className="brand">
                    <div className="brand__logo" aria-hidden="true"></div>
                    <span>TPV - GestiQCloud</span>
                    {userLabel && (
                        <span className="badge" style={{ marginLeft: 8 }} title="Usuario conectado">
                            {userLabel}
                        </span>
                    )}
                </div>
                {currentShift && (
                    <div className="shift-pill" title={t('pos:header.shiftOpen')}>
                        <span className="shift-title">{t('pos:header.shiftOpen')}</span>
                        <span className="shift-meta">
                            {t('pos:shift.opening')} {currencySymbol}{(Number(currentShift.opening_float) || 0).toFixed(2)}
                        </span>
                        {inventoryConfig.reorderPoint > 0 && (
                            <span className="shift-meta">
                                {t('pos:shift.minimumStock')}: {inventoryConfig.reorderPoint}
                            </span>
                        )}
                        <ProtectedButton
                            permission="pos:update"
                            className="btn sm danger"
                            onClick={() => shiftManagerRef.current?.openCloseModal()}
                        >
                            {t('pos:header.closingShift')}
                        </ProtectedButton>
                    </div>
                )}
                <div className="actions top-actions">
                    <ProtectedButton permission="pos:update" className="btn sm" onClick={() => setTicketNotes(prompt(t('pos:cart.ticketNotes'), ticketNotes) || ticketNotes)}>
                        {t('pos:header.notes')}
                    </ProtectedButton>
                    {canDiscount && (
                        <ProtectedButton permission="pos:update" className="btn sm" onClick={() => setGlobalDiscountPct(parseFloat(prompt(t('pos:header.discount') + ' (%)', String(globalDiscountPct)) || String(globalDiscountPct)))}>
                            {t('pos:header.discount')}
                        </ProtectedButton>
                    )}
                    {canViewReports && (
                        <ProtectedButton
                            permission="pos:read"
                            className="btn sm"
                            onClick={() => {
                                const url = selectedRegister ? `daily-counts?register_id=${selectedRegister.id}` : 'daily-counts'
                                navigate(url)
                            }}
                        >
                            {t('pos:header.dailyReports')}
                        </ProtectedButton>
                    )}
                    <ProtectedButton permission="pos:read" className="btn sm" onClick={handleHoldTicket}>
                        {t('pos:header.holdTicket')}
                    </ProtectedButton>
                    <ProtectedButton permission="pos:read" className="btn sm" onClick={handleResumeTicket}>
                        {t('pos:header.resume')}
                    </ProtectedButton>
                    <ProtectedButton permission="pos:read" className="btn sm" onClick={handleReprintLast} title={t("pos:header.reprintTooltip")}>
                        {t('pos:header.reprint')}
                    </ProtectedButton>
                    {canManagePending && (
                        <ProtectedButton permission="pos:update" className="btn sm" onClick={handlePayPending}>
                            {t('pos:header.pendingPayments')}
                        </ProtectedButton>
                    )}
                </div>
                <div className="top-meta">
                    <span className={`badge ${isOnline ? 'ok' : 'off'}`}>
                        {isOnline ? t('pos:header.online') : t('pos:header.offline')}
                    </span>
                    {pendingCount > 0 && (
                        <ProtectedButton permission="pos:read" className="badge" onClick={syncNow} title={t('pos:header.syncing')}>
                            ⟳ {pendingCount} {t('pos:header.syncing')}
                        </ProtectedButton>
                    )}
                    {esAdminEmpresa && cashiers.length > 0 && (
                        <select
                            value={selectedCashierId || ''}
                            onChange={(e) => setSelectedCashierId(e.target.value || null)}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            title={t('pos:header.cashierLabel')}
                        >
                            {!selectedCashierId && <option value="">{t('pos:header.cashierLabel')}…</option>}
                            {cashiers.map((u) => (
                                <option key={u.id} value={u.id}>
                                    {formatCashierLabel(u)}
                                </option>
                            ))}
                        </select>
                    )}
                    <select
                        value={selectedRegister?.id || ''}
                        onChange={(e) => {
                            const reg = registers.find((r) => r.id === e.target.value)
                            setSelectedRegister(reg || null)
                        }}
                        className="badge"
                        style={{ cursor: 'pointer' }}
                    >
                        {registers.map((reg) => (
                            <option key={reg.id} value={reg.id}>
                                {reg.name}
                            </option>
                        ))}
                    </select>
                    {esAdminEmpresa && warehouses.length > 1 && (
                        <select
                            value={headerWarehouseId || ''}
                            onChange={(e) => setHeaderWarehouseId(e.target.value || null)}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            title={t('pos:header.warehouseLabel')}
                        >
                            <option value="">{t('pos:header.warehouseLabel')}…</option>
                            {warehouses.map((w) => (
                                <option key={w.id} value={w.id}>
                                    {w.code} — {w.name}
                                </option>
                            ))}
                        </select>
                    )}
                </div>
            </header>

            {/* Left Column - Catalog */}
            <section className="left">
                {/* Shift Manager */}
                <ShiftManager ref={shiftManagerRef} register={selectedRegister} onShiftChange={setCurrentShift} compact />

                {/* Search */}
                <div
                    className={`search ${searchExpanded ? 'search--expanded' : 'search--collapsed'}`}
                    role="search"
                >
                    <ProtectedButton
                        permission="pos:read"
                        className="btn sm ghost search-toggle"
                        onClick={() => setSearchExpanded((prev) => !prev)}
                        type="button"
                    >
                        {t('pos:search.button')}
                    </ProtectedButton>
                    <input
                        id="search"
                        placeholder={t('pos:search.placeholder')}
                        aria-label={t('pos:search.placeholder')}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onFocus={() => setSearchExpanded(true)}
                        onBlur={() => {
                            if (!searchQuery.trim()) setSearchExpanded(false)
                        }}
                        onKeyDown={(e) => {
                            if (e.key === 'F2') {
                                e.currentTarget.focus()
                                return
                            }
                            handleSearchEnter(e)
                        }}
                    />
                    <input
                        id="barcode"
                        placeholder={t('pos:search.barcodeInput')}
                        aria-label={t('pos:search.barcodeInput')}
                        style={{ width: 180, borderLeft: '1px solid var(--border)', paddingLeft: 10 }}
                        value={barcodeInput}
                        onChange={(e) => setBarcodeInput(e.target.value)}
                        onKeyDown={handleBarcodeEnter}
                    />
                    <ProtectedButton permission="pos:read" className="btn sm" onClick={() => setSearchQuery('')}>
                        {t('common:clear')}
                    </ProtectedButton>
                </div>

                {/* View Mode Toggle */}
                <div className="view-toggle">
                    <ProtectedButton
                        permission="pos:read"
                        className={`btn sm ${viewMode === 'categories' ? 'primary' : ''}`}
                        onClick={() => setViewMode('categories')}
                    >
                        {t('pos:view.byCategories')}
                    </ProtectedButton>
                    <ProtectedButton
                        permission="pos:read"
                        className={`btn sm ${viewMode === 'all' ? 'primary' : ''}`}
                        onClick={() => setViewMode('all')}
                    >
                        {t('pos:view.all')}
                    </ProtectedButton>
                </div>

                {/* Categories - only visible in categories mode */}
                {viewMode === 'categories' && (
                    <div className="cats" role="tablist" aria-label={t('pos:catalog.title')}>
                        {categories.map((cat) => (
                            <ProtectedButton
                                permission="pos:read"
                                key={cat}
                                className={`cat ${selectedCategory === cat ? 'active' : ''}`}
                                onClick={() => setSelectedCategory(cat)}
                            >
                                {cat === '*' ? t('pos:view.all') : cat}
                            </ProtectedButton>
                        ))}
                    </div>
                )}

                {/* Product Grid */}
                <div id="catalog" className="catalog" role="list" aria-label={t('pos:catalog.title')}>
                    {filteredProducts.map((p) => (
                        <ProtectedButton
                            permission="pos:create"
                            key={p.id}
                            className="tile"
                            role="listitem"
                            title={p.sku || ''}
                            onClick={() => addToCart(p)}
                        >
                            <strong>{p.name}</strong>
                            <small>{p.price?.toFixed(2) || '0.00'}{currencySymbol}</small>
                            {p.product_metadata?.tags && (
                                <div className="tags">
                                    {p.product_metadata.tags.map((tag: string) => (
                                        <span key={tag} className="chip">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </ProtectedButton>
                    ))}
                    {filteredProducts.length === 0 && (
                        <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                            {t('pos:catalog.empty')}
                        </div>
                    )}
                </div>
            </section>

            {/* Right Column - Cart & Payment */}
            <aside className="right">
                <div className="cart" role="list" aria-label="Carrito">
                    {cart.map((item, idx) => {
                        const lineTotal = item.price * item.qty * (1 - item.discount_pct / 100)
                        return (
                            <div key={idx} className="row">
                                <div>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', justifyContent: 'space-between' }}>
                                        <strong>{item.name}</strong>
                                        <div className="line-tools">
                                             <ProtectedButton permission="pos:update" className="btn ghost" title={t('pos:cart.lineDiscount')} onClick={() => setLineDiscount(idx)}>
                                                 -%
                                             </ProtectedButton>
                                             <ProtectedButton permission="pos:update" className="btn ghost" title={t('pos:cart.lineNotes')} onClick={() => setLineNote(idx)}>
                                                 📝
                                             </ProtectedButton>
                                         </div>
                                    </div>
                                    <small style={{ color: 'var(--muted)' }}>
                                        {item.price.toFixed(2)}{currencySymbol}
                                        {item.discount_pct > 0 && ` · Desc ${item.discount_pct}%`}
                                        {item.pricing_note && ` · ${item.pricing_note}`}
                                        {item.notes && ` · ${item.notes}`}
                                    </small>
                                </div>
                                <div className="qty">
                                    <ProtectedButton permission="pos:update" aria-label="menos" onClick={() => updateQty(idx, -1)}>
                                        –
                                    </ProtectedButton>
                                    <input
                                        type="number"
                                        min="0.01"
                                        step="0.01"
                                        aria-label="cantidad"
                                        value={item.qty}
                                        onChange={(e) => {
                                            const newQty = parseFloat(e.target.value) || 0
                                            if (newQty > 0) {
                                                const updated = [...cart]
                                                const product = products.find((p) => p.id === updated[idx].product_id)
                                                if (product) {
                                                    updated[idx] = applyPricingToCartItem(updated[idx], product, newQty)
                                                } else {
                                                    updated[idx].qty = newQty
                                                }
                                                setCart(updated)
                                            }
                                        }}
                                        style={{ textAlign: 'center' }}
                                    />
                                    <ProtectedButton permission="pos:update" aria-label={t('pos:actions.increment')} onClick={() => updateQty(idx, 1)}>
                                        +
                                    </ProtectedButton>
                                </div>
                                <div className="sum">{lineTotal.toFixed(2)}{currencySymbol}</div>
                                <ProtectedButton permission="pos:update" className="del" aria-label="Delete" onClick={() => removeItem(idx)}>
                                    ✕
                                </ProtectedButton>
                            </div>
                        )
                    })}
                </div>

                {cart.length > 0 && (
                    <div className="pay">
                        <div className="totals">
                            <div>{t('pos:totals.subtotal')}</div>
                            <div className="sum">{totals.subtotal.toFixed(2)}{currencySymbol}</div>
                            <div>{t('pos:totals.discount')}</div>
                            <div className="sum">-{(totals.line_discounts + totals.global_discount).toFixed(2)}{currencySymbol}</div>
                            <div>{t('pos:totals.tax')}</div>
                            <div className="sum">{totals.tax.toFixed(2)}{currencySymbol}</div>
                            <div className="big">{t('pos:totals.total')}</div>
                            <div className="sum big">{totals.total.toFixed(2)}{currencySymbol}</div>
                        </div>
                    </div>
                )}
            </aside>

            {/* Bottom Bar */}
            {cart.length > 0 && (
                <footer
                    className="bottom"
                    style={{
                        position: 'fixed',
                        left: 16,
                        right: 16,
                        bottom: 16,
                        zIndex: 50,
                        borderRadius: 12,
                        boxShadow: '0 12px 28px rgba(0,0,0,0.18)',
                        padding: '10px 12px',
                        background: 'var(--panel, #111827)',
                        width: 'min(520px, calc(100% - 32px))',
                        marginRight: 'auto'
                    }}
                >
                    <div className="actions">
                        <ProtectedButton
                            permission="pos:update"
                            className="btn"
                            onClick={() => {
                                if (confirm(t('pos:cart.confirmClear'))) {
                                    setCart([])
                                    setGlobalDiscountPct(0)
                                    setTicketNotes('')
                                }
                            }}
                        >
                            {t('pos:cart.clearAll')}
                        </ProtectedButton>
                        <ProtectedButton permission="pos:update" className="btn" onClick={() => setTicketNotes(prompt(t('pos:cart.ticketNotes'), ticketNotes) || ticketNotes)}>
                            {t('pos:header.notes')}
                        </ProtectedButton>
                    </div>
                    <div className="actions">
                        <ProtectedButton permission="pos:create" className="btn primary" onClick={handleCheckout} disabled={cart.length === 0 || !currentShift}>
                            {cart.length > 0
                                ? t('pos:actions.chargeWithTotal', { amount: totals.total.toFixed(2), currency: currencySymbol })
                                : t('pos:actions.charge')}
                        </ProtectedButton>
                        <ProtectedButton permission="pos:create" className="btn" onClick={handleCheckoutWithoutTicket} disabled={cart.length === 0 || !currentShift}>
                            {cart.length > 0
                                ? t('pos:actions.chargeNoReceiptWithTotal', { amount: totals.total.toFixed(2), currency: currencySymbol })
                                : t('pos:actions.chargeNoReceipt')}
                        </ProtectedButton>
                    </div>
                </footer>
            )}

            {/* Modals */}

            {showBuyerModal && (
                <div
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0, 0, 0, 0.45)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 9999,
                    }}
                >
                    <div
                        style={{
                            width: 'min(560px, 92vw)',
                            background: '#fff',
                            borderRadius: 12,
                            padding: 16,
                            boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 12,
                        }}
                    >
                        <div style={{ fontWeight: 700 }}>{t('pos:buyer.documentType')}</div>
                        {buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0 && (
                            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                                {t('pos:buyer.requiresInvoiceAbove', { amount: currencySymbol + buyerPolicy.consumerFinalMaxTotal.toFixed(2) })}
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: 8 }}>
                            <ProtectedButton
                                permission="pos:create"
                                className={`btn sm ${buyerMode === 'CONSUMER_FINAL' ? 'primary' : ''}`}
                                onClick={() => handleBuyerContinue('CONSUMER_FINAL')}
                                disabled={buyerPolicy.consumerFinalEnabled === false}
                            >
                                {t('pos:buyer.consumerFinal')}
                            </ProtectedButton>
                            <ProtectedButton
                                permission="pos:create"
                                className={`btn sm ${buyerMode === 'IDENTIFIED' ? 'primary' : ''}`}
                                onClick={() => setBuyerMode('IDENTIFIED')}
                            >
                                {t('pos:buyer.invoiceWithData')}
                            </ProtectedButton>
                        </div>
                        {buyerMode === 'CONSUMER_FINAL' && !canUseConsumerFinal && (
                            <div style={{ color: '#b91c1c', fontSize: 12 }}>
                                {t('pos:buyer.excedsLimit')}
                            </div>
                        )}
                        {buyerMode === 'IDENTIFIED' && (
                            <div style={{ display: 'grid', gap: 8 }}>
                                <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#111827', marginBottom: 6 }}>
                                        {t('pos:buyer.existingClient')}
                                    </div>
                                    <input
                                        type="text"
                                        placeholder={t('pos:buyer.search')}
                                        value={clientQuery}
                                        onChange={(e) => setClientQuery(e.target.value)}
                                    />
                                    {clientsLoading && (
                                        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>{t('common:loading')}</div>
                                    )}
                                    {!clientsLoading && clientsLoadError && (
                                        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                                            <div style={{ fontSize: 12, color: '#b91c1c' }}>{clientsLoadError}</div>
                                            <ProtectedButton
                                                permission="pos:read"
                                                type="button"
                                                className="btn ghost"
                                                onClick={() => {
                                                    clientsLoadAttemptedRef.current = false
                                                    loadClients()
                                                }}
                                            >
                                                {t('common:retry')}
                                            </ProtectedButton>
                                        </div>
                                    )}
                                    {!clientsLoading && filteredClients.length > 0 && (
                                        <div style={{ display: 'grid', gap: 4, marginTop: 6, maxHeight: 160, overflow: 'auto' }}>
                                            {filteredClients.map((c) => (
                                                <ProtectedButton
                                                    permission="pos:read"
                                                    key={String(c.id)}
                                                    type="button"
                                                    className="btn ghost"
                                                    style={{ justifyContent: 'space-between' }}
                                                    onClick={() => handleSelectClient(c)}
                                                >
                                                    <span>{c.name}</span>
                                                    <span style={{ fontSize: 11, color: '#6b7280' }}>
                                                        {(c.identificacion || c.tax_id || '').toString()}
                                                    </span>
                                                </ProtectedButton>
                                            ))}
                                        </div>
                                    )}
                                    {!clientsLoading && clientQuery && filteredClients.length === 0 && (
                                        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>{t('common:noResults')}</div>
                                    )}
                                    {selectedClient && (
                                        <div style={{ marginTop: 8, fontSize: 12, color: '#111827' }}>
                                            {t('pos:buyer.selected')}: <strong>{selectedClient.name}</strong>
                                            {selectedClient.is_wholesale ? ` (${t('pos:buyer.wholesale')})` : ''}
                                            <ProtectedButton
                                                permission="pos:read"
                                                type="button"
                                                className="btn ghost"
                                                style={{ marginLeft: 8 }}
                                                onClick={clearSelectedClient}
                                            >
                                                {t('common:remove')}
                                            </ProtectedButton>
                                        </div>
                                    )}
                                </div>
                                {!selectedClient && (
                                    <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={saveBuyerAsClient}
                                            onChange={(e) => setSaveBuyerAsClient(e.target.checked)}
                                        />
                                        {t('pos:buyer.saveForFuture')}
                                    </label>
                                )}
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>{t('pos:print.format')}</div>
                                    <select
                                        value={docPrintFormat}
                                        onChange={(e) => setDocPrintFormat(e.target.value as any)}
                                        className="badge"
                                        style={{ cursor: 'pointer', padding: '6px 8px' }}
                                    >
                                        <option value="THERMAL_80MM">Recibo (80mm)</option>
                                        <option value="A4_PDF">Papel A4</option>
                                    </select>
                                </div>
                                <select
                                    value={buyerIdType}
                                    onChange={(e) => setBuyerIdType(e.target.value)}
                                    className="badge"
                                    style={{ cursor: 'pointer', padding: '6px 8px' }}
                                >
                                    {allowedIdTypes.map((opt) => (
                                        <option key={opt} value={opt}>
                                            {opt}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    type="text"
                                    placeholder="Identificacion"
                                    value={buyerIdNumber}
                                    onChange={(e) => setBuyerIdNumber(e.target.value)}
                                />
                                <input
                                    type="text"
                                    placeholder="Nombre"
                                    value={buyerName}
                                    onChange={(e) => setBuyerName(e.target.value)}
                                />
                                <input
                                    type="email"
                                    placeholder="Email (opcional)"
                                    value={buyerEmail}
                                    onChange={(e) => setBuyerEmail(e.target.value)}
                                />
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                            <ProtectedButton permission="pos:read" className="btn ghost" onClick={() => setShowBuyerModal(false)}>
                                {t('common:cancel')}
                            </ProtectedButton>
                            <ProtectedButton permission="pos:update" className="btn primary" onClick={() => handleBuyerContinue()}>
                                {t('common:continue')}
                            </ProtectedButton>
                        </div>
                    </div>
                </div>
            )}

            {showPaymentModal && currentReceiptId && (
                <PaymentModal
                    receiptId={currentReceiptId}
                    totalAmount={totals.total}
                    warehouseId={headerWarehouseId || undefined}
                    onSuccess={handlePaymentSuccess}
                    onCancel={() => setShowPaymentModal(false)}
                />
            )}

            {showInvoiceModal && currentReceiptId && (
                <ConvertToInvoiceModal
                    receiptId={currentReceiptId}
                    onSuccess={() => {
                        setShowInvoiceModal(false)
                        setCurrentReceiptId(null)
                        setAutoCreateInvoice(false)
                        alert(t('pos:errors.invoiceGeneratedSuccess'))
                    }}
                    onCancel={() => {
                        setShowInvoiceModal(false)
                        setAutoCreateInvoice(false)
                    }}
                />
            )}

            {showCreateProductModal && (
                <div
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0, 0, 0, 0.45)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 9999,
                    }}
                >
                    <div
                        style={{
                            width: 'min(520px, 92vw)',
                            background: '#fff',
                            borderRadius: 12,
                            padding: 16,
                            boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 12,
                        }}
                    >
                        <div style={{ fontWeight: 700 }}>{t('pos:createProduct.title')}</div>
                        <div style={{ display: 'grid', gap: 10 }}>
                            <label style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>
                                {t('pos:createProduct.sku')}
                            </label>
                            <input
                                type="text"
                                style={{
                                    border: '1px solid #cbd5f5',
                                    padding: '8px 10px',
                                    borderRadius: 8,
                                    outline: 'none',
                                }}
                                value={createProductForm.sku}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({ ...prev, sku: e.target.value }))
                                }
                            />
                            <label style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>
                                {t('pos:createProduct.name')} <span style={{ color: '#ef4444' }}>*</span>
                            </label>
                            <input
                                type="text"
                                style={{
                                    border: '2px solid #2563eb',
                                    padding: '8px 10px',
                                    borderRadius: 8,
                                    outline: 'none',
                                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.12)',
                                }}
                                value={createProductForm.name}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({ ...prev, name: e.target.value }))
                                }
                            />
                            {!createProductForm.name.trim() && (
                                <div style={{ fontSize: 11, color: '#b91c1c' }}>
                                    {t('pos:createProduct.nameRequired')}
                                </div>
                            )}
                            <label style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>
                                {t('pos:createProduct.price')} <span style={{ color: '#ef4444' }}>*</span>
                            </label>
                            <input
                                type="number"
                                style={{
                                    border: '2px solid #2563eb',
                                    padding: '8px 10px',
                                    borderRadius: 8,
                                    outline: 'none',
                                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.08)',
                                }}
                                value={createProductForm.price}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({
                                        ...prev,
                                        price: Number(e.target.value) || 0,
                                    }))
                                }
                                min={0}
                                step="0.01"
                            />
                            {Number(createProductForm.price) <= 0 && (
                                <div style={{ fontSize: 11, color: '#b91c1c' }}>
                                    {t('pos:createProduct.priceMinimum')}
                                </div>
                            )}
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1f2937' }}>
                                {t('pos:createProduct.stock')}
                            </label>
                            <input
                                type="number"
                                style={{ border: '1px solid #d1d5db', padding: '8px 10px', borderRadius: 8 }}
                                value={createProductForm.stock}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({
                                        ...prev,
                                        stock: Number(e.target.value) || 0,
                                    }))
                                }
                                min={0}
                                step="0.01"
                            />
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1f2937' }}>
                                {t('pos:createProduct.tax')}
                            </label>
                            <input
                                type="number"
                                style={{ border: '1px solid #d1d5db', padding: '8px 10px', borderRadius: 8 }}
                                value={createProductForm.iva_tasa}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({
                                        ...prev,
                                        iva_tasa: Number(e.target.value) || 0,
                                    }))
                                }
                                min={0}
                                step="0.01"
                            />
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1f2937' }}>
                                {t('pos:createProduct.category')}
                            </label>
                            <input
                                type="text"
                                style={{ border: '1px solid #d1d5db', padding: '8px 10px', borderRadius: 8 }}
                                value={createProductForm.categoria}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({
                                        ...prev,
                                        categoria: e.target.value,
                                    }))
                                }
                            />
                        </div>
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                            <ProtectedButton
                                permission="pos:read"
                                className="btn ghost"
                                onClick={() => setShowCreateProductModal(false)}
                                disabled={creatingProduct}
                            >
                                {t('common:cancel')}
                            </ProtectedButton>
                            <ProtectedButton
                                permission="pos:create"
                                className="btn primary"
                                disabled={
                                    creatingProduct ||
                                    !createProductForm.name.trim() ||
                                    Number(createProductForm.price) <= 0
                                }
                                onClick={async () => {
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
                                                alert(t('pos:createProduct.existingAdded'))
                                                return
                                            }
                                            const remoteMatches = await searchProductos(skuValue)
                                            const remoteProduct = Array.isArray(remoteMatches)
                                                ? remoteMatches.find((p) => {
                                                    return (
                                                        normalizeCode(p.sku) === normalizeCode(skuValue) ||
                                                        normalizeCode(p.product_metadata?.codigo_barras as string) ===
                                                        normalizeCode(skuValue)
                                                    )
                                                })
                                                : null
                                            if (remoteProduct) {
                                                setProducts((prev) => [remoteProduct, ...prev])
                                                addToCart(remoteProduct)
                                                setBarcodeInput('')
                                                setShowCreateProductModal(false)
                                                alert(t('pos:createProduct.existingAdded'))
                                                return
                                            }
                                        }
                                        const created = await createProducto({
                                            sku: skuValue || undefined,
                                            name: createProductForm.name.trim(),
                                            price: Number(createProductForm.price) || 0,
                                            stock: Number(createProductForm.stock) || 0,
                                            iva_tasa: Number(createProductForm.iva_tasa) || 0,
                                            categoria:
                                                createProductForm.categoria.trim() ||
                                                (selectedCategory !== '*' ? selectedCategory : undefined),
                                            unit: 'unit',
                                            active: true,
                                        })
                                        const stockQty = Number(createProductForm.stock) || 0
                                        if (stockQty > 0) {
                                            const warehouseId = await resolveWarehouseForStock()
                                            if (warehouseId) {
                                                try {
                                                    await adjustStock({
                                                        warehouse_id: warehouseId,
                                                        product_id: created.id,
                                                        delta: stockQty,
                                                        reason: 'POS quick add',
                                                    })
                                                } catch (err) {
                                                    console.error('No se pudo ajustar stock', err)
                                                }
                                            }
                                        }
                                        const enrichedProduct: Producto = {
                                            ...created,
                                            stock: stockQty > 0 ? stockQty : Number(created.stock ?? 0),
                                        }
                                        setProducts((prev) => [enrichedProduct, ...prev])
                                        addToCart(enrichedProduct, { ignoreReorder: true })
                                        setBarcodeInput('')
                                        setShowCreateProductModal(false)
                                    } catch (err) {
                                        alert(t('pos:createProduct.creationFailed'))
                                    } finally {
                                        setCreatingProduct(false)
                                    }
                                }}
                            >
                                {t('common:saveAndAdd')}
                            </ProtectedButton>
                        </div>
                    </div>
                </div>
            )}


            {showPrintPreview && (
                <div
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0, 0, 0, 0.45)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 9999,
                    }}
                >
                    <div
                        style={{
                            width: 'min(900px, 95vw)',
                            background: '#fff',
                            borderRadius: 12,
                            padding: 16,
                            boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 12,
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ fontWeight: 700 }}>{t('pos:print.preview')}</div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <ProtectedButton
                                    permission="pos:read"
                                    className="btn"
                                    onClick={() => {
                                        const win = printFrameRef.current?.contentWindow
                                        if (win) {
                                            const handleAfterPrint = () => {
                                                win.removeEventListener('afterprint', handleAfterPrint)
                                                setShowPrintPreview(false)
                                                setPrintHtml('')
                                                alert(t('pos:errors.printingFinished'))
                                            }
                                            win.addEventListener('afterprint', handleAfterPrint)
                                            win.focus()
                                            win.print()
                                        }
                                    }}
                                >
                                    {t('common:print')}
                                </ProtectedButton>
                                <ProtectedButton
                                    permission="pos:read"
                                    className="btn ghost"
                                    onClick={() => {
                                        setShowPrintPreview(false)
                                        setPrintHtml('')
                                    }}
                                >
                                    {t('common:close')}
                                </ProtectedButton>
                            </div>
                        </div>
                        <iframe
                            ref={printFrameRef}
                            title="ticket"
                            srcDoc={printHtml}
                            style={{ width: '100%', height: '70vh', border: '1px solid #e5e7eb', borderRadius: 8 }}
                        />
                    </div>
                </div>
            )}
            <PendingReceiptsModal
                isOpen={showPendingModal}
                shiftId={currentShift?.id || undefined}
                onClose={() => setShowPendingModal(false)}
                canManage={esAdminEmpresa}
                onPaid={() => {
                    // Hook para refrescar datos si es necesario
                }}
            />
        </div>
    )
}
