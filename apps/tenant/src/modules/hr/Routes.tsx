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
      <Route path="empleados" element={<EmpleadosList />} />
      <Route path="empleados/nuevo" element={<EmpleadoForm />} />
      <Route path="empleados/:id" element={<EmpleadoDetail />} />
      <Route path="empleados/:id/editar" element={<EmpleadoForm />} />
      <Route path="vacaciones" element={<VacacionesList />} />
      <Route path="vacaciones/nueva" element={<VacacionForm />} />
    </Routes>
  )
}
