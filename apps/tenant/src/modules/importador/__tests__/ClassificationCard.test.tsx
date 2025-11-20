/**
 * Tests para ClassificationCard component
 * Sprint 3: Unit tests de badge de clasificación
 */
import React from 'react'
import { render, screen } from '@testing-library/react'
import { ClassificationCard } from '../components/ClassificationCard'

describe('ClassificationCard', () => {
  it('returns null when suggestedParser is null', () => {
    const { container } = render(
      <ClassificationCard
        suggestedParser={null}
        confidence={0.8}
        aiProvider="local"
        enhancedByAI={false}
      />
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders classification card with high confidence', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.95}
        aiProvider="openai"
        enhancedByAI={true}
      />
    )

    expect(screen.getByText(/Clasificación Detectada/)).toBeInTheDocument()
    expect(screen.getByText('csv_products')).toBeInTheDocument()
    expect(screen.getByText('95%')).toBeInTheDocument()
    expect(screen.getByText('Alta')).toBeInTheDocument()
  })

  it('renders with medium confidence color', () => {
    const { container } = render(
      <ClassificationCard
        suggestedParser="xml_products"
        confidence={0.72}
        aiProvider="local"
        enhancedByAI={false}
      />
    )

    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText('Media')).toBeInTheDocument()
  })

  it('renders with low confidence color', () => {
    render(
      <ClassificationCard
        suggestedParser="pdf_qr"
        confidence={0.45}
        aiProvider="azure"
        enhancedByAI={true}
      />
    )

    expect(screen.getByText('45%')).toBeInTheDocument()
    expect(screen.getByText('Baja')).toBeInTheDocument()
  })

  it('shows AI provider badge when enhanced_by_ai is true', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.85}
        aiProvider="openai"
        enhancedByAI={true}
      />
    )

    expect(screen.getByText('openai')).toBeInTheDocument()
  })

  it('shows heuristic badge when enhanced_by_ai is false', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.85}
        aiProvider={null}
        enhancedByAI={false}
      />
    )

    expect(screen.getByText('Heurística')).toBeInTheDocument()
  })

  it('displays override badge when parserOverride is provided', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.85}
        aiProvider="local"
        enhancedByAI={false}
        parserOverride="xlsx_expenses"
      />
    )

    expect(screen.getByText(/OVERRIDE MANUAL/)).toBeInTheDocument()
    expect(screen.getByText('csv_products')).toBeInTheDocument()
    expect(screen.getByText('xlsx_expenses')).toBeInTheDocument()
  })

  it('renders all three badges', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.88}
        aiProvider="openai"
        enhancedByAI={true}
      />
    )

    // Parser badge
    expect(screen.getByText('📄')).toBeInTheDocument()
    // Confidence badge
    expect(screen.getByText('📊')).toBeInTheDocument()
    // Provider badge
    expect(screen.getByText('🤖')).toBeInTheDocument()
  })

  it('shows override warning message when parserOverride is set', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.85}
        aiProvider="local"
        enhancedByAI={false}
        parserOverride="xlsx_expenses"
      />
    )

    expect(
      screen.getByText(/Se usará el parser seleccionado manualmente/)
    ).toBeInTheDocument()
  })

  it('renders footer with classification info', () => {
    render(
      <ClassificationCard
        suggestedParser="csv_products"
        confidence={0.85}
        aiProvider="local"
        enhancedByAI={false}
      />
    )

    expect(
      screen.getByText(/Clasificación automática detectada/)
    ).toBeInTheDocument()
  })
})
