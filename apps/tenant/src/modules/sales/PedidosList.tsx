import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { listVentas, updateVenta, type Venta } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import { usePagination, Pagination } from '../../shared/pagination'
import { getCompanySettings, formatCurrency, type CompanySettings } from '../../services/companySettings'

function ConfirmBadge({ estado }: { estado?: string }) {
  if (estado === 'confirmed' || estado === 'emitida') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
        ✓ Confirmado
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
      ⏳ PDT confirmar
    </span>
  )
}

function DepositBadge({ amount, paid }: { amount?: number; paid?: boolean }) {
  if (!amount || amount <= 0) return <span className="text-gray-400 text-xs">—</span>
  return (
    <span className={`text-xs font-medium ${paid ? 'text-green-700' : 'text-amber-700'}`}>
      {paid ? '✓' : '⏳'} ${Number(amount).toFixed(2)}
    </span>
  )
}

export default function PedidosList() {
  const { t } = useTranslation()
  const nav = useNavigate()
  const { config } = useCompanyConfig()
  const sector = config?.sector?.plantilla || ''
  const isTaller = sector.startsWith('taller')
  const { success, error: toastError } = useToast()

  const [items, setItems] = useState<Venta[]>([])
  const [loading, setLoading] = useState(false)
  const [companySettings, setCompanySettings] = useState<CompanySettings | null>(null)
  const [q, setQ] = useState('')
  const [onlyPending, setOnlyPending] = useState(false)
  const [per] = useState(20)

  useEffect(() => {
    setLoading(true)
    Promise.all([listVentas(), getCompanySettings().catch(() => null)])
      .then(([ventas, settings]) => {
        // Solo mostrar ventas con fecha de entrega (pedidos especiales)
        setItems(ventas.filter(v => !!v.delivery_date))
        setCompanySettings(settings)
      })
      .catch(e => toastError(getErrorMessage(e)))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => items.filter(v => {
    const matchQ = !q || (v.cliente_nombre || '').toLowerCase().includes(q.toLowerCase()) ||
      (v.numero || '').toLowerCase().includes(q.toLowerCase()) ||
      (v.notas || '').toLowerCase().includes(q.toLowerCase())
    const isPending = v.estado !== 'confirmed' && v.estado !== 'emitida'
    const matchPending = !onlyPending || isPending
    return matchQ && matchPending
  }), [items, q, onlyPending])

  const sorted = useMemo(() =>
    [...filtered].sort((a, b) => {
      const da = a.delivery_date || ''
      const db_ = b.delivery_date || ''
      return da < db_ ? -1 : da > db_ ? 1 : 0
    }), [filtered])

  const { page, setPage, totalPages, view } = usePagination(sorted, per)

  async function handleConfirm(v: Venta) {
    try {
      await updateVenta(v.id, { ...v, estado: 'emitida' } as any)
      setItems(prev => prev.map(x => x.id === v.id ? { ...x, estado: 'emitida' } : x))
      success('Pedido confirmado')
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  const title = isTaller ? 'Trabajos / Cotizaciones' : 'Pedidos especiales'
  const newLabel = isTaller ? '+ Nuevo trabajo' : '+ Nuevo pedido'
  const deliveryLabel = isTaller ? 'Entrega estimada' : 'Fecha evento'

  return (
    <div className="p-4">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="font-semibold text-lg">{title}</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm font-medium"
          onClick={() => nav('../new')}
        >
          {newLabel}
        </button>
      </div>

      <div className="flex flex-wrap gap-3 mb-4 items-center">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Buscar cliente, número, notas..."
          className="border px-3 py-1.5 rounded text-sm flex-1 min-w-48"
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={onlyPending}
            onChange={e => setOnlyPending(e.target.checked)}
          />
          Solo PDT confirmar
        </label>
      </div>

      {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}

      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left border-b bg-gray-50">
            <th className="py-2 px-2">#</th>
            <th className="py-2 px-2">Cliente</th>
            <th className="py-2 px-2">{deliveryLabel}</th>
            <th className="py-2 px-2">Total</th>
            <th className="py-2 px-2">Anticipo</th>
            <th className="py-2 px-2">Estado</th>
            <th className="py-2 px-2">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {view.map(v => {
            const isPending = v.estado !== 'confirmed' && v.estado !== 'emitida'
            return (
              <tr key={v.id} className="border-b hover:bg-gray-50">
                <td className="py-2 px-2 font-mono text-xs">{v.numero || '—'}</td>
                <td className="py-2 px-2">
                  <div>{v.cliente_nombre || <span className="text-gray-400">Sin cliente</span>}</div>
                  {v.notas && <div className="text-xs text-gray-500 truncate max-w-40">{v.notas}</div>}
                </td>
                <td className="py-2 px-2">
                  {v.delivery_date
                    ? <span className="font-medium">{v.delivery_date}</span>
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="py-2 px-2 font-semibold">
                  {v.total !== null && v.total !== undefined
                    ? formatCurrency(Number(v.total), companySettings || undefined)
                    : '—'}
                </td>
                <td className="py-2 px-2">
                  <DepositBadge amount={v.deposit_amount} paid={v.deposit_paid} />
                </td>
                <td className="py-2 px-2">
                  <ConfirmBadge estado={v.estado} />
                </td>
                <td className="py-2 px-2">
                  <div className="flex gap-2 flex-wrap">
                    <Link to={`../${v.id}/edit`} className="text-blue-600 hover:underline">
                      Editar
                    </Link>
                    {isPending && (
                      <button
                        className="text-green-700 hover:underline font-medium"
                        onClick={() => handleConfirm(v)}
                      >
                        Confirmar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
          {!loading && view.length === 0 && (
            <tr>
              <td colSpan={7} className="py-6 text-center text-gray-500">
                No hay pedidos con fecha de entrega registrada
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
