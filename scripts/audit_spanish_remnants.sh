#!/bin/bash
# Script de audit: encuentra todos los restos en español

set -e

cd "$(dirname "$0")/.."

OUTPUT_FILE="AUDIT_SPANISH_REMNANTS_$(date +%Y%m%d_%H%M%S).txt"

{
    echo "======================================"
    echo "AUDIT: Spanish Remnants"
    echo "Date: $(date)"
    echo "======================================"
    echo ""

    echo "## 1. SPANISH CLASS DEFINITIONS"
    echo "=================================="
    grep -r "class.*Empresa\|class.*Nomina\|class.*Caja\|class.*Facturacion\|class.*Modulo\|class.*PlanCuentas" apps/backend/app/models/ --include="*.py" || echo "No matches found"
    echo ""

    echo "## 2. SPANISH ENUM DEFINITIONS"
    echo "=================================="
    grep -r "caja_movimiento_tipo\|caja_movimiento_categoria\|cierre_caja_status\|nomina_status\|nomina_tipo\|movimiento_tipo\|movimiento_estado" apps/backend/app/models/ --include="*.py" || echo "No matches found"
    echo ""

    echo "## 3. SPANISH IMPORTS (app.models.empresa, etc)"
    echo "=================================="
    grep -r "from app\.models\.empresa\|from app\.models\.core\.facturacion\|from app\.models\.core\.modulo\|from app\.models\.core\.plan_cuentas\|from app\.models\.finance\.caja\|from app\.models\.hr\.nomina" apps/backend/app/ --include="*.py" | head -50 || echo "No matches found"
    echo ""

    echo "## 4. SPANISH FILE/FOLDER NAMES"
    echo "=================================="
    find apps/backend/app/models -type d -name "*empresa*" -o -name "*facturacion*" -o -name "*plan_cuentas*" -o -name "*nomina*" -o -name "*caja*" 2>/dev/null || echo "No matches found"
    echo ""

    echo "## 5. SPANISH DOCSTRINGS/COMMENTS (sample - first 30)"
    echo "=================================="
    grep -r "\"\"\".*[áéíóúñ].*\"\"\"" apps/backend/app/models/ --include="*.py" | head -30 || echo "No matches found"
    echo ""

    echo "## 6. SPANISH FIELD NAMES (common patterns)"
    echo "=================================="
    grep -r "nombre_empresa\|razon_social\|tipo_empresa\|tipo_negocio\|activo\|descripcion\|fecha_pago" apps/backend/app/models/ --include="*.py" | head -30 || echo "No matches found"
    echo ""

    echo "## 7. SPANISH ROUTER REFERENCES"
    echo "=================================="
    grep -r "routers\.empresa\|routers\.nomina\|routers\.caja\|routers\.facturacion" apps/backend/app/ --include="*.py" || echo "No matches found"
    echo ""

    echo "## 8. SPANISH SERVICE REFERENCES"
    echo "=================================="
    grep -r "services.*empresa\|services.*nomina\|services.*caja\|services.*facturacion" apps/backend/app/ --include="*.py" | head -20 || echo "No matches found"
    echo ""

    echo "## 9. TESTS WITH SPANISH REFERENCES"
    echo "=================================="
    grep -r "test_empresa\|test_nomina\|test_caja\|test_facturacion" apps/backend/tests/ --include="*.py" || echo "No matches found"
    echo ""

    echo "## 10. ALEMBIC MODELS (old) IN MIGRATIONS"
    echo "=================================="
    grep -r "class Empresa\|class Nomina\|class Caja" apps/backend/alembic/ --include="*.py" || echo "No matches found"
    echo ""

    echo "======================================"
    echo "Audit completed at: $(date)"
    echo "======================================"

} | tee "$OUTPUT_FILE"

echo ""
echo "✓ Audit results saved to: $OUTPUT_FILE"
