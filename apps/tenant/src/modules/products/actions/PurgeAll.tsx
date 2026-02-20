// apps/tenant/src/modules/products/actions/PurgeAll.tsx
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { purgeProductosConfirm, purgeProductosDryRun } from '../productsApi'
import { useToast, getErrorMessage } from '../../../shared/toast'

export default function ProductosPurge() {
  const nav = useNavigate()
  const { error: toastError, success } = useToast()
  const [busy, setBusy] = useState(false)
  const [counts, setCounts] = useState<Record<string, number> | null>(null)
  const [confirmText, setConfirmText] = useState('')

  React.useEffect(() => {
    ;(async () => {
      try {
        const res = await purgeProductosDryRun()
        setCounts(res?.counts || null)
      } catch (e: any) {
        // best-effort
      }
    })()
  }, [])

  const goBack = () => nav('..')

  const onPurge = async () => {
    if ((confirmText || '').toUpperCase() !== 'PURGE') {
      toastError('Escribe PURGE para confirmar')
      return
    }
    try {
      setBusy(true)
      await purgeProductosConfirm({ confirm: 'PURGE', include_stock: true, include_categories: true })
      success('Catálogo y stock eliminados')
      nav('..')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="p-6 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Eliminar todo el catálogo</h1>
      <div className="bg-white border border-red-200 rounded-lg p-4 mb-4">
        <p className="text-red-700">
          Esta acción borrará todos los productos del catálogo y su stock asociado en todos los almacenes para este tenant.
          No se puede deshacer.
        </p>
        {counts && (
          <div className="mt-3 text-sm text-red-800">
            <div>Productos: {counts.products}</div>
            <div>Stock items: {counts.stock_items}</div>
            <div>Movimientos: {counts.stock_moves}</div>
            {typeof counts.product_categories === 'number' && <div>Categorías: {counts.product_categories}</div>}
          </div>
        )}
      </div>
      <div className="mb-4">
        <label className="block text-sm mb-1">Escribe <b>PURGE</b> para confirmar</label>
        <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} className="border px-3 py-2 rounded w-full" placeholder="PURGE" />
      </div>
      <div className="flex gap-3">
        <button onClick={onPurge} disabled={busy || (confirmText||'').toUpperCase()!=='PURGE'} className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-60">
          {busy ? 'Deleting…' : 'Delete all'}
        </button>
        <button onClick={goBack} className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
      </div>
    </div>
  )
}
