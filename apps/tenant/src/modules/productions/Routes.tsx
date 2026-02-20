import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import OrdersList from './OrdersList'
import OrderForm from './OrderForm'
import RecetasList from './RecetasList'
import RecetaCreatePage from './RecetaCreatePage'
import RecetaEditPage from './RecetaEditPage'
import RecetaShowPage from './RecetaShowPage'

export default function ProduccionRoutes() {
    return (
        <Routes>
            <Route index element={<Navigate to="recetas" replace />} />
            <Route path="ordenes" element={<OrdersList />} />
            <Route path="ordenes/nuevo" element={<OrderForm />} />
            <Route path="ordenes/:id/editar" element={<OrderForm />} />
            <Route path="recetas" element={<RecetasList />} />
            <Route path="recetas/nueva" element={<RecetaCreatePage />} />
            <Route path="recetas/:rid" element={<RecetaShowPage />} />
            <Route path="recetas/:rid/editar" element={<RecetaEditPage />} />
            <Route path="*" element={<Navigate to="recetas" replace />} />
        </Routes>
    )
}
