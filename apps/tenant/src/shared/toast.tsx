import React, { createContext, useContext, useState, useCallback } from 'react'

type Toast = { id: number; type: 'success' | 'error' | 'info' | 'warning'; message: string }

const ToastCtx = createContext<{ show: (msg: string, type?: Toast['type']) => void } | null>(null)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const show = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, type, message }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000)
  }, [])

  return (
    <ToastCtx.Provider value={{ show }}>
      {children}
      <div style={{ position: 'fixed', top: 12, right: 12, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              background:
                t.type === 'success'
                  ? '#16a34a'
                  : t.type === 'error'
                  ? '#dc2626'
                  : t.type === 'warning'
                  ? '#f59e0b'
                  : '#334155',
              color: 'white',
              padding: '10px 12px',
              borderRadius: 8,
              boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            }}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastCtx)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  const success = (m: string) => ctx.show(m, 'success')
  const error = (m: string) => ctx.show(m, 'error')
  const info = (m: string) => ctx.show(m, 'info')
  const warning = (m: string) => ctx.show(m, 'warning')
  // Compat: algunas páginas esperan showToast(message, type)
  const showToast = (m: string, type?: Toast['type']) => ctx.show(m, type)
  return { show: ctx.show, success, error, info, warning, showToast }
}

export function getErrorMessage(e: any): string {
  const d = e?.response?.data
  const detail = d?.detail
  if (Array.isArray(detail)) {
    const msgs = detail.map((it: any) => {
      const loc = (it?.loc || []).filter((x: any) => x !== 'body').join('.')
      return loc ? `${loc}: ${it?.msg || 'invalid value'}` : it?.msg || 'invalid value'
    })
    return msgs.join('; ')
  }
  if (typeof detail === 'string') return detail
  return e?.message || 'Unknown error'
}
