const fs = require('fs');
const path = require('path');

function walkDir(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory() && !entry.name.startsWith('__')) files.push(...walkDir(full));
    else if (entry.name.endsWith('.tsx')) files.push(full);
  }
  return files;
}

const spanishWords = [
  'Agregar', 'Guardar', 'Cancelar', 'Eliminar', 'Editar', 'Buscar', 'Cerrar',
  'Acciones', 'Nombre', 'Estado', 'Fecha', 'Cargando', 'Nuevo', 'Nueva',
  'Producto', 'Cliente', 'Proveedor', 'Factura', 'Seleccionar', 'Seleccione',
  'Cantidad', 'Precio', 'Almacén', 'Inventario', 'Registrar', 'Confirmar',
  'Actualizar', 'Detalle', 'Resumen', 'Observaciones', 'Notas',
  'Sin resultados', 'Sin registros', 'Volver', 'Descargar', 'Imprimir',
  'Aceptar', 'Rechazar', 'Pendiente', 'Activo', 'Inactivo', 'Borrador',
  'Completado', 'Procesando', 'Total', 'Subtotal', 'Descuento',
  'No hay', 'Error al', 'Cargando', 'Guardando', 'Eliminando',
  'Configurar', 'Crear', 'Modificar', 'Ver', 'Abrir',
  'Dirección', 'Teléfono', 'Correo',
  'Unidad', 'Empaque', 'Costo', 'Margen',
  'Sucursal', 'Turno', 'Empleado', 'Vacaciones', 'Nómina',
  'Operación', 'Movimiento',
];

const pattern = new RegExp(
  "(?:[\"'>` ])(" + spanishWords.join('|') + ")[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1 ]*(?:[\"'<`])",
  'i'
);

const files = walkDir('apps/tenant/src/modules');
let count = 0;
for (const f of files) {
  if (f.includes('RecetaDetail')) continue;
  const content = fs.readFileSync(f, 'utf8');
  const lines = content.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.trim().startsWith('import ') || line.trim().startsWith('//') || line.trim().startsWith('*')) continue;
    // skip lines that already use t()
    if (line.includes("t('") || line.includes('t("') || line.includes('t(`')) continue;
    
    const match = line.match(pattern);
    if (match) {
      const rel = path.relative('.', f).replace(/\\/g, '/');
      console.log(rel + ':' + (i + 1) + ': ' + line.trim().substring(0, 180));
      count++;
    }
  }
}
console.log('\nTotal hardcoded strings found: ' + count);
