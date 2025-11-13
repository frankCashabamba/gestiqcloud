/**
 * Tests para AIProviderSettings component
 * Sprint 3: Unit tests de selector de proveedor IA
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AIProviderSettings } from '../components/AIProviderSettings'

describe('AIProviderSettings', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders the button with initial provider', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    expect(button).toBeInTheDocument()
  })

  it('opens dropdown when button is clicked', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    
    fireEvent.click(button)
    
    expect(screen.getByText(/Configuración de IA para Clasificación/i)).toBeInTheDocument()
  })

  it('shows all provider options', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    expect(screen.getByText(/Local \(Gratuita\)/i)).toBeInTheDocument()
    expect(screen.getByText(/OpenAI GPT/i)).toBeInTheDocument()
    expect(screen.getByText(/Azure OpenAI/i)).toBeInTheDocument()
  })

  it('changes provider when option is selected', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    const openaiRadio = screen.getByLabelText(/OpenAI GPT/)
    fireEvent.click(openaiRadio)
    
    expect(openaiRadio).toBeChecked()
  })

  it('saves to localStorage when save is clicked', async () => {
    const onSave = jest.fn()
    render(<AIProviderSettings initialProvider="local" onSave={onSave} />)
    
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    const openaiRadio = screen.getByDisplayValue('openai')
    fireEvent.click(openaiRadio)
    
    const saveButton = screen.getByText(/Guardar Configuración/)
    fireEvent.click(saveButton)
    
    await waitFor(() => {
      expect(localStorage.getItem('importador_ai_provider')).toBe('openai')
    })
    
    expect(onSave).toHaveBeenCalledWith('openai')
  })

  it('loads saved provider from localStorage on mount', () => {
    localStorage.setItem('importador_ai_provider', 'azure')
    
    render(<AIProviderSettings initialProvider="local" />)
    
    // El componente debería haber cargado 'azure' del localStorage
    expect(localStorage.getItem('importador_ai_provider')).toBe('azure')
  })

  it('closes dropdown when close button is clicked', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    expect(screen.getByText(/Configuración de IA para Clasificación/i)).toBeInTheDocument()
    
    const closeButton = screen.getByText('Cerrar')
    fireEvent.click(closeButton)
    
    expect(screen.queryByText(/Configuración de IA para Clasificación/i)).not.toBeInTheDocument()
  })

  it('shows success message after save', async () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    const saveButton = screen.getByText(/Guardar Configuración/)
    fireEvent.click(saveButton)
    
    await waitFor(() => {
      expect(screen.getByText(/✓ Guardado/)).toBeInTheDocument()
    })
  })

  it('displays correct description for each provider', () => {
    render(<AIProviderSettings initialProvider="local" />)
    const button = screen.getByText(/Local \(Gratuita\)/i)
    fireEvent.click(button)
    
    expect(screen.getByText(/Clasificación basada en heurísticas y patrones/i)).toBeInTheDocument()
    expect(screen.getByText(/GPT-3.5-turbo o GPT-4/i)).toBeInTheDocument()
    expect(screen.getByText(/Azure OpenAI Service/i)).toBeInTheDocument()
  })
})
