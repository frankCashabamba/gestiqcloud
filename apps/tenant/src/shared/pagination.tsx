import React from 'react'

export function usePagination<T>(items: T[], perPageDefault = 10) {
  const [page, setPage] = React.useState(1)
  const [perPage, setPerPage] = React.useState(perPageDefault)
  const totalPages = Math.max(1, Math.ceil(items.length / perPage))
  const start = (page - 1) * perPage
  const view = items.slice(start, start + perPage)
  React.useEffect(() => { if (page > totalPages) setPage(totalPages) }, [totalPages])
  return { page, setPage, perPage, setPerPage, totalPages, view }
}

type Props = { page: number; setPage: (p: number)=>void; totalPages: number }
export function Pagination({ page, setPage, totalPages }: Props) {
  if (totalPages <= 1) return null
  const prev = () => setPage(Math.max(1, page - 1))
  const next = () => setPage(Math.min(totalPages, page + 1))
  return (
    <div className="flex items-center gap-2 text-sm mt-3">
      <button className="px-2 py-1 border rounded" onClick={prev} disabled={page===1}>Prev</button>
      <span>Página {page} de {totalPages}</span>
      <button className="px-2 py-1 border rounded" onClick={next} disabled={page===totalPages}>Next</button>
    </div>
  )
}

