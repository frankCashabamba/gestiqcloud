// src/pages/admin/empresas/EmpresaPanel.tsx <img src="/icons/empresas.png" alt="Empresas" className="w-7 h-7" />
import React, { useState } from 'react';

import { Link } from "react-router-dom";

import { Container } from './Container';
import { DeleteAllCompaniesModal } from '../components/DeleteAllCompaniesModal';
import { DeleteEmpresaModal } from '../components/DeleteCompanyModal';
import { useEmpresas } from '../hooks/useEmpresas';
import { deleteAllEmpresas, deleteEmpresa, purgeOrphanCompanyData } from '../services/empresa';

export const EmpresaPanel: React.FC = () => {
  const { empresas, loading, error } = useEmpresas();
  const [search, setSearch] = useState('');
  const [empresaAEliminar, setEmpresaAEliminar] = useState<{ id: string; name: string } | null>(null);
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [purgingOrphans, setPurgingOrphans] = useState(false);

  const normalizedSearch = search.trim().toLowerCase();
  const empresasDisponibles = (empresas ?? []).filter((e) => !deletedIds.has(String(e?.id)));
  const empresasFiltradas = (empresas ?? []).filter((e) => {
    const nombre = (e?.nombre || e?.name || '').toString().toLowerCase();
    return nombre.includes(normalizedSearch) && !deletedIds.has(String(e?.id));
  });

  const handleConfirmDelete = async (tenantId: string) => {
    const safeTenantId = (tenantId || '').trim();
    if (!safeTenantId) {
      throw new Error('Invalid company id');
    }
    const res: any = await deleteEmpresa(safeTenantId);
    setDeletedIds((prev) => {
      const next = new Set(prev);
      next.add(String(safeTenantId));
      return next;
    });
    return {
      ok: true,
      tenant_id: safeTenantId,
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

  const handleDeleteAll = async () => {
    try {
      const res: any = await deleteAllEmpresas();
      const deleted = Array.isArray(res?.deleted) ? res.deleted : [];
      setDeletedIds((prev) => {
        const next = new Set(prev);
        deleted.forEach((item: any) => {
          const tid = item?.tenant_id ? String(item.tenant_id) : '';
          if (tid) next.add(tid);
        });
        return next;
      });
      return {
        ok: Boolean(res?.ok),
        total: Number(res?.total || 0),
        deleted_count: Number(res?.deleted_count || 0),
        failed_count: Number(res?.failed_count || 0),
        failed: Array.isArray(res?.failed) ? res.failed : [],
      };
    } catch (e: any) {
      const status = e?.response?.status;
      if (status !== 404) throw e;

      // Fallback for older backends where /bulk/delete-all is not deployed yet.
      const targets = empresasDisponibles.map((empresa: any) => ({
        id: String(empresa?.id ?? empresa?.tenant_id ?? '').trim(),
        name: String(empresa?.nombre ?? empresa?.name ?? ''),
      })).filter((x) => x.id);

      const deleted: string[] = [];
      const failed: Array<{ tenant_id: string; name?: string; detail?: string }> = [];

      for (const target of targets) {
        try {
          await deleteEmpresa(target.id);
          deleted.push(target.id);
        } catch (err: any) {
          failed.push({
            tenant_id: target.id,
            name: target.name,
            detail: err?.response?.data?.detail || err?.message || 'Unknown error',
          });
        }
      }

      setDeletedIds((prev) => {
        const next = new Set(prev);
        deleted.forEach((id) => next.add(id));
        return next;
      });

      return {
        ok: failed.length === 0,
        total: targets.length,
        deleted_count: deleted.length,
        failed_count: failed.length,
        failed,
      };
    }
  };

  const handlePurgeOrphans = async () => {
    const ok = window.confirm(
      'This will remove orphan rows from related tables (users/modules/roles without tenant). Continue?'
    );
    if (!ok) return;
    try {
      setPurgingOrphans(true);
      const res: any = await purgeOrphanCompanyData();
      const deleted = res?.deleted || {};
      const lines = Object.keys(deleted)
        .sort()
        .map((k) => `${k}: ${Number(deleted[k] || 0)}`);
      window.alert(`Orphan cleanup completed.\n\n${lines.join('\n')}`);
    } catch (e: any) {
      window.alert(e?.response?.data?.detail || e?.message || 'Error purging orphan data');
    } finally {
      setPurgingOrphans(false);
    }
  };

  return (
    <Container className="empresa-page">
      <header className="empresa-header">
        <h1 className="empresa-title">Company management</h1>
        <p className="empresa-subtitle">Manage companies, modules, and access from one place.</p>
      </header>

      <div className="empresa-toolbar">
        <input
          type="search"
          placeholder="Search company..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="empresa-search"
        />
        <Link to="create" className="empresa-primary">
          New company
        </Link>
        <button
          type="button"
          onClick={() => setShowDeleteAllModal(true)}
          disabled={!empresasDisponibles.length}
          className="action-pill danger"
          title="Delete all companies"
        >
          Delete all
        </button>
        <button
          type="button"
          onClick={handlePurgeOrphans}
          disabled={purgingOrphans}
          className="action-pill amber"
          title="Purge orphan rows"
        >
          {purgingOrphans ? 'Purging...' : 'Purge orphans'}
        </button>
      </div>

      {loading ? (
        <p className="empresa-muted">Loading...</p>
      ) : error ? (
        <p className="empresa-muted" style={{ color: '#dc2626' }}>Error loading companies</p>
      ) : empresasFiltradas.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Modules</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {empresasFiltradas.map((empresa) => {
                const empresaId = String((empresa as any)?.id ?? (empresa as any)?.tenant_id ?? '').trim();
                const nombreEmpresa = empresa?.nombre || (empresa as any)?.name || 'Sin nombre';
                const modulos = (empresa as any)?.modulos || (empresa as any)?.modules || [];
                return (
                  <tr key={empresaId || String(empresa.id)}>
                    <td style={{ fontWeight: 600 }}>{nombreEmpresa}</td>
                    <td>
                      {modulos.length > 0 ? (
                        <div className="badge-group">
                          {modulos.map((modulo: string) => (
                            <span key={`${empresaId}-${modulo}`} className="badge">
                              {modulo}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="badge badge-warning">No modules</span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-pills">
                        <Link to={`/admin/companies/${empresaId}/edit`} className="action-pill blue">
                          Edit
                        </Link>
                        <Link to={`/admin/companies/${empresaId}/users`} className="action-pill green">
                          Users
                        </Link>
                        <Link to={`/admin/companies/modules/${empresaId}`} className="action-pill amber">
                          Modules
                        </Link>
                        <Link to={`/admin/companies/${empresaId}/config`} className="action-pill violet">
                          Config
                        </Link>
                        <button
                          onClick={() => setEmpresaAEliminar({ id: empresaId, name: nombreEmpresa })}
                          className="action-pill danger"
                          disabled={!empresaId}
                        >
                          Delete
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
        <div className="empresa-empty">No companies registered.</div>
      )}

      {empresaAEliminar && (
        <DeleteEmpresaModal
          empresa={empresaAEliminar}
          onClose={() => setEmpresaAEliminar(null)}
          onConfirm={handleConfirmDelete}
        />
      )}

      {showDeleteAllModal && (
        <DeleteAllCompaniesModal
          companyCount={empresasDisponibles.length}
          onClose={() => setShowDeleteAllModal(false)}
          onConfirm={handleDeleteAll}
        />
      )}
    </Container>
  );
};
