import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'

export interface ToastAction {
  label: string
  onClick: () => void | Promise<void>
}

export interface ToastOptions {
  duration?: number
  action?: ToastAction
  icon?: ReactNode
}

type Toast = {
  id: number | string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  options?: ToastOptions
}

interface ToastContextType {
  show: (msg: string, type?: Toast['type']) => void
  success: (msg: string, opts?: ToastOptions) => void
  error: (msg: string, opts?: ToastOptions) => void
  info: (msg: string, opts?: ToastOptions) => void
  warning: (msg: string, opts?: ToastOptions) => void
  showToast: (msg: string, type?: Toast['type']) => void
  dismiss: (id: string | number) => void
}

const ToastCtx = createContext<ToastContextType | null>(null)

const ICONS = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const show = useCallback((message: string, type: Toast['type'] = 'info', opts?: ToastOptions) => {
    const id = Date.now() + Math.random()
    const duration = opts?.duration ?? (type === 'error' ? 5000 : 3000)
    setToasts((t) => [...t, { id, type, message, options: opts }])
    if (duration > 0) {
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), duration)
    }
  }, [])

  const success = useCallback((m: string, opts?: ToastOptions) => show(m, 'success', opts), [show])
  const error = useCallback((m: string, opts?: ToastOptions) => show(m, 'error', opts), [show])
  const info = useCallback((m: string, opts?: ToastOptions) => show(m, 'info', opts), [show])
  const warning = useCallback((m: string, opts?: ToastOptions) => show(m, 'warning', opts), [show])
  const showToast = useCallback((m: string, type?: Toast['type']) => show(m, type), [show])
  const dismiss = useCallback((id: string | number) => {
    setToasts((t) => t.filter((x) => x.id !== id))
  }, [])

  return (
    <ToastCtx.Provider value={{ show, success, error, info, warning, showToast, dismiss }}>
      {children}
      <div
        style={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          maxWidth: 400,
        }}
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              background:
                t.type === 'success'
                  ? '#10b981'
                  : t.type === 'error'
                    ? '#ef4444'
                    : t.type === 'warning'
                      ? '#f59e0b'
                      : '#3b82f6',
              color: 'white',
              padding: '12px 16px',
              borderRadius: 6,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              animation: 'slideIn 0.3s ease-out',
              fontSize: '14px',
              fontWeight: 500,
            }}
          >
            <span style={{ fontSize: '18px', flexShrink: 0 }}>{t.options?.icon || ICONS[t.type]}</span>
            <span style={{ flex: 1 }}>{t.message}</span>
            {t.options?.action && (
              <button
                onClick={async () => {
                  await t.options!.action.onClick()
                  dismiss(t.id)
                }}
                style={{
                  flexShrink: 0,
                  padding: '6px 12px',
                  background: 'rgba(255,255,255,0.2)',
                  border: 'none',
                  borderRadius: 4,
                  color: 'inherit',
                  fontWeight: 600,
                  cursor: 'pointer',
                  marginLeft: 8,
                }}
              >
                {t.options.action.label}
              </button>
            )}
            <button
              onClick={() => dismiss(t.id)}
              style={{
                flexShrink: 0,
                width: 24,
                height: 24,
                padding: 0,
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                borderRadius: 4,
                color: 'inherit',
                fontSize: 16,
                cursor: 'pointer',
                marginLeft: 4,
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(400px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </ToastCtx.Provider>
  )
}

export function useToast(): ToastContextType {
  const ctx = useContext(ToastCtx)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
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
