/**
 * API utility functions for roles components
 * Provides simple wrapper functions for common HTTP operations
 */

// Re-export from the main services/api for compatibility
export const apiGet = async <T = any>(endpoint: string): Promise<T> => {
  const response = await fetch(`${process.env.REACT_APP_API_BASE || ''}${endpoint}`)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

export const apiPost = async <T = any>(endpoint: string, data?: any): Promise<T> => {
  const response = await fetch(`${process.env.REACT_APP_API_BASE || ''}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: data ? JSON.stringify(data) : undefined,
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

export const apiPut = async <T = any>(endpoint: string, data?: any): Promise<T> => {
  const response = await fetch(`${process.env.REACT_APP_API_BASE || ''}${endpoint}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: data ? JSON.stringify(data) : undefined,
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

export const apiDelete = async <T = any>(endpoint: string): Promise<T> => {
  const response = await fetch(`${process.env.REACT_APP_API_BASE || ''}${endpoint}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}
