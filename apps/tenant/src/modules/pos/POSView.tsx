/**
 * POSView — Terminal de punto de venta.
 *
 * Este componente actúa como orquestador de layout:
 *  - usePOSState  → todo el estado (useState / useRef / persistencia localStorage)
 *  - usePOSActions → toda la lógica de negocio (checkout, carrito, carga de datos…)
 *
 * Aquí solo viven: el JSX, guards de autenticación/permisos y la pantalla
 * de creación de caja cuando no hay registro seleccionado.
 */
import React, { useMemo } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
    ArrowLeft,
    Clock3,
    FileText,
    Menu,
    NotebookPen,
    Palette,
    Percent,
    PlusCircle,
    Printer,
    SearchCheck,
    ShoppingCart,
    Store,
    Trash2,
    UserRound,
    Wifi,
} from 'lucide-react'
import { usePermission } from '../../hooks/usePermission'
import { useDocumentIDTypes } from '../../hooks/useDocumentIDTypes'
import PermissionDenied from '../../components/PermissionDenied'
import ProtectedButton from '../../components/ProtectedButton'
import ShiftManager from './components/ShiftManager'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import { POSPaymentBar } from './components/POSPaymentBar'
import { POSKeyboardHelp } from './components/POSKeyboardHelp'
import { CatalogSection } from './components/CatalogSection'
import { CartSection } from './components/CartSection'
import { DiscountModal } from './components/DiscountModal'
import { ResumeTicketModal } from './components/ResumeTicketModal'
import { WasteModal } from './components/WasteModal'
import { QuickInputModal } from './components/QuickInputModal'
import PendingReceiptsModal from './components/PendingReceiptsModal'
import useOfflineSync from './hooks/useOfflineSync'
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'
import { useToast } from '../../shared/toast'
import { useCurrency } from '../../hooks/useCurrency'
import { useAuth } from '../../auth/AuthContext'
import { usePermissions } from '../../contexts/PermissionsContext'
import { savePosTheme } from '../../services/companySettings'
import { listWarehouses } from '../inventory/services'
import { createRegister } from './services'
import { POS_DEFAULTS } from '../../constants/defaults'
import { normalizePosTheme, POS_THEME_KEY, usePOSState } from './hooks/usePOSState'
import { usePOSActions } from './hooks/usePOSActions'
import './pos-styles.css'

export default function POSView() {
    const navigate = useNavigate()
    const can = usePermission()
    const { t } = useTranslation(['pos', 'common'])
    const { symbol: currencySymbol } = useCurrency()
    const { token, loading: authLoading, profile } = useAuth()
    const { loading: permissionsLoading } = usePermissions()
    const toast = useToast()
    const { isOnline, pendingCount, syncNow } = useOfflineSync()
    const { loading: documentIdTypesLoading } = useDocumentIDTypes()

    const isCompanyAdmin = !!(profile?.es_admin_empresa || (profile as any)?.is_company_admin)

    // -----------------------------------------------------------------------
    // Estado centralizado y acciones de negocio
    // -----------------------------------------------------------------------
    const state = usePOSState()
    const actions = usePOSActions(state, isCompanyAdmin)

    const {
        registers, selectedRegister, setSelectedRegister,
        currentShift, setCurrentShift,
        cart, setCart, globalDiscountPct, setGlobalDiscountPct,
        ticketNotes, setTicketNotes, currentReceiptId, setCurrentReceiptId,
        heldTickets, searchQuery, setSearchQuery,
        barcodeInput, setBarcodeInput, searchExpanded, setSearchExpanded,
        selectedCategory, setSelectedCategory, viewMode, setViewMode,
        filteredProducts, categories,
        buyerMode, setBuyerMode, buyerIdType, setBuyerIdType,
        buyerIdNumber, setBuyerIdNumber, buyerName, setBuyerName,
        buyerEmail, setBuyerEmail, isWholesaleCustomer,
        clients, clientsLoading, clientsLoadError, filteredClients,
        clientQuery, setClientQuery, selectedClient, clientsLoadAttemptedRef,
        saveBuyerAsClient, setSaveBuyerAsClient,
        showPaymentModal, setShowPaymentModal,
        showBuyerModal, setShowBuyerModal,
        showInvoiceModal, setShowInvoiceModal,
        showDiscountModal, setShowDiscountModal,
        showResumeTicketModal, setShowResumeTicketModal,
        showCreateProductModal, setShowCreateProductModal,
        showPendingModal, setShowPendingModal,
        showWasteModal, setShowWasteModal,
        showPrintPreview, setShowPrintPreview,
        quickInputState,
        printHtml, setPrintHtml, docPrintFormat, setDocPrintFormat,
        companySettings, setCompanySettings,
        autoCreateInvoice, setAutoCreateInvoice,
        posTheme, setPosTheme,
        cashiers, selectedCashierId, setSelectedCashierId,
        newRegisterName, setNewRegisterName,
        newRegisterCode, setNewRegisterCode,
        warehouses, setWarehouses, headerWarehouseId, setHeaderWarehouseId,
        loading, creatingProduct, createProductForm, setCreateProductForm,
        clock, topSettingsOpen, setTopSettingsOpen, topMoreOpen, setTopMoreOpen,
        printFrameRef, shiftManagerRef, createProductNameInputRef,
    } = state

    const {
        totals, allowedIdTypes, buyerPolicy, canUseConsumerFinal,
        addToCart, updateQty, removeItem, setLineDiscount, setLineNote,
        openQuickInput, closeQuickInput, applyPricingToCartItem,
        handleSelectClient, clearSelectedClient, loadClients,
        handleBuyerContinue, beginCheckout, handleCheckout,
        handleQuickConsumerFinal, handleQuickNoTicket, handleQuickInvoice,
        handlePaymentSuccess, handlePaymentCancel, handleHoldTicket, handleResumeTicketConfirm,
        handleReprintLast, handlePrintQuote, handleExpressCash, handlePayPending, handleWasteAdjust, handleCreateProductQuickSave,
        loadRegisters,
    } = actions

    // -----------------------------------------------------------------------
    // Derived (perfil / roles)
    // -----------------------------------------------------------------------
    const userLabel = useMemo(() => {
        if (!profile) return ''
        const anyProf = profile as any
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

    const dashboardPath = useMemo(() => {
        const slug = (profile as any)?.empresa_slug
        return slug ? `/${slug}` : '/'
    }, [profile])

    const formatCashierLabel = (u: any) => {
        const name = `${u.first_name || ''} ${u.last_name || ''}`.trim()
        return name || u.username || u.email || (u.id ? `#${String(u.id).slice(0, 8)}` : '')
    }

    // -----------------------------------------------------------------------
    // Atajos de teclado
    // -----------------------------------------------------------------------
    useKeyboardShortcuts({
        onF2: () => { state.searchInputRef.current?.focus(); setSearchExpanded(true) },
        onF4: () => setShowBuyerModal(true),
        onF5: () => setShowResumeTicketModal(true),
        onF6: () => setShowDiscountModal(true),
        onF7: () => { if (cart.length > 0) handlePrintQuote() },
        onF8: () => handleHoldTicket(),
        onF9: () => { if (cart.length > 0) handleCheckout() },
        onF10: () => { if (cart.length > 0) void handleExpressCash({ printTicket: false }) },
        onF11: () => { if (cart.length > 0) void handleExpressCash({ printTicket: true }) },
        onEscape: () => {
            setShowPaymentModal(false)
            setShowBuyerModal(false)
            setShowInvoiceModal(false)
            setShowDiscountModal(false)
            setShowResumeTicketModal(false)
        },
    })

    // -----------------------------------------------------------------------
    // Guards
    // -----------------------------------------------------------------------
    if (authLoading || permissionsLoading) {
        return <div className="center">{t('common:loading', { defaultValue: 'Loading...' })}</div>
    }
    if (!token || !profile) return <Navigate to="/login" replace />
    if (!can('pos:read')) return <PermissionDenied permission="pos:read" />

    // -----------------------------------------------------------------------
    // Pantalla de registro vacío
    // -----------------------------------------------------------------------
    if (!selectedRegister) {
        const createRegisterQuickly = async () => {
            try {
                state.setLoading(true)
                let ws = warehouses
                if (!ws || ws.length === 0) {
                    try { ws = (await listWarehouses()).filter((w) => w.is_active); setWarehouses(ws) } catch { }
                }
                const wh = ws && ws.length > 0 ? ws[0] : null
                const payload: any = { code: (newRegisterCode || '').trim() || undefined, name: (newRegisterName || '').trim() }
                const chosenId = headerWarehouseId || (ws && ws.length === 1 ? wh?.id : null)
                if (chosenId) payload.default_warehouse_id = chosenId
                const reg = await createRegister(payload)
                await loadRegisters()
                setSelectedRegister(reg)
                toast.success(t('pos:register.createdSuccess') + `: ${payload.name}`)
            } catch {
                toast.error(t('pos:register.createdError'))
            } finally {
                state.setLoading(false)
            }
        }

        return (
            <div className="p-6">
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold mb-2">{t('pos:register.noRegisters')}</h2>
                    <p className="text-sm text-gray-600 mb-4">{t('pos:register.createDefault')}</p>
                    {!isCompanyAdmin && <p className="text-sm text-amber-700 mb-4">{t('pos:register.adminOnly')}</p>}
                    <div className="mb-4 grid gap-3">
                        <div>
                            <label className="block text-sm font-medium mb-1">{t('pos:register.nameLabel')}</label>
                            <input value={newRegisterName} onChange={(e) => setNewRegisterName(e.target.value)} className="border rounded px-3 py-2 w-full" placeholder={t('pos:register.nameDefault')} disabled={!isCompanyAdmin} required />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-1">{t('pos:register.codeLabel')}</label>
                            <input value={newRegisterCode} onChange={(e) => setNewRegisterCode(e.target.value)} className="border rounded px-3 py-2 w-full" placeholder={t('pos:register.codeDefault')} disabled={!isCompanyAdmin} />
                        </div>
                    </div>
                    {warehouses.length > 1 && (
                        <div className="mb-4">
                            <label className="block text-sm font-medium mb-1">{t('pos:register.warehouseLabel')}</label>
                            <select value={headerWarehouseId || ''} onChange={(e) => setHeaderWarehouseId(e.target.value || null)} className="border rounded px-3 py-2">
                                <option value="">{t('pos:register.choose')}</option>
                                {warehouses.map((w) => <option key={w.id} value={w.id}>{w.code} - {w.name}</option>)}
                            </select>
                        </div>
                    )}
                    <ProtectedButton permission="pos:create" onClick={createRegisterQuickly} disabled={loading || !newRegisterName.trim() || (warehouses.length > 1 && !headerWarehouseId)} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60">
                        {loading ? t('pos:register.creating') : t('pos:register.buttonLabel')}
                    </ProtectedButton>
                </div>
            </div>
        )
    }

    // -----------------------------------------------------------------------
    // Layout principal
    // -----------------------------------------------------------------------
    return (
        <div className={`${cart.length > 0 ? 'tpv' : 'tpv tpv--no-cart'} tpv--theme-${posTheme}`}>

            {/* ---- Top Bar ---- */}
            <header className="top">
                <div className="brand">
                    <ProtectedButton permission="pos:read" className="btn sm ghost pos-action-btn" unstyled onClick={() => navigate(dashboardPath)} title={t('pos:header.backToDashboard', { defaultValue: 'Back to dashboard' })}>
                        <ArrowLeft size={14} />
                    </ProtectedButton>
                    <div className="brand__logo" aria-hidden="true" />
                    <span>POS</span>
                </div>

                <div className={`shift-pill ${currentShift ? 'shift-pill-open' : 'shift-pill-closed'}`}>
                    <span className={`shift-state ${currentShift ? 'is-open' : 'is-closed'}`}>
                        {currentShift ? t('pos:header.open', { defaultValue: 'Open' }) : t('pos:header.closed', { defaultValue: 'Closed' })}
                    </span>
                    <span className="shift-title">{t('pos:header.register', { defaultValue: 'Register' })}</span>
                    <span className="shift-meta shift-amount">{currencySymbol}{(Number(currentShift?.opening_float) || 0).toFixed(2)}</span>
                    <ProtectedButton permission="pos:update" className={`btn sm ${currentShift ? 'danger' : 'primary'} pos-shift-close`} unstyled onClick={() => shiftManagerRef.current?.openCloseModal()}>
                        {currentShift ? t('pos:header.reviewClose', { defaultValue: 'Review close' }) : t('pos:header.openRegister', { defaultValue: 'Open register' })}
                    </ProtectedButton>
                </div>

                <div className="top-live">
                    <span className={`badge ${isOnline ? 'ok' : 'off'}`}>
                        <Wifi size={12} />
                        {isOnline ? t('pos:header.online') : t('pos:header.offline')}
                    </span>
                    <span className="badge">
                        <Clock3 size={12} />
                        {clock.toLocaleTimeString()}
                    </span>
                    <ProtectedButton permission="pos:read" className="btn sm ghost pos-action-btn" unstyled onClick={() => setTopSettingsOpen((prev) => !prev)}>
                        <Palette size={14} />
                        <span className="pos-action-label">{topSettingsOpen ? t('pos:header.closeSettings', { defaultValue: 'Close settings' }) : t('pos:header.settings', { defaultValue: 'Settings' })}</span>
                    </ProtectedButton>
                </div>

                <div className="actions top-actions">
                    <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => setShowBuyerModal(true)}>
                        <UserRound size={14} />
                        <span className="pos-action-label">{t('pos:header.customer', { defaultValue: 'Customer' })}</span>
                    </ProtectedButton>
                    <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => openQuickInput({ title: t('pos:cart.ticketNotes'), value: ticketNotes, multiline: true, placeholder: t('pos:cart.ticketNotes', { defaultValue: 'Ticket notes' }), onConfirm: (value) => { setTicketNotes(value); closeQuickInput() } })}>
                        <NotebookPen size={14} />
                        <span className="pos-action-label">{t('pos:header.notes')}</span>
                    </ProtectedButton>
                    {canDiscount && (
                        <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => setShowDiscountModal(true)}>
                            <Percent size={14} />
                            <span className="pos-action-label">{t('pos:header.discountShort', { defaultValue: 'Disc.' })}</span>
                        </ProtectedButton>
                    )}
                    <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => { setCart([]); setGlobalDiscountPct(0); setTicketNotes(''); setCurrentReceiptId(null) }}>
                        <PlusCircle size={14} />
                        <span className="pos-action-label">{t('pos:new', { defaultValue: 'New sale' })}</span>
                    </ProtectedButton>
                    <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => setTopMoreOpen((prev) => !prev)}>
                        <Menu size={14} />
                        <span className="pos-action-label">{t('pos:header.more', { defaultValue: 'More' })}</span>
                    </ProtectedButton>
                </div>

                {topMoreOpen && (
                    <div className="top-more-panel">
                        {canViewReports && (
                            <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { navigate(selectedRegister ? `daily-counts?register_id=${selectedRegister.id}` : 'daily-counts'); setTopMoreOpen(false) }}>
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
                        <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { handlePrintQuote(); setTopMoreOpen(false) }}>
                            <FileText size={14} />
                            {t('pos:header.printQuote')}
                        </ProtectedButton>
                        <ProtectedButton permission="pos:read" className="btn sm pos-action-btn" unstyled onClick={() => { handleReprintLast(); setTopMoreOpen(false) }}>
                            <Printer size={14} />
                            {t('pos:header.reprint')}
                        </ProtectedButton>
                        {canManagePending && (
                            <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => { handlePayPending(); setTopMoreOpen(false) }}>
                                <Clock3 size={14} />
                                {t('pos:header.pendingPayments')}
                            </ProtectedButton>
                        )}
                        <ProtectedButton permission="pos:update" className="btn sm pos-action-btn" unstyled onClick={() => { setShowWasteModal(true); setTopMoreOpen(false) }}>
                            <Trash2 size={14} />
                            {t('pos:waste.menuLabel')}
                        </ProtectedButton>
                    </div>
                )}

                {topSettingsOpen && (
                    <div className="top-settings-panel">
                        <select
                            value={posTheme}
                            className="badge"
                            style={{ cursor: 'pointer' }}
                            onChange={async (e) => {
                                const next = normalizePosTheme(e.target.value)
                                setPosTheme(next)
                                try { localStorage.setItem(POS_THEME_KEY, next) } catch { }
                                try {
                                    await savePosTheme(next, companySettings)
                                    setCompanySettings((prev: any) => ({ ...(prev || {}), pos_config: { ...((prev as any)?.pos_config || {}), theme: next } }))
                                } catch {
                                    toast.error(t('pos:errors.saveThemeFailed', { defaultValue: 'Could not save theme for this company' }))
                                }
                            }}
                        >
                            <option value="corporate-dark">{t('pos:header.themeCorporate', { defaultValue: 'Corporate theme' })}</option>
                            <option value="soft-dark">{t('pos:header.themeSoftDark', { defaultValue: 'Soft dark theme' })}</option>
                            <option value="light">{t('pos:header.themeLight', { defaultValue: 'Light theme' })}</option>
                        </select>
                        <span className="badge ok">{typeof window.print === 'function' ? t('pos:header.printerOk', { defaultValue: 'Printer OK' }) : t('pos:header.printerUnavailable', { defaultValue: 'Printer N/A' })}</span>
                        {pendingCount > 0 && (
                            <ProtectedButton permission="pos:read" className="badge" unstyled onClick={syncNow}>
                                Sync {pendingCount}
                            </ProtectedButton>
                        )}
                        {isCompanyAdmin && cashiers.length > 0 && (
                            <select value={selectedCashierId || ''} onChange={(e) => setSelectedCashierId(e.target.value || null)} className="badge" style={{ cursor: 'pointer' }}>
                                {!selectedCashierId && <option value="">{t('pos:header.cashierLabel')}...</option>}
                                {cashiers.map((u) => <option key={u.id} value={u.id}>{formatCashierLabel(u)}</option>)}
                            </select>
                        )}
                        {userLabel && <span className="badge">{userLabel}</span>}
                        <select value={selectedRegister?.id || ''} onChange={(e) => { const reg = registers.find((r) => r.id === e.target.value); setSelectedRegister(reg || null) }} className="badge" style={{ cursor: 'pointer' }}>
                            {registers.map((reg) => <option key={reg.id} value={reg.id}>{reg.name}</option>)}
                        </select>
                        {isCompanyAdmin && warehouses.length > 1 && (
                            <select value={headerWarehouseId || ''} onChange={(e) => setHeaderWarehouseId(e.target.value || null)} className="badge" style={{ cursor: 'pointer' }}>
                                <option value="">{t('pos:header.warehouseLabel')}...</option>
                                {warehouses.map((w) => <option key={w.id} value={w.id}>{w.code} - {w.name}</option>)}
                            </select>
                        )}
                    </div>
                )}
            </header>

            {/* ---- Shift / Catalog / Cart ---- */}
            <>
                <ShiftManager ref={shiftManagerRef} register={selectedRegister} onShiftChange={setCurrentShift} compact />

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
                    searchInputRef={state.searchInputRef}
                    onAddToCart={addToCart}
                    onSearchEnter={actions.handleSearchEnter}
                    onBarcodeEnter={actions.handleBarcodeEnter}
                />

                <CartSection
                    cart={cart}
                    totals={totals}
                    isLoading={loading}
                    bulkPricingItems={(companySettings?.pos_config as any)?.bulk_pricing_items || []}
                    onUpdateQty={updateQty}
                    onQtyChange={(idx, newQty) => {
                        const updated = [...cart]
                        const product = state.products.find((p) => p.id === updated[idx].product_id)
                        if (product) updated[idx] = applyPricingToCartItem(updated[idx], product, newQty)
                        else updated[idx].qty = newQty
                        setCart(updated)
                    }}
                    onRemoveItem={removeItem}
                    onSetLineDiscount={setLineDiscount}
                    onSetLineNote={setLineNote}
                    onCheckout={handleCheckout}
                    onQuickConsumerFinal={() => { void handleQuickConsumerFinal() }}
                    onQuickInvoice={() => { void handleQuickInvoice() }}
                    onQuickNoTicket={() => { void handleQuickNoTicket() }}
                    onExpressCash={() => { void handleExpressCash({ printTicket: false }) }}
                    onExpressCashPrint={() => { void handleExpressCash({ printTicket: true }) }}
                />

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

            {/* ---- Modals ---- */}

            {/* Buyer / Identificación */}
            {showBuyerModal && (
                <div className="pos-modal-overlay" onClick={() => setShowBuyerModal(false)}>
                    <div className="pos-modal-card" style={{ maxWidth: 620, display: 'flex', flexDirection: 'column', gap: 12 }} onClick={(e) => e.stopPropagation()}>
                        <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:buyer.documentType')}</div>
                        {buyerPolicy.requireBuyerAboveAmount && buyerPolicy.consumerFinalMaxTotal > 0 && (
                            <div className="pos-modal-subtitle">{t('pos:buyer.requiresInvoiceAbove', { amount: currencySymbol + buyerPolicy.consumerFinalMaxTotal.toFixed(2) })}</div>
                        )}
                        <div style={{ display: 'flex', gap: 8 }}>
                            {(['CONSUMER_FINAL', 'IDENTIFIED'] as const).map((mode) => (
                                <ProtectedButton
                                    key={mode}
                                    permission="pos:create"
                                    unstyled
                                    disabled={mode === 'CONSUMER_FINAL' && buyerPolicy.consumerFinalEnabled === false}
                                    onClick={() => mode === 'CONSUMER_FINAL' ? handleBuyerContinue('CONSUMER_FINAL') : setBuyerMode('IDENTIFIED')}
                                    style={{
                                        height: 34, borderRadius: 10, padding: '0 12px',
                                        border: buyerMode === mode ? 'none' : '1px solid #cbd5e1',
                                        background: buyerMode === mode ? 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)' : '#e2e8f0',
                                        color: buyerMode === mode ? '#fff' : '#1e293b',
                                        fontWeight: 700,
                                    }}
                                >
                                    {mode === 'CONSUMER_FINAL' ? t('pos:buyer.consumerFinal') : t('pos:buyer.invoiceWithData')}
                                </ProtectedButton>
                            ))}
                        </div>
                        {buyerMode === 'CONSUMER_FINAL' && !canUseConsumerFinal && (
                            <div style={{ color: '#b91c1c', fontSize: 12 }}>{t('pos:buyer.excedsLimit')}</div>
                        )}
                        {buyerMode === 'IDENTIFIED' && (
                            <div style={{ display: 'grid', gap: 8 }}>
                                <div style={{ border: '1px solid #cbd5e1', borderRadius: 10, padding: 10, background: '#f8fafc' }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>{t('pos:buyer.existingClient')}</div>
                                    <input type="text" placeholder={t('pos:buyer.search')} value={clientQuery} onChange={(e) => setClientQuery(e.target.value)} className="pos-modal-input" />
                                    {clientsLoading && <div style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>{t('common:loading')}</div>}
                                    {!clientsLoading && clientsLoadError && (
                                        <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                                            <div style={{ fontSize: 12, color: '#b91c1c' }}>{clientsLoadError}</div>
                                            <ProtectedButton permission="pos:read" type="button" unstyled style={{ height: 32, borderRadius: 8, border: '1px solid #cbd5e1', background: '#e2e8f0', color: '#1e293b', fontWeight: 700 }} onClick={() => { clientsLoadAttemptedRef.current = false; loadClients() }}>
                                                {t('common:retry')}
                                            </ProtectedButton>
                                        </div>
                                    )}
                                    {!clientsLoading && filteredClients.length > 0 && (
                                        <div style={{ display: 'grid', gap: 4, marginTop: 6, maxHeight: 160, overflow: 'auto' }}>
                                            {filteredClients.map((c) => (
                                                <ProtectedButton key={String(c.id)} permission="pos:read" type="button" unstyled style={{ display: 'flex', width: '100%', justifyContent: 'space-between', alignItems: 'center', border: '1px solid #cbd5e1', background: '#ffffff', color: '#0f172a', borderRadius: 8, padding: '8px 10px' }} onClick={() => handleSelectClient(c)}>
                                                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                        {c.name}
                                                        {c.is_wholesale && <span style={{ fontSize: 10, background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d', borderRadius: 4, padding: '1px 5px', fontWeight: 700 }}>Mayorista</span>}
                                                    </span>
                                                    <span style={{ fontSize: 11, color: '#6b7280' }}>{(c.identificacion || (c as any).tax_id || '').toString()}</span>
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
                                            <ProtectedButton permission="pos:read" type="button" unstyled style={{ marginLeft: 8, height: 30, borderRadius: 8, border: '1px solid #cbd5e1', background: '#e2e8f0', color: '#1e293b', padding: '0 10px', fontWeight: 700 }} onClick={clearSelectedClient}>
                                                {t('common:remove')}
                                            </ProtectedButton>
                                        </div>
                                    )}
                                </div>
                                {!selectedClient && (
                                    <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
                                        <input type="checkbox" checked={saveBuyerAsClient} onChange={(e) => setSaveBuyerAsClient(e.target.checked)} />
                                        {t('pos:buyer.saveForFuture')}
                                    </label>
                                )}
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <div className="pos-modal-label">{t('pos:print.format')}</div>
                                    <select value={docPrintFormat} onChange={(e) => setDocPrintFormat(e.target.value as any)} className="pos-modal-select">
                                        <option value="THERMAL_80MM">{t('pos:print.receipt80mm', { defaultValue: 'Receipt (80mm)' })}</option>
                                        <option value="A4_PDF">{t('pos:print.a4Paper', { defaultValue: 'A4 Paper' })}</option>
                                    </select>
                                </div>
                                <select value={buyerIdType} onChange={(e) => setBuyerIdType(e.target.value)} className="pos-modal-select" disabled={documentIdTypesLoading || !!selectedClient}>
                                    {allowedIdTypes.length === 0 && <option value="" disabled>{documentIdTypesLoading ? t('common:loading', { defaultValue: 'Loading...' }) : t('pos:buyer.noDocumentTypes', { defaultValue: 'No document types available' })}</option>}
                                    {allowedIdTypes.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                                </select>
                                <input type="text" placeholder={t('pos:buyer.identification', { defaultValue: 'Identification' })} value={buyerIdNumber} onChange={(e) => setBuyerIdNumber(e.target.value)} className="pos-modal-input" readOnly={!!selectedClient} style={selectedClient ? { background: '#f1f5f9', color: '#64748b', cursor: 'not-allowed' } : undefined} />
                                <input type="text" placeholder={t('pos:buyer.name', { defaultValue: 'Name' })} value={buyerName} onChange={(e) => setBuyerName(e.target.value)} className="pos-modal-input" readOnly={!!selectedClient} style={selectedClient ? { background: '#f1f5f9', color: '#64748b', cursor: 'not-allowed' } : undefined} />
                                <input type="email" placeholder={t('pos:buyer.email', { defaultValue: 'Email (optional)' })} value={buyerEmail} onChange={(e) => setBuyerEmail(e.target.value)} className="pos-modal-input" readOnly={!!selectedClient} style={selectedClient ? { background: '#f1f5f9', color: '#64748b', cursor: 'not-allowed' } : undefined} />
                            </div>
                        )}
                        <div className="pos-modal-actions">
                            <ProtectedButton permission="pos:read" className="pos-modal-btn" unstyled onClick={() => setShowBuyerModal(false)}>{t('common:cancel')}</ProtectedButton>
                            <ProtectedButton permission="pos:update" className="pos-modal-btn primary" unstyled onClick={() => handleBuyerContinue()}>{t('common:continue')}</ProtectedButton>
                        </div>
                    </div>
                </div>
            )}

            {/* Payment */}
            {showPaymentModal && currentReceiptId && (
                <PaymentModal
                    receiptId={currentReceiptId}
                    totalAmount={totals.total}
                    warehouseId={headerWarehouseId || undefined}
                    onSuccess={handlePaymentSuccess}
                    onCancel={handlePaymentCancel}
                    isWholesaleCustomer={isWholesaleCustomer}
                />
            )}

            {/* Convert to Invoice */}
            {showInvoiceModal && currentReceiptId && (
                <ConvertToInvoiceModal
                    receiptId={currentReceiptId}
                    onSuccess={() => { setShowInvoiceModal(false); setCurrentReceiptId(null); setAutoCreateInvoice(false); toast.success(t('pos:errors.invoiceGeneratedSuccess')) }}
                    onCancel={() => { setShowInvoiceModal(false); setAutoCreateInvoice(false) }}
                />
            )}

            {/* Quick create product */}
            {showCreateProductModal && (
                <div className="pos-modal-overlay" onClick={() => !creatingProduct && setShowCreateProductModal(false)}>
                    <div className="pos-modal-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <div style={{ fontWeight: 800, fontSize: 20, color: '#0f172a' }}>{t('pos:createProduct.title', { defaultValue: 'Create product quickly' })}</div>
                            <div style={{ fontSize: 12, color: '#475569' }}>{t('pos:createProduct.description', { defaultValue: 'Complete the required fields to save and add to cart.' })}</div>
                        </div>
                        <div style={{ display: 'grid', gap: 10 }}>
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>{t('pos:createProduct.sku')}</label>
                            <input type="text" style={{ border: '1px solid #cbd5e1', padding: '10px 12px', borderRadius: 10, fontSize: 18, fontWeight: 600, color: '#334155', background: '#fff' }} value={createProductForm.sku} placeholder={t('pos:createProduct.skuPlaceholder', { defaultValue: 'Product code' })} onChange={(e) => setCreateProductForm((prev) => ({ ...prev, sku: e.target.value }))} />
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>{t('pos:createProduct.name')} <span style={{ color: '#dc2626' }}>*</span></label>
                            <input type="text" ref={createProductNameInputRef} style={{ border: '2px solid #2563eb', padding: '10px 12px', borderRadius: 10, boxShadow: '0 0 0 2px rgba(37,99,235,.12)', fontSize: 20, fontWeight: 700, color: '#0f172a', background: '#fff' }} value={createProductForm.name} placeholder={t('pos:createProduct.namePlaceholder', { defaultValue: 'Product name' })} onChange={(e) => setCreateProductForm((prev) => ({ ...prev, name: e.target.value }))} />
                            {!createProductForm.name.trim() && <div style={{ fontSize: 12, color: '#b91c1c' }}>{t('pos:createProduct.nameRequired')}</div>}
                            <label style={{ fontSize: 14, fontWeight: 700, color: '#1e293b' }}>{t('pos:createProduct.price')} <span style={{ color: '#dc2626' }}>*</span></label>
                            <input type="number" style={{ border: '2px solid #2563eb', padding: '10px 12px', borderRadius: 10, boxShadow: '0 0 0 2px rgba(37,99,235,.08)', fontSize: 26, fontWeight: 800, color: '#0f172a', background: '#fff' }} value={createProductForm.price} onChange={(e) => setCreateProductForm((prev) => ({ ...prev, price: Number(e.target.value) || 0 }))} min={0} step="0.01" />
                            {Number(createProductForm.price) <= 0 && <div style={{ fontSize: 12, color: '#b91c1c' }}>{t('pos:createProduct.priceMinimum')}</div>}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,minmax(0,1fr))', gap: 10 }}>
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>{t('pos:createProduct.stock')}</label>
                                    <input type="number" style={{ border: '1px solid #cbd5e1', padding: '10px 12px', borderRadius: 10, fontSize: 16, fontWeight: 600, color: '#0f172a', background: '#fff' }} value={createProductForm.stock} onChange={(e) => setCreateProductForm((prev) => ({ ...prev, stock: Number(e.target.value) || 0 }))} min={0} step="0.01" />
                                </div>
                                <div style={{ display: 'grid', gap: 6 }}>
                                    <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>{t('pos:createProduct.tax')}</label>
                                    <input type="number" style={{ border: '1px solid #cbd5e1', padding: '10px 12px', borderRadius: 10, fontSize: 16, fontWeight: 600, color: '#0f172a', background: '#fff' }} value={createProductForm.tax_rate} onChange={(e) => setCreateProductForm((prev) => ({ ...prev, tax_rate: Number(e.target.value) || 0 }))} min={0} step="0.01" />
                                </div>
                            </div>
                            <label style={{ fontSize: 13, fontWeight: 700, color: '#334155' }}>{t('pos:createProduct.category')}</label>
                            <input type="text" style={{ border: '1px solid #cbd5e1', padding: '10px 12px', borderRadius: 10, fontSize: 15, color: '#0f172a', background: '#fff' }} value={createProductForm.category} placeholder="Opcional" onChange={(e) => setCreateProductForm((prev) => ({ ...prev, category: e.target.value }))} />
                        </div>
                        <div className="pos-modal-actions">
                            <ProtectedButton permission="pos:read" unstyled disabled={creatingProduct} style={{ minWidth: 108, height: 42, borderRadius: 10, border: '1px solid #94a3b8', background: '#e2e8f0', color: '#1e293b', fontWeight: 700, fontSize: 15 }} onClick={() => setShowCreateProductModal(false)}>{t('common:cancel')}</ProtectedButton>
                            <ProtectedButton permission="pos:create" unstyled disabled={creatingProduct || !createProductForm.name.trim() || Number(createProductForm.price) <= 0} style={{ minWidth: 170, height: 42, borderRadius: 10, border: 'none', background: 'linear-gradient(135deg,#2563eb 0%,#1d4ed8 100%)', color: '#fff', fontWeight: 800, fontSize: 15, boxShadow: '0 8px 18px rgba(37,99,235,.35)' }} onClick={() => void handleCreateProductQuickSave()}>{t('common:saveAndAdd')}</ProtectedButton>
                        </div>
                    </div>
                </div>
            )}

            {/* Print preview */}
            {showPrintPreview && (
                <div className="pos-modal-overlay" onClick={() => { setShowPrintPreview(false); setPrintHtml('') }}>
                    <div className="pos-modal-card lg" style={{ display: 'flex', flexDirection: 'column', gap: 12 }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div className="pos-modal-title" style={{ fontSize: 18 }}>{t('pos:print.preview')}</div>
                            <div style={{ display: 'flex', gap: 8 }}>
                                <ProtectedButton permission="pos:read" unstyled className="pos-modal-btn primary" onClick={() => {
                                    const win = printFrameRef.current?.contentWindow
                                    if (win) {
                                        const onAfter = () => { win.removeEventListener('afterprint', onAfter); setShowPrintPreview(false); setPrintHtml(''); toast.success(t('pos:errors.printingFinished')) }
                                        win.addEventListener('afterprint', onAfter)
                                        win.focus(); win.print()
                                    }
                                }}>{t('common:print')}</ProtectedButton>
                                <ProtectedButton permission="pos:read" unstyled className="pos-modal-btn" onClick={() => { setShowPrintPreview(false); setPrintHtml('') }}>{t('common:close')}</ProtectedButton>
                            </div>
                        </div>
                        <iframe ref={printFrameRef} title="ticket" srcDoc={printHtml} style={{ width: '100%', height: '70vh', border: '1px solid #e5e7eb', borderRadius: 8 }} />
                    </div>
                </div>
            )}

            <POSKeyboardHelp bulkPricingItems={(companySettings?.pos_config as any)?.bulk_pricing_items || []} />

            <PendingReceiptsModal isOpen={showPendingModal} shiftId={currentShift?.id || undefined} onClose={() => setShowPendingModal(false)} canManage={isCompanyAdmin} onPaid={() => { }} />

            <DiscountModal isOpen={showDiscountModal} currentValue={globalDiscountPct} onConfirm={(value) => { setGlobalDiscountPct(value); setShowDiscountModal(false) }} onCancel={() => setShowDiscountModal(false)} />

            <ResumeTicketModal isOpen={showResumeTicketModal} heldTickets={heldTickets} onConfirm={handleResumeTicketConfirm} onCancel={() => setShowResumeTicketModal(false)} />

            <QuickInputModal isOpen={quickInputState.open} title={quickInputState.title} initialValue={quickInputState.value} placeholder={quickInputState.placeholder} type={quickInputState.type} multiline={quickInputState.multiline} onConfirm={(value) => quickInputState.onConfirm?.(value)} onCancel={closeQuickInput} />

            <WasteModal
                isOpen={showWasteModal}
                onCancel={() => setShowWasteModal(false)}
                onConfirm={async (payload) => { setShowWasteModal(false); await handleWasteAdjust(payload) }}
            />
        </div>
    )
}
