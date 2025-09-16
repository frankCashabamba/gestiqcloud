import {  useModulos } from "./useModulos";
import type { Modulo } from "./types";

interface Props {
  selected: number[];
  onChange: (moduloId: number) => void;
}

export default function ModuloSelector({ selected, onChange }: Props) {
  const { modulos, loading, error } = useModulos();

  const toggleModulo = (id: number) => {
    onChange(id);
  };

  return (
    <section>
      <h2 className="text-lg font-semibold text-gray-800 mb-4">📦 Módulos a contratar</h2>
      {loading && (
        <div className="mb-4 text-sm text-gray-500">Cargando módulos...</div>
      )}
      {error && (
        <div className="mb-4 bg-red-100 border border-red-300 text-red-700 px-4 py-2 rounded-lg text-sm">
          {error}
        </div>
      )}
      <div className="grid md:grid-cols-3 gap-4">
        {modulos.map((modulo) => (
          <label
            key={modulo.id}
            className="flex items-center gap-3 border p-4 rounded-xl shadow-sm hover:shadow-md transition cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.includes(modulo.id)}
              onChange={() => toggleModulo(modulo.id)}
            />
            <span className="text-sm font-medium text-gray-700">
              {modulo.icono ?? "📦"} {modulo.nombre}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}
