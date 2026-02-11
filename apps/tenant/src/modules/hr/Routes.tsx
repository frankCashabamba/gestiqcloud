import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import Panel from './Panel'
import EmployeesList from './EmployeesList'
import EmployeeForm from './EmployeeForm'
import EmployeeDetail from './EmployeeDetail'
import VacationsList from './VacationsList'
import VacationForm from './VacationForm'

export default function RRHHRoutes() {
  return (
    <ProtectedRoute
      permission="hr:read"
      fallback={<PermissionDenied permission="hr:read" />}
    >
      <Routes>
        <Route index element={<Panel />} />
        <Route path="empleados" element={<EmployeesList />} />
        <Route
          path="empleados/nuevo"
          element={
            <ProtectedRoute permission="hr:manage">
              <EmployeeForm />
            </ProtectedRoute>
          }
        />
        <Route path="empleados/:id" element={<EmployeeDetail />} />
        <Route
          path="empleados/:id/editar"
          element={
            <ProtectedRoute permission="hr:manage">
              <EmployeeForm />
            </ProtectedRoute>
          }
        />
        <Route path="vacaciones" element={<VacationsList />} />
        <Route
          path="vacaciones/nueva"
          element={
            <ProtectedRoute permission="hr:manage">
              <VacationForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
