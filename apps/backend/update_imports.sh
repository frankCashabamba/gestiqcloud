#!/bin/bash
# Script to update all imports across the codebase
# Run this from the /apps/backend directory

echo "Updating imports..."

# Replace empresa imports
find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.empresa\.empresa/from app.models.company.company/g' {} +

find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.empresa\.rolempresas/from app.models.company.company_role/g' {} +

find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.empresa\.usuarioempresa/from app.models.company.company_user/g' {} +

find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.empresa\.usuario_rolempresa/from app.models.company.company_user_role/g' {} +

find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.empresa\.settings/from app.models.company.company_settings/g' {} +

# Replace sales.venta imports
find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.sales\.venta/from app.models.sales.sale/g' {} +

# Replace purchases.compra imports
find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.purchases\.compra/from app.models.purchases.purchase/g' {} +

# Replace suppliers.proveedor imports
find . -name "*.py" -type f ! -path "./.venv/*" ! -path "*/__pycache__/*" -exec sed -i \
  's/from app\.models\.suppliers\.proveedor/from app.models.suppliers.supplier/g' {} +

echo "Import updates complete!"
