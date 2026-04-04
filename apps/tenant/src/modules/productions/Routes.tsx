import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'

const OrdersList = lazy(() => import('./OrdersList'))
const OrderForm = lazy(() => import('./OrderForm'))
const ProductionPlanner = lazy(() => import('./ProductionPlanner'))
const RecetasList = lazy(() => import('./RecetasList'))
const RecetaCreatePage = lazy(() => import('./RecetaCreatePage'))
const RecetaShowPage = lazy(() => import('./RecetaShowPage'))
const RecetaEditPage = lazy(() => import('./RecetaEditPage'))
const CostDriversPage = lazy(() => import('./CostDriversPage'))
const IngredientesMaestros = lazy(() => import('./IngredientesMaestros'))

const RouteLoader = () => <div className="p-4">Loading...</div>

function LazyElement({ children }: { children: React.ReactElement }) {
    return <Suspense fallback={<RouteLoader />}>{children}</Suspense>
}

export default function ProduccionRoutes() {
    return (
        <ProtectedRoute
            permission="manufacturing:read"
            fallback={<PermissionDenied permission="manufacturing:read" />}
        >
            <Routes>
                <Route index element={<Navigate to="recetas" replace />} />
                <Route path="planificacion" element={<LazyElement><ProductionPlanner /></LazyElement>} />
                <Route path="planner" element={<Navigate to="../planificacion" replace />} />
                <Route path="ordenes" element={<LazyElement><OrdersList /></LazyElement>} />
                <Route
                    path="ordenes/nuevo"
                    element={
                        <ProtectedRoute permission="manufacturing:create">
                            <LazyElement><OrderForm /></LazyElement>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="ordenes/:id/editar"
                    element={
                        <ProtectedRoute permission="manufacturing:update">
                            <LazyElement><OrderForm /></LazyElement>
                        </ProtectedRoute>
                    }
                />
                <Route path="recetas" element={<LazyElement><RecetasList /></LazyElement>} />
                <Route
                    path="recetas/nueva"
                    element={
                        <ProtectedRoute permission="manufacturing:create">
                            <LazyElement><RecetaCreatePage /></LazyElement>
                        </ProtectedRoute>
                    }
                />
                <Route path="recetas/:rid" element={<LazyElement><RecetaShowPage /></LazyElement>} />
                <Route
                    path="recetas/:rid/editar"
                    element={
                        <ProtectedRoute permission="manufacturing:update">
                            <LazyElement><RecetaEditPage /></LazyElement>
                        </ProtectedRoute>
                    }
                />
                <Route path="ingredientes" element={<LazyElement><IngredientesMaestros /></LazyElement>} />
                <Route
                    path="costos"
                    element={
                        <ProtectedRoute permission="manufacturing:update">
                            <LazyElement><CostDriversPage /></LazyElement>
                        </ProtectedRoute>
                    }
                />
                <Route path="*" element={<Navigate to="recetas" replace />} />
            </Routes>
        </ProtectedRoute>
    )
}
