import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import RoleList from './RolesList';
import RoleForm from './RoleForm';
import ConfirmDelete from './ConfirmDelete';
import EditWrapper from './EditWrapper';
import { defaultPermissionKeys, toPermisosObject } from '@shared/utils/permissions';
import type { Role, RoleData } from './types/roles';
import { apiGet, apiPost, apiPut, apiDelete } from '../../../lib/api';

const RolesRouter: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    apiGet<Role[]>('/v1/roles-base/')
      .then(data => {
        const normalized = data.map(role => ({
          ...role,
          permisos: toPermisosObject(role.permisos),
        }));
        setRoles(normalized);
      })
      .catch(err => console.error('❌ Error al cargar roles:', err));
  }, []);

  const handleSave = async (roleData: RoleData) => {
    const payload: RoleData = {
      nombre: roleData.nombre,
      descripcion: roleData.descripcion,
      permisos: roleData.permisos,
    };

    try {
      const saved = roleData.id
        ? await apiPut<RoleData>(`/v1/roles-base/${roleData.id}`, payload)
        : await apiPost<RoleData>('/v1/roles-base/', payload);

      const normalized: Role = {
        ...saved,
        permisos: toPermisosObject(saved.permisos),
        id: saved.id!,
      };

      setRoles(prev =>
        roleData.id
          ? prev.map(r => (r.id === normalized.id ? normalized : r))
          : [...prev, normalized]
      );
    } catch (err) {
      console.error('❌ Error al guardar rol:', err);
    }
  };

  const handleDelete = (id: number) => setDeleteId(id);

  const confirmDelete = async () => {
    if (deleteId !== null) {
      try {
        await apiDelete(`/v1/roles-base/${deleteId}`);
        setRoles(prev => prev.filter(r => r.id !== deleteId));
        setDeleteId(null);
      } catch (err) {
        console.error('❌ Error al eliminar rol:', err);
      }
    }
  };

  // Removed base role copy feature

  return (
    <>
      <Routes>
        
        <Route index element={<RoleList roles={roles} onDelete={handleDelete} />} />
        <Route path="nuevo" element={<RoleForm mode="create" onSubmit={handleSave} />} />
        <Route
          path=":id/editar"
          element={<EditWrapper roles={roles} onSubmit={handleSave} />}
        />
      </Routes>

      {deleteId !== null && (
        <ConfirmDelete
          nombre={roles.find(r => r.id === deleteId)?.nombre || ''}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteId(null)}
        />
      )}
    </>
  );
};

export default RolesRouter;
