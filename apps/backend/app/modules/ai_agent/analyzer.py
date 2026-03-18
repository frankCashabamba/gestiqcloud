import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ai.incident import Incident
from app.services.ai.base import AITask
from app.services.ai.service import AIService


async def analyze_incident_with_ia(
    incident_id: UUID,
    use_gpt4: bool = False,
    include_code_suggestions: bool = True,
    db: Session = None,
) -> dict[str, Any]:
    """
    Analiza una incidencia con IA y retorna análisis + sugerencias.
    Usa AIService (provider-agnostic) con fallback automático.
    """
    start_time = time.time()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

    prompt = _build_analysis_prompt(incident, include_code_suggestions)

    response = await AIService.query(
        task=AITask.ANALYSIS,
        prompt=prompt,
        temperature=0.3,
        max_tokens=2000,
        db=db,
        module="ai_agent",
    )

    if response.is_error:
        analysis_data = _mock_analysis_response(incident)
        analysis_data = _parse_ia_response(analysis_data)
    else:
        analysis_data = _parse_ia_response(response.content)

    incident.ia_analysis = analysis_data["analysis"]
    incident.ia_suggestion = analysis_data.get("suggestion")
    db.commit()

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "incident_id": incident_id,
        "analysis": analysis_data["analysis"],
        "suggestion": analysis_data.get("suggestion"),
        "confidence_score": analysis_data.get("confidence_score"),
        "processing_time_ms": processing_time_ms,
    }


async def suggest_fix(incident_id: UUID, db: Session) -> dict[str, Any]:
    """Sugiere código de fix para una incidencia usando AIService."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

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

    response = await AIService.query(
        task=AITask.SUGGESTION,
        prompt=prompt,
        temperature=0.3,
        max_tokens=2000,
        db=db,
        module="ai_agent",
    )

    if response.is_error:
        return {
            "suggested_code": "# No se pudo generar sugerencia\ndef fix_issue():\n    pass",
            "explanation": f"Error del proveedor IA: {response.error}",
            "affected_files": [],
        }

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "suggested_code": response.content,
            "explanation": "Respuesta no fue JSON válido",
            "affected_files": [],
        }


async def auto_resolve_incident(incident_id: UUID, db: Session) -> dict[str, Any]:
    """
    Intenta auto-resolver incidencia (sandbox).
    IMPORTANTE: En producción usar sandbox seguro (Docker, VM aislada).
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident {incident_id} no encontrado")

    if incident.severidad == "critical":
        return {
            "success": False,
            "error": "No se auto-resuelven incidencias críticas por seguridad",
            "recommendation": "Revisar manualmente",
        }

    incident.auto_resolved = True
    incident.estado = "resolved"
    incident.resolved_at = datetime.now(UTC)
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


def _mock_analysis_response(incident: Incident) -> str:
    """Genera respuesta mock cuando no hay proveedor IA disponible"""
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
        return {
            "analysis": {
                "root_cause": "Error parseando respuesta IA",
                "raw_response": response,
            },
            "suggestion": None,
            "confidence_score": 0.0,
        }
