import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import Panel from './Panel'
import EmployeesList from './EmployeesList'
import EmployeeForm from './EmployeeForm'
import EmployeeDetail from './EmployeeDetail'
import VacationsList from './VacationsList'
import VacationForm from './VacationForm'
import FichajesView from './FichajesView'
import NominaView from './NominaView'

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
        <Route path="vacations" element={<VacationsList />} />
        <Route path="vacaciones" element={<Navigate to="../vacations" replace />} />
        <Route
          path="vacations/new"
          element={
            <ProtectedRoute permission="hr:manage">
              <VacationForm />
            </ProtectedRoute>
          }
        />
        <Route path="vacaciones/nueva" element={<Navigate to="../vacations/new" replace />} />
        <Route path="fichajes" element={<Navigate to="../timekeeping" replace />} />
        <Route path="timekeeping" element={<FichajesView />} />
        <Route path="nomina" element={<Navigate to="../payroll" replace />} />
        <Route path="payroll" element={<NominaView />} />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  )
}
