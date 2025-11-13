#!/bin/bash

# Script para actualizar los nombres de campos de Sector en todos los archivos

cd "$(dirname "$0")"

FILES=(
  "apps/admin/src/features/configuracion/sectores/SectorList.tsx"
  "apps/admin/src/features/configuracion/sectores/SectorListProfessional.tsx"
  "apps/admin/src/features/configuracion/sectores/SectorFormProfessional.tsx"
  "apps/admin/src/pages/TenantConfiguracion.tsx"
)

for FILE in "${FILES[@]}"; do
  if [ -f "$FILE" ]; then
    echo "Updating $FILE..."
    sed -i 's/\.name/\.sector_name/g' "$FILE"
    sed -i 's/sector\.sector_name/sector.sector_name/g' "$FILE"
    sed -i 's/tipo_empresa_id/business_type_id/g' "$FILE"
    sed -i 's/tipo_negocio_id/business_category_id/g' "$FILE"
    sed -i 's/config_json/template_config/g' "$FILE"
  fi
done

echo "Done!"
