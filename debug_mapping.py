import sys

sys.path.insert(0, "./apps/backend")
from app.modules.imports.domain.validator import universal_validator

headers = ["Numero de Factura", "Fecha", "Cliente", "Subtotal", "Total"]
mapping = universal_validator.find_field_mapping(headers, "sales_invoice")
print("Mapping:", mapping)
print("Headers:", headers)
for h in headers:
    print("  {} -> {}".format(h, mapping.get(h, "NOT FOUND")))
