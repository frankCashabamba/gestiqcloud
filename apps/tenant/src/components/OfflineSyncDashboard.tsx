/**
 * OfflineSyncDashboard - Displays offline sync status and controls
 * 
 * Shows:
 * - Online/Offline status
 * - Pending changes by module
 * - Manual sync button
 * - Last sync time
 */

import React, { useState } from 'react'
import useOffline from '@/hooks/useOffline'

interface OfflineSyncDashboardProps {
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
  compact?: boolean
}

export default function OfflineSyncDashboard({
  position = 'bottom-right',
  compact = false
}: OfflineSyncDashboardProps) {
  const { isOnline, totalPending, syncStatus, statusCounts, syncing, syncNow, lastSyncAt } = useOffline()
  const [expanded, setExpanded] = useState(!compact)

  if (isOnline && totalPending === 0) return null

  const positionStyles = {
    'bottom-right': { bottom: 20, right: 20 },
    'bottom-left': { bottom: 20, left: 20 },
    'top-right': { top: 20, right: 20 },
    'top-left': { top: 20, left: 20 }
  }

  return (
    <div style={{
      position: 'fixed',
      ...positionStyles[position],
      background: 'white',
      border: `2px solid ${isOnline ? '#4CAF50' : '#f44336'}`,
      borderRadius: 12,
      padding: '1rem',
      boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
      maxWidth: compact ? 80 : 350,
      zIndex: 1000,
      fontFamily: 'system-ui, -apple-system, sans-serif',
      transition: 'all 0.3s ease'
    }}>
      {/* Header / Toggle Button */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          textAlign: 'left',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem'
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              display: 'inline-block',
              background: isOnline ? '#22c55e' : '#ef4444',
              boxShadow: isOnline
                ? '0 0 12px rgba(34,197,94,0.35)'
                : '0 0 12px rgba(239,68,68,0.35)'
            }}
          />
          {!compact && (
            <span style={{
              fontWeight: 'bold',
              fontSize: '0.95rem',
              color: '#333'
            }}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          )}
        </div>
        
        {compact && (
          <span style={{
            fontSize: '0.85rem',
            background: '#f44336',
            color: 'white',
            padding: '0.2rem 0.6rem',
            borderRadius: 4,
            fontWeight: 'bold'
          }}>
            {totalPending}
          </span>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div style={{ marginTop: '1rem' }}>
          {/* Pending Count */}
          {totalPending > 0 && (
            <div style={{
              background: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: 6,
              padding: '0.75rem',
              marginBottom: '1rem'
            }}>
              <div style={{
                fontWeight: 'bold',
                color: '#856404',
                marginBottom: '0.5rem',
                fontSize: '0.9rem'
              }}>
                {totalPending} cambios pendientes
              </div>

              {/* Details by Entity */}
              <div style={{
                fontSize: '0.8rem',
                color: '#666',
                lineHeight: 1.6
              }}>
                {Object.entries(syncStatus).map(([entity, count]) => (
                  count > 0 && (
                    <div key={entity} style={{ paddingLeft: '0.5rem' }}>
                      • <strong>{entity}:</strong> {count}
                    </div>
                  )
                ))}
                {Object.keys(statusCounts).length > 0 && (
                  <div style={{ paddingLeft: '0.5rem', marginTop: '0.5rem' }}>
                    <div><strong>Estados:</strong></div>
                    {Object.entries(statusCounts).map(([status, count]) => (
                      <div key={status} style={{ paddingLeft: '0.5rem' }}>
                        • {status}: {count}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Last Sync Info */}
          {lastSyncAt && (
            <div style={{
              fontSize: '0.8rem',
              color: '#999',
              marginBottom: '0.75rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid #eee'
            }}>
              <div>
                ✓ Última sincronización: {lastSyncAt.toLocaleTimeString('es-ES', {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                })}
              </div>
            </div>
          )}

          {/* Sync Button */}
          <button
            onClick={() => syncNow()}
            disabled={syncing || !isOnline}
            style={{
              width: '100%',
              padding: '0.75rem',
              background: isOnline && !syncing ? '#2196F3' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: isOnline && !syncing ? 'pointer' : 'default',
              fontSize: '0.9rem',
              fontWeight: 'bold',
              transition: 'all 0.2s',
              opacity: syncing ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
            onMouseEnter={(e) => {
              if (isOnline && !syncing) {
                e.currentTarget.style.background = '#1976D2'
              }
            }}
            onMouseLeave={(e) => {
              if (isOnline && !syncing) {
                e.currentTarget.style.background = '#2196F3'
              }
            }}
          >
            {syncing ? 'Sincronizando...' : 'Sincronizar ahora'}
          </button>

          {/* Offline Warning */}
          {!isOnline && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.75rem',
              background: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: 6,
              fontSize: '0.8rem',
              color: '#721c24'
            }}>
              Los cambios se guardan localmente y se enviarán automáticamente cuando recuperes conexión.
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
