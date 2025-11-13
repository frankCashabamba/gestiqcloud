// src/pages/admin/empresas/EmpresaPanel.tsx <img src="/icons/empresas.png" alt="Empresas" className="w-7 h-7" />
import React, { useState } from 'react';
import { Link } from "react-router-dom";
import { Container } from './Container';
import { useEmpresas } from '../hooks/useEmpresas';

export const EmpresaPanel: React.FC = () => {
  const { empresas, loading, error } = useEmpresas();
  const [search, setSearch] = useState('');

  const normalizedSearch = search.trim().toLowerCase();
  const empresasFiltradas = (empresas ?? []).filter((e) => {
    const nombre = (e?.nombre || '').toString().toLowerCase();
    return nombre.includes(normalizedSearch);
  });

  return (

      <Container className="space-y-6 py-10">
        <div className="flex justify-between items-center flex-wrap gap-2">
        <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
          Gestión de Empresas
        </h1>

        <Link
          to="crear" // relativo → /admin/empresas/crear
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
        >
          ➕ Nueva Empresa
        </Link>
      </div>

        <input
          type="search"
          placeholder="Buscar empresa..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
        />

        {loading ? (
          <p className="text-gray-500 text-sm">Cargando empresas...</p>
        ) : error ? (
          <p className="text-red-500 text-sm">❌ Error al cargar empresas.</p>
        ) : empresasFiltradas.length > 0 ? (
          <ul className="space-y-4">
            {empresasFiltradas.map((empresa) => (
              <li
                key={empresa.id}
                className="empresa-item bg-white border border-gray-200 rounded-xl shadow-sm p-4"
              >
                <div className="text-lg font-semibold text-gray-800 flex justify-between items-center flex-wrap gap-2">
                  {empresa.nombre}
                  <span className="text-sm text-gray-500">
                    {empresa.modulos && empresa.modulos.length > 0 ? (
                      `Módulos: ${empresa.modulos.join(', ')}`
                    ) : (
                      <span className="text-red-500">Sin módulos</span>
                    )}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 mt-3">
                  <a
                    href={`/admin/empresas/${empresa.id}/editar`}
                    className="inline-flex items-center gap-1 bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-3 py-1.5 rounded-md"
                  >
                    ✏️ Editar
                  </a>
                  <a
                    href={`/admin/empresas/${empresa.id}/usuarios`}
                    className="inline-flex items-center gap-1 bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1.5 rounded-md"
                  >
                    👥 Usuarios Empresa
                  </a>
                  <a
                    href={`/admin/empresas/modulos/${empresa.id}`}
                    className="inline-flex items-center gap-1 bg-yellow-500 hover:bg-yellow-600 text-white text-sm px-3 py-1.5 rounded-md"
                  >
                    ⚙️ Módulos
                  </a>
                  <a
                    href={`/admin/empresas/${empresa.id}/configuracion`}
                    className="inline-flex items-center gap-1 bg-purple-500 hover:bg-purple-600 text-white text-sm px-3 py-1.5 rounded-md"
                  >
                    🧩 Configuración avanzada
                  </a>
                  <button
                    onClick={() => alert(`Actuar como empresa ${empresa.id}`)}
                    className="inline-flex items-center gap-1 bg-blue-500 hover:bg-blue-600 text-white text-sm px-3 py-1.5 rounded-md"
                  >
                    🧭 Actuar como
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 text-sm mt-4">No hay empresas registradas aún.</p>
        )}
      </Container>
    
  );
};
