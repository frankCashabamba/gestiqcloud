"""
Example usage of Fase D - IA Configurable

Este archivo muestra cómo usar los providers de IA en el proyecto.
NO es parte del código, solo referencia.
"""

import asyncio
from datetime import datetime

from app.config.settings import settings
from app.modules.imports.ai import get_ai_provider_singleton
from app.modules.imports.ai.telemetry import ClassificationMetric, telemetry


async def example_classify_document():
    """Ejemplo 1: Clasificar un documento."""

    print("=== Ejemplo 1: Clasificar Documento ===\n")

    # Obtener provider actual (configurado en settings)
    provider = await get_ai_provider_singleton()

    # Texto de ejemplo
    text = """
    INVOICE #INV-2025-001
    Date: 2025-11-11

    Customer: ABC Corporation
    Bill To:
        123 Business St
        New York, NY 10001

    Items:
        - Consulting Services: $5,000.00
        - Software License: $2,000.00

    Subtotal: $7,000.00
    Tax (10%): $700.00
    Total: $7,700.00

    Payment Due: 30 days
    """

    # Parsers disponibles
    available_parsers = ["csv_invoices", "products_excel", "csv_expenses", "csv_bank"]

    # Clasificar
    print(f"Provider: {settings.IMPORT_AI_PROVIDER}")
    print(f"Text length: {len(text)} chars\n")

    result = await provider.classify_document(text, available_parsers)

    print(f"Suggested: {result.suggested_parser}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Provider: {result.provider}")
    print(f"Reasoning: {result.reasoning}\n")

    print("Probabilities:")
    for parser, prob in result.probabilities.items():
        print(f"  {parser}: {prob:.1%}")


async def example_extract_fields():
    """Ejemplo 2: Extraer campos de un documento."""

    print("\n=== Ejemplo 2: Extraer Campos ===\n")

    provider = await get_ai_provider_singleton()

    text = "Invoice #INV-001 Total: $1250.00 Tax: $150.00 Date: 2025-11-11"

    fields = await provider.extract_fields(
        text=text, doc_type="invoice", expected_fields=["total", "tax", "date", "invoice_number"]
    )

    print("Extracted fields:")
    for field, value in fields.items():
        print(f"  {field}: {value}")


async def example_telemetry():
    """Ejemplo 3: Ver telemetría."""

    print("\n=== Ejemplo 3: Telemetría ===\n")

    provider = await get_ai_provider_singleton()

    # Obtener stats del provider
    stats = provider.get_telemetry()
    print(f"Provider: {stats['provider']}")
    print(f"Requests: {stats.get('requests', 'N/A')}")
    print(f"Cost: ${stats.get('total_cost', 0.0):.6f}")

    # Obtener resumen global
    print("\nGlobal Telemetry:")
    summary = telemetry.get_summary()
    if summary:
        print(f"Total requests: {summary['total_requests']}")
        print(f"Total cost: ${summary['total_cost']:.6f}")
        print(f"Avg confidence: {summary['avg_confidence']:.0%}")
    else:
        print("No telemetry data yet")


async def example_cache():
    """Ejemplo 4: Usar caché."""

    print("\n=== Ejemplo 4: Cache ===\n")

    provider = await get_ai_provider_singleton()

    if not hasattr(provider, "cache") or not provider.cache:
        print("Cache is disabled in settings")
        return

    text = "Invoice #001 Total: $100.00"
    parsers = ["csv_invoices", "products_excel"]

    # Primera clasificación (miss)
    print("First classification (cache miss)...")
    await provider.classify_document(text, parsers)

    # Segunda clasificación (hit)
    print("Second classification (should be cache hit)...")
    await provider.classify_document(text, parsers)

    # Ver stats de caché
    stats = provider.get_telemetry()
    if "cache" in stats:
        print(f"\nCache stats: {stats['cache']}")


async def example_provider_switching():
    """Ejemplo 5: Cambiar provider dinámicamente."""

    print("\n=== Ejemplo 5: Provider Info ===\n")

    print(f"Current provider: {settings.IMPORT_AI_PROVIDER}")
    print(f"Confidence threshold: {settings.IMPORT_AI_CONFIDENCE_THRESHOLD}")
    print(f"Cache enabled: {settings.IMPORT_AI_CACHE_ENABLED}")

    print("\nTo switch providers, set environment variables:")
    print("  IMPORT_AI_PROVIDER=local|openai|azure")
    print("  OPENAI_API_KEY=sk-...")
    print("  IMPORT_AI_CONFIDENCE_THRESHOLD=0.8")


async def example_validate_classification():
    """Ejemplo 6: Validar clasificación para tracking de precisión."""

    print("\n=== Ejemplo 6: Validar Clasificación ===\n")

    # Clasificar
    provider = await get_ai_provider_singleton()
    text = "Invoice #001 Total: $100"
    result = await provider.classify_document(text, ["csv_invoices", "products_excel"])

    # Registrar métrica
    metric = ClassificationMetric(
        timestamp=datetime.now(),
        document_type="invoice",
        parser_suggested=result.suggested_parser,
        confidence=result.confidence,
        provider=result.provider,
        execution_time_ms=25.5,
        text_length=len(text),
        file_name="invoice_001.txt",
        tenant_id="tenant-123",
    )

    telemetry.record(metric)

    # Posteriormente, validar si fue correcto
    print("Marking as correct...")
    telemetry.mark_correct(metric_index=0, correct=True)

    # Ver precisión
    accuracy = telemetry.get_accuracy()
    print(f"Accuracy: {accuracy:.0%}")


async def run_all_examples():
    """Ejecutar todos los ejemplos."""

    print("\n" + "=" * 60)
    print("FASE D - IA CONFIGURABLE - EJEMPLOS DE USO")
    print("=" * 60)

    try:
        await example_classify_document()
        await example_extract_fields()
        await example_telemetry()
        await example_cache()
        await example_provider_switching()
        await example_validate_classification()

        print("\n" + "=" * 60)
        print("✅ Todos los ejemplos completados")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Ejecutar: python -m app.modules.imports.ai.example_usage
    asyncio.run(run_all_examples())
