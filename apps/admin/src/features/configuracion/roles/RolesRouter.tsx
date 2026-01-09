import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import RoleList from './RolesList';
import RoleForm from './RoleForm';
import ConfirmDelete from './ConfirmDelete';
import EditWrapper from './EditWrapper';
import type { Role, RoleData, RoleFromBackend } from './types/roles';
import { apiGet, apiPost, apiPut, apiDelete } from '../../../lib/api';
import { listPermisos, type GlobalPermission } from '../../../services/configuracion/permisos';

const RolesRouter: React.FC = () => {
  const [roles, setRoles] = useState<Role[]>([]);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [permissions, setPermissions] = useState<GlobalPermission[]>([]);

  const toPermMap = (perms: string[] | undefined) => {
    const keys = new Set<string>(perms || []);
    permissions.forEach((p) => keys.add(p.key));
    return Array.from(keys).reduce((acc, key) => {
      acc[key] = (perms || []).includes(key);
      return acc;
    }, {} as Record<string, boolean>);
  };

  useEffect(() => {
    apiGet<RoleFromBackend[]>('/v1/roles-base/')
      .then(data => {
        const normalized = data.map(role => ({
          ...role,
          permisos: toPermMap(role.permisos),
        }));
        setRoles(normalized);
      })
      .catch(err => console.error('❌ Error al cargar roles:', err));
    listPermisos()
      .then(setPermissions)
      .catch(err => console.error('❌ Error al cargar permisos:', err));
  }, []);

  useEffect(() => {
    setRoles((prev) =>
      prev.map((role) => ({
        ...role,
        permisos: toPermMap(
          Object.entries(role.permisos || {})
            .filter(([, val]) => val)
            .map(([key]) => key)
        ),
      }))
    );
  }, [permissions]);

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
        permisos: toPermMap(saved.permisos),
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
        <Route
          path="nuevo"
          element={<RoleForm mode="create" onSubmit={handleSave} availablePermissions={permissions} />}
        />
        <Route
          path=":id/editar"
          element={<EditWrapper roles={roles} onSubmit={handleSave} availablePermissions={permissions} />}
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
