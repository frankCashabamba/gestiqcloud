-- Migration: 2025-11-03_050_create_recipes_tables
-- Description: Introduce recipes and recipe_ingredients tables with RLS policies

SET row_security = off;

CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    rendimiento NUMERIC(12,3) NOT NULL DEFAULT 1,
    costo_total NUMERIC(12,2) DEFAULT 0,
    tiempo_preparacion INTEGER,
    instrucciones TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipes_tenant ON recipes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_recipes_product ON recipes(product_id);
CREATE INDEX IF NOT EXISTS idx_recipes_activo ON recipes(activo) WHERE activo = TRUE;

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipe_id UUID NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    producto_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    qty NUMERIC(12,3) NOT NULL,
    unidad_medida VARCHAR(20) NOT NULL,
    presentacion_compra VARCHAR(100),
    qty_presentacion NUMERIC(12,3),
    unidad_presentacion VARCHAR(20),
    costo_presentacion NUMERIC(12,2) DEFAULT 0,
    notas TEXT,
    orden INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_producto ON recipe_ingredients(producto_id);

-- Enable RLS policies
ALTER TABLE recipes ENABLE ROW LEVEL SECURITY;
ALTER TABLE recipe_ingredients ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_recipes ON recipes;
CREATE POLICY tenant_isolation_recipes ON recipes
    USING (tenant_id::text = current_setting('app.tenant_id', TRUE));

DROP POLICY IF EXISTS tenant_isolation_recipe_ingredients ON recipe_ingredients;
CREATE POLICY tenant_isolation_recipe_ingredients ON recipe_ingredients
    USING (
        EXISTS (
            SELECT 1
            FROM recipes r
            WHERE r.id = recipe_ingredients.recipe_id
              AND r.tenant_id::text = current_setting('app.tenant_id', TRUE)
        )
    );

COMMENT ON TABLE recipes IS 'Tenant specific production recipes linked to sellable products';
COMMENT ON TABLE recipe_ingredients IS 'Ingredient breakdown for recipes with purchasing context';
