"""
P0 Integration Examples

Muestra cómo usar los nuevos módulos P0 en el pipeline de imports.
"""

import sys

from app.modules.imports.domain import ImportErrorCollection, get_schema, universal_validator

# ============================================================================
# EJEMPLO 1: Validación de documento
# ============================================================================


def example_validate_sales_invoice():
    """Validar una factura de venta con datos reales."""
    print("\n" + "=" * 70)
    print("EJEMPLO 1: Validación de Factura de Venta")
    print("=" * 70)

    # Datos extraídos del archivo (después de parsing)
    sales_data = {
        "invoice_number": "FAC-2024-001",
        "invoice_date": "2024-01-15",
        "customer_name": "Acme Corporation",
        "amount_subtotal": "10000.00",
        "amount_total": "12000.00",  # Incluye IVA
    }

    # Validar
    is_valid, errors = universal_validator.validate_document_complete(
        data=sales_data,
        doc_type="sales_invoice",
        row_number=2,  # Row en archivo
        item_id="item-abc123",
        batch_id="batch-xyz789",
    )

    print(f"\nValidación: {'PASSED' if is_valid else 'FAILED'}")
    print(f"Errores: {len(errors)}")

    if is_valid:
        print("✓ Documento válido")
    else:
        for error in errors:
            print(f"\n  Row {error.row_number}, Field '{error.field_name}':")
            print(f"    Error: {error.message}")
            print(f"    Suggestion: {error.suggestion}")


# ============================================================================
# EJEMPLO 2: Validación con errores
# ============================================================================


def example_validate_with_errors():
    """Validar un documento con errores."""
    print("\n" + "=" * 70)
    print("EJEMPLO 2: Validación con Errores")
    print("=" * 70)

    # Datos incompletos/inválidos
    invalid_data = {
        "invoice_number": "FAC-2024-002",
        # Falta invoice_date
        "customer_name": "Empresa XYZ",
        "amount_subtotal": "not_a_number",  # Error: no es número
        "amount_total": "-5000.00",  # Error: negativo
    }

    is_valid, errors = universal_validator.validate_document_complete(
        data=invalid_data,
        doc_type="sales_invoice",
        row_number=3,
        item_id="item-def456",
    )

    print(f"\nValidación: {'PASSED' if is_valid else 'FAILED'}")
    print(f"Total de errores: {len(errors)}")

    # Agrupar errores por tipo
    by_category = errors.by_category()
    for category, category_errors in by_category.items():
        print(f"\n{category.value}:")
        for error in category_errors:
            print(f"  - {error.field_name}: {error.message}")


# ============================================================================
# EJEMPLO 3: Auto-detección de field mapping
# ============================================================================


def example_field_mapping():
    """Auto-detectar mapeo de columnas."""
    print("\n" + "=" * 70)
    print("EJEMPLO 3: Auto-detección de Field Mapping")
    print("=" * 70)

    # Headers del archivo Excel
    headers = [
        "Numero de Factura",
        "Fecha de Emisión",
        "Razon Social del Cliente",
        "Subtotal",
        "IVA",
        "Monto Total",
        "Notas",
    ]

    # Detectar mapeo
    mapping = universal_validator.find_field_mapping(headers, "sales_invoice")

    print(f"\nHeaders detectados: {len(headers)}")
    print(f"Campos mapeados: {len(mapping)}")

    for header, canonical in mapping.items():
        print(f"  '{header}' → '{canonical}'")

    print("\nNo mapeado:")
    for header in headers:
        if header not in mapping:
            print(f"  - {header}")


# ============================================================================
# EJEMPLO 4: Validar múltiples filas (como en parse)
# ============================================================================


def example_batch_validation():
    """Validar múltiples filas como si vinieran de un Excel."""
    print("\n" + "=" * 70)
    print("EJEMPLO 4: Validación de Lote (Múltiples Filas)")
    print("=" * 70)

    # Simular 3 filas de un archivo
    rows = [
        {
            "invoice_number": "FAC-001",
            "invoice_date": "2024-01-01",
            "customer_name": "Cliente A",
            "amount_subtotal": "1000",
            "amount_total": "1200",
        },
        {
            "invoice_number": "FAC-002",
            # Falta fecha
            "customer_name": "Cliente B",
            "amount_subtotal": "2000",
            "amount_total": "2400",
        },
        {
            "invoice_number": "FAC-003",
            "invoice_date": "2024-01-03",
            "customer_name": "Cliente C",
            "amount_subtotal": "abc",  # Inválido
            "amount_total": "1200",
        },
    ]

    batch_errors = []
    valid_count = 0
    error_count = 0

    for row_idx, row_data in enumerate(rows, start=2):  # start=2 porque fila 1 es header
        is_valid, errors = universal_validator.validate_document_complete(
            data=row_data,
            doc_type="sales_invoice",
            row_number=row_idx,
            item_id=f"item-{row_idx}",
            batch_id="batch-001",
        )

        if is_valid:
            valid_count += 1
        else:
            error_count += len(errors)
            batch_errors.extend(errors)

    print(f"\nTotal filas procesadas: {len(rows)}")
    print(f"Filas válidas: {valid_count}")
    print(f"Filas con errores: {len(rows) - valid_count}")
    print(f"Total errores: {error_count}")

    print("\nErrores por fila:")
    if batch_errors:
        errors_grouped = ImportErrorCollection()
        for e in batch_errors:
            errors_grouped.errors.append(e)
        for row_num, row_errors in errors_grouped.by_row().items():
            print(f"  Row {row_num}: {len(row_errors)} errores")


# ============================================================================
# EJEMPLO 5: Trabajar con esquemas
# ============================================================================


def example_schemas():
    """Explorar los esquemas disponibles."""
    print("\n" + "=" * 70)
    print("EJEMPLO 5: Esquemas Canónicos Disponibles")
    print("=" * 70)

    doc_types = [
        "sales_invoice",
        "purchase_invoice",
        "expense",
        "bank_tx",
    ]

    for doc_type in doc_types:
        schema = get_schema(doc_type)
        if schema:
            print(f"\n{doc_type}:")
            print(f"  Campos: {len(schema.fields)}")
            print(f"  Obligatorios: {', '.join(schema.required_fields)}")

            # Mostrar algunos campos
            for field_name in list(schema.required_fields)[:3]:
                field_def = schema.fields[field_name]
                print(f"    - {field_name} ({field_def.data_type})")
                if field_def.aliases:
                    print(f"      aliases: {field_def.aliases[:3]}")


# ============================================================================
# EJEMPLO 6: Crear y manipular errores
# ============================================================================


def example_error_handling():
    """Trabajar directamente con errors API."""
    print("\n" + "=" * 70)
    print("EJEMPLO 6: Manejo de Errores Estructurados")
    print("=" * 70)

    errors = ImportErrorCollection()

    # Agregar varios errores
    errors.add_missing_field_error(
        field_name="invoice_number",
        row_number=10,
        canonical_field="invoice_number",
    )

    errors.add_type_error(
        field_name="amount",
        expected_type="decimal",
        row_number=11,
        canonical_field="amount_total",
        raw_value="abc123",
        suggestion="Use decimal notation like 123.45",
    )

    errors.add_validation_error(
        field_name="amount",
        rule_name="is_positive",
        message="Amount must be greater than zero",
        row_number=12,
        canonical_field="amount_total",
        raw_value="-100.00",
        suggestion="Provide a positive amount",
    )

    print(f"\nTotal errores: {len(errors)}")

    # Agrupar y mostrar
    print("\nErrores por fila:")
    for row_num, row_errors in errors.by_row().items():
        print(f"  Row {row_num}:")
        for error in row_errors:
            print(f"    {error.category.value}: {error.message}")

    print("\nErrores en JSON (para API):")
    import json

    error_list = errors.to_list()
    print(json.dumps(error_list[0], indent=2))  # Mostrar primero


if __name__ == "__main__":
    try:
        example_validate_sales_invoice()
        example_validate_with_errors()
        example_field_mapping()
        example_batch_validation()
        example_schemas()
        example_error_handling()

        print("\n" + "=" * 70)
        print("Todos los ejemplos completados")
        print("=" * 70)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
