/**
 * useCart Hook - Estado del carrito
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type CartItem = {
  product_id: string
  name: string
  price: number
  qty: number
  tax_rate: number
}

type CartStore = {
  items: CartItem[]
  addItem: (product: any) => void
  updateQty: (productId: string, qty: number) => void
  removeItem: (productId: string) => void
  clearCart: () => void
  total: number
}

export const useCart = create<CartStore>()(
  persist(
    (set, get) => ({
      items: [],
      
      addItem: (product) => {
        const existing = get().items.find((item) => item.product_id === product.id)
        
        if (existing) {
          set({
            items: get().items.map((item) =>
              item.product_id === product.id
                ? { ...item, qty: item.qty + 1 }
                : item
            ),
          })
        } else {
          set({
            items: [
              ...get().items,
              {
                product_id: product.id,
                name: product.name,
                price: product.price,
                qty: 1,
                tax_rate: product.tax_rate || 0.21, // IVA 21% default
              },
            ],
          })
        }
      },
      
      updateQty: (productId, qty) => {
        if (qty <= 0) {
          get().removeItem(productId)
          return
        }
        
        set({
          items: get().items.map((item) =>
            item.product_id === productId ? { ...item, qty } : item
          ),
        })
      },
      
      removeItem: (productId) => {
        set({
          items: get().items.filter((item) => item.product_id !== productId),
        })
      },
      
      clearCart: () => {
        set({ items: [] })
      },
      
      get total() {
        return get().items.reduce(
          (sum, item) => sum + item.price * item.qty * (1 + item.tax_rate),
          0
        )
      },
    }),
    {
      name: 'tpv-cart',
    }
  )
)
