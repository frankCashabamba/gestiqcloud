// src/components/RoleList.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import type { Role } from './types/roles'; // ajusta esta ruta si es diferente


interface RoleListProps {
  roles: Role[];
  onDelete?: (id: number) => void;
}

const RoleList: React.FC<RoleListProps> = ({ roles, onDelete }) => {
  return (

    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-indigo-700 mb-4">🎛 Lista de Roles</h1>
      <Link to="nuevo" className="btn btn-primary mb-4 inline-block">➕ Nuevo Rol</Link>
      <ul className="space-y-4">
        {roles.map(rol => (
          <li key={rol.id} className="bg-white p-4 shadow rounded">
            <div className="flex justify-between items-center">
              <div>
                <strong>{rol.nombre}</strong> – <small>{rol.descripcion || 'Sin descripción'}</small>
              </div>
              <div className="flex gap-2">
                <Link to={`${rol.id}/editar`} className="text-indigo-600 hover:underline">Editar</Link>
                <button onClick={() => onDelete?.(rol.id)} className="text-red-600 hover:underline">Eliminar</button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>

  );
};

export default RoleList;
