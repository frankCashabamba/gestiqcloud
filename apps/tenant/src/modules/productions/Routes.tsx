import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import OrdersList from './OrdersList'
import OrderForm from './OrderForm'
import ProductionPlanner from './ProductionPlanner'
import RecetasList from './RecetasList'
import RecetaCreatePage from './RecetaCreatePage'
import RecetaShowPage from './RecetaShowPage'
import RecetaEditPage from './RecetaEditPage'
import CostDriversPage from './CostDriversPage'
import IngredientesMaestros from './IngredientesMaestros'

export default function ProduccionRoutes() {
    return (
        <ProtectedRoute
            permission="produccion:read"
            fallback={<PermissionDenied permission="produccion:read" />}
        >
            <Routes>
                <Route index element={<Navigate to="recetas" replace />} />
                <Route path="planificacion" element={<ProductionPlanner />} />
                <Route path="planner" element={<Navigate to="../planificacion" replace />} />
                <Route path="ordenes" element={<OrdersList />} />
                <Route
                    path="ordenes/nuevo"
                    element={
                        <ProtectedRoute permission="produccion:write">
                            <OrderForm />
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="ordenes/:id/editar"
                    element={
                        <ProtectedRoute permission="produccion:write">
                            <OrderForm />
                        </ProtectedRoute>
                    }
                />
                <Route path="recetas" element={<RecetasList />} />
                <Route
                    path="recetas/nueva"
                    element={
                        <ProtectedRoute permission="produccion:write">
                            <RecetaCreatePage />
                        </ProtectedRoute>
                    }
                />
                <Route path="recetas/:rid" element={<RecetaShowPage />} />
                <Route
                    path="recetas/:rid/editar"
                    element={
                        <ProtectedRoute permission="produccion:write">
                            <RecetaEditPage />
                        </ProtectedRoute>
                    }
                />
                <Route path="ingredientes" element={<IngredientesMaestros />} />
                <Route
                    path="costos"
                    element={
                        <ProtectedRoute permission="produccion:write">
                            <CostDriversPage />
                        </ProtectedRoute>
                    }
                />
                <Route path="*" element={<Navigate to="recetas" replace />} />
            </Routes>
        </ProtectedRoute>
    )
}
