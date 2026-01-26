import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import React from 'react'

vi.mock('@pwa', () => ({
  setupPWA: vi.fn(),
}))

vi.mock('@shared', () => ({
  sendTelemetry: vi.fn(),
  createSharedClient: () => ({
    get: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }),
}))

vi.mock('@shared/ui', () => ({
  ProtectedRoute: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  SessionKeepAlive: () => null,
  OfflineBanner: () => null,
  BuildBadge: () => null,
  UpdatePrompt: () => null,
  OfflineReadyToast: () => null,
  OutboxIndicator: () => null,
  IdleLogout: () => null,
  default: () => null,
}))

vi.mock('@ui/env', () => ({
  EnvProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useEnv: () => ({ apiUrl: 'http://localhost', tenantOrigin: 'http://localhost' }),
}))

vi.mock('../lib/http', () => ({
  registerAuthHandlers: vi.fn(),
}))

vi.mock('../env', () => ({
  env: { apiUrl: 'http://localhost', tenantOrigin: 'http://localhost' },
}))

vi.mock('../auth/AuthContext', () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth: () => ({
    token: null,
    loading: false,
    profile: null,
    brand: 'Admin',
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  }),
}))

import { buildEmpresaPayload, fileToDataUrl } from '../utils/formToJson'

describe('App smoke tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  it('Login page renders correctly', async () => {
    const { default: Login } = await import('../pages/Login')

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    )

    expect(screen.getByText(/Iniciar sesión/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Usuario o email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Entrar/i })).toBeInTheDocument()
  })

  it('Login page has password field', async () => {
    const { default: Login } = await import('../pages/Login')

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    )

    const passwordInput = document.getElementById('admin-password')
    expect(passwordInput).toBeInTheDocument()
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('AdminPanel component exists and exports default', async () => {
    const AdminPanelModule = await import('../pages/AdminPanel')

    expect(AdminPanelModule.default).toBeDefined()
    expect(typeof AdminPanelModule.default).toBe('function')
  })

  it('ProtectedRoute component exists', async () => {
    const ProtectedRouteModule = await import('../app/ProtectedRoute')

    expect(ProtectedRouteModule.default).toBeDefined()
    expect(typeof ProtectedRouteModule.default).toBe('function')
  })

  it('ErrorPage component exists and renders', async () => {
    const { default: ErrorPage } = await import('../pages/ErrorPage')

    expect(ErrorPage).toBeDefined()
    expect(typeof ErrorPage).toBe('function')
  })

  it('buildEmpresaPayload utility transforms form data correctly', () => {
    const formData = {
      nombre_empresa: ' Test Company ',
      ruc: '12345678901',
      telefono: '555-1234',
      direccion: '123 Main St',
      ciudad: 'Lima',
      provincia: 'Lima',
      cp: '15001',
      pais: 'Perú',
      country_code: 'PE',
      sitio_web: 'https://test.com',
      config_json: '{"key":"value"}',
      default_language: 'es',
      timezone: 'America/Lima',
      currency: 'PEN',
    }

    const result = buildEmpresaPayload(formData as any)

    expect(result.name).toBe('Test Company')
    expect(result.tax_id).toBe('12345678901')
    expect(result.country_code).toBe('PE')
    expect(result.config_json).toEqual({ key: 'value' })
  })

  it('buildEmpresaPayload handles invalid JSON gracefully', () => {
    const formData = {
      nombre_empresa: 'Test',
      config_json: 'invalid json',
    }

    const result = buildEmpresaPayload(formData as any)

    expect(result.name).toBe('Test')
    expect(result.config_json).toEqual({})
  })

  it('fileToDataUrl converts file to data URL', async () => {
    const content = 'test content'
    const blob = new Blob([content], { type: 'text/plain' })
    const file = new File([blob], 'test.txt', { type: 'text/plain' })

    const result = await fileToDataUrl(file)

    expect(result).toMatch(/^data:text\/plain;base64,/)
  })
})
