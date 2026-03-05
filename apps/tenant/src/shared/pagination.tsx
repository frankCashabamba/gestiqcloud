import React from 'react'
import { useTranslation } from 'react-i18next'

export function usePagination<T>(items: T[], perPageDefault = 10) {
  const [page, setPage] = React.useState(1)
  const [perPage, setPerPage] = React.useState(perPageDefault)
  const totalPages = Math.max(1, Math.ceil(items.length / perPage))
  const start = (page - 1) * perPage
  const view = items.slice(start, start + perPage)
  React.useEffect(() => { if (page > totalPages) setPage(totalPages) }, [totalPages])
  return { page, setPage, perPage, setPerPage, totalPages, view }
}

type Props = { page: number; totalPages: number; onPageChange?: (p: number)=>void; setPage?: (p: number)=>void; className?: string }
export function Pagination({ page, setPage, onPageChange, totalPages, className }: Props) {
  const { t } = useTranslation('common')
  if (totalPages <= 1) return null
  const set = onPageChange || setPage || (()=>{})
  const prev = () => set(Math.max(1, page - 1))
  const next = () => set(Math.min(totalPages, page + 1))
  return (
    <div className={`flex items-center gap-2 text-sm mt-3 ${className || ''}`}>
      <button className="px-2 py-1 border rounded" onClick={prev} disabled={page===1}>{t('pagination.prev')}</button>
      <span>{t('pagination.pageOf', { page, totalPages })}</span>
      <button className="px-2 py-1 border rounded" onClick={next} disabled={page===totalPages}>{t('pagination.next')}</button>
    </div>
  )
}
