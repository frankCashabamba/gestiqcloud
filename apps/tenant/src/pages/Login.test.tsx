import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Login from './Login'

const loginMock = vi.fn()
const navigateMock = vi.fn()
const resolveTenantPathMock = vi.fn()
const assignMock = vi.fn()

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}))

vi.mock('../lib/tenantNavigation', () => ({
  resolveTenantPath: (...args: unknown[]) => resolveTenantPathMock(...args),
}))

vi.mock('@ui/env', () => ({
  useEnv: () => ({
    apiUrl: 'http://localhost:8000',
    basePath: '/',
    tenantOrigin: 'http://tenant.local',
    adminOrigin: 'http://admin.local',
    mode: 'test',
    dev: false,
    prod: false,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
    Link: ({ to, children, ...props }: { to: string; children: React.ReactNode; [key: string]: unknown }) =>
      React.createElement('a', { href: String(to), ...props }, children),
  }
})

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      const messages: Record<string, string> = {
        'login.usernameLabel': 'Correo o usuario',
        'login.passwordLabel': 'Contraseña',
        'login.signIn': 'Iniciar sesión',
        'login.signingIn': 'Iniciando sesión…',
        'login.invalidCredentials': 'Usuario o contraseña incorrectos',
        'login.serverError': 'Error del servidor. Intenta de nuevo más tarde.',
        'login.tooManyAttempts': `Demasiados intentos. Espera ${params?.wait ?? 'a few'} segundos.`,
      }
      return messages[key] ?? key
    },
  }),
}))

describe('Login page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resolveTenantPathMock.mockResolvedValue('/demo')
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        ...window.location,
        assign: assignMock,
      },
    })
  })

  it('redirects to admin when the universal login resolves admin scope', async () => {
    loginMock.mockResolvedValue({ scope: 'admin', accessToken: 'admin-token' })

    render(<Login />)

    await userEvent.type(screen.getByLabelText('Correo o usuario'), 'root')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'secret')
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    await waitFor(() => {
      expect(assignMock).toHaveBeenCalledWith('http://admin.local/#access_token=admin-token')
    })
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('shows invalid credentials instead of fallback_disabled on 401', async () => {
    loginMock.mockRejectedValue({ status: 401 })

    render(<Login />)

    await userEvent.type(screen.getByLabelText('Correo o usuario'), 'demo.empresa')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'bad-pass')
    await userEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos')
    expect(screen.queryByText('fallback_disabled')).not.toBeInTheDocument()
  })
})
