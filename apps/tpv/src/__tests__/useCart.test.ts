/**
 * Tests: useCart Hook
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCart } from '../hooks/useCart'

describe('useCart', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
  })

  it('starts with empty cart', () => {
    const { result } = renderHook(() => useCart())
    
    expect(result.current.items).toEqual([])
    expect(result.current.total).toBe(0)
  })

  it('adds item to cart', () => {
    const { result } = renderHook(() => useCart())
    
    const product = {
      id: '123',
      name: 'Pan',
      price: 1.50,
      tax_rate: 0.10
    }
    
    act(() => {
      result.current.addItem(product)
    })
    
    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].name).toBe('Pan')
    expect(result.current.items[0].qty).toBe(1)
  })

  it('increments qty if product already in cart', () => {
    const { result } = renderHook(() => useCart())
    
    const product = {
      id: '123',
      name: 'Pan',
      price: 1.50,
      tax_rate: 0.10
    }
    
    act(() => {
      result.current.addItem(product)
      result.current.addItem(product)
    })
    
    expect(result.current.items).toHaveLength(1)
    expect(result.current.items[0].qty).toBe(2)
  })

  it('calculates total correctly', () => {
    const { result } = renderHook(() => useCart())
    
    act(() => {
      result.current.addItem({
        id: '1',
        name: 'Pan',
        price: 1.50,
        tax_rate: 0.10
      })
      result.current.addItem({
        id: '2',
        name: 'Croissant',
        price: 2.00,
        tax_rate: 0.21
      })
    })
    
    // Pan: 1.50 * 1.10 = 1.65
    // Croissant: 2.00 * 1.21 = 2.42
    // Total: 4.07
    expect(result.current.total).toBeCloseTo(4.07, 2)
  })

  it('updates quantity', () => {
    const { result } = renderHook(() => useCart())
    
    const product = {
      id: '123',
      name: 'Pan',
      price: 1.50,
      tax_rate: 0.10
    }
    
    act(() => {
      result.current.addItem(product)
      result.current.updateQty('123', 5)
    })
    
    expect(result.current.items[0].qty).toBe(5)
  })

  it('removes item when qty is 0', () => {
    const { result } = renderHook(() => useCart())
    
    const product = {
      id: '123',
      name: 'Pan',
      price: 1.50,
      tax_rate: 0.10
    }
    
    act(() => {
      result.current.addItem(product)
      result.current.updateQty('123', 0)
    })
    
    expect(result.current.items).toHaveLength(0)
  })

  it('clears cart', () => {
    const { result } = renderHook(() => useCart())
    
    act(() => {
      result.current.addItem({ id: '1', name: 'Pan', price: 1.50, tax_rate: 0.10 })
      result.current.addItem({ id: '2', name: 'Croissant', price: 2.00, tax_rate: 0.21 })
      result.current.clearCart()
    })
    
    expect(result.current.items).toHaveLength(0)
    expect(result.current.total).toBe(0)
  })
})
