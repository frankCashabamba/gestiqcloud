import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { listFacturas, removeFactura, clearInvoicesCache, type Factura } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import FacturaStatusBadge from './components/FacturaStatusBadge'
import EinvoiceStatus from './components/EinvoiceStatus'
import { useCompanyConfig } from '../../contexts/CompanyConfigContext'
import { useCurrency } from '../../hooks/useCurrency'
import { usePermission } from '../../hooks/usePermission'
import ProtectedButton from '../../components/ProtectedButton'

function sortInvoices(arr: Factura[]): Factura[] {
  // Extrae la última secuencia numérica de un string (ej: "A-2026-000037" -> 37)
  const parseNumber = (value?: string | number) => {
    if (value === undefined || value === null) return null
    if (typeof value === 'number') return Number.isFinite(value) ? value : null
    const match = value.match(/(\d+)(?!.*\d)/) // última secuencia de dígitos
    if (!match) return null
    const n = Number(match[1])
    return Number.isFinite(n) ? n : null
  }
  const parseDate = (value?: string) => {
    const ts = value ? Date.parse(value) : NaN
    return Number.isNaN(ts) ? null : ts
  }
  return [...arr].sort((a, b) => {
    // 1) número de factura descendente si es numérico
    const na = parseNumber(a.numero)
    const nb = parseNumber(b.numero)
    if (nb !== null || na !== null) {
      if (nb === null) return 1
      if (na === null) return -1
      if (nb !== na) return nb - na
    }
    // 2) fecha descendente
    const da = parseDate(a.fecha)
    const db = parseDate(b.fecha)
    if (da !== null && db !== null && db !== da) return db - da
    // 3) último recurso: orden estable por id
    return String(b.id).localeCompare(String(a.id))
  })
}

export default function FacturasList() {
  const { t } = useTranslation()
  const { config } = useCompanyConfig()
  const { formatCurrency } = useCurrency()
  const can = usePermission()
  const [items, setItems] = useState<Factura[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()
  const [estado, setEstado] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [q, setQ] = useState('')

  useEffect(() => {
    const loadFacturas = async () => {
      try {
        setLoading(true)
        setErrMsg(null)
        const facturas = await listFacturas()
        // Ordenar más recientes primero por fecha (fallback a created order)
        const sorted = sortInvoices(facturas)
        setItems(sorted)
      } catch (e: any) {
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        setLoading(false)
      }
    }

    loadFacturas()
  }, [])

  const filtered = useMemo(() => {
    const res = items.filter(v => {
      if (estado && (v.estado||'') !== estado) return false
      if (desde && v.fecha < desde) return false
      if (hasta && v.fecha > hasta) return false
      if (q && !(`${v.id}`.includes(q) || (v.estado||'').toLowerCase().includes(q.toLowerCase()))) return false
      return true
    })
    return sortInvoices(res)
  }, [items, estado, desde, hasta, q])

  const { page, setPage, totalPages, view } = usePagination(filtered, 10)

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-3">
        <h2 className="font-semibold text-lg">{t('nav.invoicing')}</h2>
        <div className="flex gap-2">
          <button className="bg-gray-200 px-3 py-1 rounded" onClick={()=> nav('sectores')}>{t('billing.sectors')}</button>
          {can('billing:create') && (
            <ProtectedButton
              permission="billing:create"
              variant="primary"
              onClick={()=> nav('nueva')}
            >
              {t('common.new')}
            </ProtectedButton>
          )}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-sm mr-2 block">{t('common.status')}</label>
          <select value={estado} onChange={(e)=> setEstado(e.target.value)} className="border px-2 py-1 rounded text-sm">
            <option value="">{t('common.all')}</option>
            <option value="borrador">{t('billing.status.draft')}</option>
            <option value="emitida">{t('billing.status.issued')}</option>
            <option value="anulada">{t('billing.status.voided')}</option>
          </select>
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.from')}</label>
          <input type="date" value={desde} onChange={(e)=> setDesde(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.to')}</label>
          <input type="date" value={hasta} onChange={(e)=> setHasta(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
        <div>
          <label className="text-sm mr-2 block">{t('common.search')}</label>
          <input placeholder={t('billing.searchPlaceholder')} value={q} onChange={(e)=> setQ(e.target.value)} className="border px-2 py-1 rounded text-sm" />
        </div>
      </div>

      {loading && <div className="text-sm text-gray-500">{t('common.loading')}</div>}
      {errMsg && <div className="bg-red-100 text-red-700 px-3 py-2 rounded mb-3">{errMsg}</div>}

      <table className="min-w-full text-sm">
      <thead><tr className="text-left border-b"><th>{t('common.date')}</th><th>{t('common.total')}</th><th>{t('common.status')}</th><th>{t('billing.einvoice')}</th><th>{t('common.actions')}</th></tr></thead>
      <tbody>
      {view.map((v) => (
      <tr key={v.id} className="border-b">
      <td>{v.fecha || '-'}</td>
      <td>
        {typeof v.total === 'number' && !Number.isNaN(v.total)
          ? formatCurrency(v.total)
          : '-'}
      </td>
      <td><FacturaStatusBadge estado={v.estado} /></td>
      <td>
      <EinvoiceStatus
        invoiceId={v.id.toString()}
          country="ES"  // TODO: Detectar desde company config
            canSend={['posted','issued','emitida'].includes((v.estado||'').toLowerCase())}
            enabled={['posted','issued','emitida'].includes((v.estado||'').toLowerCase())}
            />
          </td>
            <td className="flex gap-2">
              {['emitida','issued','posted','confirmed'].includes((v.estado||'').toLowerCase()) ? (
                <>
                  {can('billing:read') && (
                    <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline">
                      {t('common.view') || 'View'}
                    </Link>
                  )}
                  <span className="text-gray-500 text-sm">{t('common.readonly') || 'Read-only'}</span>
                </>
              ) : (
                <>
                  {can('billing:update') && (
                    <Link to={`${v.id}/editar`} className="text-blue-600 hover:underline">{t('common.edit')}</Link>
                  )}
                </>
              )}
              {can('billing:delete') && (
                <ProtectedButton
                  permission="billing:delete"
                  variant="ghost"
                  onClick={async ()=> {
                    if(!confirm(t('billing.deleteConfirm'))) return
                    try {
                      await removeFactura(v.id)
                      clearInvoicesCache()
                      setItems((p)=>p.filter(x=>x.id!==v.id))
                      success(t('billing.deleted'))
                    } catch(e:any){
                      toastError(getErrorMessage(e))
                    }
                  }}
                >
                  {t('common.delete')}
                </ProtectedButton>
              )}
            </td>
            </tr>
          ))}
          {!loading && items.length===0 && <tr><td className="py-3 px-3" colSpan={5}>{t('common.noRecords')}</td></tr>}
        </tbody>
      </table>
      <Pagination page={page} setPage={setPage} totalPages={totalPages} />
    </div>
  )
}
