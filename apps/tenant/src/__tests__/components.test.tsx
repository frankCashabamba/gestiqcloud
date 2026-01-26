/**
 * Tests for common components
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../contexts/CompanyConfigContext', () => ({
  useCompanySector: () => ({
    plantilla: 'restaurante',
  }),
  useCompanyConfig: () => ({
    config: {
      company: {
        plantilla_inicio: 'Restaurante',
      },
    },
  }),
}))

vi.mock('../hooks/useCompanySectorFullConfig', () => ({
  useCompanySectorFullConfig: () => ({
    config: {
      branding: {
        icon: '🍕',
        color: '#FF6B35',
        display_name: 'Restaurante',
      },
    },
    loading: false,
    error: null,
  }),
  getSectorIcon: (config: any) => config?.branding?.icon || '📦',
  getSectorColor: (config: any) => config?.branding?.color || '#666',
  getSectorDisplayName: (config: any) => config?.branding?.display_name || 'Default',
}))

vi.mock('../hooks/useUnits', () => ({
  useUnitsBySector: () => ({
    units: [
      { code: 'kg', label: 'Kilogramo' },
      { code: 'lt', label: 'Litro' },
      { code: 'un', label: 'Unidad' },
    ],
    loading: false,
    error: null,
  }),
}))

import { SectorBadge } from '../components/SectorBadge'
import { UnitSelector } from '../components/UnitSelector'

describe('SectorBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render with default props', () => {
    render(<SectorBadge />)
    const badge = screen.getByRole('status')
    expect(badge).toBeInTheDocument()
  })

  it('should display sector icon', () => {
    render(<SectorBadge />)
    expect(screen.getByText('🍕')).toBeInTheDocument()
  })

  it('should display sector name when showLabel is true', () => {
    render(<SectorBadge showLabel={true} />)
    expect(screen.getByText('Restaurante')).toBeInTheDocument()
  })

  it('should hide label when showLabel is false', () => {
    render(<SectorBadge showLabel={false} />)
    expect(screen.queryByText('Restaurante')).not.toBeInTheDocument()
  })

  it('should apply size class correctly', () => {
    const { container } = render(<SectorBadge size="lg" />)
    expect(container.querySelector('.sector-badge--lg')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    const { container } = render(<SectorBadge className="custom-class" />)
    expect(container.querySelector('.custom-class')).toBeInTheDocument()
  })

  it('should have accessible aria-label', () => {
    render(<SectorBadge />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveAttribute('aria-label', expect.stringContaining('Sector'))
  })
})

describe('SectorBadge - size variants', () => {
  it.each(['sm', 'md', 'lg'] as const)('should render size="%s" correctly', (size) => {
    const { container } = render(<SectorBadge size={size} />)
    expect(container.querySelector(`.sector-badge--${size}`)).toBeInTheDocument()
  })
})

describe('UnitSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render with default props', () => {
    render(<UnitSelector />)
    expect(screen.getByLabelText('Unidad de Medida')).toBeInTheDocument()
  })

  it('should render with custom label', () => {
    render(<UnitSelector label="Seleccione Unidad" />)
    expect(screen.getByLabelText('Seleccione Unidad')).toBeInTheDocument()
  })

  it('should display placeholder option', () => {
    render(<UnitSelector placeholder="Elige una opción" />)
    expect(screen.getByRole('option', { name: 'Elige una opción' })).toBeInTheDocument()
  })

  it('should render all units from hook', () => {
    render(<UnitSelector />)
    expect(screen.getByRole('option', { name: 'Kilogramo' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Litro' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unidad' })).toBeInTheDocument()
  })

  it('should call onChange when selection changes', () => {
    const handleChange = vi.fn()
    render(<UnitSelector onChange={handleChange} />)

    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'kg' } })

    expect(handleChange).toHaveBeenCalledWith('kg')
  })

  it('should show selected value', () => {
    render(<UnitSelector value="lt" />)
    const select = screen.getByRole('combobox') as HTMLSelectElement
    expect(select.value).toBe('lt')
  })

  it('should be disabled when disabled prop is true', () => {
    render(<UnitSelector disabled={true} />)
    const select = screen.getByRole('combobox')
    expect(select).toBeDisabled()
  })

  it('should apply custom className', () => {
    const { container } = render(<UnitSelector className="my-selector" />)
    expect(container.querySelector('.my-selector')).toBeInTheDocument()
  })
})
