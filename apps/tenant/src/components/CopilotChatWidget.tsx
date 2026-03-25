import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../services/api/client'
import { TENANT_AI } from '@shared/endpoints'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  id?: string          // message_id del backend (solo assistant, para feedback)
  feedback?: 'thumbs_up' | 'thumbs_down'
  streaming?: boolean  // true mientras se está recibiendo el stream
}

async function* streamChatMessage(
  message: string,
  history: { role: string; content: string }[],
  currentModule?: string,
): AsyncGenerator<{ chunk: string; done: boolean; suggestions?: string[]; message_id?: string }> {
  const baseURL = (api.defaults.baseURL || '').replace(/\/+$/, '')
  const token = localStorage.getItem('access_token_tenant') || ''

  const res = await fetch(`${baseURL}${TENANT_AI.chatStream}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: 'include',
    body: JSON.stringify({ message, history, current_module: currentModule }),
  })

  if (!res.ok || !res.body) {
    yield { chunk: 'Error al conectar con el asistente.', done: false }
    yield { chunk: '', done: true, suggestions: [] }
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          yield JSON.parse(line.slice(6))
        } catch {
          // ignore malformed SSE line
        }
      }
    }
  }
}

async function sendFeedback(messageId: string, rating: 'thumbs_up' | 'thumbs_down') {
  try {
    await api.post(TENANT_AI.feedback, { message_id: messageId, rating })
  } catch {
    // best-effort
  }
}

const MODULE_ROUTE_MATCHERS: Array<{ moduleId: string; matches: string[] }> = [
  { moduleId: 'manufacturing', matches: ['/manufacturing', '/production', '/produccion'] },
  { moduleId: 'inventory', matches: ['/inventory', '/inventario'] },
  { moduleId: 'purchases', matches: ['/purchases', '/compras'] },
  { moduleId: 'sales', matches: ['/sales', '/ventas'] },
  { moduleId: 'finance', matches: ['/finance', '/finanzas'] },
  { moduleId: 'accounting', matches: ['/accounting', '/contabilidad'] },
  { moduleId: 'einvoicing', matches: ['/einvoicing'] },
  { moduleId: 'invoicing', matches: ['/invoicing', '/facturacion'] },
  { moduleId: 'reconciliation', matches: ['/reconciliation', '/conciliacion'] },
  { moduleId: 'crm', matches: ['/crm'] },
  { moduleId: 'customers', matches: ['/customers', '/clientes', '/clients'] },
  { moduleId: 'suppliers', matches: ['/suppliers', '/proveedores'] },
  { moduleId: 'notifications', matches: ['/notifications', '/notificaciones'] },
  { moduleId: 'settings', matches: ['/settings', '/configuracion'] },
  { moduleId: 'users', matches: ['/users', '/usuarios'] },
  { moduleId: 'expenses', matches: ['/expenses', '/gastos'] },
  { moduleId: 'hr', matches: ['/hr', '/rrhh'] },
  { moduleId: 'products', matches: ['/products', '/productos'] },
  { moduleId: 'reports', matches: ['/reports', '/reportes'] },
  { moduleId: 'pos', matches: ['/pos'] },
]

function resolveCurrentModule(path: string): string | undefined {
  const match = MODULE_ROUTE_MATCHERS.find(entry => entry.matches.some(fragment => path.includes(fragment)))
  return match?.moduleId
}

export default function CopilotChatWidget() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [conversations, setConversations] = useState<{id: string, title: string | null, current_module: string | null, created_at: string, message_count: number}[]>([])

  const moduleSuggestions: Record<string, string[]> = {
    pos: ['¿Cuánto vendí hoy?', '¿Cuáles son los productos más vendidos?', '¿Hay un turno abierto?'],
    inventory: ['¿Qué productos tienen stock bajo?', '¿Cuál es el valor del inventario?', '¿Productos sin movimiento?'],
    purchases: ['¿Hay órdenes de compra pendientes?', '¿Cuánto gasté en compras este mes?', '¿Último pedido recibido?'],
    sales: ['¿Cómo van las ventas del mes?', '¿Quiénes son mis mejores clientes?', '¿Tendencia de ventas?'],
    manufacturing: ['¿Órdenes de producción activas?', '¿Qué receta tiene peor margen?', '¿Hay riesgo de rotura por ingredientes?'],
    expenses: ['¿Cuánto gasté este mes?', '¿Categorías de gasto principales?', '¿Comparar con mes anterior?'],
    finance: ['¿Resumen de cobros y pagos?', '¿Estado de cuentas?', '¿Flujo de caja?'],
    accounting: ['¿Cuántos asientos están en borrador?', '¿Últimos asientos contabilizados?', '¿Hay desbalances?'],
    crm: ['¿Cuántas oportunidades abiertas hay?', '¿Qué etapa concentra más valor?', '¿Cómo va la conversión?'],
    customers: ['¿Cuántos clientes tengo?', '¿Últimos clientes creados?', '¿Hay clientes mayoristas?'],
    suppliers: ['¿Cuántos proveedores activos tengo?', '¿Últimos proveedores creados?', '¿Compras pendientes?'],
    notifications: ['¿Cuántas notificaciones no leídas hay?', '¿Qué alertas recientes tengo?', '¿Hay algo urgente?'],
    reports: ['Resume mi último mes', '¿Dónde estoy perdiendo margen?', '¿Qué módulo necesita atención?'],
    users: ['¿Cuántos usuarios activos tengo?', '¿Cuántos administradores hay?', '¿Últimos usuarios creados?'],
    invoicing: ['¿Cuántas facturas hay pendientes?', '¿Últimas facturas emitidas?', '¿Importe facturado reciente?'],
    einvoicing: ['¿Qué envíos SRI/SII están pendientes?', '¿Hay rechazos recientes?', '¿Qué estado domina hoy?'],
    reconciliation: ['¿Qué conciliaciones siguen abiertas?', '¿Hay diferencias pendientes?', '¿Cómo van los movimientos bancarios?'],
    settings: ['Resume la configuración de la empresa', '¿Qué país y moneda están activos?', '¿Qué contexto general tengo?'],
  }
  const defaultSuggestions = [
    t('components.copilot.suggestions.sales'),
    t('components.copilot.suggestions.lowStock'),
    t('components.copilot.suggestions.topSelling'),
  ]

  const path = window.location.pathname.toLowerCase()
  const currentModule = resolveCurrentModule(path)

  const [suggestions, setSuggestions] = useState<string[]>(
    (currentModule && moduleSuggestions[currentModule]) || defaultSuggestions
  )
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus()
    }
  }, [open])

  const handleSend = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || loading) return

    const userMsg: ChatMessage = { role: 'user', content: msg, timestamp: new Date() }
    const assistantMsg: ChatMessage = { role: 'assistant', content: '', timestamp: new Date(), streaming: true }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setInput('')
    setLoading(true)
    setSuggestions([])

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }))
      history.push({ role: 'user', content: msg })

      const stream = streamChatMessage(msg, history, currentModule)

      for await (const event of stream) {
        if (!event.done) {
          setMessages(prev => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last.role === 'assistant') {
              updated[updated.length - 1] = { ...last, content: last.content + event.chunk }
            }
            return updated
          })
        } else {
          // Stream completado
          setMessages(prev => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                streaming: false,
                id: event.message_id ?? undefined,
              }
            }
            return updated
          })
          if (event.suggestions?.length) {
            setSuggestions(event.suggestions)
          }
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.role === 'assistant') {
          updated[updated.length - 1] = {
            ...last,
            content: t('common:copilot.connectionError'),
            streaming: false,
          }
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    try {
      const res = await api.get(TENANT_AI.conversations)
      setConversations(res.data)
    } catch { /* ignore */ }
  }

  const loadConversation = async (convId: string) => {
    try {
      const res = await api.get(`${TENANT_AI.conversations}/${convId}/messages`)
      const msgs: ChatMessage[] = res.data.map((m: any) => ({
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at),
        id: m.id,
      }))
      setMessages(msgs)
      setShowHistory(false)
    } catch { /* ignore */ }
  }

  const deleteConversation = async (convId: string) => {
    try {
      await api.delete(`${TENANT_AI.conversations}/${convId}`)
      setConversations(prev => prev.filter(c => c.id !== convId))
    } catch { /* ignore */ }
  }

  const toggleHistory = () => {
    if (!showHistory) loadHistory()
    setShowHistory(!showHistory)
  }

  const handleFeedback = async (msgIndex: number, rating: 'thumbs_up' | 'thumbs_down') => {
    const msg = messages[msgIndex]
    if (!msg?.id) return
    setMessages(prev =>
      prev.map((m, i) => (i === msgIndex ? { ...m, feedback: rating } : m))
    )
    await sendFeedback(msg.id, rating)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Unread indicator
  const [hasUnread, setHasUnread] = useState(false)
  useEffect(() => {
    if (!open && messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
      setHasUnread(true)
    }
  }, [messages, open])

  const handleOpen = () => {
    setOpen(true)
    setHasUnread(false)
  }

  return (
    <>
      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: '5rem',
            right: '1.5rem',
            width: '380px',
            maxHeight: '520px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
            background: 'var(--gc-surface)',
            border: '1px solid var(--gc-border)',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: 'linear-gradient(135deg, var(--gc-primary), var(--gc-primary-dark))',
              color: 'var(--gc-on-primary)',
              padding: '14px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '20px' }}>🤖</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '14px' }}>{t('copilot:title')}</div>
                <div style={{ fontSize: '11px', opacity: 0.85 }}>{t('copilot:subtitle')}</div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <button
                onClick={toggleHistory}
                style={{
                  background: showHistory ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.2)',
                  border: 'none',
                  color: 'var(--gc-on-primary)',
                  borderRadius: '50%',
                  width: '28px',
                  height: '28px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '14px',
                }}
                title="Historial de conversaciones"
              >
                📋
              </button>
              <button
                onClick={() => setOpen(false)}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  border: 'none',
                  color: 'var(--gc-on-primary)',
                  borderRadius: '50%',
                  width: '28px',
                  height: '28px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '16px',
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages / History */}
          {showHistory ? (
            <div
              style={{
                flex: 1,
                overflowY: 'auto',
                padding: '12px',
                minHeight: '200px',
                maxHeight: '320px',
                background: 'var(--gc-bg)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--gc-muted)' }}>Conversaciones anteriores</span>
                <button
                  onClick={() => { setMessages([]); setShowHistory(false) }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--gc-primary)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  + Nueva conversación
                </button>
              </div>
              {conversations.length === 0 && (
                <p style={{ fontSize: '13px', color: 'var(--gc-muted)', textAlign: 'center', padding: '24px 0' }}>Sin conversaciones guardadas</p>
              )}
              {conversations.map(conv => (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  style={{
                    padding: '8px',
                    borderRadius: '8px',
                    border: '1px solid var(--gc-border)',
                    marginBottom: '6px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'var(--gc-surface)',
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: '13px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', margin: 0 }}>{conv.title || 'Conversación'}</p>
                    <p style={{ fontSize: '11px', color: 'var(--gc-muted)', margin: 0 }}>
                      {conv.current_module && `${conv.current_module} · `}
                      {conv.message_count} msgs · {new Date(conv.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteConversation(conv.id) }}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '14px',
                      color: 'var(--gc-muted)',
                      padding: '2px 4px',
                      marginLeft: '8px',
                    }}
                    title="Eliminar"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          ) : (
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              minHeight: '200px',
              maxHeight: '320px',
              background: 'var(--gc-bg)',
            }}
          >
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--gc-muted)', padding: '24px 12px', fontSize: '13px' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>💬</div>
                <p style={{ fontWeight: 500, marginBottom: '4px' }}>{t('copilot:widgetGreeting')}</p>
                <p>{t('copilot:widgetHelpText')}</p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '8px 12px',
                    borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                    background: msg.role === 'user' ? 'var(--gc-primary)' : 'var(--gc-surface)',
                    color: msg.role === 'user' ? 'var(--gc-on-primary)' : 'var(--gc-foreground)',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.content}
                  {msg.streaming && (
                    <span style={{ display: 'inline-flex', gap: '2px', marginLeft: '4px', verticalAlign: 'middle' }}>
                      <span className="copilot-dot" style={{ animationDelay: '0s' }}>●</span>
                      <span className="copilot-dot" style={{ animationDelay: '0.2s' }}>●</span>
                      <span className="copilot-dot" style={{ animationDelay: '0.4s' }}>●</span>
                    </span>
                  )}
                </div>

                {/* Feedback buttons — solo en mensajes assistant completos con id */}
                {msg.role === 'assistant' && !msg.streaming && msg.id && (
                  <div style={{ display: 'flex', gap: '4px', marginTop: '4px' }}>
                    <button
                      onClick={() => handleFeedback(idx, 'thumbs_up')}
                      title="Útil"
                      style={{
                        background: 'none',
                        border: '1px solid var(--gc-border)',
                        borderRadius: '6px',
                        padding: '2px 6px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        opacity: msg.feedback === 'thumbs_up' ? 1 : 0.5,
                        color: msg.feedback === 'thumbs_up' ? 'var(--gc-success, #22c55e)' : 'var(--gc-muted)',
                        transition: 'opacity 0.15s',
                      }}
                    >
                      👍
                    </button>
                    <button
                      onClick={() => handleFeedback(idx, 'thumbs_down')}
                      title="No útil"
                      style={{
                        background: 'none',
                        border: '1px solid var(--gc-border)',
                        borderRadius: '6px',
                        padding: '2px 6px',
                        cursor: 'pointer',
                        fontSize: '12px',
                        opacity: msg.feedback === 'thumbs_down' ? 1 : 0.5,
                        color: msg.feedback === 'thumbs_down' ? 'var(--gc-danger, #ef4444)' : 'var(--gc-muted)',
                        transition: 'opacity 0.15s',
                      }}
                    >
                      👎
                    </button>
                  </div>
                )}
              </div>
            ))}

            <div ref={messagesEndRef} />
          </div>
          )}

          {/* Suggestions */}
          {suggestions.length > 0 && !loading && (
            <div
              style={{
                display: 'flex',
                gap: '6px',
                padding: '8px 12px',
                overflowX: 'auto',
                borderTop: '1px solid var(--gc-bg)',
                flexShrink: 0,
                background: 'var(--gc-surface)',
              }}
            >
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(s)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    border: '1px solid var(--gc-border)',
                    background: 'var(--gc-bg)',
                    color: 'var(--gc-primary)',
                    fontSize: '11px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div
            style={{
              display: 'flex',
              gap: '8px',
              padding: '10px 12px',
              borderTop: '1px solid var(--gc-border)',
              background: 'var(--gc-surface)',
              flexShrink: 0,
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('components.copilot.inputPlaceholder')}
              disabled={loading}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                border: '1px solid var(--gc-border)',
                fontSize: '13px',
                outline: 'none',
              }}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                border: 'none',
                background: input.trim() && !loading ? 'var(--gc-primary)' : 'var(--gc-border)',
                color: input.trim() && !loading ? 'var(--gc-on-primary)' : 'var(--gc-muted)',
                cursor: input.trim() && !loading ? 'pointer' : 'default',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              ➤
            </button>
          </div>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={open ? () => setOpen(false) : handleOpen}
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          border: 'none',
          background: 'linear-gradient(135deg, var(--gc-primary), var(--gc-primary-dark))',
          color: 'var(--gc-on-primary)',
          fontSize: '24px',
          cursor: 'pointer',
          boxShadow: '0 4px 16px color-mix(in srgb, var(--gc-primary) 40%, transparent)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = 'scale(1.1)'
          e.currentTarget.style.boxShadow = '0 6px 24px color-mix(in srgb, var(--gc-primary) 50%, transparent)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 16px color-mix(in srgb, var(--gc-primary) 40%, transparent)'
        }}
        title={t('copilot:buttonTitle')}
      >
        {open ? '✕' : '🤖'}
        {hasUnread && !open && (
          <span
            style={{
              position: 'absolute',
              top: '2px',
              right: '2px',
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: 'var(--gc-danger)',
              border: '2px solid var(--gc-surface)',
            }}
          />
        )}
      </button>

      {/* CSS animation for typing dots */}
      <style>{`
        @keyframes copilotBlink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }
        .copilot-dot {
          animation: copilotBlink 1.2s infinite;
          font-size: 10px;
        }
      `}</style>
    </>
  )
}
