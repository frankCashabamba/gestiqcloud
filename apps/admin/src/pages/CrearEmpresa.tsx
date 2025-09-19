import React, { useState, useEffect } from 'react';

import ModuloSelector from '../modulos/ModuloSelector';
import { useCrearEmpresa } from "../hooks/useCrearEmpresa";
import type { FormularioEmpresa } from '../typesall/empresa';

const INITIAL_STATE: FormularioEmpresa = {
  nombre_empresa: '',
  tipo_empresa: '',
  tipo_negocio: '',
  ruc: '',
  telefono: '',
  direccion: '',
  pais: '',
  provincia: '',
  ciudad: '',
  cp: '',
  sitio_web: '',
  logo: null,
  color_primario: '#4f46e5',
  plantilla_inicio: '',
  config_json: '',
  nombre_encargado: '',
  apellido_encargado: '',
  email: '',
  username: '',
  password: '',
  modulos: [],
};

export const CrearEmpresa: React.FC = () => {
  const [formData, setFormData] = useState<FormularioEmpresa>(INITIAL_STATE);
  // Username se autogenera y es solo lectura
  const [localError, setLocalError] = useState<string | null>(null);
  const { crear, loading, error, success, fieldErrors, needSecondSurname } = useCrearEmpresa();

  // Generar automáticamente username base: nombre.apellido
  useEffect(() => {
    const nombre = formData.nombre_encargado.trim().toLowerCase();
    const apellido = formData.apellido_encargado.trim().toLowerCase();
    const sugerido = nombre && apellido ? `${nombre}.${apellido}`.replace(/\s+/g, '') : '';
    setFormData(prev => ({ ...prev, username: sugerido }));
  }, [formData.nombre_encargado, formData.apellido_encargado]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    if (type === 'file') {
      setFormData({ ...formData, [name]: (e.target as HTMLInputElement).files?.[0] || null });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  const handleModuloChange = (moduloId: number) => {
    setFormData(prev => ({
      ...prev,
      modulos: prev.modulos.includes(moduloId)
        ? prev.modulos.filter(id => id !== moduloId)
        : [...prev.modulos, moduloId],
    }));
  };

  // Validadores simples
  const isValidEmail = (v: string) => /.+@.+\..+/.test(v)
  const isValidUsername = (v: string) => /^[a-z0-9_.-]{3,32}$/.test(v)
  const isStrongPassword = (v: string) => v.length >= 8
  const isValidPhone = (v: string) => v.length === 0 || /^[0-9+()\-\s]{6,20}$/.test(v)
  const isValidUrl = (v: string) => {
    if (!v) return true
    try { new URL(v.startsWith('http') ? v : `http://${v}`); return true } catch { return false }
  }
  const isValidJson = (v: string) => {
    if (!v || !v.trim()) return true
    try { JSON.parse(v); return true } catch { return false }
  }

  const validateForm = (): string | null => {
    if (!formData.nombre_empresa.trim()) return 'El nombre de la empresa es obligatorio.';
    if (!formData.nombre_encargado.trim()) return 'El nombre del encargado es obligatorio.';
    if (!formData.apellido_encargado.trim()) return 'El apellido del encargado es obligatorio.';
    if (!formData.email.trim()) return 'El correo es obligatorio.';
    if (!isValidEmail(formData.email.trim())) return 'El correo no tiene un formato válido.';
    if (!formData.username.trim()) return 'El usuario es obligatorio.';
    if (!isValidUsername(formData.username.trim())) return 'El usuario debe usar minúsculas, números o ._- (3-32).';
    // Password opcional: si viene, validar fortaleza mínima
    if (formData.password && !isStrongPassword(formData.password)) return 'La contraseña debe tener al menos 8 caracteres.';
    if (!isValidPhone(formData.telefono || '')) return 'El teléfono solo admite dígitos, +, -, espacios y ().';
    if (!isValidUrl(formData.sitio_web || '')) return 'El sitio web no es una URL válida.';
    if (!isValidJson(formData.config_json || '')) return 'config_json debe ser un JSON válido.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    const validationError = validateForm();
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    const result = await crear(formData);
    if (result) {
      setFormData(INITIAL_STATE);
      
    }
  };

  return (
   
      <div className="max-w-6xl mx-auto px-4 py-10 animate-fade-in">
        <div className="bg-white shadow-xl rounded-3xl p-8">
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold text-indigo-700 mb-2">🚀 Registrar nueva empresa</h1>
            <p className="text-gray-500 text-sm">
              Completa los datos para crear una empresa, su usuario principal y módulos activos.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-10">
            <section>
              <h2 className="text-lg font-semibold text-gray-800 mb-4">🏢 Datos de la Empresa</h2>
              <div className="grid md:grid-cols-2 gap-6">
                <input name="nombre_empresa" value={formData.nombre_empresa} onChange={handleChange} placeholder="Nombre de la empresa" className="border border-gray-300 rounded-lg px-4 py-2 text-sm" />
                <select name="tipo_empresa" value={formData.tipo_empresa} onChange={handleChange} className="border border-gray-300 rounded-lg px-4 py-2 text-sm">
                  <option value="">Tipo de empresa</option>
                  <option value="1">SRL</option>
                  <option value="2">SAC</option>
                  <option value="3">EIRL</option>
                </select>
                <select name="tipo_negocio" value={formData.tipo_negocio} onChange={handleChange} className="border border-gray-300 rounded-lg px-4 py-2 text-sm">
                  <option value="">Tipo de negocio</option>
                  <option value="1">Comercio</option>
                  <option value="2">Servicios</option>
                  <option value="3">Manufactura</option>
                </select>
                {["ruc", "telefono", "direccion", "pais", "provincia", "ciudad", "cp", "sitio_web", "color_primario", "plantilla_inicio"].map((field) => {
                  const type = field === 'color_primario' ? 'color' : field === 'sitio_web' ? 'url' : 'text'
                  const err = field === 'ruc' ? (fieldErrors as any)?.ruc : ''
                  return (
                    <div key={field} className="flex flex-col gap-1">
                      <input
                        name={field}
                        type={type as any}
                        value={(formData as any)[field]}
                        onChange={handleChange}
                        placeholder={field.replace(/_/g, ' ')}
                        aria-invalid={!!err}
                        className={`border rounded-lg px-4 py-2 text-sm ${err ? 'border-red-400' : 'border-gray-300'}`}
                      />
                      {err && <span className="text-xs text-red-600">{err}</span>}
                    </div>
                  )
                })}
                <input type="file" name="logo" onChange={handleChange} />
                <textarea name="config_json" placeholder="config_json" value={formData.config_json} onChange={handleChange} className="md:col-span-2 border border-gray-300 rounded-lg px-4 py-2 text-sm" />
                {/* Módulos dentro del mismo grid para mantener alineación visual */}
                <div className="md:col-span-2">
                  <ModuloSelector selected={formData.modulos} onChange={handleModuloChange} />
                </div>
              </div>
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-800 mb-4">👤 Usuario Administrador</h2>
              <div className="grid md:grid-cols-3 gap-6">
                {["nombre_encargado", "apellido_encargado", "email"].map((field) => {
                  const err = field === 'email' ? (fieldErrors as any)?.email : ''
                  return (
                    <div key={field} className="flex flex-col gap-1">
                      <input
                        name={field}
                        type={field === 'email' ? 'email' : 'text'}
                        required={field !== 'email' ? undefined : true}
                        value={(formData as any)[field]}
                        onChange={handleChange}
                        placeholder={field.replace(/_/g, ' ')}
                        aria-invalid={!!err}
                        className={`border rounded-lg px-4 py-2 text-sm ${err ? 'border-red-400' : 'border-gray-300'}`}
                      />
                      {err && <span className="text-xs text-red-600">{err}</span>}
                    </div>
                  )
                })}
                {needSecondSurname && (
                  <div className="flex flex-col gap-1">
                    <input
                      name="segundo_apellido_encargado"
                      type="text"
                      value={(formData as any).segundo_apellido_encargado || ''}
                      onChange={handleChange}
                      placeholder="segundo apellido"
                      className="border border-gray-300 rounded-lg px-4 py-2 text-sm"
                    />
                    <span className="text-xs text-gray-600">Se usará para sugerir un usuario único.</span>
                  </div>
                )}
                <div className="flex flex-col gap-1">
                  <input name="username" type="text" value={formData.username} readOnly placeholder="username" aria-invalid={!!(fieldErrors as any)?.username} className={`bg-gray-50 border rounded-lg px-4 py-2 text-sm ${(fieldErrors as any)?.username ? 'border-red-400' : 'border-gray-300'}`} />
                  {(fieldErrors as any)?.username && <span className="text-xs text-red-600">{(fieldErrors as any)?.username}</span>}
                </div>
                <input name="password" type="password" value={formData.password} onChange={handleChange} placeholder="Contraseña (opcional, se enviará email para crearla)" className="border border-gray-300 rounded-lg px-4 py-2 text-sm" />
              </div>
            </section>

            <div className="text-center mt-8 space-y-4">
              <button type="submit" disabled={loading} className={`w-full sm:w-auto px-6 py-3 rounded-xl font-semibold text-white transition duration-300 shadow-md ${
                loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
              }`}>
                {loading ? 'Guardando...' : '✅ Crear empresa y usuario'}
              </button>

              {localError && (
                <div className="max-w-xl mx-auto bg-red-100 border border-red-300 text-red-700 px-6 py-3 rounded-lg text-sm shadow">
                  {localError}
                </div>
              )}
              {error && (
                <div className="max-w-xl mx-auto bg-red-100 border border-red-300 text-red-700 px-6 py-3 rounded-lg text-sm shadow">
                  {error}
                </div>
              )}
              {success && (
                <div className="max-w-xl mx-auto bg-green-100 border border-green-300 text-green-700 px-6 py-3 rounded-lg text-sm shadow">
                  {success}
                </div>
              )}
            </div>

            <div className="text-center mt-8">
              <a href="/admin/empresas" className="text-sm text-indigo-600 hover:underline">
                ⬅️ Volver al listado de empresas
              </a>
            </div>
          </form>
        </div>
      </div>
 
  );
};
