import React, { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BackButton } from '@ui'
import { useTranslation } from 'react-i18next'
import { listProveedores, removeProveedor, type Proveedor } from './services'
import { useToast, getErrorMessage } from '../../shared/toast'
import { usePagination, Pagination } from '../../shared/pagination'
import { usePermission } from '../../hooks/usePermission'
import PermissionDenied from '../../components/PermissionDenied'

export default function ProveedoresList() {
  const { t } = useTranslation(['suppliers', 'common'])
  const can = usePermission()
  const [items, setItems] = useState<Proveedor[]>([])
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [filterActivo, setFilterActivo] = useState<'all' | 'active' | 'inactive'>('active')
  const [deleteId, setDeleteId] = useState<number | string | null>(null)
  const nav = useNavigate()
  const { success, error: toastError } = useToast()

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await listProveedores()
        if (cancelled) return
        setItems(data)
      } catch (e: any) {
        if (cancelled) return
        const m = getErrorMessage(e)
        setErrMsg(m)
        toastError(m)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const filtered = useMemo(() => {
    let result = items

    // Filtro activo/inactivo
    if (filterActivo === 'active') {
      result = result.filter((p) => p.active !== false)
    } else if (filterActivo === 'inactive') {
      result = result.filter((p) => p.active === false)
    }

    // Búsqueda por texto
    const term = q.toLowerCase()
    if (term) {
      result = result.filter((p) => {
        const nombre = (p.name || '').toLowerCase()
        const nombreComercial = (p.nombre_comercial || '').toLowerCase()
        const nif = (p.nif || '').toLowerCase()
        const email = (p.email || '').toLowerCase()
        return (
          nombre.includes(term) ||
          nombreComercial.includes(term) ||
          nif.includes(term) ||
          email.includes(term)
        )
      })
    }

    return result
  }, [items, q, filterActivo])

  const { page, setPage, totalPages, view } = usePagination(filtered, 15)

  const handleRemove = async () => {
    if (!deleteId) return
    const id = deleteId
    setDeleteId(null)
    try {
      await removeProveedor(id)
      setItems((prev) => prev.filter((p) => p.id !== id))
      success(t('suppliers:messages.deactivated'))
    } catch (e: any) {
      toastError(getErrorMessage(e))
    }
  }

  if (!can('suppliers:read')) {
    return <PermissionDenied permission="suppliers:read" />
  }

  return (
    <div className="p-4 space-y-4">
      <div style={{ marginBottom: '0.75rem' }}><BackButton onClick={() => nav(-1)} /></div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{t('suppliers:title')}</h2>
          <p className="text-sm text-slate-500">
            {t('suppliers:subtitle')}
          </p>
        </div>
        {can('suppliers:create') && (
          <button className="gc-button gc-button--primary" onClick={() => nav('new')}>
            + {t('suppliers:new')}
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('suppliers:searchPlaceholder')}
          className="w-full max-w-md rounded-xl border border-slate-200 px-4 py-2 text-sm"
        />
        <select
          value={filterActivo}
          onChange={(e) => setFilterActivo(e.target.value as any)}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
        >
          <option value="all">{t('common:all')}</option>
          <option value="active">{t('suppliers:status.active')}</option>
          <option value="inactive">{t('suppliers:status.inactive')}</option>
        </select>
      </div>

      {loading && <div className="text-sm text-slate-500">{t('suppliers:loading')}</div>}
      {errMsg && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">
          {errMsg}
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">{t('suppliers:table.code')}</th>
              <th className="px-4 py-3">{t('suppliers:table.name')}</th>
              <th className="px-4 py-3">{t('suppliers:table.nif')}</th>
              <th className="px-4 py-3">{t('suppliers:table.email')}</th>
              <th className="px-4 py-3">{t('suppliers:table.phone')}</th>
              <th className="px-4 py-3">{t('suppliers:table.country')}</th>
              <th className="px-4 py-3">{t('common:status')}</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {view.map((p) => (
              <tr key={p.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3 font-mono text-xs text-slate-600">
                  PRV-{String(p.id).padStart(5, '0')}
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`${p.id}`}
                    className="font-medium text-blue-600 hover:text-blue-500 hover:underline"
                  >
                    {p.name}
                  </Link>
                  {p.nombre_comercial && (
                    <div className="text-xs text-slate-500">{p.nombre_comercial}</div>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-600">{p.nif || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.email || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.phone || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{p.pais || '—'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                      p.active !== false
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {p.active !== false ? t('suppliers:status.active') : t('suppliers:status.inactive')}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex flex-wrap items-center justify-end gap-3">
                    {can('suppliers:update') && (
                      <Link
                        to={`${p.id}/edit`}
                        className="text-sm font-medium text-blue-600 hover:text-blue-500"
                      >
                        {t('common:edit')}
                      </Link>
                    )}
                    {can('suppliers:delete') && (
                      <button
                        className="text-sm font-medium text-rose-600 hover:text-rose-500"
                        onClick={() => setDeleteId(p.id)}
                      >
                        {t('suppliers:actions.deactivate')}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!loading && view.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={8}>
                  {t('suppliers:empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} setPage={setPage} totalPages={totalPages} />

      {deleteId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDeleteId(null)}>
          <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="font-bold text-gray-900 mb-2">{t('suppliers:confirmDelete')}</h3>
            <p className="text-sm text-gray-500 mb-5">{t('suppliers:confirmDeleteBody', 'Esta acción desactivará al proveedor.')}</p>
            <div className="flex gap-2 justify-end">
              <button className="px-4 py-2 border rounded-xl text-sm" onClick={() => setDeleteId(null)}>{t('common:cancel')}</button>
              <button className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-semibold" onClick={() => void handleRemove()}>{t('suppliers:actions.deactivate')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
