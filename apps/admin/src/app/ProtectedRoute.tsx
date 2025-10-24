import { ProtectedRoute as SharedProtectedRoute } from '@shared/ui'
import { useAuth } from '../auth/AuthContext'

export default function ProtectedRoute() {
  return <SharedProtectedRoute useAuth={useAuth as any} />
}
