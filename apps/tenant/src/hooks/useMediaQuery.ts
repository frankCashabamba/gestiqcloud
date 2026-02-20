/**
 * useMediaQuery - Hook para detectar media queries
 */
import { useState, useEffect } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    // SSR check
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mediaQueryList = window.matchMedia(query)
    const handleChange = (e: MediaQueryListEvent) => {
      setMatches(e.matches)
    }

    // Use addEventListener if available (modern browsers)
    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener('change', handleChange)
      return () => mediaQueryList.removeEventListener('change', handleChange)
    }

    // Fallback for older browsers
    mediaQueryList.addListener(handleChange)
    return () => mediaQueryList.removeListener(handleChange)
  }, [query])

  return matches
}
