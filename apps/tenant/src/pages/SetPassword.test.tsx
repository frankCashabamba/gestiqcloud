import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import SetPassword from './SetPassword'

const loginMock = vi.fn()
const navigateMock = vi.fn()
const resolveTenantPathMock = vi.fn()
const successMock = vi.fn()
const errorMock = vi.fn()
const getMock = vi.fn()
const postMock = vi.fn()

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}))

vi.mock('../lib/tenantNavigation', () => ({
  resolveTenantPath: (...args: unknown[]) => resolveTenantPathMock(...args),
}))

vi.mock('../shared/api/client', () => ({
  default: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}))

vi.mock('../shared/toast', () => ({
  useToast: () => ({
    success: successMock,
    error: errorMock,
  }),
  getErrorMessage: (err: any) => err?.message ?? 'error',
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useSearchParams: () => [new URLSearchParams('token=test-token')],
  }
})

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const messages: Record<string, string> = {
        'pages.setPassword.title': 'Establecer contrasena',
        'pages.setPassword.newPassword': 'Nueva contrasena',
        'pages.setPassword.confirmPassword': 'Confirmar contrasena',
        'pages.setPassword.save': 'Guardar',
        'pages.setPassword.saving': 'Guardando...',
        'pages.setPassword.success': 'Contrasena guardada',
        'pages.setPassword.errors.invalidToken': 'Token invalido',
        'pages.setPassword.errors.loginFailed': 'No se pudo iniciar sesion',
        'pages.setPassword.errors.mismatch': 'Las contrasenas no coinciden',
      }
      return messages[key] ?? key
    },
  }),
}))

describe('SetPassword page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getMock.mockResolvedValue({ data: { csrfToken: 'token' } })
    loginMock.mockResolvedValue({ scope: 'tenant', accessToken: 'tenant-token' })
    resolveTenantPathMock.mockResolvedValue('/demo-empresa')
  })

  it('redirects first-time company admins to onboarding after setting password', async () => {
    postMock.mockResolvedValue({
      data: {
        email: 'franklin@example.com',
        requires_onboarding: true,
      },
    })

    render(<SetPassword />)

    await userEvent.type(screen.getByPlaceholderText('Nueva contrasena'), 'StrongPass1!')
    await userEvent.type(screen.getByPlaceholderText('Confirmar contrasena'), 'StrongPass1!')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({
        identificador: 'franklin@example.com',
        password: 'StrongPass1!',
      })
    })
    expect(navigateMock).toHaveBeenCalledWith('/onboarding')
    expect(resolveTenantPathMock).not.toHaveBeenCalled()
  })

  it('falls back to tenant resolution when onboarding is not required', async () => {
    postMock.mockResolvedValue({
      data: {
        username: 'franklin',
        requires_onboarding: false,
      },
    })

    render(<SetPassword />)

    await userEvent.type(screen.getByPlaceholderText('Nueva contrasena'), 'StrongPass1!')
    await userEvent.type(screen.getByPlaceholderText('Confirmar contrasena'), 'StrongPass1!')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(resolveTenantPathMock).toHaveBeenCalled()
    })
    expect(navigateMock).toHaveBeenCalledWith('/demo-empresa')
  })
})
