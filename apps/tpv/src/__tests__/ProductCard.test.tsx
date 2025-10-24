/**
 * Tests: ProductCard Component
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ProductCard from '../components/ProductCard'

describe('ProductCard', () => {
  const mockProduct = {
    id: '123',
    name: 'Pan Integral',
    sku: 'PAN-001',
    price: 1.50,
    stock: 100,
    category: 'pan'
  }

  it('renders product information', () => {
    const onClick = vi.fn()
    render(<ProductCard product={mockProduct} onClick={onClick} />)
    
    expect(screen.getByText('Pan Integral')).toBeInTheDocument()
    expect(screen.getByText('1,50 €')).toBeInTheDocument()
    expect(screen.getByText('PAN-001')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<ProductCard product={mockProduct} onClick={onClick} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('shows low stock badge when stock < 10', () => {
    const lowStockProduct = { ...mockProduct, stock: 5 }
    const onClick = vi.fn()
    render(<ProductCard product={lowStockProduct} onClick={onClick} />)
    
    expect(screen.getByText('5 left')).toBeInTheDocument()
  })

  it('is disabled when out of stock', () => {
    const outOfStockProduct = { ...mockProduct, stock: 0 }
    const onClick = vi.fn()
    render(<ProductCard product={outOfStockProduct} onClick={onClick} />)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(screen.getByText('Agotado')).toBeInTheDocument()
  })

  it('displays correct emoji for category', () => {
    const onClick = vi.fn()
    render(<ProductCard product={mockProduct} onClick={onClick} />)
    
    // Debe mostrar 🥖 para 'pan'
    expect(screen.getByText('🥖')).toBeInTheDocument()
  })
})
