import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../services/api/client'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[],
): Promise<{ reply: string; suggestions: string[] }> {
  const res = await api.post('/api/v1/tenant/ai/chat', { message, history })
  return res.data
}

export default function CopilotChatWidget() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([
    t('components.copilot.suggestions.sales'),
    t('components.copilot.suggestions.lowStock'),
    t('components.copilot.suggestions.topSelling'),
  ])
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
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    setSuggestions([])

    try {
      const history = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))
      const data = await sendChatMessage(msg, history)
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.reply,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMsg])
      if (data.suggestions?.length) {
        setSuggestions(data.suggestions)
      }
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: t('common:copilot.connectionError'),
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
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
            background: '#fff',
            border: '1px solid #e2e8f0',
          }}
        >
          {/* Header */}
          <div
            style={{
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              color: '#fff',
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
                <div style={{ fontWeight: 600, fontSize: '14px' }}>{t('common:copilot.title')}</div>
                <div style={{ fontSize: '11px', opacity: 0.85 }}>{t('common:copilot.subtitle')}</div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: 'none',
                color: '#fff',
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

          {/* Messages */}
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
              background: '#f8fafc',
            }}
          >
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', color: '#94a3b8', padding: '24px 12px', fontSize: '13px' }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>💬</div>
                <p style={{ fontWeight: 500, marginBottom: '4px' }}>{t('components.copilot.greeting')}</p>
                <p>{t('components.copilot.helpText')}</p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '8px 12px',
                    borderRadius: msg.role === 'user' ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                    background: msg.role === 'user' ? '#6366f1' : '#fff',
                    color: msg.role === 'user' ? '#fff' : '#1e293b',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                <div
                  style={{
                    padding: '8px 16px',
                    borderRadius: '12px 12px 12px 2px',
                    background: '#fff',
                    fontSize: '13px',
                    color: '#94a3b8',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                  }}
                >
                  <span style={{ display: 'inline-flex', gap: '3px' }}>
                    <span className="copilot-dot" style={{ animationDelay: '0s' }}>●</span>
                    <span className="copilot-dot" style={{ animationDelay: '0.2s' }}>●</span>
                    <span className="copilot-dot" style={{ animationDelay: '0.4s' }}>●</span>
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {suggestions.length > 0 && !loading && (
            <div
              style={{
                display: 'flex',
                gap: '6px',
                padding: '8px 12px',
                overflowX: 'auto',
                borderTop: '1px solid #f1f5f9',
                flexShrink: 0,
                background: '#fff',
              }}
            >
              {suggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(s)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    border: '1px solid #e2e8f0',
                    background: '#f8fafc',
                    color: '#6366f1',
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
              borderTop: '1px solid #e2e8f0',
              background: '#fff',
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
                border: '1px solid #e2e8f0',
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
                background: input.trim() && !loading ? '#6366f1' : '#e2e8f0',
                color: input.trim() && !loading ? '#fff' : '#94a3b8',
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
          background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
          color: '#fff',
          fontSize: '24px',
          cursor: 'pointer',
          boxShadow: '0 4px 16px rgba(99,102,241,0.4)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'transform 0.2s, box-shadow 0.2s',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = 'scale(1.1)'
          e.currentTarget.style.boxShadow = '0 6px 24px rgba(99,102,241,0.5)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 16px rgba(99,102,241,0.4)'
        }}
        title={t('components.copilot.buttonTitle')}
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
              background: '#ef4444',
              border: '2px solid #fff',
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
