/**
 * POSView - Terminal Punto de Venta Profesional
 * Diseño basado en tpv_pro.html con integración completa backend
 */
import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import ShiftManager, { type ShiftManagerHandle } from './components/ShiftManager'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import useOfflineSync from './hooks/useOfflineSync'
import { useCurrency } from '../../hooks/useCurrency'
import { useAuth } from '../../auth/AuthContext'
import { listWarehouses, adjustStock, type Warehouse } from '../inventario/services'
import { listUsuarios } from '../usuarios/services'
import type { Usuario } from '../usuarios/types'
import { listClientes, type Cliente } from '../clientes/services'
import {
    listRegisters,
    createRegister,
    createReceipt,
    printReceipt,
    addToOutbox,
    calculateReceiptTotals,
    issueDocument,
    renderDocument,
    type ReceiptTotals,
    type SaleDraft,
} from './services'
import { createProducto, listProductos, searchProductos, type Producto } from '../productos/services'
import { getCompanySettings, getDefaultReorderPoint, getDefaultTaxRate } from '../../services/companySettings'
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

const POS_DRAFT_KEY = 'posDraftState'

const DEFAULT_ID_TYPES = ['CEDULA', 'RUC', 'PASSPORT']

export default function POSView() {
    const navigate = useNavigate()
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
    const [showCreateProductModal, setShowCreateProductModal] = useState(false)
    const [loading, setLoading] = useState(false)
    const [creatingProduct, setCreatingProduct] = useState(false)
    const [heldTickets, setHeldTickets] = useState<HeldTicket[]>([])
    const [showPendingModal, setShowPendingModal] = useState(false)
    const [showPrintPreview, setShowPrintPreview] = useState(false)
    const [printHtml, setPrintHtml] = useState('')
    const printFrameRef = useRef<HTMLIFrameElement>(null)
    const [cashiers, setCashiers] = useState<Usuario[]>([])
    const [selectedCashierId, setSelectedCashierId] = useState<string | null>(null)
    const [newRegisterName, setNewRegisterName] = useState('Caja Principal')
    const [newRegisterCode, setNewRegisterCode] = useState('CAJA-1')
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
    const [clientQuery, setClientQuery] = useState('')
    const [selectedClient, setSelectedClient] = useState<Cliente | null>(null)
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
    const shiftManagerRef = useRef<ShiftManagerHandle | null>(null)
    const barcodeBufferRef = useRef('')
    const barcodeTimerRef = useRef<number | null>(null)

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
                    // silencioso: si inventario no está disponible, POS sigue funcionando
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
        ;(async () => {
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
            // Para POS, si no hay configuración explícita, preferimos 0 (no forzar 15% por defecto)
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
        try {
            setClientsLoading(true)
            const data = await listClientes()
            setClients(data)
        } catch (error) {
            console.error('Error loading clients:', error)
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

        // En modo categorías, filtrar por categoría seleccionada
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

        // Búsqueda por texto siempre activa
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
        loadClients()
    }, [showBuyerModal, buyerMode, clients.length, clientsLoading])

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
            alert(`Stock insuficiente. Disponible: ${stock}`)
            return true
        }

        if (!opts?.ignoreReorder) {
            const reorderPoint = getReorderPoint(product)
            if (reorderPoint > 0 && remaining < reorderPoint) {
                alert(`Stock bajo del minimo de stock (${reorderPoint}). No se puede vender.`)
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
        const existing = cart.find((item) => item.product_id === product.id)
        const nextQty = existing ? existing.qty + 1 : 1
        if (violatesStockPolicy(product, nextQty, opts)) return

        if (existing) {
            setCart(
                cart.map((item) =>
                    item.product_id === product.id
                        ? applyPricingToCartItem(item, product, nextQty)
                        : item
                )
            )
        } else {
            const baseItem: CartItem = {
                product_id: product.id,
                sku: product.sku || '',
                name: product.name,
                price: product.price || 0,
                // Preservar 0% si el producto lo tiene; solo usar fallback de configuracion cuando viene null/undefined
                iva_tasa: (product as any).iva_tasa ?? defaultTaxPct,
                qty: 1,
                discount_pct: 0,
                categoria: product.categoria || (product.product_metadata?.categoria as any),
            }
            const priced = applyPricingToCartItem(baseItem, product, 1)
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
    }

    const clearSelectedClient = () => {
        setSelectedClient(null)
        setClientQuery('')
        setIsWholesaleCustomer(false)
    }

    const removeItem = (index: number) => {
        setCart(cart.filter((_, i) => i !== index))
    }

    const setLineDiscount = (index: number) => {
        const value = prompt('Descuento línea (%)', String(cart[index].discount_pct))
        if (value === null) return
        const pct = Math.min(100, Math.max(0, parseFloat(value) || 0))
        setCart(cart.map((item, i) => (i === index ? { ...item, discount_pct: pct } : item)))
    }

const setLineNote = (index: number) => {
        const value = prompt('Notas de línea', cart[index].notes || '')
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
                const shouldCreate = confirm(`Producto no encontrado: ${code}\n¿Deseas crearlo?`)
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

    // Totales calculados por el backend (fuente única de verdad)
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
                .replace(/\s+/g, ' ')
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
                        const shouldCreate = confirm(`Producto no encontrado: ${code}\n¿Deseas crearlo?`)
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
            alert('El total supera el limite para consumidor final. Se requieren datos.')
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
                // Fallback a cálculo local en caso de error de red
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
        const currency = companySettings?.currency || 'USD'
        const posId = selectedRegister?.id ? String(selectedRegister.id) : 'pos'

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
            alert('Error al preparar el pago')
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
            alert('El total requiere datos del comprador.')
            return
        }
        if (mode == 'IDENTIFIED') {
            const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
            if (!normalized) {
                alert('Selecciona el tipo de identificacion del comprador.')
                return
            }
            if (!buyerIdNumber.trim() || !buyerName.trim()) {
                alert('Completa nombre e identificacion del comprador.')
                return
            }
        }
        setShowBuyerModal(false)
        await startCheckout()
    }


    const handleCheckout = () => {
        if (cart.length === 0) {
            alert('No hay l?neas en el carrito')
            return
        }
        if (!currentShift) {
            alert('Abre un turno primero')
            return
        }
        setShowBuyerModal(true)
    }


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
                    if (docId) {
                        const html = await renderDocument(docId)
                        setPrintHtml(html)
                        setShowPrintPreview(true)
                        docPrinted = true
                    }
                } catch (err) {
                    console.error('Error emitiendo documento:', err)
                    if (buyerMode === 'IDENTIFIED') {
                        alert('No se pudo emitir documento con datos. Se imprimira ticket simple.')
                    }
                }
            }

            if (!docPrinted) {
                const html = await printReceipt(currentReceiptId, '58mm')
                setPrintHtml(html)
                setShowPrintPreview(true)
            }

            // Reset
            setCart([])
            setGlobalDiscountPct(0)
            setTicketNotes('')
            setBuyerMode('CONSUMER_FINAL')
            setBuyerIdType('')
            setBuyerIdNumber('')
            setBuyerName('')
            setBuyerEmail('')
            localStorage.removeItem(POS_DRAFT_KEY)
            setShowPaymentModal(false)
            pendingSaleRef.current = null

            alert('Venta completada ✓')
        } catch (error: any) {
            if (!isOnline) {
                await addToOutbox({ type: 'receipt', data: { cart, totals } })
                alert('Ticket guardado offline. Se sincronizará cuando haya conexión.')
                setCart([])
                setShowPaymentModal(false)
            } else {
                alert(error.response?.data?.detail || 'Error al crear ticket')
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
            alert('No hay líneas en el carrito')
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
        alert(`Ticket en espera: ${id}\nUsa Reimprimir para recuperar.`)
    }

    const handleResumeTicket = () => {
        if (heldTickets.length === 0) {
            alert('No hay tickets en espera')
            return
        }
        const list = heldTickets.map((t) => t.id).join(', ')
        const pick = prompt(`Tickets en espera:\n${list}\nEscribe ID para recuperar`)
        if (!pick) return
        const trimmed = pick.trim()
        const idx = heldTickets.findIndex((t) => t.id === trimmed)
        if (idx < 0) {
            alert('ID no encontrado')
            return
        }
        const ticket = heldTickets[idx]
        setHeldTickets([...heldTickets.slice(0, idx), ...heldTickets.slice(idx + 1)])
        setCart(ticket.cart)
        setGlobalDiscountPct(ticket.globalDiscountPct || 0)
        setTicketNotes(ticket.ticketNotes || '')
        setCurrentReceiptId(null)
        alert(`Ticket recuperado: ${trimmed}`)
    }

    const handlePayPending = async () => {
        if (!currentShift) {
            alert('Abre un turno primero')
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
                // Si hay más de un almacén y el usuario eligió uno, respétalo
                const chosenId = headerWarehouseId || (ws && ws.length === 1 ? wh?.id : null)
                if (chosenId) payload.default_warehouse_id = chosenId
                const reg = await createRegister(payload)
                await loadRegisters()
                setSelectedRegister(reg)
                alert(`Caja creada: ${payload.name}`)
            } catch (e) {
                console.error('No se pudo crear la caja', e)
                alert('No se pudo crear la caja. Revisa permisos o intenta desde Admin.')
            } finally {
                setLoading(false)
            }
        }

        return (
            <div className="p-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold mb-2">No hay cajas registradas</h2>
                    <p className="text-sm text-gray-600 mb-4">
                        Crea una caja por defecto para comenzar a vender. Usaremos tu único almacén activo si está disponible.
                    </p>
                    {!esAdminEmpresa && (
                        <p className="text-sm text-amber-700 mb-4">
                            Solo un administrador puede crear cajas. Solicita acceso o crea la caja desde Admin.
                        </p>
                    )}
                    <div className="mb-4 grid gap-3">
                        <div>
                            <label className="block text-sm font-medium mb-1">Nombre de la caja</label>
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
                            <label className="block text-sm font-medium mb-1">CODIGO (opcional)</label>
                            <input
                                value={newRegisterCode}
                                onChange={(e) => setNewRegisterCode(e.target.value)}
                                className="border rounded px-3 py-2 w-full"
                                placeholder="CAJA-1"
                                disabled={!esAdminEmpresa}
                            />
                        </div>
                    </div>

                    {warehouses.length > 1 && (
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-1">Selecciona almacén por defecto</label>
                            <select
                                value={headerWarehouseId || ''}
                                onChange={(e) => setHeaderWarehouseId(e.target.value || null)}
                                className="border rounded px-3 py-2"
                            >
                                <option value="">— Elegir —</option>
                                {warehouses.map((w) => (
                                    <option key={w.id} value={w.id}>
                                        {w.code} - {w.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                    <button
                        onClick={crearCajaRapida}
                        disabled={!esAdminEmpresa || loading || !newRegisterName.trim() || (warehouses.length > 1 && !headerWarehouseId)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60"
                    >
                        {loading ? 'Creando…' : 'Crear caja'}
                    </button>
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
                    <div className="shift-pill" title="Turno abierto">
                        <span className="shift-title">Turno abierto</span>
                        <span className="shift-meta">
                            Fondo {currencySymbol}{(Number(currentShift.opening_float) || 0).toFixed(2)}
                        </span>
                        {inventoryConfig.reorderPoint > 0 && (
                            <span className="shift-meta">
                                Minimo stock: {inventoryConfig.reorderPoint}
                            </span>
                        )}
                        <button
                            className="btn sm danger"
                            onClick={() => shiftManagerRef.current?.openCloseModal()}
                        >
                            Cerrar turno
                        </button>
                    </div>
                )}
                <div className="actions top-actions">
                <button className="btn sm" onClick={() => setTicketNotes(prompt('Notas del ticket', ticketNotes) || ticketNotes)}>
                Notas
                </button>
                {canDiscount && (
                <button className="btn sm" onClick={() => setGlobalDiscountPct(parseFloat(prompt('Descuento global (%)', String(globalDiscountPct)) || String(globalDiscountPct)))}>
                Descuento
                </button>
                )}
                {canViewReports && (
                <button className="btn sm" onClick={() => {
                      const url = selectedRegister ? `daily-counts?register_id=${selectedRegister.id}` : 'daily-counts'
                    navigate(url)
                    }}>
                        Reportes diarios
                    </button>
                )}
                <button className="btn sm" onClick={handleHoldTicket}>
                Ticket en espera
                </button>
                    <button className="btn sm" onClick={handleResumeTicket}>
                        Reimprimir
                    </button>
                {canManagePending && (
                <button className="btn sm" onClick={handlePayPending}>
                    Cobrar pendientes
                </button>
                )}
                </div>
                <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span className={`badge ${isOnline ? 'ok' : 'off'}`}>
                        {isOnline ? 'Online' : 'Offline'}
                    </span>
                    {pendingCount > 0 && (
                        <button className="badge" onClick={syncNow} title="Sincronizar">
                            ⟳ {pendingCount} pendientes
                        </button>
                    )}
                    {esAdminEmpresa && cashiers.length > 0 && (
                        <select
                            value={selectedCashierId || ''}
                            onChange={(e) => setSelectedCashierId(e.target.value || null)}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            title="Cajero activo"
                        >
                            {!selectedCashierId && <option value="">Cajero…</option>}
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
                            title="Almacén"
                        >
                            <option value="">Almacén…</option>
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
                    <button
                        className="btn sm ghost search-toggle"
                        onClick={() => setSearchExpanded((prev) => !prev)}
                        type="button"
                    >
                        Buscar
                    </button>
                    <input
                        id="search"
                        placeholder="Buscar productos o escanear c??digo (F2)"
                        aria-label="Buscar productos"
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
                        placeholder="Codigo de barras"
                        aria-label="Codigo de barras"
                        style={{ width: 180, borderLeft: '1px solid var(--border)', paddingLeft: 10 }}
                        value={barcodeInput}
                        onChange={(e) => setBarcodeInput(e.target.value)}
                        onKeyDown={handleBarcodeEnter}
                    />
                    <button className="btn sm" onClick={() => setSearchQuery('')}>
                        Limpiar
                    </button>
                </div>

                {/* View Mode Toggle */}
                <div className="view-toggle">
                    <button
                        className={`btn sm ${viewMode === 'categories' ? 'primary' : ''}`}
                        onClick={() => setViewMode('categories')}
                    >
                        Por categorias
                    </button>
                    <button
                        className={`btn sm ${viewMode === 'all' ? 'primary' : ''}`}
                        onClick={() => setViewMode('all')}
                    >
                        Todos
                    </button>
                </div>

                {/* Categories - solo visible en modo categorias */}
                {viewMode === 'categories' && (
                    <div className="cats" role="tablist" aria-label="Categorias">
                        {categories.map((cat) => (
                            <button
                                key={cat}
                                className={`cat ${selectedCategory === cat ? 'active' : ''}`}
                                onClick={() => setSelectedCategory(cat)}
                            >
                                {cat === '*' ? 'Todo' : cat}
                            </button>
                        ))}
                    </div>
                )}

                {/* Product Grid */}
                <div id="catalog" className="catalog" role="list" aria-label="Catálogo">
                    {filteredProducts.map((p) => (
                        <button
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
                        </button>
                    ))}
                    {filteredProducts.length === 0 && (
                        <div style={{ gridColumn: '1/-1', textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                            No se encontraron productos
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
                                            <button className="btn ghost" title="Descuento línea" onClick={() => setLineDiscount(idx)}>
                                                -%
                                            </button>
                                            <button className="btn ghost" title="Notas" onClick={() => setLineNote(idx)}>
                                                📝
                                            </button>
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
                                    <button aria-label="menos" onClick={() => updateQty(idx, -1)}>
                                        –
                                    </button>
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
                                    <button aria-label="más" onClick={() => updateQty(idx, 1)}>
                                        +
                                    </button>
                                </div>
                                <div className="sum">{lineTotal.toFixed(2)}{currencySymbol}</div>
                                <button className="del" aria-label="Delete" onClick={() => removeItem(idx)}>
                                    ✕
                                </button>
                            </div>
                        )
                    })}
                                    </div>

                {cart.length > 0 && (
                    <div className="pay">
                        <div className="totals">
                        <div>Subtotal</div>
                        <div className="sum">{totals.subtotal.toFixed(2)}{currencySymbol}</div>
                        <div>Descuento</div>
                        <div className="sum">-{(totals.line_discounts + totals.global_discount).toFixed(2)}{currencySymbol}</div>
                        <div>IVA</div>
                        <div className="sum">{totals.tax.toFixed(2)}{currencySymbol}</div>
                        <div className="big">Total</div>
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
                    <button
                        className="btn"
                        onClick={() => {
                            if (confirm('¿Vaciar carrito?')) {
                                setCart([])
                                setGlobalDiscountPct(0)
                                setTicketNotes('')
                            }
                        }}
                    >
                        Borrar todo
                    </button>
                    <button className="btn" onClick={() => setTicketNotes(prompt('Notas del ticket', ticketNotes) || ticketNotes)}>
                        Notas
                    </button>
                </div>
                <div className="actions">
                    <button className="btn primary" onClick={handleCheckout} disabled={cart.length === 0 || !currentShift}>
                        {cart.length > 0 ? `Cobrar ${totals.total.toFixed(2)}${currencySymbol}` : 'Cobrar'}
                    </button>
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
                        <div style={{ fontWeight: 700 }}>Tipo de documento</div>
                        {buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0 && (
                            <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                                Desde {currencySymbol}{buyerPolicy.consumerFinalMaxTotal.toFixed(2)} se requiere factura con datos.
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: 8 }}>
                            <button
                                className={`btn sm ${buyerMode === 'CONSUMER_FINAL' ? 'primary' : ''}`}
                                onClick={() => handleBuyerContinue('CONSUMER_FINAL')}
                                disabled={buyerPolicy.consumerFinalEnabled === false}
                            >
                                Consumidor final
                            </button>
                            <button
                                className={`btn sm ${buyerMode === 'IDENTIFIED' ? 'primary' : ''}`}
                                onClick={() => setBuyerMode('IDENTIFIED')}
                            >
                                Factura / Con datos
                            </button>
                        </div>
                        {buyerMode === 'CONSUMER_FINAL' && !canUseConsumerFinal && (
                            <div style={{ color: '#b91c1c', fontSize: 12 }}>
                                Total supera el limite permitido para consumidor final.
                            </div>
                        )}
                        {buyerMode === 'IDENTIFIED' && (
                            <div style={{ display: 'grid', gap: 8 }}>
                                <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 8 }}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#111827', marginBottom: 6 }}>
                                        Cliente existente
                                    </div>
                                    <input
                                        type="text"
                                        placeholder="Buscar cliente (nombre, RUC, email)"
                                        value={clientQuery}
                                        onChange={(e) => setClientQuery(e.target.value)}
                                    />
                                    {clientsLoading && (
                                        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>Cargando clientes...</div>
                                    )}
                                    {!clientsLoading && filteredClients.length > 0 && (
                                        <div style={{ display: 'grid', gap: 4, marginTop: 6, maxHeight: 160, overflow: 'auto' }}>
                                            {filteredClients.map((c) => (
                                                <button
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
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                    {!clientsLoading && clientQuery && filteredClients.length === 0 && (
                                        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 6 }}>Sin resultados.</div>
                                    )}
                                    {selectedClient && (
                                        <div style={{ marginTop: 8, fontSize: 12, color: '#111827' }}>
                                            Seleccionado: <strong>{selectedClient.name}</strong>
                                            {selectedClient.is_wholesale ? ' (Mayorista)' : ''}
                                            <button
                                                type="button"
                                                className="btn ghost"
                                                style={{ marginLeft: 8 }}
                                                onClick={clearSelectedClient}
                                            >
                                                Quitar
                                            </button>
                                        </div>
                                    )}
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
                            <button className="btn ghost" onClick={() => setShowBuyerModal(false)}>
                                Cancelar
                            </button>
                            <button className="btn primary" onClick={() => handleBuyerContinue()}>
                                Continuar
                            </button>
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
                        alert('Factura generada correctamente')
                    }}
                    onCancel={() => setShowInvoiceModal(false)}
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
                        <div style={{ fontWeight: 700 }}>Crear producto rapido</div>
                        <div style={{ display: 'grid', gap: 10 }}>
                            <label style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>
                                Codigo (SKU)
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
                                Nombre <span style={{ color: '#ef4444' }}>*</span>
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
                                    Ingresa un nombre para continuar.
                                </div>
                            )}
                            <label style={{ fontSize: 12, fontWeight: 700, color: '#111827' }}>
                                Precio <span style={{ color: '#ef4444' }}>*</span>
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
                                    El precio debe ser mayor a 0.
                                </div>
                            )}
                            <label style={{ fontSize: 12, fontWeight: 600, color: '#1f2937' }}>
                                Stock
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
                                IVA (%)
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
                                Categoria (opcional)
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
                            <button
                                className="btn ghost"
                                onClick={() => setShowCreateProductModal(false)}
                                disabled={creatingProduct}
                            >
                                Cancelar
                            </button>
                            <button
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
                                                alert('Producto existente agregado al carrito.')
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
                                                alert('Producto existente agregado al carrito.')
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
                                        alert('No se pudo crear el producto')
                                    } finally {
                                        setCreatingProduct(false)
                                    }
                                }}
                            >
                                Guardar y agregar
                            </button>
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
                            <div style={{ fontWeight: 700 }}>Vista previa del ticket</div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <button
                                    className="btn"
                                    onClick={() => {
                                        const win = printFrameRef.current?.contentWindow
                                        if (win) {
                                            const handleAfterPrint = () => {
                                                win.removeEventListener('afterprint', handleAfterPrint)
                                                setShowPrintPreview(false)
                                                setPrintHtml('')
                                                alert('Impresion finalizada')
                                            }
                                            win.addEventListener('afterprint', handleAfterPrint)
                                            win.focus()
                                            win.print()
                                        }
                                    }}
                                >
                                    Imprimir
                                </button>
                                <button
                                    className="btn ghost"
                                    onClick={() => {
                                        setShowPrintPreview(false)
                                        setPrintHtml('')
                                    }}
                                >
                                    Cerrar
                                </button>
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
