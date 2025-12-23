-- Migración: Agregar placeholders dinámicos a sector_templates.template_config
-- Fase 4 Paso 4: Eliminar hardcoding de placeholders en formularios
-- Fecha: 1 Diciembre 2025

-- Actualizar PANADERÍA con placeholders
UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,inventory,placeholders}',
  jsonb_build_object(
    'lote', 'Ej: H-2025-028',
    'numero_serie', 'Ej: SN-ALT-123456789',
    'ubicacion', 'Ej: Vitrina-A, Horno-2',
    'expires_at', 'Ej: 15/01/2026'
  )
)
WHERE code = 'panaderia';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,products,placeholders}',
  jsonb_build_object(
    'codigo', 'Ej: PAN-001',
    'nombre', 'Ej: Pan Blanco 500g',
    'precio', 'Ej: 2.50',
    'sku', 'Ej: SKU-PAN-001',
    'lote', 'Ej: H-2025-028'
  )
)
WHERE code = 'panaderia';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,customers,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: Juan García López',
    'telefono', 'Ej: +34 612 345 678',
    'email', 'Ej: juan@example.com',
    'direccion', 'Ej: Calle Principal 123, Madrid'
  )
)
WHERE code = 'panaderia';

-- Actualizar TALLER con placeholders
UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,inventory,placeholders}',
  jsonb_build_object(
    'lote', 'Ej: LOT-BRK-2025-001',
    'numero_serie', 'Ej: OEM-BRK-2025-001',
    'ubicacion', 'Ej: Almacén-A, Estante-3',
    'codigo_oem', 'Ej: OEM123456'
  )
)
WHERE code = 'taller';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,products,placeholders}',
  jsonb_build_object(
    'codigo', 'Ej: FRENO-001',
    'nombre', 'Ej: Pastilla de Freno Delantera',
    'numero_oem', 'Ej: OEM123456',
    'sku', 'Ej: SKU-FRENO-001',
    'precio', 'Ej: 45.99'
  )
)
WHERE code = 'taller';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,customers,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: Taller García S.L.',
    'telefono', 'Ej: +34 912 345 678',
    'email', 'Ej: contacto@tallergarcia.es',
    'direccion', 'Ej: Avenida Principal 456, Madrid'
  )
)
WHERE code = 'taller';

-- Actualizar RETAIL con placeholders
UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,inventory,placeholders}',
  jsonb_build_object(
    'lote', 'Ej: LOT-RET-2025-001',
    'numero_serie', 'Ej: SN-RET-2025-001',
    'ubicacion', 'Ej: Pasillo-A, Estante-2',
    'codigo_proveedor', 'Ej: PROV-12345'
  )
)
WHERE code = 'retail';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,products,placeholders}',
  jsonb_build_object(
    'codigo', 'Ej: ROPA-001',
    'nombre', 'Ej: Camiseta Azul T-M',
    'sku', 'Ej: SKU-ROPA-001-BL-M',
    'precio', 'Ej: 19.99',
    'color', 'Ej: Azul'
  )
)
WHERE code = 'retail';

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,customers,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: María García López',
    'telefono', 'Ej: +34 612 345 678',
    'email', 'Ej: maria@example.com',
    'direccion', 'Ej: Calle Central 789, Madrid'
  )
)
WHERE code = 'retail';

-- Agregar placeholders generales para otros módulos
UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,expenses,placeholders}',
  jsonb_build_object(
    'numero_factura', 'Ej: FACT-2025-001',
    'descripcion', 'Ej: Compra de materiales de embalaje',
    'importe', 'Ej: 150.50'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,accounting,placeholders}',
  jsonb_build_object(
    'numero_asiento', 'Ej: A-001',
    'cuenta', 'Ej: 1000',
    'descripcion', 'Ej: Compra de materiales',
    'debe', 'Ej: 500.00'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,hr,placeholders}',
  jsonb_build_object(
    'codigo_empleado', 'Ej: EMP001',
    'nombre', 'Ej: Juan García López',
    'departamento', 'Ej: Ventas, RRHH, etc.',
    'puesto', 'Ej: Cajero, Gerente, etc.',
    'numero_cuenta', 'Ej: ES00 0000 0000 0000 0000 0000'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,suppliers,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: Proveedor Premium S.A.',
    'web', 'Ej: https://',
    'iban', 'Ej: ES00 0000 0000 0000 0000 0000',
    'telefono', 'Ej: +34 912 345 678',
    'email', 'Ej: contacto@proveedor.es'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,importing,placeholders}',
  jsonb_build_object(
    'nombre_lote', 'Ej: Proveedor Lácteos - Mensual',
    'descripcion', 'Ej: Importación de productos para el mes de diciembre',
    'fecha_entrega', 'Ej: 15/12/2025'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,roles,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: Cajero, Vendedor, Contador',
    'descripcion', 'Ej: Rol para personal de caja y atención al cliente'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,vacation,placeholders}',
  jsonb_build_object(
    'motivo', 'Ej: Vacaciones anuales, asunto personal, etc.',
    'fecha_inicio', 'Ej: 15/08/2026',
    'fecha_fin', 'Ej: 31/08/2026'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,categories,placeholders}',
  jsonb_build_object(
    'nombre', 'Ej: Pan, Bollería, Ropa...',
    'descripcion', 'Ej: Categoría para clasificación de productos'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,pos,placeholders}',
  jsonb_build_object(
    'motivo_devolucion', 'Ej: Producto defectuoso, cliente insatisfecho...',
    'numero_factura', 'Ej: FACT-2025-001'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,alerts,placeholders}',
  jsonb_build_object(
    'numeros_telefonicos', 'números separados por coma (ej: +34123456789)',
    'mensaje', 'Ej: Se ha agotado el stock de producto XYZ'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

UPDATE public.sector_templates
SET template_config = jsonb_set(
  template_config,
  '{fields,accounting_plan,placeholders}',
  jsonb_build_object(
    'codigos_cuenta', 'Ej: 1000, 2000',
    'descripcion', 'Ej: Cuentas para activo corriente'
  )
)
WHERE code IN ('panaderia', 'taller', 'retail');

-- Verificar que las actualizaciones se hayan completado
SELECT
  code,
  jsonb_path_exists(template_config, '$.fields.inventory.placeholders') as has_inventory_placeholders,
  jsonb_path_exists(template_config, '$.fields.products.placeholders') as has_product_placeholders,
  jsonb_path_exists(template_config, '$.fields.customers.placeholders') as has_customer_placeholders
FROM public.sector_templates
WHERE code IN ('panaderia', 'taller', 'retail')
ORDER BY code;
