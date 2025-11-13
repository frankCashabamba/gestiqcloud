import React from 'react'
import { Navigate, Route, Routes as RouterRoutes } from 'react-router-dom'
import Panel, { MovimientosPage } from './Panel'
import PlanCuentasList from './PlanCuentasList'
import PlanCuentasForm from './PlanCuentasForm'
import AsientosList from './AsientosList'
import AsientoForm from './AsientoForm'
import { DashboardContable } from './components/DashboardContable'
import { LibroDiario } from './components/LibroDiario'
import { LibroMayor } from './components/LibroMayor'
import { PerdidasGanancias } from './components/PerdidasGanancias'
import { ConciliacionBancaria } from './components/ConciliacionBancaria'
import { PlanContable } from './components/PlanContable'

export default function ContabilidadRoutes() {
    return (
        <RouterRoutes>
            <Route element={<Panel />}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<DashboardContable />} />
                <Route path="movimientos" element={<MovimientosPage />} />
                <Route path="libro-diario" element={<LibroDiario />} />
                <Route path="libro-mayor" element={<LibroMayor />} />
                <Route path="pyl" element={<PerdidasGanancias />} />
                <Route path="conciliacion" element={<ConciliacionBancaria />} />
                <Route path="plan-contable" element={<PlanContable />} />

                <Route path="plan-cuentas" element={<PlanCuentasList />} />
                <Route path="plan-cuentas/nuevo" element={<PlanCuentasForm />} />
                <Route path="plan-cuentas/:id/editar" element={<PlanCuentasForm />} />
                <Route path="asientos" element={<AsientosList />} />
                <Route path="asientos/nuevo" element={<AsientoForm />} />
                <Route path="asientos/:id/editar" element={<AsientoForm />} />
                <Route path="*" element={<Navigate to="dashboard" replace />} />
            </Route>
        </RouterRoutes>
    )
}
