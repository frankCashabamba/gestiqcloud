import React from 'react'
import { useTranslation } from 'react-i18next'

type Props = {
  /** Clave canónica del módulo afectado (para el mensaje y el log). */
  module: string
  children: React.ReactNode
}

type State = {
  hasError: boolean
  error: Error | null
}

/**
 * ModuleErrorBoundary
 *
 * Aísla los errores de render de un módulo para que una excepción en uno
 * no tumbe toda la app tenant. Muestra un fallback con el módulo afectado,
 * botones para recargar o volver, y el detalle del error en modo dev.
 *
 * El error se registra en consola y se emite el evento `tenant:module-error`
 * en window, para que cualquier capa de telemetría lo recoja sin acoplar
 * este componente a una implementación concreta.
 */
export default class ModuleErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Siempre dejamos rastro en consola.
    // eslint-disable-next-line no-console
    console.error(`[module:${this.props.module}] render error`, error, info)
    if (typeof window !== 'undefined') {
      try {
        window.dispatchEvent(
          new CustomEvent('tenant:module-error', {
            detail: {
              module: this.props.module,
              message: error?.message,
              stack: error?.stack,
              componentStack: info?.componentStack,
            },
          }),
        )
      } catch {
        /* no-op: el boundary nunca debe fallar por el log */
      }
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <ModuleErrorFallback
          module={this.props.module}
          error={this.state.error}
          onRetry={this.handleReset}
        />
      )
    }
    return this.props.children
  }
}

function ModuleErrorFallback({
  module,
  error,
  onRetry,
}: {
  module: string
  error: Error | null
  onRetry: () => void
}) {
  const { t } = useTranslation()
  const isDev = Boolean((import.meta as any)?.env?.DEV)

  return (
    <div
      role="alert"
      style={{
        margin: '2rem auto',
        maxWidth: 640,
        padding: '2rem',
        textAlign: 'center',
        borderRadius: '0.5rem',
        backgroundColor: 'color-mix(in srgb, var(--gc-danger) 8%, white)',
        border: '1px solid color-mix(in srgb, var(--gc-danger) 30%, white)',
      }}
    >
      <h2 style={{ color: 'var(--gc-danger)', marginBottom: '0.5rem' }}>
        {t('errors.moduleCrashedTitle', 'Este módulo tuvo un problema')}
      </h2>
      <p style={{ color: 'var(--gc-foreground)', marginBottom: '1rem' }}>
        {t('errors.moduleCrashedBody', 'El módulo')} <code>{module}</code>{' '}
        {t('errors.moduleCrashedBodyTail', 'no pudo mostrarse correctamente.')}
      </p>

      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
        <button type="button" onClick={onRetry} style={btnStyle('var(--gc-primary, #2563eb)')}>
          {t('common.retry', 'Reintentar')}
        </button>
        <button type="button" onClick={() => window.location.reload()} style={btnStyle('#6b7280')}>
          {t('common.reload', 'Recargar página')}
        </button>
        <button type="button" onClick={() => window.history.back()} style={btnStyle('#6b7280', true)}>
          {t('common.goBack', 'Volver')}
        </button>
      </div>

      {isDev && error && (
        <pre
          style={{
            marginTop: '1.5rem',
            padding: '1rem',
            textAlign: 'left',
            overflow: 'auto',
            maxHeight: 240,
            fontSize: '0.75rem',
            background: '#0b1020',
            color: '#e5e7eb',
            borderRadius: '0.375rem',
          }}
        >
          {error.message}
          {'\n\n'}
          {error.stack}
        </pre>
      )}
    </div>
  )
}

function btnStyle(color: string, outline = false): React.CSSProperties {
  return {
    padding: '0.5rem 1rem',
    borderRadius: '0.375rem',
    cursor: 'pointer',
    fontSize: '0.875rem',
    border: outline ? `1px solid ${color}` : 'none',
    background: outline ? 'transparent' : color,
    color: outline ? color : 'white',
  }
}
