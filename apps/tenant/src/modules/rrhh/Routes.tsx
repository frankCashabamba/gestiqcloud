import { Routes, Route } from 'react-router-dom'
import Panel from './Panel'
import EmpleadosList from './EmpleadosList'
import EmpleadoForm from './EmpleadoForm'
import EmpleadoDetail from './EmpleadoDetail'
import VacacionesList from './VacacionesList'
import VacacionForm from './VacacionForm'

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
