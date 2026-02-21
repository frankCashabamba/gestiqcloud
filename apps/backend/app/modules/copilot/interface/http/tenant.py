from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import ensure_rls, tenant_id_from_request
from app.services.ai.base import AITask
from app.services.ai.service import AIService
from app.modules.copilot.services import (
    create_invoice_draft,
    create_order_draft,
    create_transfer_draft,
    get_smart_suggestions,
    query_readonly,
    query_readonly_enhanced,
    suggest_overlay_fields,
)

logger = logging.getLogger(__name__)


def _feature_enabled() -> bool:
    value = str(os.getenv("COPILOT_TENANT_ENABLED", "1")).strip().lower()
    return value in ("1", "true", "yes", "on")


def _require_tenant_access(request: Request) -> dict[str, Any]:
    claims = getattr(request.state, "access_claims", None) or {}
    kind = str(claims.get("kind", "")).strip().lower()
    scope = str(claims.get("scope", "")).strip().lower()
    scopes_claim = claims.get("scopes")
    scopes: set[str] = set()
    if isinstance(scopes_claim, (list, tuple, set)):
        scopes = {str(s).strip().lower() for s in scopes_claim if s}
    elif isinstance(scopes_claim, str) and scopes_claim.strip():
        scopes = {scopes_claim.strip().lower()}

    if kind == "tenant" or scope == "tenant" or "tenant" in scopes:
        return claims

    # Fallback for legacy tokens that only carry tenant_id.
    if claims.get("tenant_id"):
        return claims

    raise HTTPException(status_code=403, detail="forbidden")


router = APIRouter(
    prefix="/ai",
    tags=["Copilot"],
    dependencies=[
        Depends(with_access_claims),
        Depends(_require_tenant_access),
        Depends(ensure_rls),
    ],
)


class AskIn(BaseModel):
    topic: str = Field(
        description="ventas_mes|ventas_por_almacen|top_productos|stock_bajo|pendientes_sri_sii|cobros_pagos"
    )
    params: dict[str, Any] | None = None
    with_ai_insights: bool = Field(default=True, description="Enable AI analysis insights")


@router.post("/ask", response_model=dict[str, Any])
async def ai_ask(payload: AskIn, db: Session = Depends(get_db)):
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")

    try:
        if payload.with_ai_insights:
            # Obtener datos + análisis IA
            out = await query_readonly_enhanced(
                db, payload.topic, payload.params or {}, with_ai_insights=True
            )
        else:
            # Solo datos sin análisis
            out = query_readonly(db, payload.topic, payload.params or {})

        # Masking is done inside service for PII fields
        return out
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}", exc_info=True)
        # Fallback a datos sin análisis
        return query_readonly(db, payload.topic, payload.params or {})


class ActIn(BaseModel):
    action: str = Field(
        description="create_invoice_draft|create_order_draft|create_transfer_draft|suggest_overlay_fields"
    )
    payload: dict[str, Any] | None = None


def _allow(action: str) -> bool:
    allowed = os.getenv(
        "COPILOT_ALLOWED_ACTIONS",
        "create_invoice_draft,create_order_draft,create_transfer_draft,suggest_overlay_fields",
    )
    set_allowed = {a.strip() for a in allowed.split(",") if a.strip()}
    return action in set_allowed


@router.post("/act", response_model=dict[str, Any])
def ai_act(payload: ActIn, request: Request, db: Session = Depends(get_db)):
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    if not _allow(payload.action):
        raise HTTPException(status_code=403, detail="action_not_allowed")

    if payload.action == "create_invoice_draft":
        claims = request.state.access_claims
        tenant_id = claims.get("tenant_id")
        if tenant_id is None or not str(tenant_id).isdigit():
            # In este backend convivimos con tenant_id mientras dura la transición
            raise HTTPException(status_code=400, detail="empresa_id_required_for_invoice")
        return create_invoice_draft(db, int(tenant_id), payload.payload or {})

    if payload.action == "create_order_draft":
        tid = tenant_id_from_request(request)
        return create_order_draft(db, payload.payload or {}, tenant_id=tid)

    if payload.action == "create_transfer_draft":
        tid = tenant_id_from_request(request)
        return create_transfer_draft(db, payload.payload or {}, tenant_id=tid)

    if payload.action == "suggest_overlay_fields":
        return suggest_overlay_fields(db)

    raise HTTPException(status_code=400, detail="unknown_action")


class SuggestionsOut(BaseModel):
    suggestions: list[dict[str, Any]]
    generated_at: datetime
    ai_enabled: bool


@router.get("/suggestions", response_model=SuggestionsOut)
async def ai_suggestions(db: Session = Depends(get_db)):
    """Obtiene sugerencias inteligentes generadas por IA basadas en datos empresariales"""
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")

    try:
        suggestions = await get_smart_suggestions(db)
        return {
            "suggestions": suggestions,
            "generated_at": datetime.utcnow(),
            "ai_enabled": True,
        }
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}", exc_info=True)
        return {
            "suggestions": [],
            "generated_at": datetime.utcnow(),
            "ai_enabled": False,
        }


class ChatIn(BaseModel):
    message: str = Field(description="User message / question")
    history: list[dict[str, str]] = Field(default_factory=list, description="Previous messages [{role,content}]")


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []


@router.post("/chat", response_model=ChatOut)
async def ai_chat(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
    """Chat conversacional con el asistente IA del negocio"""
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")

    try:
        # Build context from business data
        context_parts = []
        try:
            stock = query_readonly(db, "stock_bajo", {"threshold": 5})
            if stock["cards"][0].get("data"):
                context_parts.append(f"Productos con stock bajo: {len(stock['cards'][0]['data'])}")
        except Exception:
            pass

        try:
            top = query_readonly(db, "top_productos", {})
            if top["cards"][0].get("data"):
                names = ", ".join(p.get("name", "?") for p in top["cards"][0]["data"][:5])
                context_parts.append(f"Productos más vendidos: {names}")
        except Exception:
            pass

        biz_context = "\n".join(context_parts) if context_parts else "No hay datos de contexto disponibles."

        # Build conversation history for prompt
        history_text = ""
        for msg in payload.history[-10:]:  # Last 10 messages only
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"\n{'Usuario' if role == 'user' else 'Asistente'}: {content}"

        prompt = f"""Eres el asistente IA de GestiqCloud, un ERP/CRM. Ayudas al usuario con consultas sobre su negocio, inventario, ventas, facturación y problemas operativos.

Contexto del negocio:
{biz_context}

{f'Historial de conversación:{history_text}' if history_text else ''}

Usuario: {payload.message}

Responde de forma concisa, útil y en español. Si detectas un problema, sugiere soluciones concretas.
Responde SOLO con JSON: {{"reply": "tu respuesta", "suggestions": ["pregunta sugerida 1", "pregunta sugerida 2"]}}"""

        response = await AIService.query(
            task=AITask.CHAT,
            prompt=prompt,
            temperature=0.6,
            max_tokens=500,
        )

        if response.is_error:
            return {"reply": "Lo siento, no pude procesar tu consulta en este momento. Intenta de nuevo.", "suggestions": []}

        try:
            data = json.loads(response.content)
            return {
                "reply": data.get("reply", response.content),
                "suggestions": data.get("suggestions", [])[:3],
            }
        except json.JSONDecodeError:
            return {"reply": response.content, "suggestions": []}

    except Exception as e:
        logger.error(f"Error in /chat endpoint: {e}", exc_info=True)
        return {"reply": "Ocurrió un error procesando tu mensaje. Intenta de nuevo.", "suggestions": []}
