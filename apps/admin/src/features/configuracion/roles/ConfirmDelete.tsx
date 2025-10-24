// src/pages/configuracion/roles/ConfirmDelete.tsx
import React from 'react';

interface ConfirmDeleteProps {
  nombre: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDelete: React.FC<ConfirmDeleteProps> = ({ nombre, onConfirm, onCancel }) => {
  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-40 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 text-center">
        <h2 className="text-xl font-bold mb-4">¿Eliminar el rol "{nombre}"?</h2>
        <p className="text-gray-600 mb-6">Esta acción no se puede deshacer.</p>
        <button onClick={onConfirm} className="bg-red-600 text-white px-4 py-2 rounded">Eliminar</button>
        <button onClick={onCancel} className="ml-4 text-gray-600 underline">Cancelar</button>
      </div>
    </div>
  );
};

export default ConfirmDelete;