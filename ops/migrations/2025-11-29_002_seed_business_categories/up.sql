-- Migración: Insertar datos de ejemplo en business_categories
-- Eliminación de hardcoding: Cargar categorías desde BD
-- Fecha: 29 Noviembre 2025

-- Insertar categorías de negocio
INSERT INTO public.business_categories (id, code, name, description, is_active, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'retail', 'Retail / Tienda', 'Comercio minorista y tiendas', true, NOW(), NOW()),
  (gen_random_uuid(), 'services', 'Servicios', 'Prestación de servicios profesionales', true, NOW(), NOW()),
  (gen_random_uuid(), 'manufacturing', 'Manufactura', 'Producción y manufactura industrial', true, NOW(), NOW()),
  (gen_random_uuid(), 'food_beverage', 'Alimentos y Bebidas', 'Sector alimentario y bebidas', true, NOW(), NOW()),
  (gen_random_uuid(), 'healthcare', 'Salud', 'Servicios de salud y clínicas', true, NOW(), NOW()),
  (gen_random_uuid(), 'education', 'Educación', 'Instituciones educativas', true, NOW(), NOW())
ON CONFLICT DO NOTHING;
