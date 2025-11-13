import React, { useState } from 'react';
import {
  Close as CloseIcon,
  Edit as EditIcon,
  CloudUpload as CloudUploadIcon,
  CheckCircle as CheckCircleIcon,
  ErrorOutline as ErrorOutlineIcon
} from '@mui/icons-material';

interface PreviewItem {
  nombre: string;
  precio: number;
  cantidad: number;
  categoria: string;
  _validation?: {
    valid: boolean;
    errors: string[];
  };
  _normalized?: Record<string, any>;
}

interface VistaPreviaProps {
  analysis: {
    headers: string[];
    total_rows: number;
    suggested_mapping: Record<string, string>;
  };
  previewItems: PreviewItem[];
  categories: string[];
  stats: {
    total: number;
    categories: number;
    with_stock?: number;
    zero_stock?: number;
  };
  onConfirm: (mapping: Record<string, string>) => Promise<void>;
  onCancel: () => void;
}

export function VistaPrevia({
  analysis,
  previewItems,
  categories,
  stats,
  onConfirm,
  onCancel
}: VistaPreviaProps) {
  const [customMapping, setCustomMapping] = useState<Record<string, string>>(
    analysis.suggested_mapping || {}
  );
  const [loading, setLoading] = useState(false);
  const [showMappingEditor, setShowMappingEditor] = useState(false);

  const validItems = previewItems.filter(item => item._validation?.valid);
  const invalidItems = previewItems.filter(item => !item._validation?.valid);

  const handleConfirmImport = async () => {
    setLoading(true);
    try {
      await onConfirm(customMapping);
    } finally {
      setLoading(false);
    }
  };

  const updateMapping = (excelCol: string, destField: string) => {
    setCustomMapping(prev => ({
      ...prev,
      [excelCol]: destField
    }));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">📊 Vista Previa de Importación</h2>
            <p className="text-blue-100 mt-1">
              {stats.total} productos detectados • {stats.categories} categorías
            </p>
          </div>
          <button
            onClick={onCancel}
            className="text-white hover:bg-white/20 p-2 rounded-lg transition"
          >
            <CloseIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Resumen */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="text-3xl font-bold text-blue-600">{stats.total}</div>
              <div className="text-sm text-gray-600">Total Productos</div>
            </div>
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <div className="text-3xl font-bold text-green-600">{validItems.length}</div>
              <div className="text-sm text-gray-600">Válidos ✓</div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg border border-red-200">
              <div className="text-3xl font-bold text-red-600">{invalidItems.length}</div>
              <div className="text-sm text-gray-600">Con Errores</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <div className="text-3xl font-bold text-purple-600">{categories.length}</div>
              <div className="text-sm text-gray-600">Categorías</div>
            </div>
          </div>

          {/* Categorías Detectadas */}
          {categories.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold mb-3">🏷️ Categorías Detectadas</h3>
              <div className="flex flex-wrap gap-2">
                {categories.map((cat, idx) => (
                  <span
                    key={idx}
                    className="bg-indigo-100 text-indigo-800 px-3 py-1 rounded-full text-sm font-medium"
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Mapeo de Columnas */}
          <div className="mb-6">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-lg font-semibold">🔗 Mapeo de Columnas</h3>
              <button
                onClick={() => setShowMappingEditor(!showMappingEditor)}
                className="text-blue-600 hover:text-blue-800 flex items-center gap-2 text-sm"
              >
                <EditIcon className="w-4 h-4" />
                {showMappingEditor ? 'Ocultar' : 'Editar Mapeo'}
              </button>
            </div>

            {showMappingEditor && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-2">
                {Object.entries(customMapping).map(([excelCol, destField]) => (
                  <div key={excelCol} className="flex items-center gap-4">
                    <div className="flex-1 font-mono text-sm">{excelCol}</div>
                    <span>→</span>
                    <select
                      value={destField}
                      onChange={(e) => updateMapping(excelCol, e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                    >
                      <option value="ignore">Ignorar</option>
                      <option value="name">Nombre</option>
                      <option value="precio">Precio</option>
                      <option value="cantidad">Cantidad</option>
                      <option value="categoria">Categoría</option>
                      <option value="sku">SKU/Código</option>
                      <option value="costo">Costo</option>
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Vista Previa Tabla */}
          <div>
            <h3 className="text-lg font-semibold mb-3">👁️ Primeros 10 Productos</h3>
            <div className="overflow-x-auto border border-gray-200 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-gray-100">
                  <tr>
                    <th className="px-4 py-3 text-left">#</th>
                    <th className="px-4 py-3 text-left">Nombre</th>
                    <th className="px-4 py-3 text-right">Precio</th>
                    <th className="px-4 py-3 text-right">Cantidad</th>
                    <th className="px-4 py-3 text-left">Categoría</th>
                    <th className="px-4 py-3 text-center">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {previewItems.map((item, idx) => (
                    <tr
                      key={idx}
                      className={`border-t ${
                        item._validation?.valid
                          ? 'bg-white hover:bg-green-50'
                          : 'bg-red-50 hover:bg-red-100'
                      }`}
                    >
                      <td className="px-4 py-3 text-gray-600">{idx + 1}</td>
                      <td className="px-4 py-3 font-medium">{item.nombre || '—'}</td>
                      <td className="px-4 py-3 text-right">
                        {item.precio ? `$${item.precio.toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">{item.cantidad || 0}</td>
                      <td className="px-4 py-3">
                        <span className="bg-gray-100 px-2 py-1 rounded text-xs">
                          {item.categoria || 'SIN_CATEGORIA'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {item._validation?.valid ? (
                          <CheckCircleIcon className="w-5 h-5 text-green-600 mx-auto" />
                        ) : (
                          <div className="group relative">
                            <ErrorOutlineIcon className="w-5 h-5 text-red-600 mx-auto cursor-help" />
                            <div className="hidden group-hover:block absolute z-10 bg-gray-900 text-white text-xs p-2 rounded shadow-lg right-0 mt-1 w-48">
                              {item._validation?.errors.join(', ')}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Advertencias */}
          {invalidItems.length > 0 && (
            <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <ErrorOutlineIcon className="w-5 h-5 text-yellow-600 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-yellow-900">
                    {invalidItems.length} producto(s) con errores
                  </h4>
                  <p className="text-sm text-yellow-700 mt-1">
                    Estos productos no se importarán hasta que corrijas los errores. 
                    Puedes continuar con los {validItems.length} válidos.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 p-6 border-t flex justify-between items-center">
          <button
            onClick={onCancel}
            className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-lg font-medium transition"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirmImport}
            disabled={loading || validItems.length === 0}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-medium flex items-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Importando...
              </>
            ) : (
              <>
                <CloudUploadIcon className="w-5 h-5" />
                Importar {validItems.length} Productos →
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
