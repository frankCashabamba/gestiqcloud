/**
 * ConflictResolver - Modal for resolving offline sync conflicts
 * 
 * Shows local vs remote versions of conflicted entities
 * and allows user to choose which version to keep
 */

import React, { useEffect, useState } from 'react'
import { getSyncManager } from '@/lib/syncManager'
import { ConflictInfo } from '@/lib/offlineStore'

type ResolutionChoice = 'local' | 'remote' | null

interface ConflictResolverProps {
  onConflictResolved?: () => void
}

export default function ConflictResolver({ onConflictResolved }: ConflictResolverProps) {
  const [conflicts, setConflicts] = useState<ConflictInfo[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number>(-1)
  const [resolving, setResolving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const checkConflicts = async () => {
      try {
        const manager = getSyncManager()
        const all = await manager.getConflicts()
        setConflicts(all)
      } catch (error) {
        console.error('Failed to fetch conflicts:', error)
      }
    }

    // Check initially
    checkConflicts()

    // Re-check periodically
    const interval = setInterval(checkConflicts, 5000)

    return () => clearInterval(interval)
  }, [])

  const handleResolve = async (choice: ResolutionChoice) => {
    if (!choice || selectedIdx < 0) return

    const conflict = conflicts[selectedIdx]
    setResolving(true)
    setMessage(null)

    try {
      const manager = getSyncManager()
      await manager.resolveConflict(
        conflict.entity,
        conflict.id,
        choice,
        choice === 'remote' ? conflict.remote : undefined
      )

      setMessage(`✅ Conflicto resuelto (usando ${choice === 'local' ? 'cambios locales' : 'versión servidor'})`)
      
      // Remove from list
      setTimeout(() => {
        setConflicts(c => c.filter((_, i) => i !== selectedIdx))
        setSelectedIdx(-1)
        setMessage(null)
        onConflictResolved?.()
      }, 1500)
    } catch (error) {
      console.error('Failed to resolve conflict:', error)
      setMessage('❌ Error al resolver conflicto. Intenta de nuevo.')
    } finally {
      setResolving(false)
    }
  }

  if (conflicts.length === 0) return null

  const selected = selectedIdx >= 0 ? conflicts[selectedIdx] : null

  const getDiffFields = (local: any, remote: any) => {
    const fields: string[] = []
    if (!remote) return fields
    
    const allKeys = new Set([...Object.keys(local || {}), ...Object.keys(remote || {})])
    for (const key of allKeys) {
      if (local[key] !== remote[key]) {
        fields.push(key)
      }
    }
    return fields
  }

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.75)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '1rem',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <div style={{
        background: 'white',
        borderRadius: 12,
        padding: '2rem',
        maxWidth: 1000,
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
        animation: 'slideUp 0.3s ease'
      }}>
        {/* Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ margin: '0 0 0.5rem', color: '#e74c3c', fontSize: '1.5rem' }}>
            ⚠️ Conflictos de Sincronización
          </h2>
          <p style={{ margin: 0, color: '#666', fontSize: '0.95rem' }}>
            {conflicts.length} conflicto(s) detectado(s). Elige qué versión mantener.
          </p>
        </div>

        {/* List or Detail View */}
        {!selected ? (
          <div>
            <div style={{ marginBottom: '1rem', maxHeight: 400, overflow: 'auto' }}>
              {conflicts.map((c, idx) => (
                <button
                  key={`${c.entity}:${c.id}`}
                  onClick={() => setSelectedIdx(idx)}
                  style={{
                    width: '100%',
                    padding: '1rem',
                    border: '1px solid #ddd',
                    borderRadius: 8,
                    marginBottom: '0.5rem',
                    background: '#f9f9f9',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.2s',
                    fontSize: '0.95rem'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = '#f0f0f0'
                    e.currentTarget.style.borderColor = '#999'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = '#f9f9f9'
                    e.currentTarget.style.borderColor = '#ddd'
                  }}
                >
                  <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
                    {c.entity.toUpperCase()} • {c.id}
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#999' }}>
                    Local v{c.localVersion} vs Servidor v{c.remoteVersion}
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div>
            {/* Conflict Detail */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ margin: '0 0 1rem', fontSize: '1.2rem' }}>
                {selected.entity.toUpperCase()}: {selected.id}
              </h3>

              {/* Diff Fields */}
              {getDiffFields(selected.local, selected.remote).length > 0 && (
                <div style={{
                  background: '#fff3cd',
                  border: '1px solid #ffc107',
                  borderRadius: 6,
                  padding: '0.75rem',
                  marginBottom: '1rem',
                  fontSize: '0.9rem'
                }}>
                  <strong>Campos en conflicto:</strong> {getDiffFields(selected.local, selected.remote).join(', ')}
                </div>
              )}

              {/* Comparison Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '1.5rem',
                marginBottom: '1.5rem'
              }}>
                {/* Local Version */}
                <div style={{
                  border: '2px solid #4CAF50',
                  borderRadius: 8,
                  padding: '1rem',
                  background: '#f1f8f4'
                }}>
                  <h4 style={{
                    margin: '0 0 0.75rem',
                    color: '#2e7d32',
                    fontSize: '0.95rem',
                    fontWeight: 600
                  }}>
                    📱 Cambios Locales (v{selected.localVersion})
                  </h4>
                  <pre style={{
                    margin: 0,
                    fontSize: '0.8rem',
                    maxHeight: 350,
                    overflow: 'auto',
                    background: 'white',
                    padding: '0.75rem',
                    borderRadius: 4,
                    border: '1px solid #e0e0e0',
                    color: '#333'
                  }}>
                    {JSON.stringify(selected.local, null, 2)}
                  </pre>
                </div>

                {/* Remote Version */}
                <div style={{
                  border: '2px solid #FF9800',
                  borderRadius: 8,
                  padding: '1rem',
                  background: '#fff8f1'
                }}>
                  <h4 style={{
                    margin: '0 0 0.75rem',
                    color: '#e65100',
                    fontSize: '0.95rem',
                    fontWeight: 600
                  }}>
                    🌐 Versión Servidor (v{selected.remoteVersion})
                  </h4>
                  <pre style={{
                    margin: 0,
                    fontSize: '0.8rem',
                    maxHeight: 350,
                    overflow: 'auto',
                    background: 'white',
                    padding: '0.75rem',
                    borderRadius: 4,
                    border: '1px solid #e0e0e0',
                    color: '#333'
                  }}>
                    {JSON.stringify(selected.remote || {}, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Resolution Message */}
              {message && (
                <div style={{
                  background: message.startsWith('✅') ? '#d4edda' : '#f8d7da',
                  border: `1px solid ${message.startsWith('✅') ? '#c3e6cb' : '#f5c6cb'}`,
                  color: message.startsWith('✅') ? '#155724' : '#721c24',
                  padding: '0.75rem',
                  borderRadius: 6,
                  marginBottom: '1rem',
                  fontSize: '0.9rem'
                }}>
                  {message}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: '0.75rem'
              }}>
                <button
                  onClick={() => handleResolve('local')}
                  disabled={resolving}
                  style={{
                    padding: '0.75rem',
                    background: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: resolving ? 'wait' : 'pointer',
                    fontWeight: 'bold',
                    fontSize: '0.9rem',
                    opacity: resolving ? 0.7 : 1,
                    transition: 'opacity 0.2s'
                  }}
                >
                  ✅ Usar Locales
                </button>

                <button
                  onClick={() => handleResolve('remote')}
                  disabled={resolving}
                  style={{
                    padding: '0.75rem',
                    background: '#FF9800',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: resolving ? 'wait' : 'pointer',
                    fontWeight: 'bold',
                    fontSize: '0.9rem',
                    opacity: resolving ? 0.7 : 1,
                    transition: 'opacity 0.2s'
                  }}
                >
                  ✅ Usar Servidor
                </button>

                <button
                  onClick={() => setSelectedIdx(-1)}
                  disabled={resolving}
                  style={{
                    padding: '0.75rem',
                    background: '#999',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: resolving ? 'wait' : 'pointer',
                    fontSize: '0.9rem',
                    opacity: resolving ? 0.7 : 1,
                    transition: 'opacity 0.2s'
                  }}
                >
                  Atrás
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes slideUp {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  )
}
