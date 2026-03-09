import React from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { SessionKeepAlive } from '../../../../packages/ui/src/SessionKeepAlive'

describe('SessionKeepAlive', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('closes the warning modal when the token changes externally', async () => {
    const logout = vi.fn(async () => {})

    function Harness() {
      const [token, setToken] = React.useState('token-1')
      const auth = React.useMemo(
        () => ({
          token,
          refresh: vi.fn(async () => true),
          logout,
        }),
        [token],
      )

      return (
        <>
          <SessionKeepAlive
            useAuth={() => auth}
            warnAfterMs={1_000}
            responseWindowMs={5_000}
          />
          <button type="button" onClick={() => setToken('token-2')}>
            rotate
          </button>
        </>
      )
    }

    render(<Harness />)

    await act(async () => {
      vi.advanceTimersByTime(1_000)
    })

    expect(screen.getByText('Seguir conectado')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'rotate' }))

    expect(screen.queryByText('Seguir conectado')).not.toBeInTheDocument()

    await act(async () => {
      vi.advanceTimersByTime(5_000)
    })

    expect(logout).not.toHaveBeenCalled()
  })
})
