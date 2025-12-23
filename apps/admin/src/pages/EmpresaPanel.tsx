// src/pages/admin/empresas/EmpresaPanel.tsx <img src="/icons/empresas.png" alt="Empresas" className="w-7 h-7" />
import React, { useState } from 'react';
import { Link } from "react-router-dom";
import { Container } from './Container';
import { useEmpresas } from '../hooks/useEmpresas';
import { deleteEmpresa } from '../services/empresa';
import { DeleteEmpresaModal } from '../components/DeleteEmpresaModal';

export const EmpresaPanel: React.FC = () => {
  const { empresas, loading, error } = useEmpresas();
  const [search, setSearch] = useState('');
  const [empresaAEliminar, setEmpresaAEliminar] = useState<{ id: string; name: string } | null>(null);
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());

  const normalizedSearch = search.trim().toLowerCase();
  const empresasFiltradas = (empresas ?? []).filter((e) => {
    const nombre = (e?.nombre || e?.name || '').toString().toLowerCase();
    return nombre.includes(normalizedSearch) && !deletedIds.has(String(e?.id));
  });

  const handleConfirmDelete = async (tenantId: string) => {
    const res: any = await deleteEmpresa(tenantId);
    setDeletedIds((prev) => {
      const next = new Set(prev);
      next.add(String(tenantId));
      return next;
    });
    return {
      ok: true,
      tenant_id: tenantId,
      name: empresaAEliminar?.name || '',
      registros_eliminados: res?.registros_eliminados || {
        usuarios: 0,
        productos: 0,
        facturas: 0,
        clientes: 0,
        modulos: 0,
        roles: 0,
      },
    };
  };

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
            {empresasFiltradas.map((empresa) => {
              const nombreEmpresa = empresa?.nombre || (empresa as any)?.name || '(Sin nombre)';
              const modulos = (empresa as any)?.modulos || (empresa as any)?.modules || [];
              return (
                <li
                  key={empresa.id}
                  className="empresa-item bg-white border border-gray-200 rounded-xl shadow-sm p-4"
                >
                  <div className="text-lg font-semibold text-gray-800 flex justify-between items-center flex-wrap gap-2">
                    {nombreEmpresa}
                    <span className="text-sm text-gray-500">
                      {Array.isArray(modulos) && modulos.length > 0 ? (
                        `Módulos: ${modulos.join(', ')}`
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
                    <button
                      onClick={() => setEmpresaAEliminar({ id: String(empresa.id), name: nombreEmpresa })}
                      className="inline-flex items-center gap-1 bg-red-500 hover:bg-red-600 text-white text-sm px-3 py-1.5 rounded-md"
                    >
                      🗑️ Eliminar
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="text-gray-500 text-sm mt-4">No hay empresas registradas aún.</p>
        )}

      {empresaAEliminar && (
        <DeleteEmpresaModal
          empresa={empresaAEliminar}
          onClose={() => setEmpresaAEliminar(null)}
          onConfirm={handleConfirmDelete}
        />
      )}
      </Container>

  );
};
