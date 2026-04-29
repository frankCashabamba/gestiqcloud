/**
 * usePOSState — Estado centralizado del terminal POS.
 *
 * Extrae todas las declaraciones useState / useRef de POSView y las
 * persistence effects asociadas (localStorage, reloj). Las acciones
 * de negocio (checkout, load, etc.) viven en usePOSActions.
 */
import { useRef, useState, useEffect, useMemo, useCallback } from 'react'
import type { ShiftManagerHandle } from '../components/ShiftManager'
import type { Usuario } from '../../users/types'
import type { Cliente as Customer } from '../../customers/services'
import type { Producto as Product } from '../../products/productsApi'
import type { Warehouse } from '../../inventory/services'
import type { SaleDraft } from '../services'
import type { POSReceiptLine, ReceiptCreateRequest } from '../../../types/pos'
import { POS_DRAFT_KEY } from '../../../constants/storage'
import { POS_DEFAULTS } from '../../../constants/defaults'

// ---------------------------------------------------------------------------
// Tipos públicos
// ---------------------------------------------------------------------------

export type CartItem = {
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

export type HeldTicket = {
    id: string
    cart: CartItem[]
    globalDiscountPct: number
    ticketNotes?: string
}

export type LastPrintJob =
    | { kind: 'document'; documentId: string; format: 'THERMAL_80MM' | 'A4_PDF' }
    | { kind: 'receipt'; receiptId: string; width: '58mm' | '80mm' }

export type PosDraftState = {
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

export type PaymentDraftContext = {
    draftLines: POSReceiptLine[]
    createPayload: Pick<ReceiptCreateRequest, 'register_id' | 'shift_id' | 'cashier_id' | 'customer_id' | 'client_request_id' | 'lines' | 'metadata'>
}

export type PosTheme = 'corporate-dark' | 'soft-dark' | 'light'

export const POS_THEME_KEY = 'POS_THEME'

export const normalizePosTheme = (value?: string | null): PosTheme => {
    if (value === 'soft-dark' || value === 'light' || value === 'corporate-dark') return value
    return 'corporate-dark'
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function usePOSState() {
    // ------------------------------------------------------------------
    // Registers / Shifts
    // ------------------------------------------------------------------
    const [registers, setRegisters] = useState<any[]>([])
    const [selectedRegister, setSelectedRegister] = useState<any>(null)
    const [currentShift, setCurrentShift] = useState<any>(null)

    // ------------------------------------------------------------------
    // Products & Catalog
    // ------------------------------------------------------------------
    const [products, setProducts] = useState<Product[]>([])
    const [defaultTaxPct, setDefaultTaxPct] = useState<number>(0)
    const [searchQuery, setSearchQuery] = useState('')
    const [barcodeInput, setBarcodeInput] = useState('')
    const [searchExpanded, setSearchExpanded] = useState(false)
    const [selectedCategory, setSelectedCategory] = useState<string>('*')
    const [viewMode, setViewMode] = useState<'categories' | 'all'>('categories')
    const [inventoryConfig, setInventoryConfig] = useState<{
        reorderPoint: number
        allowNegative: boolean
    }>({ reorderPoint: 0, allowNegative: false })

    // ------------------------------------------------------------------
    // Cart / Ticket
    // ------------------------------------------------------------------
    const [cart, setCart] = useState<CartItem[]>([])
    const [globalDiscountPct, setGlobalDiscountPct] = useState(0)
    const [ticketNotes, setTicketNotes] = useState('')
    const [currentReceiptId, setCurrentReceiptId] = useState<string | null>(null)
    const [paymentDraftContext, setPaymentDraftContext] = useState<PaymentDraftContext | null>(null)
    const [heldTickets, setHeldTickets] = useState<HeldTicket[]>([])

    // ------------------------------------------------------------------
    // Buyer / Client
    // ------------------------------------------------------------------
    const [buyerMode, setBuyerMode] = useState<'CONSUMER_FINAL' | 'IDENTIFIED'>('CONSUMER_FINAL')
    const [buyerIdType, setBuyerIdType] = useState('')
    const [buyerIdNumber, setBuyerIdNumber] = useState('')
    const [buyerName, setBuyerName] = useState('')
    const [buyerEmail, setBuyerEmail] = useState('')
    const [isWholesaleCustomer, setIsWholesaleCustomer] = useState(false)
    const [clients, setClients] = useState<Customer[]>([])
    const [clientsLoading, setClientsLoading] = useState(false)
    const [clientsLoadError, setClientsLoadError] = useState<string | null>(null)
    const [clientQuery, setClientQuery] = useState('')
    const [selectedClient, setSelectedClient] = useState<Customer | null>(null)
    const [saveBuyerAsClient, setSaveBuyerAsClient] = useState(true)

    // ------------------------------------------------------------------
    // Modals
    // ------------------------------------------------------------------
    const [showPaymentModal, setShowPaymentModal] = useState(false)
    const [showBuyerModal, setShowBuyerModal] = useState(false)
    const [showInvoiceModal, setShowInvoiceModal] = useState(false)
    const [showDiscountModal, setShowDiscountModal] = useState(false)
    const [showResumeTicketModal, setShowResumeTicketModal] = useState(false)
    const [showCreateProductModal, setShowCreateProductModal] = useState(false)
    const [showPendingModal, setShowPendingModal] = useState(false)
    const [showWasteModal, setShowWasteModal] = useState(false)
    const [showPrintPreview, setShowPrintPreview] = useState(false)
    const [quickInputState, setQuickInputState] = useState<{
        open: boolean
        title: string
        value: string
        placeholder?: string
        type?: 'text' | 'number'
        multiline?: boolean
        onConfirm?: (value: string) => void
    }>({ open: false, title: '', value: '', type: 'text' })

    // ------------------------------------------------------------------
    // Print
    // ------------------------------------------------------------------
    const [lastPrintJob, setLastPrintJob] = useState<LastPrintJob | null>(null)
    const [printHtml, setPrintHtml] = useState('')
    const [docPrintFormat, setDocPrintFormat] = useState<'THERMAL_80MM' | 'A4_PDF'>('THERMAL_80MM')
    const [skipPrint, setSkipPrint] = useState(false)

    // ------------------------------------------------------------------
    // Settings & Config
    // ------------------------------------------------------------------
    const [companySettings, setCompanySettings] = useState<any | null>(null)
    const [documentConfig, setDocumentConfig] = useState<any | null>(null)
    const [autoCreateInvoice, setAutoCreateInvoice] = useState(false)
    const [posTheme, setPosTheme] = useState<PosTheme>(() => {
        try {
            return normalizePosTheme(localStorage.getItem(POS_THEME_KEY))
        } catch {
            return 'corporate-dark'
        }
    })

    // ------------------------------------------------------------------
    // Cashiers / Registers setup
    // ------------------------------------------------------------------
    const [cashiers, setCashiers] = useState<Usuario[]>([])
    const [selectedCashierId, setSelectedCashierId] = useState<string | null>(null)
    const [newRegisterName, setNewRegisterName] = useState(POS_DEFAULTS.REGISTER_NAME)
    const [newRegisterCode, setNewRegisterCode] = useState(POS_DEFAULTS.REGISTER_CODE)

    // ------------------------------------------------------------------
    // Warehouses
    // ------------------------------------------------------------------
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [headerWarehouseId, setHeaderWarehouseId] = useState<string | null>(null)

    // ------------------------------------------------------------------
    // UI misc
    // ------------------------------------------------------------------
    const [loading, setLoading] = useState(false)
    const [creatingProduct, setCreatingProduct] = useState(false)
    const [clock, setClock] = useState(() => new Date())
    const [topSettingsOpen, setTopSettingsOpen] = useState(false)
    const [topMoreOpen, setTopMoreOpen] = useState(false)
    const [createProductForm, setCreateProductForm] = useState<{
        sku: string
        name: string
        price: number | string
        stock: number
        tax_rate: number
        category: string
    }>({
        sku: '',
        name: '',
        price: 0,
        stock: 1,
        tax_rate: 0,
        category: '',
    })

    // ------------------------------------------------------------------
    // Refs
    // ------------------------------------------------------------------
    const printFrameRef = useRef<HTMLIFrameElement>(null)
    const clientsLoadAttemptedRef = useRef(false)
    const pendingSaleRef = useRef<SaleDraft | null>(null)
    const buyerAlertRef = useRef(false)
    const buyerContinueRef = useRef(false)
    const shiftManagerRef = useRef<ShiftManagerHandle | null>(null)
    const barcodeBufferRef = useRef('')
    const barcodeTimerRef = useRef<number | null>(null)
    const searchInputRef = useRef<HTMLInputElement>(null)
    const createProductNameInputRef = useRef<HTMLInputElement>(null)

    // ------------------------------------------------------------------
    // Effects: persistencia de estado
    // ------------------------------------------------------------------

    // Reloj
    useEffect(() => {
        const timer = window.setInterval(() => setClock(new Date()), 1000)
        return () => window.clearInterval(timer)
    }, [])

    // Restaurar lastPrintJob desde localStorage al montar
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

    // Restaurar tickets retenidos desde localStorage al montar
    useEffect(() => {
        try {
            const raw = localStorage.getItem('posHeldTickets')
            if (raw) {
                const parsed = JSON.parse(raw)
                if (Array.isArray(parsed)) setHeldTickets(parsed)
            }
        } catch { }
    }, [])

    // Carga el draft del ticket activo desde localStorage hacia React state.
    //
    // IMPORTANTE: localStorage es la única fuente de verdad persistente para el
    // draft del carrito. IndexedDB (storeEntity('receipt', ...)) sólo se usa
    // para encolar mutations offline (recibos creados / pendientes de checkout),
    // no para drafts en edición. Mantenemos React state como fuente de verdad
    // en memoria — todos los useEffect de persistencia espejan React → localStorage.
    const loadDraft = useCallback(() => {
        try {
            const raw = localStorage.getItem(POS_DRAFT_KEY)
            if (!raw) return false
            const draft = JSON.parse(raw) as Partial<PosDraftState>
            if (draft.cart && Array.isArray(draft.cart)) setCart(draft.cart)
            if (typeof draft.globalDiscountPct === 'number') setGlobalDiscountPct(draft.globalDiscountPct)
            if (typeof draft.ticketNotes === 'string') setTicketNotes(draft.ticketNotes)
            if (draft.buyerMode === 'CONSUMER_FINAL' || draft.buyerMode === 'IDENTIFIED') {
                setBuyerMode(draft.buyerMode)
            }
            if (typeof draft.buyerIdType === 'string') setBuyerIdType(draft.buyerIdType)
            if (typeof draft.isWholesaleCustomer === 'boolean') {
                setIsWholesaleCustomer(draft.isWholesaleCustomer)
            }
            if (draft.selectedCustomerId) {
                setSelectedClient({
                    id: draft.selectedCustomerId,
                    name: draft.selectedCustomerName || 'Customer',
                    is_wholesale: !!draft.isWholesaleCustomer,
                } as Customer)
            }
            return true
        } catch {
            // ignorar draft corrupto
            return false
        }
    }, [])

    // Limpia el draft persistido y resetea el carrito en memoria. Se invoca
    // tras un checkout exitoso o cuando el usuario descarta el ticket.
    const clearDraft = useCallback(() => {
        try {
            localStorage.removeItem(POS_DRAFT_KEY)
        } catch { }
        setCart([])
        setGlobalDiscountPct(0)
        setTicketNotes('')
    }, [])

    // Restaurar draft del ticket activo al montar.
    // Se ejecuta antes de cualquier llamada a IndexedDB para evitar que el
    // estado en memoria diverja del draft persistido cuando el usuario vuelve
    // de offline.
    useEffect(() => {
        loadDraft()
    }, [loadDraft])

    // Persistir tickets retenidos
    useEffect(() => {
        try {
            localStorage.setItem('posHeldTickets', JSON.stringify(heldTickets))
        } catch { }
    }, [heldTickets])

    // Persistir draft del ticket activo
    useEffect(() => {
        try {
            const draft: Partial<PosDraftState> = {
                cart,
                globalDiscountPct,
                ticketNotes,
                buyerMode,
                buyerIdType,
                isWholesaleCustomer,
                selectedCustomerId: selectedClient ? String(selectedClient.id) : null,
                // selectedCustomerName omitido: dato personal del comprador, no se persiste en localStorage
            }
            if ((draft.cart?.length || 0) === 0 && !draft.ticketNotes) {
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
        isWholesaleCustomer,
        selectedClient,
    ])

    // Reset cliente cuando buyer vuelve a CONSUMER_FINAL
    useEffect(() => {
        if (buyerMode === 'CONSUMER_FINAL') {
            setSelectedClient(null)
            setIsWholesaleCustomer(false)
        }
    }, [buyerMode])

    // Sincronizar isWholesaleCustomer con el cliente seleccionado
    useEffect(() => {
        setIsWholesaleCustomer(!!selectedClient?.is_wholesale)
    }, [selectedClient])

    // Limpiar estado de búsqueda de clientes al cerrar modal
    useEffect(() => {
        if (showBuyerModal) return
        setClientQuery('')
        setClientsLoadError(null)
        setClients([])
        clientsLoadAttemptedRef.current = false
    }, [showBuyerModal])

    // ------------------------------------------------------------------
    // Derived state
    // ------------------------------------------------------------------

    const categories = useMemo(() => {
        const cats = new Set<string>()
        products.forEach((p) => {
            if (p.category || p.product_metadata?.categoria) {
                cats.add(p.category || (p.product_metadata?.categoria as any))
            }
        })
        return ['*', ...Array.from(cats).sort()]
    }, [products])

    const filteredProducts = useMemo(() => {
        let result = products
        if (viewMode === 'categories' && selectedCategory !== '*') {
            result = result.filter(
                (p) =>
                    p.category === selectedCategory ||
                    (p.product_metadata?.categoria || '') === selectedCategory
            )
        }
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

    // ------------------------------------------------------------------
    // Helpers de persistencia
    // ------------------------------------------------------------------

    const setAndPersistLastPrintJob = (job: LastPrintJob | null) => {
        setLastPrintJob(job)
        try {
            if (!job) localStorage.removeItem('POS_LAST_PRINT_JOB')
            else localStorage.setItem('POS_LAST_PRINT_JOB', JSON.stringify(job))
        } catch { }
    }

    // ------------------------------------------------------------------
    // Return
    // ------------------------------------------------------------------
    return {
        // Registers / Shifts
        registers, setRegisters,
        selectedRegister, setSelectedRegister,
        currentShift, setCurrentShift,

        // Products & Catalog
        products, setProducts,
        defaultTaxPct, setDefaultTaxPct,
        searchQuery, setSearchQuery,
        barcodeInput, setBarcodeInput,
        searchExpanded, setSearchExpanded,
        selectedCategory, setSelectedCategory,
        viewMode, setViewMode,
        inventoryConfig, setInventoryConfig,

        // Cart / Ticket
        cart, setCart,
        globalDiscountPct, setGlobalDiscountPct,
        ticketNotes, setTicketNotes,
        currentReceiptId, setCurrentReceiptId,
        paymentDraftContext, setPaymentDraftContext,
        heldTickets, setHeldTickets,

        // Buyer / Client
        buyerMode, setBuyerMode,
        buyerIdType, setBuyerIdType,
        buyerIdNumber, setBuyerIdNumber,
        buyerName, setBuyerName,
        buyerEmail, setBuyerEmail,
        isWholesaleCustomer, setIsWholesaleCustomer,
        clients, setClients,
        clientsLoading, setClientsLoading,
        clientsLoadError, setClientsLoadError,
        clientQuery, setClientQuery,
        selectedClient, setSelectedClient,
        saveBuyerAsClient, setSaveBuyerAsClient,

        // Modals
        showPaymentModal, setShowPaymentModal,
        showBuyerModal, setShowBuyerModal,
        showInvoiceModal, setShowInvoiceModal,
        showDiscountModal, setShowDiscountModal,
        showResumeTicketModal, setShowResumeTicketModal,
        showCreateProductModal, setShowCreateProductModal,
        showPendingModal, setShowPendingModal,
        showWasteModal, setShowWasteModal,
        showPrintPreview, setShowPrintPreview,
        quickInputState, setQuickInputState,

        // Print
        lastPrintJob, setLastPrintJob,
        setAndPersistLastPrintJob,
        printHtml, setPrintHtml,
        docPrintFormat, setDocPrintFormat,
        skipPrint, setSkipPrint,

        // Settings & Config
        companySettings, setCompanySettings,
        documentConfig, setDocumentConfig,
        autoCreateInvoice, setAutoCreateInvoice,
        posTheme, setPosTheme,

        // Cashiers / Registers setup
        cashiers, setCashiers,
        selectedCashierId, setSelectedCashierId,
        newRegisterName, setNewRegisterName,
        newRegisterCode, setNewRegisterCode,

        // Warehouses
        warehouses, setWarehouses,
        headerWarehouseId, setHeaderWarehouseId,

        // UI misc
        loading, setLoading,
        creatingProduct, setCreatingProduct,
        clock,
        topSettingsOpen, setTopSettingsOpen,
        topMoreOpen, setTopMoreOpen,
        createProductForm, setCreateProductForm,

        // Refs
        printFrameRef,
        clientsLoadAttemptedRef,
        pendingSaleRef,
        buyerAlertRef,
        buyerContinueRef,
        shiftManagerRef,
        barcodeBufferRef,
        barcodeTimerRef,
        searchInputRef,
        createProductNameInputRef,

        // Derived
        categories,
        filteredProducts,
        filteredClients,

        // Draft persistence (localStorage)
        loadDraft,
        clearDraft,
    }
}

export type POSState = ReturnType<typeof usePOSState>
