import json
import os
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ai.incident import Incident


async def analyze_incident_with_ia(
    incident_id: UUID,
    use_gpt4: bool = False,
    include_code_suggestions: bool = True,
    db: Session = None,
) -> dict[str, Any]:
    """
    Analiza una incidencia con IA (GPT-4/Claude) y retorna análisis + sugerencias

    Args:
        incident_id: UUID de la incidencia
        use_gpt4: Si usar GPT-4 (más caro pero mejor) o GPT-3.5
        include_code_suggestions: Si incluir sugerencias de código
        db: Sesión de base de datos

    Returns:
        Dict con analysis, suggestion, confidence_score, processing_time_ms
    """
    start_time = time.time()

    # 1. Obtener incident
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

    # 2. Construir prompt con contexto
    prompt = _build_analysis_prompt(incident, include_code_suggestions)

    # 3. Llamar LLM
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if openai_api_key and openai_api_key != "your-openai-key-here":
        # Usar OpenAI API real
        analysis_result = await _call_openai_api(
            prompt=prompt,
            model="gpt-4" if use_gpt4 else "gpt-3.5-turbo",
            api_key=openai_api_key,
        )
    else:
        # Mock response para desarrollo
        analysis_result = _mock_analysis_response(incident)

    # 4. Parsear respuesta
    analysis_data = _parse_ia_response(analysis_result)

    # 5. Guardar ia_analysis en DB
    incident.ia_analysis = analysis_data["analysis"]
    incident.ia_suggestion = analysis_data.get("suggestion")
    db.commit()

    # 6. Calcular tiempo de procesamiento
    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "incident_id": incident_id,
        "analysis": analysis_data["analysis"],
        "suggestion": analysis_data.get("suggestion"),
        "confidence_score": analysis_data.get("confidence_score"),
        "processing_time_ms": processing_time_ms,
    }


async def suggest_fix(incident_id: UUID, db: Session) -> dict[str, Any]:
    """
    Sugiere código de fix para una incidencia

    Returns:
        Dict con suggested_code, explanation, affected_files
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

    openai_api_key = os.getenv("OPENAI_API_KEY")

    if openai_api_key and openai_api_key != "your-openai-key-here":
        prompt = f"""
Genera código Python para resolver esta incidencia:

Tipo: {incident.tipo}
Título: {incident.titulo}
Descripción: {incident.description}
Stack Trace: {incident.stack_trace}

Retorna JSON con:
- suggested_code: str (código Python completo)
- explanation: str (explicación del fix)
- affected_files: list[str] (archivos a modificar)
"""
        result = await _call_openai_api(prompt, "gpt-4", openai_api_key)
        return json.loads(result)
    else:
        # Mock
        return {
            "suggested_code": "# Mock code fix\ndef fix_issue():\n    pass",
            "explanation": "Sugerencia de código (mock para desarrollo sin API key)",
            "affected_files": ["app/models/example.py"],
        }


async def auto_resolve_incident(incident_id: UUID, db: Session) -> dict[str, Any]:
    """
    Intenta auto-resolver incidencia (sandbox)

    IMPORTANTE: En producción usar sandbox seguro (Docker, VM aislada)

    Returns:
        Dict con success, applied_fix, test_results
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

    # Por seguridad, solo auto-resolver ciertos tipos
    if incident.severidad == "critical":
        return {
            "success": False,
            "error": "No se auto-resuelven incidencias críticas por seguridad",
            "recommendation": "Revisar manualmente",
        }

    # Mock de auto-resolución
    # En producción: ejecutar en sandbox, aplicar fix, ejecutar tests
    incident.auto_resolved = True
    incident.estado = "resolved"
    incident.resolved_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "applied_fix": "Mock auto-resolution",
        "test_results": "All tests passed (mock)",
        "recommendation": "Verificar en staging antes de desplegar",
    }


# ============================================================================
# HELPERS PRIVADOS
# ============================================================================


def _build_analysis_prompt(incident: Incident, include_code: bool) -> str:
    """Construye prompt para análisis de IA"""
    prompt = f"""
Eres un experto en diagnóstico de errores de software. Analiza esta incidencia:

TIPO: {incident.tipo}
SEVERIDAD: {incident.severidad}
TÍTULO: {incident.titulo}
DESCRIPCIÓN: {incident.description or "N/A"}

STACK TRACE:
{incident.stack_trace or "N/A"}

CONTEXTO ADICIONAL:
{json.dumps(incident.context, indent=2) if incident.context else "N/A"}

Retorna análisis en formato JSON con:
- root_cause: str (causa raíz probable)
- severity_justification: str (por qué tiene esta severidad)
- impact: str (impacto en el sistema)
- recommended_actions: list[str] (pasos para resolver)
- confidence_score: float (0.0-1.0)
"""

    if include_code:
        prompt += "\n- code_suggestion: str (código Python sugerido para fix)"

    return prompt


async def _call_openai_api(prompt: str, model: str, api_key: str) -> str:
    """Llama a OpenAI API (requiere aiohttp)"""
    try:
        import aiohttp

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un experto en diagnóstico de errores de software.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data["choices"][0]["message"]["content"]

    except ImportError:
        raise ImportError("Se requiere 'aiohttp' para usar OpenAI API: pip install aiohttp")
    except Exception as e:
        raise Exception(f"Error llamando OpenAI API: {str(e)}")


def _mock_analysis_response(incident: Incident) -> str:
    """Genera respuesta mock para desarrollo sin API key"""
    analysis = {
        "root_cause": f"Error en módulo relacionado con {incident.tipo}",
        "severity_justification": f"Severidad {incident.severidad} basada en impacto potencial",
        "impact": "Impacto en funcionalidad del sistema (análisis mock)",
        "recommended_actions": [
            "Revisar logs detallados",
            "Verificar configuración del módulo",
            "Ejecutar tests unitarios",
            "Validar datos de entrada",
        ],
        "confidence_score": 0.75,
        "code_suggestion": "# Mock code suggestion\n# Revisar implementación en módulo afectado",
    }
    return json.dumps(analysis, indent=2)


def _parse_ia_response(response: str) -> dict[str, Any]:
    """Parsea respuesta de IA a formato estructurado"""
    try:
        # Intentar parsear como JSON
        data = json.loads(response)

        return {
            "analysis": {
                "root_cause": data.get("root_cause", "Desconocido"),
                "severity_justification": data.get("severity_justification", ""),
                "impact": data.get("impact", ""),
                "recommended_actions": data.get("recommended_actions", []),
            },
            "suggestion": data.get("code_suggestion"),
            "confidence_score": data.get("confidence_score", 0.5),
        }
    except json.JSONDecodeError:
        # Si no es JSON válido, retornar respuesta como texto
        return {
            "analysis": {
                "root_cause": "Error parseando respuesta IA",
                "raw_response": response,
            },
            "suggestion": None,
            "confidence_score": 0.0,
        }
