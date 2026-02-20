/**
 * POSView - Professional Point of Sale terminal (REFACTORED)
 * Now with keyboard shortcuts, toast notifications, and responsive layout
 */
import React, { useCallback, useState, useEffect, useMemo, useRef } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
    ArrowLeft,
    Clock3,
    Menu,
    NotebookPen,
    Palette,
    Percent,
    PlusCircle,
    Printer,
    SearchCheck,
    ShoppingCart,
    Store,
    UserRound,
    Wifi,
} from 'lucide-react'
import { usePermission } from '../../hooks/usePermission'
import { useDocumentIDTypes } from '../../hooks/useDocumentIDTypes'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import ShiftManager, { type ShiftManagerHandle } from './components/ShiftManager'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import { POSPaymentBar } from './components/POSPaymentBar'
import { POSKeyboardHelp } from './components/POSKeyboardHelp'
import { CatalogSection } from './components/CatalogSection'
import { CartSection } from './components/CartSection'
import { DiscountModal } from './components/DiscountModal'
import { ResumeTicketModal } from './components/ResumeTicketModal'
import { QuickInputModal } from './components/QuickInputModal'
import useOfflineSync from './hooks/useOfflineSync'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { useToast } from '../../shared/toast'
import { useCurrency } from '../../hooks/useCurrency'
import { useAuth } from '../../auth/AuthContext'
import { usePermissions } from '../../contexts/PermissionsContext'
import { POS_DRAFT_KEY } from '../../constants/storage'
import { POS_DEFAULTS } from '../../constants/defaults'
import { listWarehouses, adjustStock, type Warehouse } from '../inventory/services'
import { listUsuarios } from '../users/services'
import type { Usuario } from '../users/types'
import { createCliente as createCustomer, listClientes as listCustomers, type Cliente as Customer } from '../customers/services'
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
import { createProducto as createProduct, listProductos as listProducts, searchProductos as searchProducts, updateProducto as updateProduct, type Producto as Product } from '../products/productsApi'
import { getCompanySettings, getDefaultReorderPoint, getDefaultTaxRate, savePosTheme, shouldCreateInvoice } from '../../services/companySettings'
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

// ID types now loaded from API via useDocumentIDTypes hook
// Removed hardcoded default: ['CEDULA', 'RUC', 'PASSPORT']
type PosTheme = 'corporate-dark' | 'soft-dark' | 'light'
const POS_THEME_KEY = 'POS_THEME'

const normalizePosTheme = (value?: string | null): PosTheme => {
    if (value === 'soft-dark' || value === 'light' || value === 'corporate-dark') return value
    return 'corporate-dark'
}

export default function POSView() {
    const navigate = useNavigate()
    const can = usePermission()
    const { t } = useTranslation(['pos', 'common'])
    const { symbol: currencySymbol } = useCurrency()
    const { token, loading: authLoading, profile } = useAuth()
    const { loading: permissionsLoading } = usePermissions()
    const toast = useToast()
    const isCompanyAdmin = !!(profile?.es_admin_empresa || (profile as any)?.is_company_admin)
    const [registers, setRegisters] = useState<any[]>([])
    const [selectedRegister, setSelectedRegister] = useState<any>(null)
    const [currentShift, setCurrentShift] = useState<any>(null)
    const [products, setProducts] = useState<Product[]>([])
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
    const [showDiscountModal, setShowDiscountModal] = useState(false)
    const [showResumeTicketModal, setShowResumeTicketModal] = useState(false)
    const [quickInputState, setQuickInputState] = useState<{
        open: boolean
        title: string
        value: string
        placeholder?: string
        type?: 'text' | 'number'
        multiline?: boolean
        onConfirm?: (value: string) => void
    }>({ open: false, title: '', value: '', type: 'text' })
    const [autoCreateInvoice, setAutoCreateInvoice] = useState(false)
    const [showCreateProductModal, setShowCreateProductModal] = useState(false)
    const [loading, setLoading] = useState(false)
    const [creatingProduct, setCreatingProduct] = useState(false)
    const [heldTickets, setHeldTickets] = useState<HeldTicket[]>([])
    const [lastPrintJob, setLastPrintJob] = useState<LastPrintJob | null>(null)
    const [showPendingModal, setShowPendingModal] = useState(false)
    const [showPrintPreview, setShowPrintPreview] = useState(false)
    const [printHtml, setPrintHtml] = useState('')
    const [clock, setClock] = useState(() => new Date())
    const [topSettingsOpen, setTopSettingsOpen] = useState(false)
    const [topMoreOpen, setTopMoreOpen] = useState(false)
    const [posTheme, setPosTheme] = useState<PosTheme>(() => {
        try {
            return normalizePosTheme(localStorage.getItem(POS_THEME_KEY))
        } catch {
            return 'corporate-dark'
        }
    })
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
    const [clients, setClients] = useState<Customer[]>([])
    const [clientsLoading, setClientsLoading] = useState(false)
    const [clientsLoadError, setClientsLoadError] = useState<string | null>(null)
    const clientsLoadAttemptedRef = useRef(false)
    const [clientQuery, setClientQuery] = useState('')
    const [selectedClient, setSelectedClient] = useState<Customer | null>(null)
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

    const shiftManagerRef = useRef<ShiftManagerHandle | null>(null)
    const barcodeBufferRef = useRef('')
    const barcodeTimerRef = useRef<number | null>(null)
    const [skipPrint, setSkipPrint] = useState(false)
    const searchInputRef = useRef<HTMLInputElement>(null)
    const createProductNameInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        const timer = window.setInterval(() => setClock(new Date()), 1000)
        return () => window.clearInterval(timer)
    }, [])

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
    const isAdminRole = isCompanyAdmin || roleList.includes('admin') || roleList.includes('owner')
    const canViewReports = hasRoles ? (isAdminRole || roleList.includes('manager')) : true
    const canManagePending = hasRoles ? (isAdminRole || roleList.includes('manager')) : true
    const canDiscount = hasRoles ? (isAdminRole || roleList.includes('supervisor')) : true

    const formatCashierLabel = (u: Usuario) => {
        const name = `${u.first_name || ''} ${u.last_name || ''}`.trim()
        return name || u.username || u.email || (u.id ? `#${String(u.id).slice(0, 8)}` : '')
    }

    const { isOnline, pendingCount, syncNow } = useOfflineSync()
    const dashboardPath = useMemo(() => {
        const slug = (profile as any)?.empresa_slug
        return slug ? `/${slug}` : '/'
    }, [profile])
    // Warehouses (admin users)
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
        if (!isCompanyAdmin) return
            ; (async () => {
                try {
                    const users = await listUsuarios()
                    const actives = users.filter((u) => u.active)
                    setCashiers(actives)
                } catch {
                    // silencioso
                }
            })()
    }, [isCompanyAdmin])

    useEffect(() => {
        if (buyerMode === 'CONSUMER_FINAL') {
            setSelectedClient(null)
            setIsWholesaleCustomer(false)
        }
    }, [buyerMode])

    useEffect(() => {
        setIsWholesaleCustomer(!!selectedClient?.is_wholesale)
    }, [selectedClient])

    // Persist held tickets in localStorage across reloads
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
                    name: draft.selectedCustomerName || draft.buyerName || 'Customer',
                    is_wholesale: !!draft.isWholesaleCustomer,
                } as Customer)
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

    // Sistema de atajos de teclado
    useKeyboardShortcuts({
        onF2: () => {
            searchInputRef.current?.focus()
            setSearchExpanded(true)
        },
        onF4: () => {
            setShowBuyerModal(true)
        },
        onF5: () => {
            setShowResumeTicketModal(true)
        },
        onF6: () => {
            setShowDiscountModal(true)
        },
        onF8: () => {
            handleHoldTicket()
        },
        onF9: () => {
            if (cart.length > 0) handleCheckout()
        },
        onEscape: () => {
            setShowPaymentModal(false)
            setShowBuyerModal(false)
            setShowInvoiceModal(false)
            setShowDiscountModal(false)
            setShowResumeTicketModal(false)
        },
    })

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
            try {
                const hasLocalTheme = !!localStorage.getItem(POS_THEME_KEY)
                if (!hasLocalTheme) {
                    const settingsAny = settings as any
                    const themeFromSettings =
                        settingsAny?.pos_config?.theme ||
                        settingsAny?.settings?.pos_theme ||
                        settingsAny?.ui?.pos_theme ||
                        settingsAny?.branding?.pos_theme
                    const normalized = normalizePosTheme(themeFromSettings)
                    setPosTheme(normalized)
                }
            } catch { }
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
            // Filter out-of-stock products for POS
            const data = await listProducts(true) // hideOutOfStock = true
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
            const data = await listCustomers()
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
            console.error('Could not resolve default warehouse', err)
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

        // In categories view, filter by selected category
        if (viewMode === 'categories' && selectedCategory !== '*') {
            result = result.filter(
                (p) => p.categoria === selectedCategory || (p.product_metadata?.categoria || '') === selectedCategory
            )
        }

        // No ocultar catalogo por stock minimo: el cajero debe poder ver/buscar
        // all products and resolve final pricing at checkout.

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
    }, [products, selectedCategory, searchQuery, viewMode])

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

    const getReorderPoint = (product: Product) => {
        const point = Number(product.product_metadata?.reorder_point ?? inventoryConfig.reorderPoint ?? 0)
        return Number.isFinite(point) ? point : 0
    }

    const violatesStockPolicy = (
        product: Product,
        desiredQty: number,
        opts?: { ignoreReorder?: boolean }
    ) => {
        const stock = Number(product.stock ?? 0)
        const remaining = stock - desiredQty

        if (!inventoryConfig.allowNegative && remaining < 0) {
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
            return {
                unitPrice: cfg.price,
                source: 'wholesale' as const,
                note: t('pos:messages.wholesale', { defaultValue: 'Wholesale' }),
            }
        }

        const threshold = resolveWholesaleThreshold(cfg, packKey)
        if (threshold <= 0) {
            return {
                unitPrice: cfg.price,
                source: 'wholesale' as const,
                note: t('pos:messages.wholesale', { defaultValue: 'Wholesale' }),
            }
        }
        if (qty <= threshold) {
            return { unitPrice: basePrice, source: 'retail' as const }
        }

        const mixedTotal = basePrice * threshold + cfg.price * (qty - threshold)
        const unitPrice = mixedTotal / qty
        return {
            unitPrice,
            source: 'wholesale_mixed' as const,
            note: t('pos:messages.partialWholesaleFrom', {
                threshold: String(threshold),
                defaultValue: 'Partial wholesale from {{threshold}}',
            }),
        }
    }

    const applyPricingToCartItem = (item: CartItem, product: Product, qty: number) => {
        const pricing = getPricingForProduct(product, qty)
        return {
            ...item,
            qty,
            price: pricing.unitPrice,
            price_source: pricing.source,
            pricing_note: pricing.note,
        }
    }

    const addToCart = (product: Product, opts?: { ignoreReorder?: boolean }) => {
        const existing = cart.find((item) => item.product_id === product.id)
        let basePrice = Number(product.price ?? 0)
        if ((!Number.isFinite(basePrice) || basePrice <= 0) && existing && existing.price > 0) {
            basePrice = existing.price
        }
        if (!Number.isFinite(basePrice) || basePrice <= 0) {
            openQuickInput({
                title: t('pos:prompts.enterPriceForProduct', {
                    defaultValue: `Price for ${product.name}`,
                    name: product.name,
                }),
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
                    setProducts((prev) =>
                        prev.map((p) => (p.id === product.id ? { ...p, price: enteredPrice } : p))
                    )
                    addToCart(pricedProduct, opts)

                    toast.info(t('pos:messages.priceEnteredForSale', { defaultValue: 'Price applied for this sale' }), {
                        action: {
                            label: t('common:save', { defaultValue: 'Save' }),
                            onClick: async () => {
                                try {
                                    await updateProduct(product.id, { price: enteredPrice })
                                    setProducts((prev) =>
                                        prev.map((p) => (p.id === product.id ? { ...p, price: enteredPrice } : p))
                                    )
                                    toast.success(t('pos:messages.priceSavedInProduct', { defaultValue: 'Price saved on product' }))
                                } catch (error) {
                                    console.error('Could not save product price', error)
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

    const handleSelectClient = (client: Customer) => {
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
            const created = await createCustomer({
                name,
                identificacion: idNumber,
                identificacion_tipo: normalizeIdType(buyerIdType, allowedIdTypes) || buyerIdType || undefined,
                email: buyerEmail.trim() || undefined,
                is_wholesale: isWholesaleCustomer || undefined,
            } as any)
            setClients((prev) => [created, ...prev])
            setSelectedClient(created)
        } catch (err) {
            console.error('Could not save customer:', err)
        }
    }

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
                toast.warning(`${t('pos:errors.productNotFound')}: ${code}`, {
                    duration: 0,
                    action: {
                        label: t('common:create', { defaultValue: 'Create' }),
                        onClick: () => {
                            setCreateProductForm({
                                sku: code,
                                name: '',
                                price: 0,
                                stock: 1,
                                iva_tasa: defaultTaxPct,
                                categoria: selectedCategory !== '*' ? selectedCategory : '',
                            })
                            setShowCreateProductModal(true)
                        },
                    },
                })
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

    const { data: documentIdTypes, loading: documentIdTypesLoading } = useDocumentIDTypes()

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
        const sanitized = idTypeOptions
            .map((value) => value.trim())
            .filter((value) => value && value.toUpperCase() !== 'NONE')
        if (sanitized.length > 0) return sanitized
        return apiIdTypeOptions
    }, [idTypeOptions, apiIdTypeOptions])

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
                        toast.warning(`${t('pos:errors.productNotFound')}: ${code}`, {
                            duration: 0,
                            action: {
                                label: t('common:create', { defaultValue: 'Create' }),
                                onClick: () => {
                                    setCreateProductForm({
                                        sku: code,
                                        name: '',
                                        price: 0,
                                        stock: 1,
                                        iva_tasa: defaultTaxPct,
                                        categoria: selectedCategory !== '*' ? selectedCategory : '',
                                    })
                                    setShowCreateProductModal(true)
                                },
                            },
                        })
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
            toast.warning(t('pos:errors.totalExceedsLimit'))
            setBuyerMode('IDENTIFIED')
        }
        if (canUseConsumerFinal) buyerAlertRef.current = false
    }, [buyerMode, canUseConsumerFinal, showBuyerModal])

    useEffect(() => {
        if (showBuyerModal) {
            buyerContinueRef.current = false
        }
    }, [showBuyerModal])

    // Recalculate totals when cart or global discount changes
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
                cashier_id: isCompanyAdmin ? selectedCashierId || undefined : undefined,
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
                toast.error(t('pos:errors.currencyNotConfigured'))
            } else {
                toast.error(t('pos:errors.preparePaymentFailed'))
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
            toast.warning(t('pos:errors.requiresBuyerData'))
            return
        }
        if (mode == 'IDENTIFIED') {
            const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
            if (!normalized) {
                toast.warning(t('pos:errors.selectIdentificationType'))
                return
            }
            if (!buyerIdNumber.trim() || !buyerName.trim()) {
                toast.warning(t('pos:errors.completeIdentification'))
                return
            }
        }
        if (mode == 'IDENTIFIED') {
            await maybeSaveBuyerAsClient()
        }
        setShowBuyerModal(false)
        await startCheckout()
    }

    useEffect(() => {
        if (!showBuyerModal) return
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                e.preventDefault()
                setShowBuyerModal(false)
                return
            }
            if (e.key === 'Enter') {
                const target = e.target as HTMLElement | null
                const tag = target?.tagName?.toLowerCase()
                if (tag === 'textarea') return
                e.preventDefault()
                void handleBuyerContinue()
            }
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [showBuyerModal, handleBuyerContinue])


    const beginCheckout = (opts?: { skipPrint?: boolean }) => {
        if (cart.length === 0) {
            toast.warning(t('pos:errors.emptyCart'))
            return
        }
        if (!currentShift) {
            toast.warning(t('pos:errors.noShiftOpen'))
            return
        }
        setSkipPrint(!!opts?.skipPrint)
        setShowBuyerModal(true)
    }

    const canStartCheckout = () => {
        if (cart.length === 0) {
            toast.warning(t('pos:errors.emptyCart'))
            return false
        }
        if (!currentShift) {
            toast.warning(t('pos:errors.noShiftOpen'))
            return false
        }
        return true
    }

    const handleQuickConsumerFinal = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(false)
        if (!canUseConsumerFinal) {
            setBuyerMode('IDENTIFIED')
            setShowBuyerModal(true)
            toast.warning(t('pos:errors.requiresBuyerData'))
            return
        }
        await handleBuyerContinue('CONSUMER_FINAL')
    }

    const handleQuickNoTicket = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(true)
        if (!canUseConsumerFinal) {
            setBuyerMode('IDENTIFIED')
            setShowBuyerModal(true)
            toast.warning(t('pos:errors.requiresBuyerData'))
            return
        }
        await handleBuyerContinue('CONSUMER_FINAL')
    }

    const handleQuickInvoice = async () => {
        if (!canStartCheckout()) return
        setSkipPrint(false)
        const normalized = normalizeIdType(buyerIdType, allowedIdTypes)
        const hasBuyerData = !!normalized && !!buyerIdNumber.trim() && !!buyerName.trim()
        if (!hasBuyerData) {
            setBuyerMode('IDENTIFIED')
            setShowBuyerModal(true)
            toast.info(
                t('pos:messages.completeBuyerDataQuick', {
                    defaultValue: 'Complete customer data to issue invoice quickly',
                })
            )
            return
        }
        await handleBuyerContinue('IDENTIFIED')
    }

    const handleCheckout = () => beginCheckout({ skipPrint: false })


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
                toast.success(t('pos:messages.invoiceCreation'))
            } else {
                toast.success(t('pos:messages.saleSupervisor'))
            }
        } catch (error: any) {
            if (!isOnline) {
                await addToOutbox({ type: 'receipt', data: { cart, totals } })
                toast.warning(t('pos:errors.offlineSync'))
                setCart([])
                setShowPaymentModal(false)
            } else {
                toast.error(error.response?.data?.detail || t('pos:errors.createTicketFailed'))
            }
        } finally {
            setLoading(false)
        }
    }

    const handleHoldTicket = () => {
        if (cart.length === 0) {
            toast.warning(t('pos:errors.emptyCart'))
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
        toast.success(t('pos:messages.heldTicketInfo', { id }), {
            action: {
                label: t('pos:common.undo'),
                onClick: () => {
                    // Undo: restaurar carrito
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
        if (idx < 0) {
            toast.error(t('pos:errors.idNotFound'))
            return
        }
        const ticket = heldTickets[idx]
        setHeldTickets([...heldTickets.slice(0, idx), ...heldTickets.slice(idx + 1)])
        setCart(ticket.cart)
        setGlobalDiscountPct(ticket.globalDiscountPct || 0)
        setTicketNotes(ticket.ticketNotes || '')
        setCurrentReceiptId(null)
        setShowResumeTicketModal(false)
        toast.success(t('pos:messages.ticketRecovered', { ticketId }))
    }

    const handleReprintLast = async () => {
        if (!lastPrintJob) {
            toast.info(t('pos:errors.nothingToReprint'))
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
            toast.error(t('pos:errors.reprintFailed'))
        } finally {
            setLoading(false)
        }
    }

    const handlePayPending = async () => {
        if (!currentShift) {
            toast.warning(t('pos:errors.noShiftOpen'))
            return
        }
        setShowPendingModal(true)
    }

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
                    toast.success(t('pos:createProduct.existingAdded'))
                    return
                }
            }
            const created = await createProduct({
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
                        console.error('Could not adjust stock', err)
                    }
                }
            }
            const enrichedProduct: Product = {
                ...created,
                stock: stockQty > 0 ? stockQty : Number(created.stock ?? 0),
            }
            setProducts((prev) => [enrichedProduct, ...prev])
            addToCart(enrichedProduct, { ignoreReorder: true })
            setBarcodeInput('')
            setShowCreateProductModal(false)
        } catch (err) {
            toast.error(t('pos:createProduct.creationFailed'))
        } finally {
            setCreatingProduct(false)
        }
    }, [addToCart, createProductForm, resolveWarehouseForStock, selectedCategory, t, toast])

    useEffect(() => {
        if (!showCreateProductModal) return

        const focusTimer = window.setTimeout(() => {
            createProductNameInputRef.current?.focus()
            createProductNameInputRef.current?.select()
        }, 20)

        const onKey = (e: KeyboardEvent) => {
            if (!showCreateProductModal) return
            if (e.key === 'Escape' && !creatingProduct) {
                e.preventDefault()
                setShowCreateProductModal(false)
                return
            }
            if (e.key === 'Enter' && !creatingProduct) {
                const target = e.target as HTMLElement | null
                const tag = target?.tagName?.toLowerCase()
                if (tag === 'textarea') return
                e.preventDefault()
                void handleCreateProductQuickSave()
            }
        }

        window.addEventListener('keydown', onKey)
        return () => {
            window.clearTimeout(focusTimer)
            window.removeEventListener('keydown', onKey)
        }
    }, [showCreateProductModal, creatingProduct, handleCreateProductQuickSave])

    if (authLoading || permissionsLoading) {
        return <div className="center">{t('common:loading', { defaultValue: 'Loading...' })}</div>
    }

    if (!token || !profile) {
        return <Navigate to="/login" replace />
    }

    if (!can('pos:read')) {
        return <PermissionDenied permission="pos:read" />
    }

    if (!selectedRegister) {
        const createRegisterQuickly = async () => {
            try {
                setLoading(true)
                // Try to fetch active warehouses
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
                toast.success(t('pos:register.createdSuccess') + `: ${payload.name}`)
            } catch (e) {
                console.error('Could not create register', e)
                toast.error(t('pos:register.createdError'))
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
                    {!isCompanyAdmin && (
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
                                placeholder={t('pos:register.nameDefault')}
                                disabled={!isCompanyAdmin}
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
                                disabled={!isCompanyAdmin}
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
                        onClick={createRegisterQuickly}
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
        <div className={`${cart.length > 0 ? 'tpv' : 'tpv tpv--no-cart'} tpv--theme-${posTheme}`}>
            {/* Top Bar */}
            <header className="top">
                <div className="brand">
                    <ProtectedButton
                        permission="pos:read"
                        className="btn sm ghost pos-action-btn"
                        unstyled
                        onClick={() => navigate(dashboardPath)}
                        title={t('pos:header.backToDashboard', { defaultValue: 'Back to dashboard' })}
                    >
                        <ArrowLeft size={14} />
                    </ProtectedButton>
                    <div className="brand__logo" aria-hidden="true"></div>
                    <span>POS</span>
                </div>
                <div className={`shift-pill ${currentShift ? 'shift-pill-open' : 'shift-pill-closed'}`} title={currentShift ? t('pos:header.registerOpen', { defaultValue: 'Register open' }) : t('pos:header.registerClosed', { defaultValue: 'Register closed' })}>
                    <span className={`shift-state ${currentShift ? 'is-open' : 'is-closed'}`}>
                        {currentShift ? t('pos:header.open', { defaultValue: 'Open' }) : t('pos:header.closed', { defaultValue: 'Closed' })}
                    </span>
                    <span className="shift-title">{t('pos:header.register', { defaultValue: 'Register' })}</span>
                    <span className="shift-meta shift-amount">
                        {currencySymbol}{(Number(currentShift?.opening_float) || 0).toFixed(2)}
                    </span>
                    <ProtectedButton
                        permission="pos:update"
                        className={`btn sm ${currentShift ? 'danger' : 'primary'} pos-shift-close`}
                        unstyled
                        onClick={() => shiftManagerRef.current?.openCloseModal()}
                        title={currentShift ? t('pos:header.reviewClose', { defaultValue: 'Review close' }) : t('pos:header.openRegister', { defaultValue: 'Open register' })}
                    >
                        {currentShift ? t('pos:header.reviewClose', { defaultValue: 'Review close' }) : t('pos:header.openRegister', { defaultValue: 'Open register' })}
                    </ProtectedButton>
                </div>
                <div className="top-live">
                    <span className={`badge ${isOnline ? 'ok' : 'off'}`}>
                        <Wifi size={12} />
                        {isOnline ? t('pos:header.online') : t('pos:header.offline')}
                    </span>
                    <span className="badge" title={t('pos:header.currentTime', { defaultValue: 'Current time' })}>
                        <Clock3 size={12} />
                        {clock.toLocaleTimeString()}
                    </span>
                    <ProtectedButton
                        permission="pos:read"
                        className="btn sm ghost pos-action-btn"
                        unstyled
                        onClick={() => setTopSettingsOpen((prev) => !prev)}
                    >
                        <Palette size={14} />
                        <span className="pos-action-label">{topSettingsOpen
                            ? t('pos:header.closeSettings', { defaultValue: 'Close settings' })
                            : t('pos:header.settings', { defaultValue: 'Settings' })}</span>
                    </ProtectedButton>
                </div>
                <div className="actions top-actions">
                    <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => setShowBuyerModal(true)} title={t('pos:header.customer', { defaultValue: 'Customer' })}>
                        <UserRound size={14} />
                        <span className="pos-action-label">{t('pos:header.customer', { defaultValue: 'Customer' })}</span>
                    </ProtectedButton>
                    <ProtectedButton
                        permission="pos:update"
                        className="btn sm pos-action-btn"
                        unstyled
                        onClick={() =>
                            openQuickInput({
                                title: t('pos:cart.ticketNotes'),
                                value: ticketNotes,
                                multiline: true,
                                placeholder: t('pos:cart.ticketNotes', { defaultValue: 'Ticket notes' }),
                                onConfirm: (value) => {
                                    setTicketNotes(value)
                                    closeQuickInput()
                                },
                            })
                        }
                        title={t('pos:header.notes')}
                    >
                        <NotebookPen size={14} />
                        <span className="pos-action-label">{t('pos:header.notes')}</span>
                    </ProtectedButton>
                    {canDiscount && (
                         <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => setShowDiscountModal(true)} title={t('pos:header.discount')}>
                             <Percent size={14} />
                             <span className="pos-action-label">{t('pos:header.discountShort', { defaultValue: 'Disc.' })}</span>
                         </ProtectedButton>
                     )}
                    <ProtectedButton
                        permission="pos:update"
                        className="btn sm pos-action-btn"
                        unstyled
                        onClick={() => {
                            setCart([])
                            setGlobalDiscountPct(0)
                            setTicketNotes('')
                            setCurrentReceiptId(null)
                        }}
                        title={t('pos:new', { defaultValue: 'New sale' })}
                    >
                        <PlusCircle size={14} />
                        <span className="pos-action-label">{t('pos:new', { defaultValue: 'New sale' })}</span>
                    </ProtectedButton>
                    <ProtectedButton
                        permission="pos:read"
                        className="btn sm pos-action-btn"
                        unstyled
                        onClick={() => setTopMoreOpen((prev) => !prev)}
                        title={t('pos:header.moreActions', { defaultValue: 'More actions' })}
                    >
                        <Menu size={14} />
                        <span className="pos-action-label">{t('pos:header.more', { defaultValue: 'More' })}</span>
                    </ProtectedButton>
                </div>
                {topMoreOpen && (
                    <div className="top-more-panel">
                        {canViewReports && (
                            <ProtectedButton
                                permission="pos:read"
                                className="btn sm pos-action-btn"
                                unstyled
                                onClick={() => {
                                    const url = selectedRegister ? `daily-counts?register_id=${selectedRegister.id}` : 'daily-counts'
                                    navigate(url)
                                    setTopMoreOpen(false)
                                }}
                            >
                                <SearchCheck size={14} />
                                {t('pos:header.dailyReports')}
                            </ProtectedButton>
                        )}
                        <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { handleHoldTicket(); setTopMoreOpen(false) }}>
                            <ShoppingCart size={14} />
                            {t('pos:header.holdTicket')}
                        </ProtectedButton>
                        <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { setShowResumeTicketModal(true); setTopMoreOpen(false) }}>
                            <Store size={14} />
                            {t('pos:header.resume')}
                        </ProtectedButton>
                        <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { handleReprintLast(); setTopMoreOpen(false) }} title={t("pos:header.reprintTooltip")}>
                            <Printer size={14} />
                            {t('pos:header.reprint')}
                        </ProtectedButton>
                        {canManagePending && (
                            <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => { handlePayPending(); setTopMoreOpen(false) }}>
                                <Clock3 size={14} />
                                {t('pos:header.pendingPayments')}
                            </ProtectedButton>
                        )}
                    </div>
                )}
                {topSettingsOpen && (
                    <div className="top-settings-panel">
                    <select
                        value={posTheme}
                        onChange={async (e) => {
                            const next = normalizePosTheme(e.target.value)
                            setPosTheme(next)
                            try { localStorage.setItem(POS_THEME_KEY, next) } catch { }
                            try {
                                await savePosTheme(next, companySettings)
                                setCompanySettings((prev: any) => ({
                                    ...(prev || {}),
                                    pos_config: {
                                        ...((prev as any)?.pos_config || {}),
                                        theme: next,
                                    },
                                }))
                            } catch (err) {
                                console.error('Could not save POS theme in backend', err)
                                toast.error(t('pos:errors.saveThemeFailed', { defaultValue: 'Could not save theme for this company' }))
                            }
                        }}
                        className="badge"
                        style={{ cursor: 'pointer' }}
                        title={t('pos:header.themeLabel', { defaultValue: 'Visual theme' })}
                    >
                        <option value="corporate-dark">{t('pos:header.themeCorporate', { defaultValue: 'Corporate theme' })}</option>
                        <option value="soft-dark">{t('pos:header.themeSoftDark', { defaultValue: 'Soft dark theme' })}</option>
                        <option value="light">{t('pos:header.themeLight', { defaultValue: 'Light theme' })}</option>
                    </select>
                    <span className="badge ok" title={t('pos:header.printerStatus', { defaultValue: 'Printer status' })}>
                        {typeof window.print === 'function'
                            ? t('pos:header.printerOk', { defaultValue: 'Printer OK' })
                            : t('pos:header.printerUnavailable', { defaultValue: 'Printer N/A' })}
                    </span>
                    {pendingCount > 0 && (
                        <ProtectedButton permission="pos:read" className="badge" unstyled onClick={syncNow} title={t('pos:header.syncing')}>
                            Sync {pendingCount}
                        </ProtectedButton>
                    )}
                    {isCompanyAdmin && cashiers.length > 0 && (
                        <select
                            value={selectedCashierId || ''}
                            onChange={(e) => setSelectedCashierId(e.target.value || null)}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            title={t('pos:header.cashierLabel')}
                        >
                            {!selectedCashierId && <option value="">{t('pos:header.cashierLabel')}...</option>}
                            {cashiers.map((u) => (
                                <option key={u.id} value={u.id}>
                                    {formatCashierLabel(u)}
                                </option>
                            ))}
                        </select>
                    )}
                    {userLabel && <span className="badge">{userLabel}</span>}
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
                    {isCompanyAdmin && warehouses.length > 1 && (
                        <select
                            value={headerWarehouseId || ''}
                            onChange={(e) => setHeaderWarehouseId(e.target.value || null)}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            title={t('pos:header.warehouseLabel')}
                        >
                            <option value="">{t('pos:header.warehouseLabel')}...</option>
                            {warehouses.map((w) => (
                                <option key={w.id} value={w.id}>
                                    {w.code} - {w.name}
                                </option>
                            ))}
                        </select>
                    )}
                    </div>
                )}
            </header>

            {/* ShiftManager & Catalog & Cart */}
            <>
                {/* Shift Manager */}
                <ShiftManager ref={shiftManagerRef} register={selectedRegister} onShiftChange={setCurrentShift} compact />

                {/* Catalog Section */}
                <CatalogSection
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    barcodeInput={barcodeInput}
                    setBarcodeInput={setBarcodeInput}
                    searchExpanded={searchExpanded}
                    setSearchExpanded={setSearchExpanded}
                    selectedCategory={selectedCategory}
                    setSelectedCategory={setSelectedCategory}
                    viewMode={viewMode}
                    setViewMode={setViewMode}
                    filteredProducts={filteredProducts}
                    categories={categories}
                    searchInputRef={searchInputRef}
                    onAddToCart={addToCart}
                    onSearchEnter={handleSearchEnter}
                    onBarcodeEnter={handleBarcodeEnter}
                />

                {/* Cart Section */}
                <CartSection
                    cart={cart}
                    totals={totals}
                    isLoading={loading}
                    onUpdateQty={updateQty}
                    onQtyChange={(idx, newQty) => {
                        const updated = [...cart]
                        const product = products.find((p) => p.id === updated[idx].product_id)
                        if (product) {
                            updated[idx] = applyPricingToCartItem(updated[idx], product, newQty)
                        } else {
                            updated[idx].qty = newQty
                        }
                        setCart(updated)
                    }}
                    onRemoveItem={removeItem}
                    onSetLineDiscount={setLineDiscount}
                    onSetLineNote={setLineNote}
                    onCheckout={handleCheckout}
                    onQuickConsumerFinal={() => { void handleQuickConsumerFinal() }}
                    onQuickInvoice={() => { void handleQuickInvoice() }}
                    onQuickNoTicket={() => { void handleQuickNoTicket() }}
                />

                {/* Bottom Bar */}
                {cart.length > 0 && (
                    <footer className="bottom">
                        <POSPaymentBar
                            subtotal={totals.subtotal}
                            discount={totals.line_discounts + totals.global_discount}
                            tax={totals.tax}
                            cartTotal={totals.total}
                            cartIsEmpty={cart.length === 0 || !currentShift}
                            onPayClick={handleCheckout}
                            isLoading={loading}
                        />
                    </footer>
                )}
            </>

            {/* Modals */}

            {showBuyerModal && (
                <div
                    className="pos-modal-overlay"
                    onClick={() => setShowBuyerModal(false)}
                >
                    <div
                        className="pos-modal-card"
                        style={{ maxWidth: 620, display: 'flex', flexDirection: 'column', gap: 12 }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:buyer.documentType')}</div>
                        {buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0 && (
                            <div className="pos-modal-subtitle">
                                {t('pos:buyer.requiresInvoiceAbove', { amount: currencySymbol + buyerPolicy.consumerFinalMaxTotal.toFixed(2) })}
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: 8 }}>
                            <ProtectedButton
                                permission="pos:create"
                                unstyled
                                onClick={() => handleBuyerContinue('CONSUMER_FINAL')}
                                disabled={buyerPolicy.consumerFinalEnabled === false}
                                style={{
                                    height: 34,
                                    borderRadius: 10,
                                    padding: '0 12px',
                                    border: buyerMode === 'CONSUMER_FINAL' ? 'none' : '1px solid #cbd5e1',
                                    background: buyerMode === 'CONSUMER_FINAL'
                                        ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)'
                                        : '#e2e8f0',
                                    color: buyerMode === 'CONSUMER_FINAL' ? '#fff' : '#1e293b',
                                    fontWeight: 700,
                                }}
                            >
                                {t('pos:buyer.consumerFinal')}
                            </ProtectedButton>
                            <ProtectedButton
                                permission="pos:create"
                                unstyled
                                onClick={() => setBuyerMode('IDENTIFIED')}
                                style={{
                                    height: 34,
                                    borderRadius: 10,
                                    padding: '0 12px',
                                    border: buyerMode === 'IDENTIFIED' ? 'none' : '1px solid #cbd5e1',
                                    background: buyerMode === 'IDENTIFIED'
                                        ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)'
                                        : '#e2e8f0',
                                    color: buyerMode === 'IDENTIFIED' ? '#fff' : '#1e293b',
                                    fontWeight: 700,
                                }}
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
                                <div style={{ border: '1px solid #cbd5e1', borderRadius: 10, padding: 10, background: '#f8fafc' }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>
                                        {t('pos:buyer.existingClient')}
                                    </div>
                                    <input
                                        type="text"
                                        placeholder={t('pos:buyer.search')}
                                        value={clientQuery}
                                        onChange={(e) => setClientQuery(e.target.value)}
                                        className="pos-modal-input"
                                    />
                                    {clientsLoading && (
                                        <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>{t('common:loading')}</div>
                                    )}
                                    {!clientsLoading && clientsLoadError && (
                                        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                                            <div style={{ fontSize: 12, color: '#b91c1c' }}>{clientsLoadError}</div>
                                            <ProtectedButton
                                                permission="pos:read"
                                                type="button"
                                                unstyled
                                                style={{ height: 32, borderRadius: 8, border: '1px solid #cbd5e1', background: '#e2e8f0', color: '#1e293b', fontWeight: 700 }}
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
                                                    unstyled
                                                    style={{
                                                        display: 'flex',
                                                        width: '100%',
                                                        justifyContent: 'space-between',
                                                        alignItems: 'center',
                                                        border: '1px solid #cbd5e1',
                                                        background: '#ffffff',
                                                        color: '#0f172a',
                                                        borderRadius: 8,
                                                        padding: '8px 10px',
                                                    }}
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
                                                unstyled
                                                style={{
                                                    marginLeft: 8,
                                                    height: 30,
                                                    borderRadius: 8,
                                                    border: '1px solid #cbd5e1',
                                                    background: '#e2e8f0',
                                                    color: '#1e293b',
                                                    padding: '0 10px',
                                                    fontWeight: 700,
                                                }}
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
                                    <div className="pos-modal-label">{t('pos:print.format')}</div>
                                    <select
                                        value={docPrintFormat}
                                        onChange={(e) => setDocPrintFormat(e.target.value as any)}
                                        className="pos-modal-select"
                                    >
                                        <option value="THERMAL_80MM">{t('pos:print.receipt80mm', { defaultValue: 'Receipt (80mm)' })}</option>
                                        <option value="A4_PDF">{t('pos:print.a4Paper', { defaultValue: 'A4 Paper' })}</option>
                                    </select>
                                </div>
                                <select
                                    value={buyerIdType}
                                    onChange={(e) => setBuyerIdType(e.target.value)}
                                    className="pos-modal-select"
                                    disabled={documentIdTypesLoading}
                                >
                                    {allowedIdTypes.length === 0 && (
                                        <option value="" disabled>
                                            {documentIdTypesLoading
                                                ? t('common:loading', { defaultValue: 'Loading...' })
                                                : t('pos:buyer.noDocumentTypes', { defaultValue: 'No document types available' })}
                                        </option>
                                    )}
                                    {allowedIdTypes.map((opt) => (
                                        <option key={opt} value={opt}>
                                            {opt}
                                        </option>
                                    ))}
                                </select>
                                <input
                                    type="text"
                                    placeholder={t('pos:buyer.identification', { defaultValue: 'Identification' })}
                                    value={buyerIdNumber}
                                    onChange={(e) => setBuyerIdNumber(e.target.value)}
                                    className="pos-modal-input"
                                />
                                <input
                                    type="text"
                                    placeholder={t('pos:buyer.name', { defaultValue: 'Name' })}
                                    value={buyerName}
                                    onChange={(e) => setBuyerName(e.target.value)}
                                    className="pos-modal-input"
                                />
                                <input
                                    type="email"
                                    placeholder={t('pos:buyer.email', { defaultValue: 'Email (optional)' })}
                                    value={buyerEmail}
                                    onChange={(e) => setBuyerEmail(e.target.value)}
                                    className="pos-modal-input"
                                />
                            </div>
                        )}
                        <div className="pos-modal-actions">
                            <ProtectedButton permission="pos:read" className="pos-modal-btn" unstyled onClick={() => setShowBuyerModal(false)}>
                                {t('common:cancel')}
                            </ProtectedButton>
                            <ProtectedButton permission="pos:update" className="pos-modal-btn primary" unstyled onClick={() => handleBuyerContinue()}>
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
                        toast.success(t('pos:errors.invoiceGeneratedSuccess'))
                    }}
                    onCancel={() => {
                        setShowInvoiceModal(false)
                        setAutoCreateInvoice(false)
                    }}
                />
            )}

            {showCreateProductModal && (
                <div
                    className="pos-modal-overlay"
                    onClick={() => !creatingProduct && setShowCreateProductModal(false)}
                >
                    <div
                        className="pos-modal-card"
                        style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ fontWeight: 800, fontSize: 20, color: '#0f172a' }}>
                                {t('pos:createProduct.title', { defaultValue: 'Create product quickly' })}
                            </div>
                            <div style={{ fontSize: 12, color: '#475569' }}>
                                {t('pos:createProduct.description', { defaultValue: 'Complete the required fields to save and add to cart.' })}
                            </div>
                        </div>
                        <div style={{ display: 'grid', gap: 10 }}>
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>
                                {t('pos:createProduct.sku')}
                            </label>
                            <input
                                type="text"
                                style={{
                                    border: '1px solid #cbd5e1',
                                    padding: '10px 12px',
                                    borderRadius: 10,
                                    outline: 'none',
                                    fontSize: 18,
                                    fontWeight: 600,
                                    color: '#334155',
                                    background: '#fff',
                                }}
                                value={createProductForm.sku}
                                placeholder={t('pos:createProduct.skuPlaceholder', { defaultValue: 'Product code' })}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({ ...prev, sku: e.target.value }))
                                }
                            />
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>
                                {t('pos:createProduct.name')} <span style={{ color: '#dc2626' }}>*</span>
                            </label>
                            <input
                                type="text"
                                ref={createProductNameInputRef}
                                style={{
                                    border: '2px solid #2563eb',
                                    padding: '10px 12px',
                                    borderRadius: 10,
                                    outline: 'none',
                                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.12)',
                                    fontSize: 20,
                                    fontWeight: 700,
                                    color: '#0f172a',
                                    background: '#fff',
                                }}
                                value={createProductForm.name}
                                placeholder={t('pos:createProduct.namePlaceholder', { defaultValue: 'Product name' })}
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({ ...prev, name: e.target.value }))
                                }
                            />
                            {!createProductForm.name.trim() && (
                                <div style={{ fontSize: 12, color: '#b91c1c' }}>
                                    {t('pos:createProduct.nameRequired')}
                                </div>
                            )}
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>
                                {t('pos:createProduct.price')} <span style={{ color: '#dc2626' }}>*</span>
                            </label>
                            <input
                                type="number"
                                style={{
                                    border: '2px solid #2563eb',
                                    padding: '10px 12px',
                                    borderRadius: 10,
                                    outline: 'none',
                                    boxShadow: '0 0 0 2px rgba(37, 99, 235, 0.08)',
                                    fontSize: 26,
                                    fontWeight: 800,
                                    color: '#0f172a',
                                    background: '#fff',
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
                                <div style={{ fontSize: 12, color: '#b91c1c' }}>
                                    {t('pos:createProduct.priceMinimum')}
                                </div>
                            )}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 10 }}>
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>
                                        {t('pos:createProduct.stock')}
                                    </label>
                                    <input
                                        type="number"
                                        style={{
                                            border: '1px solid #cbd5e1',
                                            padding: '10px 12px',
                                            borderRadius: 10,
                                            fontSize: 16,
                                            fontWeight: 600,
                                            color: '#0f172a',
                                            background: '#fff',
                                        }}
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
                                </div>
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>
                                        {t('pos:createProduct.tax')}
                                    </label>
                                    <input
                                        type="number"
                                        style={{
                                            border: '1px solid #cbd5e1',
                                            padding: '10px 12px',
                                            borderRadius: 10,
                                            fontSize: 16,
                                            fontWeight: 600,
                                            color: '#0f172a',
                                            background: '#fff',
                                        }}
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
                                </div>
                            </div>
                            <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>
                                {t('pos:createProduct.category')}
                            </label>
                            <input
                                type="text"
                                style={{
                                    border: '1px solid #cbd5e1',
                                    padding: '10px 12px',
                                    borderRadius: 10,
                                    fontSize: 15,
                                    color: '#0f172a',
                                    background: '#fff',
                                }}
                                value={createProductForm.categoria}
                                placeholder="Opcional"
                                onChange={(e) =>
                                    setCreateProductForm((prev) => ({
                                        ...prev,
                                        categoria: e.target.value,
                                    }))
                                }
                            />
                        </div>
                        <div className="pos-modal-actions">
                            <ProtectedButton
                                permission="pos:read"
                                unstyled
                                onClick={() => setShowCreateProductModal(false)}
                                disabled={creatingProduct}
                                style={{
                                    minWidth: 108,
                                    height: 42,
                                    borderRadius: 10,
                                    border: '1px solid #94a3b8',
                                    background: '#e2e8f0',
                                    color: '#1e293b',
                                    fontWeight: 700,
                                    fontSize: 15,
                                }}
                            >
                                {t('common:cancel')}
                            </ProtectedButton>
                            <ProtectedButton
                                permission="pos:create"
                                unstyled
                                disabled={
                                    creatingProduct ||
                                    !createProductForm.name.trim() ||
                                    Number(createProductForm.price) <= 0
                                }
                                style={{
                                    minWidth: 170,
                                    height: 42,
                                    borderRadius: 10,
                                    border: 'none',
                                    background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                                    color: '#fff',
                                    fontWeight: 800,
                                    fontSize: 15,
                                    boxShadow: '0 8px 18px rgba(37, 99, 235, 0.35)',
                                }}
                                onClick={() => void handleCreateProductQuickSave()}
                            >
                                {t('common:saveAndAdd')}
                            </ProtectedButton>
                        </div>
                    </div>
                </div>
            )}


            {showPrintPreview && (
                <div
                    className="pos-modal-overlay"
                    onClick={() => {
                        setShowPrintPreview(false)
                        setPrintHtml('')
                    }}
                >
                    <div
                        className="pos-modal-card lg"
                        style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:print.preview')}</div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <ProtectedButton
                                    permission="pos:read"
                                    unstyled
                                    className="pos-modal-btn primary"
                                    onClick={() => {
                                        const win = printFrameRef.current?.contentWindow
                                        if (win) {
                                            const handleAfterPrint = () => {
                                                win.removeEventListener('afterprint', handleAfterPrint)
                                                setShowPrintPreview(false)
                                                setPrintHtml('')
                                                toast.success(t('pos:errors.printingFinished'))
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
                                    unstyled
                                    className="pos-modal-btn"
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
            <POSKeyboardHelp />
            <PendingReceiptsModal
                isOpen={showPendingModal}
                shiftId={currentShift?.id || undefined}
                onClose={() => setShowPendingModal(false)}
                canManage={isCompanyAdmin}
                onPaid={() => {
                    // Hook to refresh data if needed
                }}
            />

            {/* Discount Modal (New) */}
            <DiscountModal
                isOpen={showDiscountModal}
                currentValue={globalDiscountPct}
                onConfirm={(value) => {
                    setGlobalDiscountPct(value)
                    setShowDiscountModal(false)
                }}
                onCancel={() => setShowDiscountModal(false)}
            />

            {/* Resume Ticket Modal (New) */}
            <ResumeTicketModal
                isOpen={showResumeTicketModal}
                heldTickets={heldTickets}
                onConfirm={handleResumeTicketConfirm}
                onCancel={() => setShowResumeTicketModal(false)}
            />
            <QuickInputModal
                isOpen={quickInputState.open}
                title={quickInputState.title}
                initialValue={quickInputState.value}
                placeholder={quickInputState.placeholder}
                type={quickInputState.type}
                multiline={quickInputState.multiline}
                onConfirm={(value) => quickInputState.onConfirm?.(value)}
                onCancel={closeQuickInput}
            />
        </div>
    )
}
