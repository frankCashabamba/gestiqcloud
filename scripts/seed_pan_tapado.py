#!/usr/bin/env python3
"""
Seed Script - Receta Pan Tapado
Crea receta completa con 10 ingredientes exactos con conversiones correctas
"""

import sys
import os
from uuid import uuid4

# Agregar path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.core.products import Recipe, RecipeIngredient, Product


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DB_DSN = os.getenv(
    "DB_DSN", "postgresql://postgres:root@localhost:5432/gestiqclouddb_dev"
)


# ============================================================================
# DATOS: PAN TAPADO (144 unidades)
# ============================================================================

PAN_TAPADO_DATA = {
    "nombre": "Pan Tapado",
    "rendimiento": 144,
    "tiempo_preparacion": 120,  # 2 horas
    "instrucciones": """
RECETA PAN TAPADO (144 unidades)

1. MEZCLAR SECOS:
   - Harina, azúcar, sal, margarina

2. ACTIVAR LEVADURA:
   - Mezclar levadura con leche tibia

3. FORMAR MASA:
   - Combinar secos con líquidos
   - Agregar huevos
   - Amasar hasta suave y elástica (15-20 min)

4. PRIMERA FERMENTACIÓN:
   - Dejar reposar 1 hora o hasta duplicar tamaño

5. FORMAR PANES:
   - Dividir en 144 porciones
   - Formar bolitas
   - Colocar en bandejas

6. SEGUNDA FERMENTACIÓN:
   - Dejar reposar 30 min

7. HORNEAR:
   - 180°C (350°F)
   - 15-18 minutos
   - Hasta dorar

8. ACABADO:
   - Pincelar con mantequilla
   - Dejar enfriar
""".strip(),
}

# Ingredientes con conversiones exactas
INGREDIENTES = [
    {
        "nombre": "Harina de Trigo",
        "qty": 50,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Saco 110 lbs",
        "qty_presentacion": 110,
        "unidad_presentacion": "lb",
        "costo_presentacion": 35.00,
    },
    {
        "nombre": "Azúcar Blanca",
        "qty": 7,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Saco 100 lbs",
        "qty_presentacion": 100,
        "unidad_presentacion": "lb",
        "costo_presentacion": 45.00,
    },
    {
        "nombre": "Sal",
        "qty": 0.5,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Paquete 2 lbs",
        "qty_presentacion": 2,
        "unidad_presentacion": "lb",
        "costo_presentacion": 1.50,
    },
    {
        "nombre": "Levadura Instantánea",
        "qty": 1,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Paquete 1 lb",
        "qty_presentacion": 1,
        "unidad_presentacion": "lb",
        "costo_presentacion": 8.00,
    },
    {
        "nombre": "Leche en Polvo",
        "qty": 2.5,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Bolsa 5 lbs",
        "qty_presentacion": 5,
        "unidad_presentacion": "lb",
        "costo_presentacion": 18.00,
    },
    {
        "nombre": "Margarina",
        "qty": 5,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Caja 10 lbs",
        "qty_presentacion": 10,
        "unidad_presentacion": "lb",
        "costo_presentacion": 22.00,
    },
    {
        "nombre": "Huevos",
        "qty": 24,  # unidades
        "unidad_medida": "uds",
        "presentacion_compra": "Bandeja 30 huevos",
        "qty_presentacion": 30,
        "unidad_presentacion": "uds",
        "costo_presentacion": 6.00,
    },
    {
        "nombre": "Agua",
        "qty": 3,  # galones
        "unidad_medida": "gal",
        "presentacion_compra": "Galón 1 gal",
        "qty_presentacion": 1,
        "unidad_presentacion": "gal",
        "costo_presentacion": 0.50,
    },
    {
        "nombre": "Mantequilla (para acabado)",
        "qty": 1,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Barra 1 lb",
        "qty_presentacion": 1,
        "unidad_presentacion": "lb",
        "costo_presentacion": 4.00,
    },
    {
        "nombre": "Mejorador de Pan",
        "qty": 0.25,  # lb
        "unidad_medida": "lb",
        "presentacion_compra": "Bolsa 1 lb",
        "qty_presentacion": 1,
        "unidad_presentacion": "lb",
        "costo_presentacion": 12.00,
    },
]


# ============================================================================
# FUNCIONES
# ============================================================================


def create_or_get_product(session, tenant_id: str, nombre: str):
    """Crea o busca producto por nombre"""
    product = (
        session.query(Product)
        .filter(Product.tenant_id == tenant_id, Product.name == nombre)
        .first()
    )

    if product:
        print(f"  ✓ Producto encontrado: {nombre}")
        return product

    # Crear producto
    product = Product(
        id=uuid4(),
        tenant_id=tenant_id,
        name=nombre,
        description=f"Ingrediente para {PAN_TAPADO_DATA['nombre']}",
        price=0.0,  # No es para venta directa
        cost=0.0,
        stock_qty=0,
        active=True,
    )
    session.add(product)
    session.flush()

    print(f"  + Producto creado: {nombre}")
    return product


def seed_pan_tapado(tenant_id: str):
    """Crea receta completa de Pan Tapado"""

    engine = create_engine(DB_DSN)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Establecer tenant_id para RLS
        session.execute(text(f"SET app.tenant_id = '{tenant_id}'"))

        print(f"\n{'=' * 60}")
        print(f"CREANDO RECETA: {PAN_TAPADO_DATA['nombre']}")
        print(f"Tenant ID: {tenant_id}")
        print(f"{'=' * 60}\n")

        # 1. Crear producto final "Pan Tapado"
        print("1. Creando producto final...")
        producto_final = create_or_get_product(session, tenant_id, "Pan Tapado")

        # 2. Verificar si ya existe la receta
        existing_recipe = (
            session.query(Recipe)
            .filter(
                Recipe.tenant_id == tenant_id,
                Recipe.nombre == PAN_TAPADO_DATA["nombre"],
            )
            .first()
        )

        if existing_recipe:
            print(
                f"\n⚠️  Receta '{PAN_TAPADO_DATA['nombre']}' ya existe (ID: {existing_recipe.id})"
            )
            print("   Eliminando para recrear...")
            session.delete(existing_recipe)
            session.commit()

        # 3. Crear receta
        print("\n2. Creando receta...")
        recipe = Recipe(
            id=uuid4(),
            tenant_id=tenant_id,
            product_id=producto_final.id,
            nombre=PAN_TAPADO_DATA["nombre"],
            rendimiento=PAN_TAPADO_DATA["rendimiento"],
            tiempo_preparacion=PAN_TAPADO_DATA["tiempo_preparacion"],
            instrucciones=PAN_TAPADO_DATA["instrucciones"],
            costo_total=0,  # Se calculará automáticamente
            activo=True,
        )
        session.add(recipe)
        session.flush()

        print(f"  ✓ Receta creada: {recipe.nombre} (ID: {recipe.id})")

        # 4. Crear ingredientes
        print("\n3. Creando ingredientes...")

        for i, ing_data in enumerate(INGREDIENTES, 1):
            # Crear/obtener producto ingrediente
            producto = create_or_get_product(session, tenant_id, ing_data["nombre"])

            # Crear ingrediente de receta
            ingrediente = RecipeIngredient(
                id=uuid4(),
                recipe_id=recipe.id,
                producto_id=producto.id,
                qty=ing_data["qty"],
                unidad_medida=ing_data["unidad_medida"],
                presentacion_compra=ing_data["presentacion_compra"],
                qty_presentacion=ing_data["qty_presentacion"],
                unidad_presentacion=ing_data["unidad_presentacion"],
                costo_presentacion=ing_data["costo_presentacion"],
                orden=i,
            )
            session.add(ingrediente)

            # Calcular costo
            costo_unitario = (
                ing_data["costo_presentacion"] / ing_data["qty_presentacion"]
            )
            costo_ingrediente = ing_data["qty"] * costo_unitario

            print(
                f"  {i:2d}. {ing_data['nombre']:<30} "
                f"{ing_data['qty']:>8.2f} {ing_data['unidad_medida']:<4} "
                f"→ ${costo_ingrediente:>8.2f}"
            )

        session.flush()

        # 5. Calcular costo total (trigger automático)
        session.commit()

        # 6. Refrescar y mostrar resultado
        session.refresh(recipe)

        print(f"\n{'=' * 60}")
        print("✅ RECETA CREADA EXITOSAMENTE")
        print(f"{'=' * 60}")
        print(f"Nombre:         {recipe.nombre}")
        print(f"Rendimiento:    {recipe.rendimiento} unidades")
        print(f"Costo Total:    ${float(recipe.costo_total):,.2f}")
        print(f"Costo/Unidad:   ${float(recipe.costo_por_unidad):,.4f}")
        print(f"Tiempo Prep:    {recipe.tiempo_preparacion} minutos")
        print(f"Ingredientes:   {len(INGREDIENTES)}")
        print(f"{'=' * 60}\n")

        # 7. Ejemplo de producción
        print("\n📊 EJEMPLO DE PRODUCCIÓN:")
        print("-" * 60)

        qty_to_produce = 1000
        batches = qty_to_produce / recipe.rendimiento
        costo_total_produccion = float(recipe.costo_total) * batches

        print(f"Para producir {qty_to_produce} panes:")
        print(f"  - Batches necesarios: {batches:.2f}")
        print(f"  - Costo total:        ${costo_total_produccion:,.2f}")
        print(
            f"  - Costo/unidad:       ${costo_total_produccion / qty_to_produce:,.4f}"
        )
        print(
            f"  - Tiempo estimado:    {recipe.tiempo_preparacion * batches:.0f} min "
            f"({recipe.tiempo_preparacion * batches / 60:.1f} horas)"
        )
        print("-" * 60)

        return recipe.id

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Obtener tenant_id
    tenant_id = os.getenv("TENANT_ID")

    if not tenant_id:
        print("❌ ERROR: Debe configurar variable TENANT_ID")
        print("\nUso:")
        print("  export TENANT_ID='uuid-del-tenant'")
        print("  python scripts/seed_pan_tapado.py")
        print("\nO bien:")
        print("  TENANT_ID='uuid' python scripts/seed_pan_tapado.py")
        sys.exit(1)

    try:
        recipe_id = seed_pan_tapado(tenant_id)
        print(f"\n✅ Receta creada con ID: {recipe_id}\n")

    except Exception as e:
        print(f"\n❌ Error fatal: {e}\n")
        sys.exit(1)
