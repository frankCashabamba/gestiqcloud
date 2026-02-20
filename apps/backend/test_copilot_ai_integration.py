"""
Test de integración del módulo Copilot con IA
Verifica que los nuevos endpoints funcionen correctamente
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_query_readonly_enhanced_with_ai():
    """Verifica que query_readonly_enhanced devuelve insights IA"""
    from app.modules.copilot.services import query_readonly_enhanced
    from app.services.ai.base import AIResponse

    # Mock de BD
    mock_db = MagicMock()

    # Mock de AIService
    with patch("app.modules.copilot.services.AIService.query") as mock_ai:
        # Simular respuesta IA
        mock_ai.return_value = AIResponse(
            task="analysis",
            content=json.dumps(
                {
                    "findings": ["Ventas crecieron 15% este mes", "Top producto es X"],
                    "trends": ["Tendencia alcista en marzo"],
                    "recommendations": ["Aumentar stock de producto X"],
                    "alerts": [],
                }
            ),
            model="llama3.1:8b",
            processing_time_ms=250,
        )

        # Mockear query_readonly
        with patch("app.modules.copilot.services.query_readonly") as mock_query:
            mock_query.return_value = {
                "cards": [{"title": "Ventas por mes", "data": [{"mes": "2025-03", "pedidos": 15}]}],
                "sql": "SELECT ...",
            }

            # Ejecutar
            result = await query_readonly_enhanced(mock_db, "ventas_mes", with_ai_insights=True)

            # Verificar
            assert "ai_insights" in result
            assert "ai_model" in result
            assert result["ai_model"] == "llama3.1:8b"
            assert "findings" in result["ai_insights"]
            assert len(result["ai_insights"]["findings"]) > 0

            # Verificar que se llamó a AIService.query
            mock_ai.assert_called_once()

            print("✅ Test query_readonly_enhanced PASSED")


@pytest.mark.asyncio
async def test_get_smart_suggestions():
    """Verifica que get_smart_suggestions genera sugerencias"""
    from app.modules.copilot.services import get_smart_suggestions

    mock_db = MagicMock()

    with patch("app.modules.copilot.services.AIService.generate_suggestion") as mock_suggest:
        # Simular sugerencias
        mock_suggest.side_effect = [
            "Considera ordenar más stock del producto X que tiene demanda alta",
            "Oportunidad: bundlear producto A con B",
            "Revisar cobros pendientes por más de 30 días",
        ]

        with patch("app.modules.copilot.services.query_readonly") as mock_query:
            # Mock para cada llamada a query_readonly
            call_count = [0]

            def query_side_effect(db, topic, params):
                call_count[0] += 1
                if topic == "stock_bajo":
                    return {
                        "cards": [{"data": [{"product_id": 1, "qty": 2}, {"product_id": 2, "qty": 3}]}]
                    }
                elif topic == "top_productos":
                    return {
                        "cards": [
                            {
                                "data": [
                                    {"id": 1, "name": "Pan Integral"},
                                    {"id": 2, "name": "Pan Blanco"},
                                ]
                            }
                        ]
                    }
                else:  # cobros_pagos
                    return {"cards": [{"data": [{"tipo": "pago", "estado": "pending"}]}]}
                return {"cards": [{"data": []}]}

            mock_query.side_effect = query_side_effect

            # Ejecutar
            suggestions = await get_smart_suggestions(mock_db)

            # Verificar
            assert isinstance(suggestions, list)
            assert len(suggestions) == 3
            assert suggestions[0]["type"] == "inventory"
            assert suggestions[1]["type"] == "sales"
            assert suggestions[2]["type"] == "finance"

            # Verificar que tienen contenido
            for suggestion in suggestions:
                assert "type" in suggestion
                assert "content" in suggestion
                assert "action" in suggestion
                assert "priority" in suggestion
                assert len(suggestion["content"]) > 0

            print("✅ Test get_smart_suggestions PASSED")


@pytest.mark.asyncio
async def test_ai_ask_endpoint_with_insights():
    """Verifica el endpoint POST /ai/ask con insights"""
    from fastapi.testclient import TestClient

    # Este test requeriría un cliente HTTP real
    # Por ahora es un placeholder para documentar cómo testear
    print("⚠️  Endpoint test requiere cliente HTTP - usar pytest con async support")


def test_copilot_module_structure():
    """Verifica que la estructura del módulo es correcta"""
    from app.modules.copilot import services

    # Verificar que existan las funciones esperadas
    assert hasattr(services, "query_readonly")
    assert hasattr(services, "query_readonly_enhanced")
    assert hasattr(services, "get_smart_suggestions")
    assert hasattr(services, "create_invoice_draft")
    assert hasattr(services, "create_order_draft")
    assert hasattr(services, "create_transfer_draft")
    assert hasattr(services, "suggest_overlay_fields")

    print("✅ Test module structure PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("PRUEBAS DE INTEGRACIÓN COPILOT + IA")
    print("=" * 60)

    # Test structure
    test_copilot_module_structure()

    # Test con asyncio
    print("\nEjecutando tests async...")
    asyncio.run(test_query_readonly_enhanced_with_ai())
    asyncio.run(test_get_smart_suggestions())

    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 60)
