import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import type { RoleData } from './types/roles';
import { permisosToArray } from '@shared/utils/permissions';
import type { GlobalPermission } from '../../../services/configuracion/permisos';
import { apiPost, apiPut } from '../../../lib/api';
// Layout no es necesario: ya hay LayoutAdmin en App

interface RoleFormProps {
  mode: 'create' | 'edit';
  initialData?: RoleData;
  onSubmit: (data: RoleData) => void;
  availablePermissions: GlobalPermission[];
}

const RoleForm: React.FC<RoleFormProps> = ({ mode, initialData, onSubmit, availablePermissions }) => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const buildPerms = (perms?: string[]) => {
    const keys = new Set<string>();
    availablePermissions.forEach((p) => keys.add(p.key));
    (perms || []).forEach((p) => keys.add(p));
    return Array.from(keys).reduce((acc, key) => {
      acc[key] = (perms || []).includes(key);
      return acc;
    }, {} as Record<string, boolean>);
  };

  const [form, setForm] = useState({
    nombre: initialData?.nombre || '',
    descripcion: initialData?.descripcion || '',
    permisos: buildPerms(initialData?.permisos),
  });

  const [errors, setErrors] = useState<{ nombre?: string; descripcion?: string }>({});

  React.useEffect(() => {
    setForm((prev) => ({
      ...prev,
      permisos: {
        ...buildPerms(Object.keys(prev.permisos || {}).filter((k) => prev.permisos[k])),
      },
    }));
  }, [availablePermissions]);

  const handleInputChange = (field: 'nombre' | 'descripcion', value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handlePermissionToggle = (key: string) => {
    setForm(prev => ({
      ...prev,
      permisos: {
        ...prev.permisos,
        [key]: !prev.permisos[key],
      },
    }));
  };

  // Removed "Copiar desde rol base" feature

  const validate = () => {
    const newErrors: typeof errors = {};
    if (!form.nombre.trim()) newErrors.nombre = 'El nombre del rol es obligatorio.';
    if (!form.descripcion.trim()) newErrors.descripcion = 'La descripción es obligatoria.';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (isSubmitting || !validate()) return;

    setIsSubmitting(true);

    const payload: RoleData = {
      id: initialData?.id,
      nombre: form.nombre.trim(),
      descripcion: form.descripcion.trim(),
      permisos: permisosToArray(form.permisos),
    };

    const endpoint = mode === 'edit'
      ? `/v1/roles-base/${initialData?.id}`
      : '/v1/roles-base/';

    try {
      const savedRole = mode === 'edit'
        ? await apiPut<RoleData>(endpoint, payload)
        : await apiPost<RoleData>(endpoint, payload);

      toast.success(`✅ Rol ${mode === 'edit' ? 'actualizado' : 'creado'} correctamente`);
      onSubmit(savedRole);
      navigate('/admin/configuracion/roles', { replace: true });
    } catch (err: any) {
      toast.error(`❌ ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <ToastContainer />
      <h1 className="text-2xl font-bold mb-6">
        {mode === 'edit' ? '✏️ Editar Rol' : '➕ Crear Rol'}
      </h1>

      {/* Removed: Copiar desde rol base */}

      <div className="mb-4">
        <label className="block font-medium text-sm mb-1">
          Nombre del rol <span className="text-red-600">*</span>
        </label>
        <input
          type="text"
          value={form.nombre}
          onChange={e => handleInputChange('nombre', e.target.value)}
          className="w-full border p-2"
        />
        {errors.nombre && <p className="text-red-600 text-sm mt-1">{errors.nombre}</p>}
      </div>

      <div className="mb-6">
        <label className="block font-medium text-sm mb-1">
          Descripción <span className="text-red-600">*</span>
        </label>
        <input
          type="text"
          value={form.descripcion}
          onChange={e => handleInputChange('descripcion', e.target.value)}
          className="w-full border p-2"
        />
        {errors.descripcion && <p className="text-red-600 text-sm mt-1">{errors.descripcion}</p>}
      </div>

      <fieldset className="mb-6">
        <legend className="text-lg font-semibold mb-2">Permisos disponibles</legend>
        <div className="grid grid-cols-2 gap-2">
          {Array.from(
            new Set([
              ...availablePermissions.map((p) => p.key),
              ...Object.keys(form.permisos || {}),
            ])
          )
            .sort()
            .map((key) => {
              const meta = availablePermissions.find((p) => p.key === key);
              const label = meta?.description ? `${meta.description} (${key})` : key;
              return (
            <div key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`permiso-${key}`}
                checked={!!form.permisos[key]}
                onChange={() => handlePermissionToggle(key)}
              />
              <label htmlFor={`permiso-${key}`}>{label}</label>
            </div>
              );
            })}
        </div>
      </fieldset>

      <div className="flex gap-4">
        <button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          💾 {isSubmitting ? 'Guardando...' : 'Save'}
        </button>
        <button
          onClick={() => navigate(-1)}
          className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded"
        >
          Cancelar
        </button>
      </div>
    </div>
  );

};

export default RoleForm;
