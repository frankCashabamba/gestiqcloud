# Plan de Cobertura Frontend → Backend
**GestiQCloud MVP - Frontend Implementation Roadmap**

> **Estado**: Backend 95% operativo | Frontend 60% cubierto  
> **Objetivo**: Alcanzar 100% de cobertura frontend sobre endpoints backend

---

## 📊 Resumen Ejecutivo

### Backend Implementado (Ready)
✅ **POS**: 900 líneas - 13 endpoints  
✅ **Payments**: 250 líneas - 4 endpoints  
✅ **E-factura**: 700 líneas - Workers SRI/Facturae  
✅ **Numeración**: 150 líneas - Servicio completo  
✅ **Store Credits**: Migraciones + lógica  

### Frontend Pendiente
🔲 **30 componentes** por implementar  
🔲 **8 vistas** nuevas  
🔲 **15 servicios API** por conectar  

---

## 🎯 Prioridad de Implementación

### Sprint 1 (Alta Prioridad) - 5-7 días
**POS Devoluciones + Store Credits + E-factura Básica**

#### 1. POS - Sistema de Devoluciones
**Ubicación**: `apps/tenant/src/modules/pos/components/`

##### 1.1 RefundModal.tsx
```tsx
/**
 * Modal para devoluciones de tickets POS
 * Conecta con: POST /api/v1/pos/receipts/{id}/refund
 */
import React, { useState } from 'react'
import { refundReceipt } from '../services'
import type { POSReceipt, RefundRequest } from '../../../types/pos'

interface RefundModalProps {
  receipt: POSReceipt
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function RefundModal({ 
  receipt, 
  isOpen, 
  onClose, 
  onSuccess 
}: RefundModalProps) {
  const [refundMethod, setRefundMethod] = useState<'original' | 'cash' | 'store_credit'>('original')
  const [reason, setReason] = useState('')
  const [linesToRefund, setLinesToRefund] = useState<string[]>([]) // line_ids
  const [loading, setLoading] = useState(false)

  const handleRefund = async () => {
    if (!reason.trim()) {
      alert('Debe indicar el motivo de devolución')
      return
    }

    setLoading(true)
    try {
      const payload: RefundRequest = {
        reason,
        refund_method: refundMethod,
        line_ids: linesToRefund.length > 0 ? linesToRefund : undefined,
        restock: true // Opcionar según UI
      }

      await refundReceipt(receipt.id, payload)
      alert('Devolución procesada exitosamente')
      onSuccess()
      onClose()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al procesar devolución')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-4">Devolución - Ticket #{receipt.number}</h2>
        
        {/* Líneas del ticket */}
        <div className="mb-4">
          <h3 className="font-semibold mb-2">Productos a devolver:</h3>
          {receipt.lines.map(line => (
            <label key={line.id} className="flex items-center gap-2 p-2 hover:bg-gray-50">
              <input
                type="checkbox"
                checked={linesToRefund.includes(line.id)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setLinesToRefund([...linesToRefund, line.id])
                  } else {
                    setLinesToRefund(linesToRefund.filter(id => id !== line.id))
                  }
                }}
              />
              <span>{line.product_name} x{line.qty}</span>
              <span className="ml-auto font-semibold">{line.line_total.toFixed(2)} €</span>
            </label>
          ))}
          {linesToRefund.length === 0 && (
            <p className="text-sm text-gray-500 mt-2">
              Si no selecciona productos, se devolverá el ticket completo
            </p>
          )}
        </div>

        {/* Método de reembolso */}
        <div className="mb-4">
          <label className="block font-semibold mb-2">Método de reembolso:</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setRefundMethod('original')}
              className={`px-4 py-2 rounded border-2 ${
                refundMethod === 'original' ? 'border-blue-600 bg-blue-50' : 'border-gray-300'
              }`}
            >
              💳 Método original
            </button>
            <button
              type="button"
              onClick={() => setRefundMethod('cash')}
              className={`px-4 py-2 rounded border-2 ${
                refundMethod === 'cash' ? 'border-green-600 bg-green-50' : 'border-gray-300'
              }`}
            >
              💵 Efectivo
            </button>
            <button
              type="button"
              onClick={() => setRefundMethod('store_credit')}
              className={`px-4 py-2 rounded border-2 ${
                refundMethod === 'store_credit' ? 'border-purple-600 bg-purple-50' : 'border-gray-300'
              }`}
            >
              🎟️ Vale/Crédito
            </button>
          </div>
        </div>

        {/* Motivo */}
        <div className="mb-6">
          <label className="block font-semibold mb-2">Motivo de devolución:</label>
          <textarea
            className="w-full border rounded p-2"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Ej: Producto defectuoso, cliente insatisfecho..."
          />
        </div>

        {/* Botones */}
        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            Cancelar
          </button>
          <button
            onClick={handleRefund}
            disabled={loading || !reason.trim()}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? 'Procesando...' : 'Procesar Devolución'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

**Integración en POSView.tsx**:
```tsx
// Agregar al componente principal
import RefundModal from './components/RefundModal'

// En el estado:
const [refundModalOpen, setRefundModalOpen] = useState(false)
const [selectedReceipt, setSelectedReceipt] = useState<POSReceipt | null>(null)

// Botón en lista de tickets:
<button
  onClick={() => {
    setSelectedReceipt(receipt)
    setRefundModalOpen(true)
  }}
  className="text-red-600 hover:underline"
>
  Devolución
</button>

// Modal:
<RefundModal
  receipt={selectedReceipt}
  isOpen={refundModalOpen}
  onClose={() => setRefundModalOpen(false)}
  onSuccess={() => {
    // Recargar lista de tickets
    loadReceipts()
  }}
/>
```

##### 1.2 StoreCreditsList.tsx
**Ubicación**: `apps/tenant/src/modules/pos/components/StoreCreditsList.tsx`

```tsx
/**
 * Vista de gestión de vales/store credits
 * Conecta con: GET /api/v1/pos/store_credits
 */
import React, { useState, useEffect } from 'react'
import { listStoreCredits, getStoreCreditByCode } from '../services'
import type { StoreCredit } from '../../../types/pos'

export default function StoreCreditsList() {
  const [credits, setCredits] = useState<StoreCredit[]>([])
  const [searchCode, setSearchCode] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCredits()
  }, [])

  const loadCredits = async () => {
    setLoading(true)
    try {
      const data = await listStoreCredits()
      setCredits(data)
    } catch (error) {
      console.error('Error loading store credits:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchCode.trim()) {
      loadCredits()
      return
    }

    setLoading(true)
    try {
      const credit = await getStoreCreditByCode(searchCode)
      setCredits([credit])
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Vale no encontrado')
      setCredits([])
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      redeemed: 'bg-gray-100 text-gray-800',
      expired: 'bg-red-100 text-red-800',
      void: 'bg-orange-100 text-orange-800'
    }
    return colors[status as keyof typeof colors] || 'bg-gray-100'
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Vales y Créditos de Tienda</h1>

      {/* Búsqueda */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Buscar por código..."
          value={searchCode}
          onChange={(e) => setSearchCode(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1 border rounded px-3 py-2"
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Buscar
        </button>
        <button
          onClick={loadCredits}
          className="px-4 py-2 border rounded hover:bg-gray-50"
        >
          Ver todos
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Código</th>
                <th className="border p-2 text-left">Cliente</th>
                <th className="border p-2 text-right">Importe Inicial</th>
                <th className="border p-2 text-right">Restante</th>
                <th className="border p-2 text-center">Moneda</th>
                <th className="border p-2 text-center">Estado</th>
                <th className="border p-2 text-left">Vencimiento</th>
                <th className="border p-2 text-left">Creado</th>
              </tr>
            </thead>
            <tbody>
              {credits.length === 0 ? (
                <tr>
                  <td colSpan={8} className="border p-4 text-center text-gray-500">
                    No hay vales disponibles
                  </td>
                </tr>
              ) : (
                credits.map(credit => (
                  <tr key={credit.id} className="hover:bg-gray-50">
                    <td className="border p-2 font-mono">{credit.code}</td>
                    <td className="border p-2">{credit.customer_id || '-'}</td>
                    <td className="border p-2 text-right">{credit.amount_initial.toFixed(2)}</td>
                    <td className="border p-2 text-right font-semibold">
                      {credit.amount_remaining.toFixed(2)}
                    </td>
                    <td className="border p-2 text-center">{credit.currency}</td>
                    <td className="border p-2 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(credit.status)}`}>
                        {credit.status}
                      </span>
                    </td>
                    <td className="border p-2">
                      {credit.expires_at || 'Sin vencimiento'}
                    </td>
                    <td className="border p-2">
                      {new Date(credit.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

**Agregar ruta**: En `apps/tenant/src/modules/pos/Routes.tsx`:
```tsx
import StoreCreditsList from './components/StoreCreditsList'

// En el array de rutas:
{
  path: 'vales',
  element: <StoreCreditsList />
}
```

---

#### 2. E-factura - Envío y Estado

##### 2.1 SendEInvoiceButton.tsx
**Ubicación**: `apps/tenant/src/modules/facturacion/components/`

```tsx
/**
 * Botón para enviar factura electrónica (SRI Ecuador / Facturae España)
 * Conecta con: POST /api/v1/einvoicing/send/{invoice_id}
 */
import React, { useState } from 'react'
import tenantApi from '../../../shared/api/client'

interface SendEInvoiceButtonProps {
  invoiceId: string
  country: 'EC' | 'ES'
  onSuccess?: () => void
}

export default function SendEInvoiceButton({ 
  invoiceId, 
  country, 
  onSuccess 
}: SendEInvoiceButtonProps) {
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')

  const handleSend = async () => {
    const confirmed = confirm(
      country === 'EC' 
        ? '¿Enviar factura electrónica al SRI?' 
        : '¿Enviar Facturae a la AEAT?'
    )
    if (!confirmed) return

    setLoading(true)
    setStatus('sending')

    try {
      const { data } = await tenantApi.post(
        `/api/v1/einvoicing/send/${invoiceId}`,
        { country }
      )

      setStatus('success')
      alert(
        country === 'EC'
          ? `Factura enviada al SRI. Clave: ${data.clave_acceso || 'generada'}`
          : 'Facturae enviada a AEAT correctamente'
      )
      onSuccess?.()
    } catch (error: any) {
      setStatus('error')
      const errorMsg = error.response?.data?.detail || 'Error al enviar factura'
      alert(errorMsg)
    } finally {
      setLoading(false)
    }
  }

  const buttonClass = {
    idle: 'bg-blue-600 hover:bg-blue-700',
    sending: 'bg-yellow-500 cursor-wait',
    success: 'bg-green-600',
    error: 'bg-red-600'
  }[status]

  const buttonText = {
    idle: country === 'EC' ? '📤 Enviar SRI' : '📤 Enviar Facturae',
    sending: 'Enviando...',
    success: '✓ Enviado',
    error: '✗ Error'
  }[status]

  return (
    <button
      onClick={handleSend}
      disabled={loading || status === 'success'}
      className={`px-4 py-2 text-white rounded ${buttonClass} disabled:opacity-50`}
    >
      {buttonText}
    </button>
  )
}
```

**Integrar en List.tsx**:
```tsx
// En apps/tenant/src/modules/facturacion/List.tsx
import SendEInvoiceButton from './components/SendEInvoiceButton'

// En la columna de acciones de la tabla:
<td className="border p-2">
  {invoice.estado === 'posted' && (
    <SendEInvoiceButton
      invoiceId={invoice.id}
      country={empresa.country} // 'EC' o 'ES'
      onSuccess={() => loadInvoices()} // Recargar lista
    />
  )}
</td>
```

##### 2.2 EInvoiceStatusView.tsx
**Ubicación**: `apps/tenant/src/modules/facturacion/components/`

```tsx
/**
 * Vista de estado de envío de factura electrónica
 * Conecta con: GET /api/v1/einvoicing/status/{kind}/{ref}
 */
import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import tenantApi from '../../../shared/api/client'

interface EInvoiceStatus {
  kind: 'SRI' | 'SII'
  ref: string
  status: 'pending' | 'authorized' | 'rejected'
  clave_acceso?: string
  error_message?: string
  submitted_at?: string
  xml_content?: string
}

export default function EInvoiceStatusView() {
  const { invoiceId } = useParams<{ invoiceId: string }>()
  const [status, setStatus] = useState<EInvoiceStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStatus()
  }, [invoiceId])

  const loadStatus = async () => {
    try {
      // Intentar buscar en SRI
      const { data: sriData } = await tenantApi.get(
        `/api/v1/einvoicing/status/SRI/${invoiceId}`
      )
      setStatus({ kind: 'SRI', ...sriData })
    } catch (sriError) {
      try {
        // Si no está en SRI, buscar en SII
        const { data: siiData } = await tenantApi.get(
          `/api/v1/einvoicing/status/SII/${invoiceId}`
        )
        setStatus({ kind: 'SII', ...siiData })
      } catch (siiError) {
        console.error('No se encontró estado de e-factura')
      }
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (st: string) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      authorized: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800'
    }
    return colors[st as keyof typeof colors] || 'bg-gray-100'
  }

  if (loading) return <div className="p-6">Cargando estado...</div>

  if (!status) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Esta factura aún no ha sido enviada electrónicamente</p>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">
        Estado de E-factura - {status.kind}
      </h1>

      <div className="bg-white shadow rounded-lg p-6 space-y-4">
        <div>
          <label className="text-sm text-gray-600">Estado:</label>
          <div className="mt-1">
            <span className={`px-3 py-1 rounded ${getStatusBadge(status.status)}`}>
              {status.status.toUpperCase()}
            </span>
          </div>
        </div>

        {status.clave_acceso && (
          <div>
            <label className="text-sm text-gray-600">Clave de Acceso:</label>
            <p className="font-mono text-sm mt-1">{status.clave_acceso}</p>
          </div>
        )}

        {status.submitted_at && (
          <div>
            <label className="text-sm text-gray-600">Fecha de Envío:</label>
            <p className="mt-1">{new Date(status.submitted_at).toLocaleString()}</p>
          </div>
        )}

        {status.error_message && (
          <div className="bg-red-50 border border-red-200 rounded p-4">
            <label className="text-sm font-semibold text-red-800">Error:</label>
            <p className="text-red-700 mt-1">{status.error_message}</p>
          </div>
        )}

        {status.xml_content && (
          <div>
            <label className="text-sm text-gray-600 mb-2 block">XML Generado:</label>
            <pre className="bg-gray-100 p-4 rounded text-xs overflow-x-auto">
              {status.xml_content}
            </pre>
          </div>
        )}

        <div className="pt-4">
          <button
            onClick={loadStatus}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            🔄 Actualizar Estado
          </button>
        </div>
      </div>
    </div>
  )
}
```

**Agregar ruta**: En `apps/tenant/src/modules/facturacion/Routes.tsx`:
```tsx
import EInvoiceStatusView from './components/EInvoiceStatusView'

// Nueva ruta:
{
  path: ':id/estatus-einvoice',
  element: <EInvoiceStatusView />
}
```

---

#### 3. Settings - Numeración Documental

##### 3.1 DocSeriesManager.tsx
**Ubicación**: `apps/tenant/src/modules/settings/components/`

```tsx
/**
 * CRUD de series documentales
 * Conecta con endpoints de numeración (por implementar en backend)
 */
import React, { useState, useEffect } from 'react'
import tenantApi from '../../../shared/api/client'

interface DocSeries {
  id: string
  tenant_id: string
  register_id?: string
  doc_type: 'R' | 'F' | 'C' // Recibo, Factura, Abono
  name: string
  current_no: number
  reset_policy: 'yearly' | 'never'
  active: boolean
}

export default function DocSeriesManager() {
  const [series, setSeries] = useState<DocSeries[]>([])
  const [editing, setEditing] = useState<DocSeries | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSeries()
  }, [])

  const loadSeries = async () => {
    setLoading(true)
    try {
      // TODO: Backend debe exponer GET /api/v1/pos/doc_series
      const { data } = await tenantApi.get('/api/v1/pos/doc_series')
      setSeries(data || [])
    } catch (error) {
      console.error('Error loading series:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!editing) return

    try {
      if (editing.id.startsWith('new-')) {
        // Crear nueva
        await tenantApi.post('/api/v1/pos/doc_series', editing)
      } else {
        // Actualizar
        await tenantApi.put(`/api/v1/pos/doc_series/${editing.id}`, editing)
      }
      alert('Serie guardada')
      setEditing(null)
      loadSeries()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al guardar')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('¿Eliminar esta serie?')) return

    try {
      await tenantApi.delete(`/api/v1/pos/doc_series/${id}`)
      alert('Serie eliminada')
      loadSeries()
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Error al eliminar')
    }
  }

  const docTypeLabel = {
    R: 'Recibo/Ticket',
    F: 'Factura',
    C: 'Abono/Devolución'
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Numeración Documental</h1>
        <button
          onClick={() => setEditing({
            id: `new-${Date.now()}`,
            tenant_id: '',
            doc_type: 'R',
            name: '',
            current_no: 0,
            reset_policy: 'yearly',
            active: true
          })}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          + Nueva Serie
        </button>
      </div>

      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Tipo Doc</th>
                <th className="border p-2 text-left">Serie/Prefijo</th>
                <th className="border p-2 text-center">Número Actual</th>
                <th className="border p-2 text-center">Reseteo</th>
                <th className="border p-2 text-center">Activo</th>
                <th className="border p-2 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {series.length === 0 ? (
                <tr>
                  <td colSpan={6} className="border p-4 text-center text-gray-500">
                    No hay series configuradas
                  </td>
                </tr>
              ) : (
                series.map(s => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="border p-2">{docTypeLabel[s.doc_type]}</td>
                    <td className="border p-2 font-mono">{s.name}</td>
                    <td className="border p-2 text-center font-semibold">{s.current_no}</td>
                    <td className="border p-2 text-center">{s.reset_policy}</td>
                    <td className="border p-2 text-center">
                      {s.active ? '✅' : '❌'}
                    </td>
                    <td className="border p-2 text-center">
                      <button
                        onClick={() => setEditing(s)}
                        className="text-blue-600 hover:underline mr-2"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="text-red-600 hover:underline"
                      >
                        Eliminar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal de edición */}
      {editing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">
              {editing.id.startsWith('new-') ? 'Nueva Serie' : 'Editar Serie'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1">Tipo de Documento:</label>
                <select
                  value={editing.doc_type}
                  onChange={(e) => setEditing({ ...editing, doc_type: e.target.value as any })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="R">Recibo/Ticket</option>
                  <option value="F">Factura</option>
                  <option value="C">Abono/Devolución</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Serie/Prefijo:</label>
                <input
                  type="text"
                  value={editing.name}
                  onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                  placeholder="Ej: T001, FAC2025"
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Número Actual:</label>
                <input
                  type="number"
                  value={editing.current_no}
                  onChange={(e) => setEditing({ ...editing, current_no: parseInt(e.target.value) })}
                  className="w-full border rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1">Política de Reseteo:</label>
                <select
                  value={editing.reset_policy}
                  onChange={(e) => setEditing({ ...editing, reset_policy: e.target.value as any })}
                  className="w-full border rounded px-3 py-2"
                >
                  <option value="yearly">Anual</option>
                  <option value="never">Nunca</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editing.active}
                  onChange={(e) => setEditing({ ...editing, active: e.target.checked })}
                />
                <label>Serie activa</label>
              </div>
            </div>

            <div className="flex gap-2 justify-end mt-6">
              <button
                onClick={() => setEditing(null)}
                className="px-4 py-2 border rounded hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

**Agregar ruta** en settings:
```tsx
// En apps/tenant/src/modules/settings/Routes.tsx
import DocSeriesManager from './components/DocSeriesManager'

// Nueva ruta:
{
  path: 'numeracion',
  element: <DocSeriesManager />
}
```

---

### Sprint 2 (Media Prioridad) - 4-5 días
**Pagos Online + Historial + Mejoras UX**

#### 4. Pagos Online Dashboard

##### 4.1 PaymentLinksView.tsx
**Ubicación**: `apps/tenant/src/modules/payments/`

```tsx
/**
 * Vista de enlaces de pago generados
 * Conecta con: GET /api/v1/payments/links (por implementar en backend)
 */
import React, { useState, useEffect } from 'react'
import tenantApi from '../../shared/api/client'

interface PaymentLink {
  id: string
  invoice_id: string
  invoice_number: string
  provider: 'stripe' | 'kushki' | 'payphone'
  url: string
  amount: number
  currency: string
  status: 'pending' | 'completed' | 'expired'
  created_at: string
  expires_at?: string
}

export default function PaymentLinksView() {
  const [links, setLinks] = useState<PaymentLink[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadLinks()
  }, [])

  const loadLinks = async () => {
    setLoading(true)
    try {
      const { data } = await tenantApi.get('/api/v1/payments/links')
      setLinks(data || [])
    } catch (error) {
      console.error('Error loading payment links:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (url: string) => {
    navigator.clipboard.writeText(url)
    alert('Enlace copiado al portapapeles')
  }

  const getStatusBadge = (status: string) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      completed: 'bg-green-100 text-green-800',
      expired: 'bg-red-100 text-red-800'
    }
    return colors[status as keyof typeof colors] || 'bg-gray-100'
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Enlaces de Pago</h1>
        <button
          onClick={loadLinks}
          className="px-4 py-2 border rounded hover:bg-gray-50"
        >
          🔄 Actualizar
        </button>
      </div>

      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Factura</th>
                <th className="border p-2 text-left">Proveedor</th>
                <th className="border p-2 text-right">Importe</th>
                <th className="border p-2 text-center">Estado</th>
                <th className="border p-2 text-left">Creado</th>
                <th className="border p-2 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {links.length === 0 ? (
                <tr>
                  <td colSpan={6} className="border p-4 text-center text-gray-500">
                    No hay enlaces de pago generados
                  </td>
                </tr>
              ) : (
                links.map(link => (
                  <tr key={link.id} className="hover:bg-gray-50">
                    <td className="border p-2">{link.invoice_number}</td>
                    <td className="border p-2 capitalize">{link.provider}</td>
                    <td className="border p-2 text-right font-semibold">
                      {link.amount.toFixed(2)} {link.currency}
                    </td>
                    <td className="border p-2 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${getStatusBadge(link.status)}`}>
                        {link.status}
                      </span>
                    </td>
                    <td className="border p-2">
                      {new Date(link.created_at).toLocaleString()}
                    </td>
                    <td className="border p-2 text-center">
                      <button
                        onClick={() => copyToClipboard(link.url)}
                        className="text-blue-600 hover:underline mr-2"
                      >
                        📋 Copiar
                      </button>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-green-600 hover:underline"
                      >
                        🔗 Abrir
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

##### 4.2 TransactionsDashboard.tsx
```tsx
/**
 * Dashboard de transacciones de pago
 * Conecta con: GET /api/v1/payments/transactions
 */
import React, { useState, useEffect } from 'react'
import tenantApi from '../../shared/api/client'

interface Transaction {
  id: string
  invoice_id: string
  invoice_number: string
  provider: string
  amount: number
  currency: string
  status: 'pending' | 'success' | 'failed'
  ref: string
  created_at: string
}

export default function TransactionsDashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [filter, setFilter] = useState<'all' | 'success' | 'failed'>('all')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadTransactions()
  }, [filter])

  const loadTransactions = async () => {
    setLoading(true)
    try {
      const params = filter !== 'all' ? { status: filter } : {}
      const { data } = await tenantApi.get('/api/v1/payments/transactions', { params })
      setTransactions(data || [])
    } catch (error) {
      console.error('Error loading transactions:', error)
    } finally {
      setLoading(false)
    }
  }

  const totalAmount = transactions
    .filter(t => t.status === 'success')
    .reduce((sum, t) => sum + t.amount, 0)

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Transacciones de Pago</h1>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-green-50 border border-green-200 rounded p-4">
          <p className="text-sm text-gray-600">Total Cobrado</p>
          <p className="text-2xl font-bold text-green-700">
            {totalAmount.toFixed(2)} €
          </p>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded p-4">
          <p className="text-sm text-gray-600">Transacciones</p>
          <p className="text-2xl font-bold text-blue-700">
            {transactions.length}
          </p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
          <p className="text-sm text-gray-600">Tasa de Éxito</p>
          <p className="text-2xl font-bold text-yellow-700">
            {transactions.length > 0
              ? ((transactions.filter(t => t.status === 'success').length / transactions.length) * 100).toFixed(1)
              : 0}%
          </p>
        </div>
      </div>

      {/* Filtros */}
      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          Todas
        </button>
        <button
          onClick={() => setFilter('success')}
          className={`px-4 py-2 rounded ${filter === 'success' ? 'bg-green-600 text-white' : 'bg-gray-200'}`}
        >
          Exitosas
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={`px-4 py-2 rounded ${filter === 'failed' ? 'bg-red-600 text-white' : 'bg-gray-200'}`}
        >
          Fallidas
        </button>
      </div>

      {/* Tabla */}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Fecha</th>
                <th className="border p-2 text-left">Factura</th>
                <th className="border p-2 text-left">Proveedor</th>
                <th className="border p-2 text-right">Importe</th>
                <th className="border p-2 text-center">Estado</th>
                <th className="border p-2 text-left">Referencia</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map(tx => (
                <tr key={tx.id} className="hover:bg-gray-50">
                  <td className="border p-2">
                    {new Date(tx.created_at).toLocaleString()}
                  </td>
                  <td className="border p-2">{tx.invoice_number}</td>
                  <td className="border p-2 capitalize">{tx.provider}</td>
                  <td className="border p-2 text-right font-semibold">
                    {tx.amount.toFixed(2)} {tx.currency}
                  </td>
                  <td className="border p-2 text-center">
                    {tx.status === 'success' ? '✅' : tx.status === 'failed' ? '❌' : '⏳'}
                  </td>
                  <td className="border p-2 font-mono text-xs">{tx.ref}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

---

### Sprint 3 (Baja Prioridad) - 3 días
**Mejoras UX + Notificaciones**

#### 5. Notificaciones en Tiempo Real

##### 5.1 PaymentNotifications.tsx
```tsx
/**
 * Sistema de notificaciones de pagos recibidos
 * Usa WebSocket o polling
 */
import React, { useEffect, useState } from 'react'
import tenantApi from '../../shared/api/client'

interface Notification {
  id: string
  type: 'payment_received' | 'einvoice_accepted' | 'einvoice_rejected'
  message: string
  timestamp: string
  read: boolean
}

export default function PaymentNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [showPanel, setShowPanel] = useState(false)

  useEffect(() => {
    // Polling cada 30 segundos (mejorar con WebSocket en producción)
    const interval = setInterval(fetchNotifications, 30000)
    fetchNotifications()
    return () => clearInterval(interval)
  }, [])

  const fetchNotifications = async () => {
    try {
      const { data } = await tenantApi.get('/api/v1/notifications')
      setNotifications(data || [])
    } catch (error) {
      console.error('Error fetching notifications:', error)
    }
  }

  const markAsRead = async (id: string) => {
    try {
      await tenantApi.patch(`/api/v1/notifications/${id}/read`)
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, read: true } : n))
      )
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div className="relative">
      <button
        onClick={() => setShowPanel(!showPanel)}
        className="relative p-2 hover:bg-gray-100 rounded"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 bg-red-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {showPanel && (
        <div className="absolute right-0 mt-2 w-80 bg-white shadow-lg rounded-lg border z-50">
          <div className="p-4 border-b">
            <h3 className="font-semibold">Notificaciones</h3>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-gray-500 text-center">No hay notificaciones</p>
            ) : (
              notifications.map(notif => (
                <div
                  key={notif.id}
                  className={`p-3 border-b hover:bg-gray-50 cursor-pointer ${
                    !notif.read ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => markAsRead(notif.id)}
                >
                  <p className="text-sm">{notif.message}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(notif.timestamp).toLocaleString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
```

#### 5.2 ReceiptHistoryView.tsx
```tsx
/**
 * Vista de histórico de tickets con filtros avanzados
 */
import React, { useState, useEffect } from 'react'
import { listReceipts } from '../modules/pos/services'
import type { POSReceipt } from '../types/pos'

export default function ReceiptHistoryView() {
  const [receipts, setReceipts] = useState<POSReceipt[]>([])
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    status: 'all',
    shiftId: ''
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadReceipts()
  }, [filters])

  const loadReceipts = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.status !== 'all') params.status = filters.status
      if (filters.shiftId) params.shift_id = filters.shiftId

      const data = await listReceipts(params)
      
      // Filtrar por fechas en frontend
      let filtered = data
      if (filters.dateFrom) {
        filtered = filtered.filter(r => r.created_at >= filters.dateFrom)
      }
      if (filters.dateTo) {
        filtered = filtered.filter(r => r.created_at <= filters.dateTo)
      }

      setReceipts(filtered)
    } catch (error) {
      console.error('Error loading receipts:', error)
    } finally {
      setLoading(false)
    }
  }

  const totalSales = receipts
    .filter(r => r.status === 'paid')
    .reduce((sum, r) => sum + r.gross_total, 0)

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Histórico de Tickets</h1>

      {/* Filtros */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Desde:</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Hasta:</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              className="w-full border rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Estado:</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full border rounded px-3 py-2"
            >
              <option value="all">Todos</option>
              <option value="draft">Borrador</option>
              <option value="paid">Pagado</option>
              <option value="voided">Anulado</option>
              <option value="invoiced">Facturado</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={loadReceipts}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Buscar
            </button>
          </div>
        </div>
      </div>

      {/* KPI */}
      <div className="bg-green-50 border border-green-200 rounded p-4 mb-6">
        <p className="text-sm text-gray-600">Total Ventas (Pagadas)</p>
        <p className="text-3xl font-bold text-green-700">
          {totalSales.toFixed(2)} €
        </p>
      </div>

      {/* Tabla */}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Número</th>
                <th className="border p-2 text-left">Fecha</th>
                <th className="border p-2 text-right">Total</th>
                <th className="border p-2 text-center">Estado</th>
                <th className="border p-2 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {receipts.map(receipt => (
                <tr key={receipt.id} className="hover:bg-gray-50">
                  <td className="border p-2 font-mono">{receipt.number}</td>
                  <td className="border p-2">
                    {new Date(receipt.created_at).toLocaleString()}
                  </td>
                  <td className="border p-2 text-right font-semibold">
                    {receipt.gross_total.toFixed(2)} {receipt.currency}
                  </td>
                  <td className="border p-2 text-center">
                    <span className={`px-2 py-1 rounded text-xs ${
                      receipt.status === 'paid' ? 'bg-green-100 text-green-800' :
                      receipt.status === 'voided' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {receipt.status}
                    </span>
                  </td>
                  <td className="border p-2 text-center">
                    <button className="text-blue-600 hover:underline mr-2">
                      Ver
                    </button>
                    <button className="text-gray-600 hover:underline">
                      Imprimir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

---

## 📋 Checklist de Implementación

### Backend (Endpoints faltantes)
- [ ] `GET /api/v1/pos/doc_series` - Listar series
- [ ] `POST /api/v1/pos/doc_series` - Crear serie
- [ ] `PUT /api/v1/pos/doc_series/{id}` - Actualizar serie
- [ ] `DELETE /api/v1/pos/doc_series/{id}` - Eliminar serie
- [ ] `GET /api/v1/einvoicing/status/{kind}/{ref}` - Estado submission
- [ ] `POST /api/v1/einvoicing/send/{invoice_id}` - Enviar e-factura
- [ ] `GET /api/v1/payments/links` - Listar payment links
- [ ] `GET /api/v1/payments/transactions` - Listar transacciones
- [ ] `GET /api/v1/notifications` - Obtener notificaciones
- [ ] `PATCH /api/v1/notifications/{id}/read` - Marcar como leída

### Frontend - Alta Prioridad (Sprint 1)
- [ ] RefundModal.tsx + integración en POSView
- [ ] StoreCreditsList.tsx + ruta
- [ ] SendEInvoiceButton.tsx + integración en List.tsx
- [ ] EInvoiceStatusView.tsx + ruta
- [ ] DocSeriesManager.tsx + ruta en settings
- [ ] Actualizar tipos en types/pos.ts

### Frontend - Media Prioridad (Sprint 2)
- [ ] PaymentLinksView.tsx + ruta
- [ ] TransactionsDashboard.tsx + ruta
- [ ] Crear módulo payments/ con Routes.tsx

### Frontend - Baja Prioridad (Sprint 3)
- [ ] PaymentNotifications.tsx + integración en layout
- [ ] ReceiptHistoryView.tsx + ruta
- [ ] WebSocket para notificaciones en tiempo real

### Tipos TypeScript
Agregar en `apps/tenant/src/types/pos.ts`:
```typescript
export interface RefundRequest {
  reason: string
  refund_method: 'original' | 'cash' | 'store_credit'
  line_ids?: string[]
  restock?: boolean
}

export interface StoreCredit {
  id: string
  tenant_id: string
  code: string
  customer_id?: string
  currency: string
  amount_initial: number
  amount_remaining: number
  expires_at?: string
  status: 'active' | 'redeemed' | 'expired' | 'void'
  created_at: string
}

export interface DocSeries {
  id: string
  tenant_id: string
  register_id?: string
  doc_type: 'R' | 'F' | 'C'
  name: string
  current_no: number
  reset_policy: 'yearly' | 'never'
  active: boolean
  created_at: string
}
```

---

## 🚀 Plan de Ejecución

### Semana 1: Sprint 1 Alta Prioridad
**Día 1-2**: POS Devoluciones
- RefundModal.tsx completo
- Integración en POSView
- StoreCreditsList.tsx
- Testing manual

**Día 3-4**: E-factura
- SendEInvoiceButton.tsx
- Integración en List.tsx
- EInvoiceStatusView.tsx
- Probar con backend SRI/Facturae

**Día 5**: Numeración
- DocSeriesManager.tsx
- Crear endpoints backend faltantes
- Testing CRUD completo

### Semana 2: Sprint 2 Media Prioridad
**Día 1-2**: Pagos Online
- PaymentLinksView.tsx
- TransactionsDashboard.tsx
- Crear módulo payments/

**Día 3-4**: Testing integración
- Probar flujo completo POS → Pago → Webhook
- Validar enlaces de pago Stripe/Kushki/PayPhone

**Día 5**: Documentación
- Actualizar AGENTS.md
- Crear guías de usuario
- Screenshots y videos demo

### Semana 3 (Opcional): Sprint 3 Mejoras
**Día 1-2**: Notificaciones
- PaymentNotifications.tsx
- ReceiptHistoryView.tsx

**Día 3**: WebSocket (si hay tiempo)
- Implementar notificaciones en tiempo real
- Backend: WebSocket endpoint

---

## 📊 Métricas de Éxito

### Cobertura
- ✅ **100% endpoints backend** cubiertos con UI
- ✅ **Todos los flujos críticos** implementados
- ✅ **Zero dead endpoints** (todos usados)

### UX
- ⚡ Tiempo de devolución < 30s
- ⚡ Generación payment link < 5s
- ⚡ Envío e-factura < 10s

### Testing
- ✅ Manual testing completo (10 casos)
- ✅ Unit tests principales componentes
- ✅ E2E tests flujos críticos

---

## 🔗 Referencias

- [AGENTS.md](./AGENTS.md) - Arquitectura completa
- [SETUP_AND_TEST.md](./SETUP_AND_TEST.md) - Testing backend
- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) - Código de referencia
- Backend routers:
  - [apps/backend/app/routers/pos.py](./apps/backend/app/routers/pos.py)
  - [apps/backend/app/routers/payments.py](./apps/backend/app/routers/payments.py)
  - [apps/backend/app/workers/einvoicing_tasks.py](./apps/backend/app/workers/einvoicing_tasks.py)

---

**Versión**: 1.0.0  
**Fecha**: Enero 2025  
**Estado**: Plan de Implementación Detallado  
**Responsable**: GestiQCloud Frontend Team
