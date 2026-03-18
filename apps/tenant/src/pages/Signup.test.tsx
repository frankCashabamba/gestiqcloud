import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { TENANT_AUTH } from '@shared/endpoints'
import Signup from './Signup'

const postMock = vi.fn()
const loginMock = vi.fn()
const navigateMock = vi.fn()
const successMock = vi.fn()
const errorMock = vi.fn()

vi.mock('../shared/api/client', () => ({
  default: {
    post: (...args: unknown[]) => postMock(...args),
  },
}))

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({
    login: (...args: unknown[]) => loginMock(...args),
  }),
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
  }
})

describe('Signup page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    postMock.mockResolvedValue({ data: { ok: true } })
    loginMock.mockResolvedValue({ scope: 'tenant', accessToken: 'tenant-token' })
  })

  it('creates the tenant account and redirects to onboarding', async () => {
    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    )

    await userEvent.type(screen.getByLabelText('Empresa'), 'Gestiq Foods SL')
    await userEvent.type(screen.getByLabelText('Nombre'), 'Frank')
    await userEvent.type(screen.getByLabelText('Apellidos'), 'Tester')
    await userEvent.type(screen.getByLabelText('Email'), 'signup@example.com')
    await userEvent.type(screen.getByLabelText('Contrasena'), 'StrongPass1!')
    await userEvent.clear(screen.getByLabelText('Zona horaria'))
    await userEvent.type(screen.getByLabelText('Zona horaria'), 'Europe/Madrid')
    await userEvent.click(screen.getByRole('button', { name: 'Crear empresa y continuar' }))

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith(
        TENANT_AUTH.signup,
        expect.objectContaining({
          company_name: 'Gestiq Foods SL',
          first_name: 'Frank',
          last_name: 'Tester',
          email: 'signup@example.com',
          password: 'StrongPass1!',
          country_code: 'ES',
          default_language: 'es',
          timezone: 'Europe/Madrid',
          currency: 'EUR',
        }),
      )
    })
    expect(loginMock).toHaveBeenCalledWith({
      identificador: 'signup@example.com',
      password: 'StrongPass1!',
    })
    expect(successMock).toHaveBeenCalledWith('Cuenta creada correctamente')
    expect(navigateMock).toHaveBeenCalledWith('/onboarding')
    expect(errorMock).not.toHaveBeenCalled()
  })
})
