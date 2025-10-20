/**
 * Test provider for ElectricSQL testing
 *
 * Provides a test context that mocks ElectricSQL functionality
 * for testing offline/online scenarios.
 */

import React, { createContext, useContext, useEffect } from 'react'
import { vi } from 'vitest'

interface Conflict {
  table: string
  id: string
  local?: any
  remote?: any
  conflict_details?: any
}

interface ElectricTestContextType {
  isOnline: boolean
  conflicts: Conflict[]
  setOnline: (online: boolean) => void
  addConflict: (conflict: Conflict) => void
  clearConflicts: () => void
}

const ElectricTestContext = createContext<ElectricTestContextType | null>(null)

export const useElectricTest = () => {
  const context = useContext(ElectricTestContext)
  if (!context) {
    throw new Error('useElectricTest must be used within ElectricTestProvider')
  }
  return context
}

interface ElectricTestProviderProps {
  children: React.ReactNode
  initialOnline?: boolean
  initialConflicts?: Conflict[]
}

export const ElectricTestProvider: React.FC<ElectricTestProviderProps> = ({
  children,
  initialOnline = true,
  initialConflicts = []
}) => {
  const [isOnline, setIsOnline] = React.useState(initialOnline)
  const [conflicts, setConflicts] = React.useState<Conflict[]>(initialConflicts)

  // Mock navigator.onLine
  useEffect(() => {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: isOnline
    })
  }, [isOnline])

  // Mock ElectricSQL functions
  useEffect(() => {
    const { initElectric, setupOnlineSync, setConflictHandler, isOnline: mockIsOnline } =
      require('../lib/electric')

    // Mock implementations
    vi.mocked(mockIsOnline).mockReturnValue(isOnline)

    vi.mocked(initElectric).mockResolvedValue({
      db: {},
      sync: vi.fn().mockResolvedValue({ conflicts: [] })
    })

    vi.mocked(setupOnlineSync).mockImplementation(() => {
      // Setup mock event listeners
    })

    vi.mocked(setConflictHandler).mockImplementation((callback) => {
      // If there are initial conflicts, call the callback
      if (conflicts.length > 0) {
        callback(conflicts)
      }
    })
  }, [isOnline, conflicts])

  const setOnline = (online: boolean) => {
    setIsOnline(online)

    // Dispatch online/offline events
    const event = new Event(online ? 'online' : 'offline')
    window.dispatchEvent(event)
  }

  const addConflict = (conflict: Conflict) => {
    setConflicts(prev => [...prev, conflict])
  }

  const clearConflicts = () => {
    setConflicts([])
  }

  const value: ElectricTestContextType = {
    isOnline,
    conflicts,
    setOnline,
    addConflict,
    clearConflicts
  }

  return (
    <ElectricTestContext.Provider value={value}>
      {children}
    </ElectricTestContext.Provider>
  )
}

// Test utilities
export const simulateOffline = () => {
  window.dispatchEvent(new Event('offline'))
}

export const simulateOnline = () => {
  window.dispatchEvent(new Event('online'))
}

export const simulateNetworkChange = (online: boolean) => {
  Object.defineProperty(navigator, 'onLine', {
    writable: true,
    value: online
  })

  const event = new Event(online ? 'online' : 'offline')
  window.dispatchEvent(event)
}
