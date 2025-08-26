import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

type Role = 'superadmin' | 'admin' | 'user' | undefined

export function useAuthGuard(requiredRole?: Role) {
  const { token, profile, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (loading) return // espera a que resuelva el estado inicial

    if (!token) {
      navigate('/login', { replace: true })
      return
    }

    if (requiredRole === 'superadmin' && !profile?.is_superadmin) {
      navigate('/', { replace: true })
    }
  }, [token, profile, loading, requiredRole, navigate])
}

export default useAuthGuard
