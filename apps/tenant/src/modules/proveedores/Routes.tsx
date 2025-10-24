import React from 'react';
import { Routes, Route } from 'react-router-dom';

import ProveedoresList from './List';
import ProveedorForm from './Form';

export default function ProveedoresRoutes() {
  return (
    <Routes>
      <Route index element={<ProveedoresList />} />
      <Route path="nuevo" element={<ProveedorForm />} />
      <Route path=":id/editar" element={<ProveedorForm />} />
    </Routes>
  );
}
