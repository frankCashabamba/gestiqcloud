import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from '../../auth/ProtectedRoute'
import PermissionDenied from '../../components/PermissionDenied'
import ProveedoresList from './List';
import ProveedorForm from './Form';
import ProveedorDetail from './Detail';

export default function ProveedoresRoutes() {
  return (
    <ProtectedRoute
      permission="suppliers:read"
      fallback={<PermissionDenied permission="suppliers:read" />}
    >
      <Routes>
        <Route index element={<ProveedoresList />} />
        <Route
          path="nuevo"
          element={
            <ProtectedRoute permission="suppliers:create">
              <ProveedorForm />
            </ProtectedRoute>
          }
        />
        <Route path=":id" element={<ProveedorDetail />} />
        <Route
          path=":id/editar"
          element={
            <ProtectedRoute permission="suppliers:update">
              <ProveedorForm />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="." replace />} />
      </Routes>
    </ProtectedRoute>
  );
}
