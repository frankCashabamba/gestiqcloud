import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { getProductMargins, getProfitReport, type ProductMarginRow } from '../../services/api/profit-reports'
import { listProducts } from '../../services/api/products'
import { fetchBodegas } from '../inventory/services/inventory'
import { getCompanySettings, formatCurrency as formatCurrencyWithSettings, type CompanySettings } from '../../services/companySettings'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'
import './reportes.css'

type Warehouse = { id: string; name: string }
type Product = { id: string; name: string }

const toISO = (d: Date) => d.toISOString().split('T')[0]
const addDays = (d: Date, days: number) => new Date(d.getTime() + days * 86400000)

// Map new API response to old format for backward compatibility
const mapProductMarginRow = (row: ProductMarginRow) => ({
  product_id: row.product_id,
  sales_net: row.revenue,
  cogs: row.cogs,
  gross_profit: row.gross_profit,
  margin_pct: row.margin_pct / 100, // Convert from percentage to decimal
})

const formatMoney = (v: number, settings?: CompanySettings | null) =>
  formatCurrencyWithSettings(v || 0, settings || undefined)

const formatPct = (v: number) => `${(v * 100).toFixed(2)}%`

export default function MarginsDashboard() {
  const { empresa } = useParams()
  const { t } = useTranslation(['reportes', 'common'])
  const can = usePermission()
  const [companySettings, setCompanySettings] = useState<CompanySettings | null>(null)
  const [fromDate, setFromDate] = useState(() => toISO(addDays(new Date(), -30)))
  const [toDate, setToDate] = useState(() => toISO(new Date()))
  const [warehouseId, setWarehouseId] = useState<string | ''>('')
  const [threshold, setThreshold] = useState(0.15)
  const [products, setProducts] = useState<Product[]>([])
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [productRows, setProductRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'productos' | 'clientes' | 'detalle'>('productos')
  const [error, setError] = useState<string | null>(null)

  const dateParams = useMemo(() => ({
    from: fromDate,
    to: toISO(addDays(new Date(toDate), 1)),
  }), [fromDate, toDate])

  useEffect(() => {
    let mounted = true
    ;(async () => {
      try {
        const settings = await getCompanySettings()
        if (mounted) setCompanySettings(settings)
        const [ws, prods] = await Promise.all([fetchBodegas(), listProducts({ limit: 500 })])
        if (!mounted) return
        setWarehouses(ws.map((w) => ({ id: String(w.id), name: w.name })))
        setProducts(prods.map((p) => ({ id: p.id, name: p.name })))
      } catch {}
    })()
    return () => { mounted = false }
  }, [empresa])

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    ;(async () => {
      try {
        const data = await getProductMargins(dateParams.from, dateParams.to, {
          limit: 200,
          sort_by: 'revenue',
        })
        if (!mounted) return
        // Map API response to component format
        setProductRows(data.products.map(mapProductMarginRow))
      } catch (e: any) {
        if (!mounted) return
        setError(e?.message || 'Error loading reports')
      } finally {
        if (mounted) setLoading(false)
      }
    })()
    return () => { mounted = false }
  }, [dateParams])

  const productNameById = useMemo(() => {
    const map = new Map(products.map((p) => [p.id, p.name]))
    return (id: string) => map.get(id) || id
  }, [products])

  const totals = useMemo(() => {
    const sales = productRows.reduce((acc, r) => acc + (r.sales_net || 0), 0)
    const cogs = productRows.reduce((acc, r) => acc + (r.cogs || 0), 0)
    const profit = productRows.reduce((acc, r) => acc + (r.gross_profit || 0), 0)
    const margin = sales > 0 ? profit / sales : 0
    return { sales, cogs, profit, margin }
  }, [productRows])

  const topByProfit = useMemo(() => {
    return [...productRows].sort((a, b) => (b.gross_profit || 0) - (a.gross_profit || 0)).slice(0, 5)
  }, [productRows])

  const worstByMargin = useMemo(() => {
    return [...productRows].sort((a, b) => (a.margin_pct || 0) - (b.margin_pct || 0)).slice(0, 5)
  }, [productRows])

  const alerts = useMemo(() => {
    const low = productRows.filter((r) => (r.margin_pct || 0) < threshold)
    const negative = productRows.filter((r) => (r.gross_profit || 0) < 0)
    return { low, negative }
  }, [productRows, threshold])

  if (!can('reportes:read')) {
    return <PermissionDenied permission="reportes:read" />
  }

  return (
    <div className="reports-shell">
      <div className="reports-hero">
        <div>
          <h1>{t('reportes:margins.title')}</h1>
          <p>{t('reportes:margins.subtitle')}</p>
        </div>
        <div className="reports-filters">
          <div className="field">
            <label>{t('reportes:margins.filters.from')}</label>
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </div>
          <div className="field">
            <label>{t('reportes:margins.filters.to')}</label>
            <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </div>
          <div className="field">
            <label>{t('reportes:margins.filters.warehouse')}</label>
            <select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)}>
              <option value="">{t('reportes:all')}</option>
              {warehouses.map((w) => (
                <option key={w.id} value={w.id}>{w.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>{t('reportes:margins.filters.threshold')}</label>
            <input
              type="number"
              min={0}
              max={1}
              step="0.01"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
            />
          </div>
        </div>
      </div>

      <div className="reports-cards">
        <div className="card">
          <span>{t('reportes:margins.cards.netSales')}</span>
          <strong>{formatMoney(totals.sales, companySettings)}</strong>
        </div>
        <div className="card">
          <span>{t('reportes:margins.cards.cogs')}</span>
          <strong>{formatMoney(totals.cogs, companySettings)}</strong>
        </div>
        <div className="card highlight">
          <span>{t('reportes:margins.cards.grossProfit')}</span>
          <strong>{formatMoney(totals.profit, companySettings)}</strong>
        </div>
        <div className="card">
          <span>{t('reportes:margins.cards.grossMargin')}</span>
          <strong>{formatPct(totals.margin)}</strong>
        </div>
      </div>

      <div className="reports-grid">
         <div className="panel">
           <h3>{t('reportes:topProfit')}</h3>
           {topByProfit.map((r) => (
             <div key={r.product_id} className="row">
               <span>{productNameById(r.product_id)}</span>
               <strong>{formatMoney(r.gross_profit, companySettings)}</strong>
             </div>
           ))}
         </div>
         <div className="panel">
           <h3>{t('reportes:worstMargin')}</h3>
           {worstByMargin.map((r) => (
             <div key={r.product_id} className="row">
               <span>{productNameById(r.product_id)}</span>
               <strong>{formatPct(r.margin_pct)}</strong>
             </div>
           ))}
         </div>
         <div className="panel">
           <h3>{t('reportes:alerts')}</h3>
           <p>{t('reportes:lowMargin')}: {alerts.low.length}</p>
           <p>{t('reportes:negativeProfit')}: {alerts.negative.length}</p>
         </div>
       </div>

       <div className="tabs">
          <button className={activeTab === 'productos' ? 'active' : ''} onClick={() => setActiveTab('productos')}>{t('reportes:margins.tabs.products')}</button>
        </div>

        {loading ? <div className="panel">{t('common:loading')}</div> : null}
       {error ? <div className="panel error">{error}</div> : null}

       {!loading && !error && activeTab === 'productos' ? (
        <div className="panel table-panel">
          <table>
            <thead>
              <tr>
                <th>{t('reportes:margins.table.product')}</th>
                <th>{t('reportes:margins.table.netSales')}</th>
                <th>{t('reportes:margins.table.cogs')}</th>
                <th>{t('reportes:margins.table.profit')}</th>
                <th>{t('reportes:margins.table.margin')}</th>
              </tr>
            </thead>
            <tbody>
              {productRows.map((r) => {
                const low = (r.margin_pct || 0) < threshold
                const neg = (r.gross_profit || 0) < 0
                return (
                  <tr key={r.product_id} className={neg ? 'neg' : low ? 'low' : ''}>
                    <td>{productNameById(r.product_id)}</td>
                    <td>{formatMoney(r.sales_net, companySettings)}</td>
                    <td>{formatMoney(r.cogs, companySettings)}</td>
                    <td>{formatMoney(r.gross_profit, companySettings)}</td>
                    <td>{formatPct(r.margin_pct)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : null}


    </div>
  )
}
