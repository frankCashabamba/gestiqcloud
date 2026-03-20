/**
 * CostDriversPage - Gestión de tipos de costos indirectos de producción
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  listCostDrivers,
  listCostDriverUnitTypes,
  createCostDriver,
  updateCostDriver,
  deleteCostDriver,
  type CostDriver,
  type CostDriverCreate,
  type CostDriverUnitType,
} from '../../services/api/productionCosts';
import ProductionAvailabilityGuard from './ProductionAvailabilityGuard';

interface EditForm {
  code: string;
  name: string;
  unit: string;
  default_rate: string;
  consumption_rate: string;
}

const DEFAULT_COST_DRIVER_UNIT = '';

const createEmptyForm = (unit: string = DEFAULT_COST_DRIVER_UNIT): EditForm => ({
  code: '',
  name: '',
  unit,
  default_rate: '',
  consumption_rate: '',
});

export default function CostDriversPage() {
  return (
    <ProductionAvailabilityGuard>
      <CostDriversPageContent />
    </ProductionAvailabilityGuard>
  );
}

function CostDriversPageContent() {
  const { t } = useTranslation(['productions', 'common']);
  const navigate = useNavigate();
  const { empresa } = useParams();
  const basePath = `${empresa ? `/${empresa}` : ''}/manufacturing`;

  const [drivers, setDrivers] = useState<CostDriver[]>([]);
  const [unitTypes, setUnitTypes] = useState<CostDriverUnitType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<EditForm>(createEmptyForm());

  useEffect(() => {
    loadDrivers();
  }, []);

  const loadDrivers = async () => {
    try {
      setLoading(true);
      const [driversData, unitTypesData] = await Promise.all([
        listCostDrivers(),
        listCostDriverUnitTypes().catch(() => []),
      ]);
      const normalizedUnitTypes = Array.isArray(unitTypesData) ? unitTypesData : [];
      const defaultUnit = normalizedUnitTypes[0]?.code || DEFAULT_COST_DRIVER_UNIT;
      const data = Array.isArray(driversData) ? driversData : [];
      setDrivers(Array.isArray(data) ? data : []);
      setUnitTypes(normalizedUnitTypes);
      setForm((current) => (
        current.code || current.name || current.default_rate || current.consumption_rate || current.unit !== DEFAULT_COST_DRIVER_UNIT
          ? current
          : createEmptyForm(defaultUnit)
      ));
      setError(null);
    } catch (err: any) {
      setError(err?.message || t('productions:costDrivers.errorLoading'));
    } finally {
      setLoading(false);
    }
  };

  const getUnitLabel = (code: string) => {
    const ut = unitTypes.find((u) => u.code === code);
    if (!ut) return code;
    return ut.name_es || ut.name_en || ut.code;
  };

  const handleSave = async () => {
    if (!form.code.trim() || !form.name.trim()) return;
    try {
      setSaving(true);
      setError(null);
      const payload: CostDriverCreate = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        unit: form.unit,
        default_rate: Number(form.default_rate) || 0,
      };
      if (form.consumption_rate !== '') {
        payload.consumption_rate = Number(form.consumption_rate);
      }
      if (editingId) {
        await updateCostDriver(editingId, payload);
      } else {
        await createCostDriver(payload);
      }
      setShowForm(false);
      setEditingId(null);
      setForm(createEmptyForm(unitTypes[0]?.code || DEFAULT_COST_DRIVER_UNIT));
      await loadDrivers();
    } catch (err: any) {
      setError(err?.message || t('productions:costDrivers.errorSaving'));
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
      consumption_rate: d.consumption_rate != null ? String(d.consumption_rate) : '',
    });
    setShowForm(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t('productions:costDrivers.deleteConfirm'))) return;
    try {
      await deleteCostDriver(id);
      await loadDrivers();
    } catch (err: any) {
      alert(err?.message || t('productions:costDrivers.errorDeleting'));
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setForm(createEmptyForm(unitTypes[0]?.code || DEFAULT_COST_DRIVER_UNIT));
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t('productions:costDrivers.title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t('productions:costDrivers.description')}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="px-3 py-2 text-sm border rounded hover:bg-gray-50"
            onClick={() => navigate(basePath)}
          >
            {t('productions:costDrivers.back')}
          </button>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={() => {
              setEditingId(null);
              setForm(createEmptyForm(unitTypes[0]?.code || DEFAULT_COST_DRIVER_UNIT));
              setShowForm(true);
            }}
          >
            + {t('productions:costDrivers.new')}
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
              ? t('productions:costDrivers.edit')
              : t('productions:costDrivers.new')}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {t('productions:costDrivers.code')}
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
                {t('productions:costDrivers.name')}
              </label>
              <input
                type="text"
                className="w-full px-3 py-2 border rounded text-sm"
                placeholder={t('productions:costDrivers.namePlaceholder')}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {t('productions:costDrivers.unit')}
              </label>
              <select
                className="w-full px-3 py-2 border rounded text-sm"
                value={form.unit}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
              >
                {unitTypes.map((o) => (
                  <option key={o.code} value={o.code}>
                    {(o.name_es || o.name_en || o.code)} ({o.code})
                  </option>
                ))}
                {unitTypes.length === 0 && <option value={form.unit}>{form.unit}</option>}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">
                {t('productions:costDrivers.defaultRate')}
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
          <div className="mt-3">
            <label className="block text-xs text-gray-600 mb-1">
              {t('productions:costDrivers.consumptionRate')}
              <span className="ml-1 text-gray-400">{t('productions:costDrivers.consumptionRateHint')}</span>
            </label>
            <input
              type="number"
              className="px-3 py-2 border rounded text-sm w-48"
              placeholder="ej: 2.0"
              min="0"
              step="0.01"
              value={form.consumption_rate}
              onChange={(e) => setForm({ ...form, consumption_rate: e.target.value })}
            />
          </div>
          <div className="flex gap-2 mt-4">
            <button
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              onClick={handleSave}
              disabled={saving || !form.code.trim() || !form.name.trim() || !form.unit.trim()}
            >
              {saving ? t('productions:costDrivers.saving') : t('productions:costDrivers.save')}
            </button>
            <button
              className="px-4 py-2 text-sm border rounded hover:bg-gray-100"
              onClick={handleCancel}
            >
              {t('productions:costDrivers.cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-gray-500 text-center py-10">{t('productions:costDrivers.loading')}</p>
      ) : drivers.length === 0 ? (
        <div className="text-center py-16 border rounded-lg bg-white">
          <p className="text-gray-500 text-lg mb-2">
            {t('productions:costDrivers.empty')}
          </p>
          <p className="text-gray-400 text-sm mb-4">
            {t('productions:costDrivers.emptyDescription')}
          </p>
          <button
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
            onClick={() => {
              setEditingId(null);
              setForm(createEmptyForm(unitTypes[0]?.code || DEFAULT_COST_DRIVER_UNIT));
              setShowForm(true);
            }}
          >
            + {t('productions:costDrivers.createFirst')}
          </button>
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.code')}
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.name')}
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.unit')}
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.defaultRate')}
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.consumptionRate')}
                </th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.status')}
                </th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">
                  {t('productions:costDrivers.actions')}
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
                  <td className="px-4 py-3 text-right text-gray-600">
                    {d.consumption_rate != null ? `${Number(d.consumption_rate).toFixed(2)}/hr` : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs ${
                        d.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {d.is_active ? t('productions:costDrivers.active') : t('productions:costDrivers.inactive')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="text-blue-600 hover:underline text-sm mr-3"
                      onClick={() => handleEdit(d)}
                    >
                      {t('productions:edit')}
                    </button>
                    <button
                      className="text-red-600 hover:underline text-sm"
                      onClick={() => handleDelete(d.id)}
                    >
                      {t('productions:delete')}
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
