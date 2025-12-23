-- Migración: Cargar datos de sector templates que estaban hardcodeados
-- Inserta los templates de panadería, taller y retail en la BD
-- Solo si no existen ya

INSERT INTO public.sector_templates (id, code, name, description, template_config, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'panaderia', 'Panadería', 'Sector de panadería y pastelería',
  jsonb_build_object(
    'modules', jsonb_build_object(
      'pos', jsonb_build_object('enabled', true, 'order', 5),
      'ventas', jsonb_build_object('enabled', true, 'order', 10),
      'inventario', jsonb_build_object('enabled', true, 'order', 20),
      'facturacion', jsonb_build_object('enabled', true, 'order', 15),
      'contabilidad', jsonb_build_object('enabled', false)
    ),
    'branding', jsonb_build_object(
      'color_primario', '#f59e0b',
      'logo', null,
      'plantilla_inicio', 'panaderia',
      'dashboard_template', 'panaderia_dashboard.html',
      'icon', '🥐',
      'displayName', 'Panadería',
      'units', jsonb_build_array(
        jsonb_build_object('code', 'unit', 'label', 'Unidad'),
        jsonb_build_object('code', 'kg', 'label', 'Kilogramo'),
        jsonb_build_object('code', 'g', 'label', 'Gramo'),
        jsonb_build_object('code', 'dozen', 'label', 'Docena')
      ),
      'format_rules', jsonb_build_object(
        'quantity', jsonb_build_object('decimals', 0, 'suffix', 'uds'),
        'weight', jsonb_build_object('metric', 'kg'),
        'date', jsonb_build_object('suffix', 'dd/MMM')
      ),
      'print_config', jsonb_build_object(
        'width', 58,
        'fontSize', 9,
        'showLogo', false,
        'showDetails', false
      ),
      'required_fields', jsonb_build_object(
        'product', jsonb_build_array('expires_at'),
        'inventory', jsonb_build_array('expires_at')
      )
    ),
    'defaults', jsonb_build_object(
      'categories', jsonb_build_array('Pan', 'Pasteles', 'Bollería', 'Bebidas'),
      'tax_rate', 0.15,
      'currency', 'EUR',
      'locale', 'es',
      'timezone', 'Europe/Madrid',
      'price_includes_tax', true
    ),
    'pos', jsonb_build_object(
      'receipt_width_mm', 58,
      'print_mode', 'system',
      'return_window_days', 15,
      'enable_weights', true,
      'enable_batch_tracking', true
    ),
    'inventory', jsonb_build_object(
      'enable_expiry_tracking', true,
      'enable_lot_tracking', true,
      'enable_serial_tracking', false,
      'auto_reorder', true,
      'reorder_point_days', 3
    )
  ),
  true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.sector_templates WHERE code = 'panaderia')
ON CONFLICT (code) DO NOTHING;

INSERT INTO public.sector_templates (id, code, name, description, template_config, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'taller', 'Taller Mecánico', 'Sector de taller mecánico y automotriz',
  jsonb_build_object(
    'modules', jsonb_build_object(
      'pos', jsonb_build_object('enabled', true, 'order', 5),
      'ventas', jsonb_build_object('enabled', true, 'order', 10),
      'inventario', jsonb_build_object('enabled', true, 'order', 20),
      'facturacion', jsonb_build_object('enabled', true, 'order', 15),
      'contabilidad', jsonb_build_object('enabled', true, 'order', 25)
    ),
    'branding', jsonb_build_object(
      'color_primario', '#1e40af',
      'logo', null,
      'plantilla_inicio', 'taller',
      'dashboard_template', 'taller_dashboard.html',
      'icon', '🔧',
      'displayName', 'Taller Mecánico',
      'units', jsonb_build_array(
        jsonb_build_object('code', 'unit', 'label', 'Unidad'),
        jsonb_build_object('code', 'pair', 'label', 'Par'),
        jsonb_build_object('code', 'set', 'label', 'Juego'),
        jsonb_build_object('code', 'l', 'label', 'Litro'),
        jsonb_build_object('code', 'ml', 'label', 'Mililitro')
      ),
      'format_rules', jsonb_build_object(
        'quantity', jsonb_build_object('decimals', 2, 'suffix', 'uds'),
        'weight', jsonb_build_object('metric', 'kg'),
        'date', jsonb_build_object('suffix', 'dd/MM/yyyy')
      ),
      'print_config', jsonb_build_object(
        'width', 80,
        'fontSize', 10,
        'showLogo', true,
        'showDetails', true
      ),
      'required_fields', jsonb_build_object(
        'product', jsonb_build_array(),
        'inventory', jsonb_build_array()
      )
    ),
    'defaults', jsonb_build_object(
      'categories', jsonb_build_array('Repuestos', 'Servicios', 'Accesorios', 'Herramientas'),
      'tax_rate', 0.15,
      'currency', 'EUR',
      'locale', 'es',
      'timezone', 'Europe/Madrid',
      'price_includes_tax', true
    ),
    'pos', jsonb_build_object(
      'receipt_width_mm', 80,
      'print_mode', 'system',
      'return_window_days', 30,
      'enable_weights', false,
      'enable_batch_tracking', false
    ),
    'inventory', jsonb_build_object(
      'enable_expiry_tracking', false,
      'enable_lot_tracking', false,
      'enable_serial_tracking', true,
      'auto_reorder', true,
      'reorder_point_days', 7
    )
  ),
  true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.sector_templates WHERE code = 'taller')
ON CONFLICT (code) DO NOTHING;

INSERT INTO public.sector_templates (id, code, name, description, template_config, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'retail', 'Retail / Tienda', 'Sector comercial y tiendas retail',
  jsonb_build_object(
    'modules', jsonb_build_object(
      'pos', jsonb_build_object('enabled', true, 'order', 5),
      'ventas', jsonb_build_object('enabled', true, 'order', 10),
      'inventario', jsonb_build_object('enabled', true, 'order', 20),
      'facturacion', jsonb_build_object('enabled', true, 'order', 15),
      'contabilidad', jsonb_build_object('enabled', true, 'order', 25)
    ),
    'branding', jsonb_build_object(
      'color_primario', '#059669',
      'logo', null,
      'plantilla_inicio', 'retail',
      'dashboard_template', 'retail_dashboard.html',
      'icon', '🏪',
      'displayName', 'Retail',
      'units', jsonb_build_array(
        jsonb_build_object('code', 'unit', 'label', 'Unidad'),
        jsonb_build_object('code', 'kg', 'label', 'Kilogramo'),
        jsonb_build_object('code', 'l', 'label', 'Litro'),
        jsonb_build_object('code', 'm', 'label', 'Metro'),
        jsonb_build_object('code', 'm2', 'label', 'Metro cuadrado'),
        jsonb_build_object('code', 'm3', 'label', 'Metro cúbico')
      ),
      'format_rules', jsonb_build_object(
        'quantity', jsonb_build_object('decimals', 0, 'suffix', ''),
        'weight', jsonb_build_object('metric', 'kg'),
        'date', jsonb_build_object('suffix', 'dd/MM/yyyy')
      ),
      'print_config', jsonb_build_object(
        'width', 58,
        'fontSize', 10,
        'showLogo', true,
        'showDetails', false
      ),
      'required_fields', jsonb_build_object(
        'product', jsonb_build_array('sku'),
        'inventory', jsonb_build_array()
      )
    ),
    'defaults', jsonb_build_object(
      'categories', jsonb_build_array('Ropa', 'Electrónica', 'Hogar', 'Accesorios'),
      'tax_rate', 0.21,
      'currency', 'EUR',
      'locale', 'es',
      'timezone', 'Europe/Madrid',
      'price_includes_tax', true
    ),
    'pos', jsonb_build_object(
      'receipt_width_mm', 58,
      'print_mode', 'system',
      'return_window_days', 14,
      'enable_weights', false,
      'enable_batch_tracking', false
    ),
    'inventory', jsonb_build_object(
      'enable_expiry_tracking', false,
      'enable_lot_tracking', false,
      'enable_serial_tracking', false,
      'auto_reorder', true,
      'reorder_point_days', 7
    )
  ),
  true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM public.sector_templates WHERE code = 'retail')
ON CONFLICT (code) DO NOTHING;
