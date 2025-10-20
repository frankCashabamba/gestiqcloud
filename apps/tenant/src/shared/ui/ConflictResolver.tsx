/**
 * Conflict Resolver UI Component
 *
 * Shows sync conflicts that require manual user intervention.
 * Allows users to choose how to resolve conflicts.
 */

import React, { useState } from 'react'
import { setConflictHandler } from '../../lib/electric'

interface Conflict {
  table: string
  id: string
  local: any
  remote: any
  resolution?: string
  conflict_details?: any
}

interface ConflictResolverProps {
  onResolve: (conflict: Conflict, resolution: 'local' | 'remote' | 'merge') => void
}

export const ConflictResolver: React.FC<ConflictResolverProps> = ({ onResolve }) => {
  const [conflicts, setConflicts] = useState<Conflict[]>([])

  // Register conflict handler
  React.useEffect(() => {
    setConflictHandler((newConflicts: Conflict[]) => {
      setConflicts(prev => [...prev, ...newConflicts])
    })
  }, [])

  const handleResolve = (conflict: Conflict, choice: 'local' | 'remote' | 'merge') => {
    onResolve(conflict, choice)
    setConflicts(prev => prev.filter(c => c.id !== conflict.id))
  }

  if (conflicts.length === 0) {
    return null
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
        <h2 className="text-xl font-bold mb-4">Conflicto de Sincronización</h2>
        <p className="text-gray-600 mb-4">
          Se encontraron cambios conflictivos durante la sincronización. Por favor, elija cómo resolver:
        </p>

        {conflicts.map((conflict) => (
          <div key={conflict.id} className="border rounded-lg p-4 mb-4">
            <div className="mb-2">
              <strong>Tabla:</strong> {conflict.table} | <strong>ID:</strong> {conflict.id}
            </div>

            {conflict.table === 'products' && conflict.conflict_details && (
              <div className="mb-3 p-3 bg-yellow-50 rounded">
                <p className="text-sm text-yellow-800">
                  <strong>Conflicto de precio:</strong><br />
                  Precio local: ${conflict.conflict_details.local_price}<br />
                  Precio remoto: ${conflict.conflict_details.remote_price}
                </p>
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button
                onClick={() => handleResolve(conflict, 'local')}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Usar Cambios Locales
              </button>
              <button
                onClick={() => handleResolve(conflict, 'remote')}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
              >
                Usar Cambios Remotos
              </button>
              {conflict.table === 'products' && (
                <button
                  onClick={() => handleResolve(conflict, 'merge')}
                  className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
                >
                  Mantener Precio Más Alto
                </button>
              )}
            </div>
          </div>
        ))}

        <div className="flex justify-end mt-4">
          <button
            onClick={() => setConflicts([])}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Resolver Más Tarde
          </button>
        </div>
      </div>
    </div>
  )
}

// Hook for using conflict resolver
export const useConflictResolver = () => {
  const [pendingConflicts, setPendingConflicts] = useState<Conflict[]>([])

  React.useEffect(() => {
    setConflictHandler((conflicts: Conflict[]) => {
      setPendingConflicts(prev => [...prev, ...conflicts])
    })
  }, [])

  const resolveConflict = (conflict: Conflict, choice: 'local' | 'remote' | 'merge') => {
    // Send resolution to backend
    // Implementation depends on ElectricSQL API

    setPendingConflicts(prev => prev.filter(c => c.id !== conflict.id))
  }

  return {
    conflicts: pendingConflicts,
    resolveConflict
  }
}
