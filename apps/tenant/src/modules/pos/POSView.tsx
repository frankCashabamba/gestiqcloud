/**
 * POSView - Terminal Punto de Venta Profesional
 * Diseño basado en tpv_pro.html con integración completa backend
 */
import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ShiftManager from './components/ShiftManager'
import PaymentModal from './components/PaymentModal'
import ConvertToInvoiceModal from './components/ConvertToInvoiceModal'
import useOfflineSync from './hooks/useOfflineSync'
import { useCurrency } from '../../hooks/useCurrency'
import { useAuth } from '../../auth/AuthContext'
import { listWarehouses, type Warehouse } from '../inventario/services'
import {
    listRegisters,
    createRegister,
    createReceipt,
    printReceipt,
    addToOutbox,
    calculateReceiptTotals,
    type ReceiptTotals,
} from './services'
import { listProductos, type Producto } from '../productos/services'
import './pos-styles.css'

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
}

export default function POSView() {
    const navigate = useNavigate()
    const { symbol: currencySymbol } = useCurrency()
    const { profile } = useAuth()
    const esAdminEmpresa = !!profile?.es_admin_empresa
    const [registers, setRegisters] = useState<any[]>([])
    const [selectedRegister, setSelectedRegister] = useState<any>(null)
    const [currentShift, setCurrentShift] = useState<any>(null)
    const [products, setProducts] = useState<Producto[]>([])
    const [cart, setCart] = useState<CartItem[]>([])
    const [searchQuery, setSearchQuery] = useState('')
    const [barcodeInput, setBarcodeInput] = useState('')
    const [selectedCategory, setSelectedCategory] = useState<string>('*')
    const [viewMode, setViewMode] = useState<'categories' | 'all'>('categories')
    const [globalDiscountPct, setGlobalDiscountPct] = useState(0)
    const [ticketNotes, setTicketNotes] = useState('')
    const [currentReceiptId, setCurrentReceiptId] = useState<string | null>(null)
    const [showPaymentModal, setShowPaymentModal] = useState(false)
    const [showInvoiceModal, setShowInvoiceModal] = useState(false)
    const [loading, setLoading] = useState(false)

    const userLabel = useMemo(() => {
        if (!profile) return ''
        const anyProf: any = profile as any
        const name = anyProf.username || anyProf.name || anyProf.full_name || anyProf.email
        return name || (profile.user_id ? `#${String(profile.user_id).slice(0, 8)}` : '')
    }, [profile])

    const { isOnline, pendingCount, syncNow } = useOfflineSync()
    // Almacenes (para admins)
    const [warehouses, setWarehouses] = useState<Warehouse[]>([])
    const [headerWarehouseId, setHeaderWarehouseId] = useState<string | null>(null)

    useEffect(() => {
        loadRegisters()
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

    const loadRegisters = async () => {
        try {
            const data = await listRegisters()
            setRegisters(data.filter((r: any) => r.active))
            if (data.length > 0) setSelectedRegister(data[0])
        } catch (error) {
            console.error('Error loading registers:', error)
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

        // En modo categorías, filtrar por categoría seleccionada
        if (viewMode === 'categories' && selectedCategory !== '*') {
            result = result.filter(
                (p) => p.categoria === selectedCategory || (p.product_metadata?.categoria || '') === selectedCategory
            )
        }

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
    }, [products, selectedCategory, searchQuery, viewMode])

    const addToCart = (product: Producto) => {
        const existing = cart.find((item) => item.product_id === product.id)
        if (existing) {
            setCart(
                cart.map((item) =>
                    item.product_id === product.id ? { ...item, qty: item.qty + 1 } : item
                )
            )
        } else {
            const newItem: CartItem = {
                product_id: product.id,
                sku: product.sku || '',
                name: product.name,
                price: product.price || 0,
                // Preservar 0% si el producto lo tiene; solo usar fallback si es null/undefined
                iva_tasa: (product as any).iva_tasa ?? 21,
                qty: 1,
                discount_pct: 0,
                categoria: product.categoria || (product.product_metadata?.categoria as any),
            }
            setCart([...cart, newItem])
        }
    }

    const updateQty = (index: number, delta: number) => {
        setCart(
            cart.map((item, i) =>
                i === index ? { ...item, qty: Math.max(1, item.qty + delta) } : item
            )
        )
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

    const handleBarcodeEnter = (e: React.KeyboardEvent) => {
        if (e.key !== 'Enter') return
        const code = barcodeInput.trim().toLowerCase()
        const product = products.find(
            (p) =>
                (p.sku || '').toLowerCase() === code ||
                (p.product_metadata?.codigo_barras || '').toLowerCase() === code
        )
        if (product) {
            addToCart(product)
            setBarcodeInput('')
        } else {
            alert('Producto no encontrado: ' + code)
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

    const handleCheckout = async () => {
        if (cart.length === 0) {
            alert('No hay líneas en el carrito')
            return
        }
        if (!currentShift) {
            alert('Abre un turno primero')
            return
        }

        try {
            setLoading(true)
            const receiptData = {
                register_id: selectedRegister.id,
                shift_id: currentShift.id,
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

    const handlePaymentSuccess = async () => {
        try {
            setLoading(true)
            // Use existing receipt; do not recreate
            if (!currentReceiptId) {
                setLoading(false)
                return
            }

            // Imprimir automáticamente
            const html = await printReceipt(currentReceiptId, '58mm')
            const printWindow = window.open('', '_blank')
            if (printWindow) {
                printWindow.document.write(html)
                printWindow.document.close()
            }

            // Reset
            setCart([])
            setGlobalDiscountPct(0)
            setTicketNotes('')
            setShowPaymentModal(false)

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
                const payload: any = { code: 'CAJA-1', name: 'Caja Principal' }
                // Si hay más de un almacén y el usuario eligió uno, respétalo
                const chosenId = headerWarehouseId || (ws && ws.length === 1 ? wh?.id : null)
                if (chosenId) payload.default_warehouse_id = chosenId
                const reg = await createRegister(payload)
                await loadRegisters()
                setSelectedRegister(reg)
                alert('Caja creada: CAJA-1')
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
                        disabled={loading || (warehouses.length > 1 && !headerWarehouseId)}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-60"
                    >
                        {loading ? 'Creando…' : 'Crear CAJA-1'}
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="tpv">
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
                <div className="actions">
                <button className="btn sm" onClick={() => setTicketNotes(prompt('Notas del ticket', ticketNotes) || ticketNotes)}>
                Notas
                </button>
                <button className="btn sm" onClick={() => setGlobalDiscountPct(parseFloat(prompt('Descuento global (%)', String(globalDiscountPct)) || String(globalDiscountPct)))}>
                Descuento
                </button>
                <button className="btn sm" onClick={() => {
                      const url = selectedRegister ? `/pos/daily-counts?register_id=${selectedRegister.id}` : '/pos/daily-counts'
                      navigate(url)
                    }}>
                        📊 Reportes Diarios
                    </button>
                <button className="btn sm" onClick={() => alert('Función en desarrollo')}>
                Ticket en espera
                </button>
                    <button className="btn sm" onClick={() => alert('Función en desarrollo')}>
                        Reimprimir
                    </button>
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
                <ShiftManager register={selectedRegister} onShiftChange={setCurrentShift} />

                {/* Search */}
                <div className="search" role="search">
                    <input
                        id="search"
                        placeholder="Buscar productos o escanear código (F2)"
                        aria-label="Buscar productos"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'F2' && e.currentTarget.focus()}
                    />
                    <input
                        id="barcode"
                        placeholder="Código de barras"
                        aria-label="Código de barras"
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
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', padding: '0 4px' }}>
                    <button
                        className={`btn sm ${viewMode === 'categories' ? 'primary' : ''}`}
                        onClick={() => setViewMode('categories')}
                        style={{ flex: 1 }}
                    >
                        📂 Por Categorías
                    </button>
                    <button
                        className={`btn sm ${viewMode === 'all' ? 'primary' : ''}`}
                        onClick={() => setViewMode('all')}
                        style={{ flex: 1 }}
                    >
                        📋 Todos
                    </button>
                </div>

                {/* Categories - solo visible en modo categorías */}
                {viewMode === 'categories' && (
                    <div className="cats" role="tablist" aria-label="Categorías">
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
                                                updated[idx].qty = newQty
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
                    {cart.length === 0 && (
                        <div style={{ textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
                            Carrito vacío
                        </div>
                    )}
                </div>

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

                    <div className="paymodes" role="group" aria-label="Métodos de pago">
                        <button className="btn" onClick={handleCheckout}>
                            Efectivo
                        </button>
                        <button className="btn" onClick={handleCheckout}>
                            Tarjeta
                        </button>
                        <button className="btn" onClick={handleCheckout}>
                            Mixto
                        </button>
                        <button className="btn ghost" onClick={() => alert('Función en desarrollo')}>
                            Abrir cajón
                        </button>
                    </div>
                </div>
            </aside>

            {/* Bottom Bar */}
            <footer className="bottom">
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

            {/* Modals */}
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
        </div>
    )
}
