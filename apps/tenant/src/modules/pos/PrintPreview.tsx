/**
 * Print Preview - Vista previa de impresión
 */
import React, { useState, useEffect } from 'react'

type PrintPreviewProps = {
  receiptId: string
  onClose: () => void
}

export default function PrintPreview({ receiptId, onClose }: PrintPreviewProps) {
  const [htmlContent, setHtmlContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [width, setWidth] = useState<'58mm' | '80mm'>('58mm')

  useEffect(() => {
    loadPrintHTML()
  }, [receiptId, width])

  const loadPrintHTML = async () => {
    try {
      setLoading(true)
      const response = await fetch(
        `/api/v1/pos/receipts/${receiptId}/print?width=${width}`,
        { credentials: 'include' }
      )
      const html = await response.text()
      setHtmlContent(html)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handlePrint = () => {
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(htmlContent)
      printWindow.document.close()
      printWindow.focus()
      setTimeout(() => {
        printWindow.print()
      }, 250)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-3xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Vista Previa de Impresión</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-2 hover:bg-slate-100"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Controles */}
        <div className="mt-4 flex items-center gap-4">
          <div className="flex gap-2">
            <button
              onClick={() => setWidth('58mm')}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                width === '58mm'
                  ? 'bg-blue-600 text-white'
                  : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              58mm
            </button>
            <button
              onClick={() => setWidth('80mm')}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                width === '80mm'
                  ? 'bg-blue-600 text-white'
                  : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              80mm
            </button>
          </div>

          <button
            onClick={handlePrint}
            disabled={loading}
            className="ml-auto rounded-lg bg-green-600 px-6 py-2 font-medium text-white hover:bg-green-500 disabled:bg-slate-300"
          >
            🖨️ Imprimir
          </button>
        </div>

        {/* Preview */}
        <div className="mt-6 max-h-[600px] overflow-auto rounded-lg border border-slate-200 bg-white p-4">
          {loading ? (
            <div className="flex justify-center p-12">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
            </div>
          ) : (
            <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
          )}
        </div>
      </div>
    </div>
  )
}
