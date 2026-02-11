import React from 'react'
import { Navigate, Route, Routes as RouterRoutes } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import Panel, { MovimientosPage } from './Panel'
import ChartOfAccountsList from './ChartOfAccountsList'
import ChartOfAccountsForm from './ChartOfAccountsForm'
import JournalEntriesList from './JournalEntriesList'
import JournalEntryForm from './JournalEntryForm'
import { DashboardContable } from './components/DashboardContable'
import { LibroDiario } from './components/LibroDiario'
import { LibroMayor } from './components/LibroMayor'
import { PerdidasGanancias } from './components/PerdidasGanancias'
import { ConciliacionBancaria } from './components/ConciliacionBancaria'
import PosAccountingSettings from './components/PosAccountingSettings'
import PaymentMethods from './components/PaymentMethods'

export default function ContabilidadRoutes() {
    return (
        <ProtectedRoute
            permission="accounting:read"
            fallback={<PermissionDenied permission="accounting:read" />}
        >
        <RouterRoutes>
            <Route element={<Panel />}>
                <Route index element={<Navigate to="dashboard" replace />} />
                <Route path="dashboard" element={<DashboardContable />} />
                <Route path="movimientos" element={<MovimientosPage />} />
                <Route path="libro-diario" element={<LibroDiario />} />
                <Route path="libro-mayor" element={<LibroMayor />} />
                <Route path="pyl" element={<PerdidasGanancias />} />
                <Route path="conciliacion" element={<ConciliacionBancaria />} />
                <Route path="plan-contable" element={<ChartOfAccountsList />} />
                <Route path="pos-config" element={<PosAccountingSettings />} />
                <Route path="pos-payment-methods" element={<PaymentMethods />} />

                <Route path="plan-cuentas" element={<ChartOfAccountsList />} />
                <Route path="plan-cuentas/nuevo" element={<ChartOfAccountsForm />} />
                <Route path="plan-cuentas/:id/editar" element={<ChartOfAccountsForm />} />
                <Route path="asientos" element={<JournalEntriesList />} />
                <Route path="asientos/nuevo" element={<JournalEntryForm />} />
                <Route path="asientos/:id/editar" element={<JournalEntryForm />} />
                <Route path="*" element={<Navigate to="dashboard" replace />} />
            </Route>
        </RouterRoutes>
        </ProtectedRoute>
    )
}
