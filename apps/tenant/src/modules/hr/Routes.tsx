import { Routes, Route } from 'react-router-dom'
import Panel from './Panel'
import EmployeesList from './EmployeesList'
import EmployeeForm from './EmployeeForm'
import EmployeeDetail from './EmployeeDetail'
import VacationsList from './VacationsList'
import VacationForm from './VacationForm'

export default function RRHHRoutes() {
  return (
    <Routes>
      <Route index element={<Panel />} />
      <Route path="empleados" element={<EmployeesList />} />
      <Route path="empleados/nuevo" element={<EmployeeForm />} />
      <Route path="empleados/:id" element={<EmployeeDetail />} />
      <Route path="empleados/:id/editar" element={<EmployeeForm />} />
      <Route path="vacaciones" element={<VacationsList />} />
      <Route path="vacaciones/nueva" element={<VacationForm />} />
    </Routes>
  )
}
