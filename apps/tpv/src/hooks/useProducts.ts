/**
 * useProducts Hook - Cache de productos con offline support
 */
import { useQuery } from '@tanstack/react-query'
import { fetchProducts } from '../services/api'
import { getProductsFromCache, saveProductsToCache } from '../db/operations'

export function useProducts() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: async () => {
      try {
        const products = await fetchProducts()
        // Guardar en cache local
        await saveProductsToCache(products)
        return products
      } catch (err) {
        // Si falla, intentar cargar desde cache
        const cached = await getProductsFromCache()
        if (cached.length > 0) {
          console.log('Using cached products (offline)')
          return cached
        }
        throw err
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    gcTime: 60 * 60 * 1000, // 1 hora
  })

  return {
    products: data || [],
    loading: isLoading,
    error,
  }
}
