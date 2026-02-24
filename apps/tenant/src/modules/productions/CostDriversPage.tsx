/**
 * CostDriversPage - Gestión de tipos de costos indirectos de producción
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  listCostDrivers,
  createCostDriver,
  updateCostDriver,
  deleteCostDriver,
  type CostDriver,
} from '../../services/api/productionCosts';
import { useI18n } from '../../i18n/I18nProvider';
import { useUnits } from '../../hooks/useGlobalCatalogs';

interface EditForm {
  code: string;
  name: string;
  unit: string;
  default_rate: string;
}

const emptyForm: EditForm = { code: '', name: '', unit: 'HORA', default_rate: '' };

export default function CostDriversPage() {
  const { lang } = useI18n();
  const isEs = String(lang || 'en').toLowerCase().startsWith('es');
  const L = (en: string, es: string) => (isEs ? es : en);
  const navigate = useNavigate();
  const { empresa } = useParams();
  const basePath = `${empresa ? `/${empresa}` : ''}/produccion`;

  const [drivers, setDrivers] = useState<CostDriver[]>([]);
  const { items: unitTypes } = useUnits();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<EditForm>(emptyForm);

  useEffect(() => {
    loadDrivers();
  }, []);

  const loadDrivers = async () => {
    try {
      setLoading(true);
      const data = await listCostDrivers();
      setDrivers(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      setError(err?.message || L('Error loading cost drivers', 'Error al cargar tipos de costo'));
    } finally {
      setLoading(false);
    }
  };

  const getUnitLabel = (code: string) => {
    const ut = unitTypes.find((u) => u.code === code);
    if (!ut) return code;
    return ut.name;
  };

  const handleSave = async () => {
    if (!form.code.trim() || !form.name.trim()) return;
    try {
      setSaving(true);
      setError(null);
      const payload = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        unit: form.unit,
        default_rate: Number(form.default_rate) || 0,
      };
      if (editingId) {
        await updateCostDriver(editingId, payload);
      } else {
        await createCostDriver(payload);
      }
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      await loadDrivers();
    } catch (err: any) {
      setError(err?.message || L('Error saving', 'Error al guardar'));
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (d: CostDriver) => {
    setEditingId(d.id);
    setForm({
      code: d.code,
      name: d.name,
      unit: d.unit,
      default_rate: String(d.default_rate),
    });
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(L('Delete this cost driver?', '¿Eliminar este tipo de costo?'))) return;
    try {
      await deleteCostDriver(id);
      await loadDrivers();
    } catch (err: any) {
      alert(err?.message || L('Error deleting', 'Error al eliminar'));
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm);
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {L('Production Cost Types', 'Tipos de Costo de Producción')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {L(
              'Define labor roles, energy, packaging, and other indirect cost categories.',
              'Define roles de mano de obra, energía, empaque y otros costos indirectos.'
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="px-3 py-2 text-sm border rounded hover:bg-gray-50"
            onClick={() => navigate(basePath)}
          >
            {L('← Back', '← Volver')}
          </button>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={() => {
              setEditingId(null);
              setForm(emptyForm);
              setShowForm(true);
            }}
          >
            + {L('New cost type', 'Nuevo tipo de costo')}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded text-sm">
          {error}
        </div>
      )}

      {/* Form */}
      {showForm && (
        <div className="mb-6 p-4 border rounded-lg bg-gray-50">
          <h2 className="text-lg font-semibold mb-3">
            {editingId
              ? L('Edit cost type', 'Editar tipo de costo')
              : L('New cost type', 'Nuevo tipo de costo')}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {L('Code', 'Código')}
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border rounded text-sm"
                placeholder="LABOR_BAKER"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                disabled={!!editingId}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {L('Name', 'Nombre')}
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border rounded text-sm"
                placeholder={L('e.g. Baker', 'ej. Panadero')}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {L('Unit', 'Unidad')}
              </label>
              <select
                className="w-full px-3 py-2 border rounded text-sm"
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              >
                {unitTypes.map((o) => (
                  <option key={o.code} value={o.code}>
                    {o.name} ({o.abbreviation})
                  </option>
                ))}
                {unitTypes.length === 0 && <option value={form.unit}>{form.unit}</option>}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {L('Default rate', 'Tarifa por defecto')}
              </label>
              <input
                type="number"
                className="w-full px-3 py-2 border rounded text-sm"
                placeholder="0.00"
                min="0"
                step="0.01"
                value={form.default_rate}
                onChange={(e) => setForm({ ...form, default_rate: e.target.value })}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              onClick={handleSave}
              disabled={saving || !form.code.trim() || !form.name.trim()}
            >
              {saving ? L('Saving...', 'Guardando...') : L('Save', 'Guardar')}
            </button>
            <button
              className="px-4 py-2 text-sm border rounded hover:bg-gray-100"
              onClick={handleCancel}
            >
              {L('Cancel', 'Cancelar')}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-gray-500 text-center py-10">{L('Loading...', 'Cargando...')}</p>
      ) : drivers.length === 0 ? (
        <div className="text-center py-16 border rounded-lg bg-white">
          <p className="text-gray-500 text-lg mb-2">
            {L('No cost types defined yet', 'No hay tipos de costo definidos')}
          </p>
          <p className="text-gray-400 text-sm mb-4">
            {L(
              'Create cost types like labor roles, energy, packaging to track indirect production costs.',
              'Crea tipos como roles de mano de obra, energía, empaque para rastrear costos indirectos.'
            )}
          </p>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={() => {
              setEditingId(null);
              setForm(emptyForm);
              setShowForm(true);
            }}
          >
            + {L('Create first cost type', 'Crear primer tipo de costo')}
          </button>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {L('Code', 'Código')}
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {L('Name', 'Nombre')}
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {L('Unit', 'Unidad')}
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">
                  {L('Default rate', 'Tarifa')}
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">
                  {L('Status', 'Estado')}
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">
                  {L('Actions', 'Acciones')}
                </th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((d) => (
                <tr key={d.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{d.code}</td>
                  <td className="px-4 py-3 font-medium">{d.name}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {getUnitLabel(d.unit)}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    ${Number(d.default_rate).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                        d.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {d.is_active ? L('Active', 'Activo') : L('Inactive', 'Inactivo')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="text-blue-600 hover:underline text-sm mr-3"
                      onClick={() => handleEdit(d)}
                    >
                      {L('Edit', 'Editar')}
                    </button>
                    <button
                      className="text-red-600 hover:underline text-sm"
                      onClick={() => handleDelete(d.id)}
                    >
                      {L('Delete', 'Eliminar')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
