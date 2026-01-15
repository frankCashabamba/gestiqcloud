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
    <Container className="empresa-page">
      <header className="empresa-header">
        <h1 className="empresa-title">Gestion de empresas</h1>
        <p className="empresa-subtitle">Administra empresas, modulos y accesos desde un solo lugar.</p>
      </header>

      <div className="empresa-toolbar">
        <input
          type="search"
          placeholder="Buscar empresa..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="empresa-search"
        />
        <Link to="crear" className="empresa-primary">
          Nueva empresa
        </Link>
      </div>

      {loading ? (
        <p className="empresa-muted">Cargando...</p>
      ) : error ? (
        <p className="empresa-muted" style={{ color: '#dc2626' }}>Error al cargar empresas</p>
      ) : empresasFiltradas.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Empresa</th>
                <th>Modulos</th>
                <th style={{ textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {empresasFiltradas.map((empresa) => {
                const nombreEmpresa = empresa?.nombre || (empresa as any)?.name || 'Sin nombre';
                const modulos = (empresa as any)?.modulos || (empresa as any)?.modules || [];
                return (
                  <tr key={empresa.id}>
                    <td style={{ fontWeight: 600 }}>{nombreEmpresa}</td>
                    <td>
                      {modulos.length > 0 ? (
                        <div className="badge-group">
                          {modulos.map((modulo: string) => (
                            <span key={`${empresa.id}-${modulo}`} className="badge">
                              {modulo}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="badge badge-warning">Sin modulos</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-pills">
                        <Link to={`/admin/empresas/${empresa.id}/editar`} className="action-pill blue">
                          Editar
                        </Link>
                        <Link to={`/admin/empresas/${empresa.id}/usuarios`} className="action-pill green">
                          Usuarios
                        </Link>
                        <Link to={`/admin/empresas/modulos/${empresa.id}`} className="action-pill amber">
                          Modulos
                        </Link>
                        <Link to={`/admin/empresas/${empresa.id}/configuracion`} className="action-pill violet">
                          Config
                        </Link>
                        <button
                          onClick={() => setEmpresaAEliminar({ id: String(empresa.id), name: nombreEmpresa })}
                          className="action-pill danger"
                        >
                          Eliminar
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empresa-empty">No hay empresas registradas.</div>
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
