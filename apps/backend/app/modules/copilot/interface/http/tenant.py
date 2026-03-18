from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.db.rls import ensure_rls, tenant_id_from_request
from app.modules.copilot.context_builder import CopilotContextBuilder
from app.modules.copilot.services import (
    create_invoice_draft,
    create_order_draft,
    create_transfer_draft,
    get_smart_suggestions,
    query_readonly,
    query_readonly_enhanced,
    suggest_overlay_fields,
)
from app.services.ai.base import AITask
from app.services.ai.service import AIService

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


# --- Per-tenant AI rate limiting ---
_ai_rate_buckets: dict[str, list[float]] = {}

AI_CHAT_LIMIT = int(os.getenv("AI_CHAT_RATE_LIMIT", "20"))  # per minute
AI_SUGGEST_LIMIT = int(os.getenv("AI_SUGGEST_RATE_LIMIT", "5"))  # per minute


def _check_ai_rate_limit(request: Request, limit: int = AI_CHAT_LIMIT) -> None:
    """Simple in-memory per-tenant rate limit for AI endpoints."""
    import time

    claims = getattr(request.state, "access_claims", None) or {}
    tenant_id = claims.get("tenant_id", "unknown") if isinstance(claims, dict) else "unknown"
    key = f"ai:{tenant_id}"
    now = time.time()
    window = 60.0

    bucket = _ai_rate_buckets.get(key, [])
    bucket = [t for t in bucket if now - t < window]

    if len(bucket) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"ai_rate_limit_exceeded: max {limit} requests/min per tenant",
        )

    bucket.append(now)
    _ai_rate_buckets[key] = bucket


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
        description="ventas_mes|ventas_por_almacen|top_productos|stock_bajo|pendientes_sri_sii|cobros_pagos|pos_hoy|gastos_mes|produccion_activa|compras_pendientes|prediccion_reorden|anomalias_ventas|clasificar_gasto"
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
        if tenant_id is None:
            raise HTTPException(status_code=400, detail="empresa_id_required_for_invoice")
        return create_invoice_draft(db, str(tenant_id), payload.payload or {})

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
async def ai_suggestions(request: Request, db: Session = Depends(get_db)):
    """Obtiene sugerencias inteligentes generadas por IA basadas en datos empresariales"""
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    _check_ai_rate_limit(request, AI_SUGGEST_LIMIT)

    try:
        suggestions = await get_smart_suggestions(db)
        return {
            "suggestions": suggestions,
            "generated_at": datetime.now(UTC),
            "ai_enabled": True,
        }
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}", exc_info=True)
        return {
            "suggestions": [],
            "generated_at": datetime.now(UTC),
            "ai_enabled": False,
        }


class ChatIn(BaseModel):
    message: str = Field(description="User message / question")
    history: list[dict[str, str]] = Field(
        default_factory=list, description="Previous messages [{role,content}]"
    )
    current_module: str | None = Field(
        default=None,
        description="Active module in frontend (pos, inventory, sales, purchases, etc.)",
    )


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []


@router.post("/chat", response_model=ChatOut)
async def ai_chat(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
    """Chat conversacional con el asistente IA del negocio"""
    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    _check_ai_rate_limit(request, AI_CHAT_LIMIT)

    try:
        tenant_id = tenant_id_from_request(request)

        # Build module-specific context via CopilotContextBuilder
        biz_context = CopilotContextBuilder.build(db, str(tenant_id), payload.current_module)

        # Tenant metadata for system prompt
        tenant_meta = ""
        try:
            tenant_row = db.execute(
                text("SELECT name, sector, country, currency " "FROM tenants WHERE id = :tid"),
                {"tid": str(tenant_id)},
            ).fetchone()
            if tenant_row:
                parts = []
                if tenant_row[0]:
                    parts.append(f"Empresa: {tenant_row[0]}")
                if tenant_row[1]:
                    parts.append(f"Sector: {tenant_row[1]}")
                if tenant_row[2]:
                    parts.append(f"País: {tenant_row[2]}")
                if tenant_row[3]:
                    parts.append(f"Moneda: {tenant_row[3]}")
                tenant_meta = " | ".join(parts)
        except Exception:
            pass

        # Build conversation history for prompt
        history_text = ""
        for msg in payload.history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"\n{'Usuario' if role == 'user' else 'Asistente'}: {content}"

        module_label = payload.current_module or "general"
        prompt = f"""Eres el asistente IA de GestiqCloud, un ERP/CRM/POS. Ayudas al usuario con consultas sobre su negocio.
{f'Tenant: {tenant_meta}' if tenant_meta else ''}
Módulo activo: {module_label}

Datos del módulo (JSON):
{biz_context}

{f'Historial de conversación:{history_text}' if history_text else ''}

Usuario: {payload.message}

Responde de forma concisa, útil y en español. Usa los datos del módulo para dar respuestas específicas.
Si detectas un problema, sugiere soluciones concretas.
Responde SOLO con JSON: {{"reply": "tu respuesta", "suggestions": ["pregunta sugerida 1", "pregunta sugerida 2"]}}"""

        response = await AIService.query(
            task=AITask.CHAT,
            prompt=prompt,
            temperature=0.6,
            max_tokens=500,
        )

        if response.is_error:
            return {
                "reply": "Lo siento, no pude procesar tu consulta en este momento. Intenta de nuevo.",
                "suggestions": [],
            }

        try:
            data = json.loads(response.content)
            reply_text = data.get("reply", response.content)
            suggestions = data.get("suggestions", [])[:3]
        except json.JSONDecodeError:
            reply_text = response.content
            suggestions = []

        # Persist conversation (best-effort)
        _persist_chat(db, request, payload, reply_text)

        return {"reply": reply_text, "suggestions": suggestions}

    except Exception as e:
        logger.error("Error in /chat endpoint: %s", e, exc_info=True)
        return {
            "reply": "Ocurrió un error procesando tu mensaje. Intenta de nuevo.",
            "suggestions": [],
        }


def _persist_chat(db: Session, request: Request, payload: ChatIn, reply_text: str) -> str | None:
    """Best-effort persistence of chat messages. Returns assistant message_id or None."""
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        user_id = claims.get("user_id")
        if not user_id:
            return None

        tenant_id = tenant_id_from_request(request)
        conv_id = None

        if payload.history:
            last_conv = db.execute(
                text(
                    "SELECT id FROM copilot_conversations "
                    "WHERE tenant_id = :tid AND user_id = :uid "
                    "AND current_module IS NOT DISTINCT FROM :mod "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"tid": str(tenant_id), "uid": str(user_id), "mod": payload.current_module},
            ).first()
            if last_conv:
                conv_id = str(last_conv[0])

        if not conv_id:
            conv_row = db.execute(
                text(
                    "INSERT INTO copilot_conversations(id, tenant_id, user_id, title, current_module) "
                    "VALUES (gen_random_uuid(), :tid, :uid, :title, :mod) RETURNING id"
                ),
                {
                    "tid": str(tenant_id),
                    "uid": str(user_id),
                    "title": payload.message[:100],
                    "mod": payload.current_module,
                },
            ).first()
            conv_id = str(conv_row[0])

        db.execute(
            text(
                "INSERT INTO copilot_messages(id, conversation_id, role, content) "
                "VALUES (gen_random_uuid(), :cid, 'user', :content)"
            ),
            {"cid": conv_id, "content": payload.message},
        )
        asst_row = db.execute(
            text(
                "INSERT INTO copilot_messages(id, conversation_id, role, content) "
                "VALUES (gen_random_uuid(), :cid, 'assistant', :content) RETURNING id"
            ),
            {"cid": conv_id, "content": reply_text},
        ).first()
        db.execute(
            text("UPDATE copilot_conversations SET updated_at = NOW() WHERE id = :cid"),
            {"cid": conv_id},
        )
        db.commit()
        return str(asst_row[0]) if asst_row else None
    except Exception as e:
        logger.debug("Failed to persist chat: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return None


@router.post("/chat/stream")
async def ai_chat_stream(payload: ChatIn, request: Request, db: Session = Depends(get_db)):
    """Chat con streaming SSE — respuesta progresiva por chunks"""
    import asyncio

    if not _feature_enabled():
        raise HTTPException(status_code=403, detail="copilot_disabled")
    _check_ai_rate_limit(request, AI_CHAT_LIMIT)

    tenant_id = tenant_id_from_request(request)
    biz_context = CopilotContextBuilder.build(db, str(tenant_id), payload.current_module)

    # Tenant metadata
    tenant_meta = ""
    try:
        tenant_row = db.execute(
            text("SELECT name, sector, country, currency " "FROM tenants WHERE id = :tid"),
            {"tid": str(tenant_id)},
        ).fetchone()
        if tenant_row:
            parts = []
            if tenant_row[0]:
                parts.append(f"Empresa: {tenant_row[0]}")
            if tenant_row[1]:
                parts.append(f"Sector: {tenant_row[1]}")
            if tenant_row[2]:
                parts.append(f"País: {tenant_row[2]}")
            if tenant_row[3]:
                parts.append(f"Moneda: {tenant_row[3]}")
            tenant_meta = " | ".join(parts)
    except Exception:
        pass

    history_text = ""
    for msg in payload.history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"\n{'Usuario' if role == 'user' else 'Asistente'}: {content}"

    module_label = payload.current_module or "general"
    prompt = f"""Eres el asistente IA de GestiqCloud, un ERP/CRM/POS. Ayudas al usuario con consultas sobre su negocio.
{f'Tenant: {tenant_meta}' if tenant_meta else ''}
Módulo activo: {module_label}

Datos del módulo (JSON):
{biz_context}

{f'Historial de conversación:{history_text}' if history_text else ''}

Usuario: {payload.message}

Responde de forma concisa, útil y en español. Usa los datos del módulo para dar respuestas específicas.
Si detectas un problema, sugiere soluciones concretas."""

    async def generate():
        try:
            response = await AIService.query(
                task=AITask.CHAT,
                prompt=prompt,
                temperature=0.6,
                max_tokens=500,
            )

            if response.is_error:
                yield f"data: {json.dumps({'chunk': 'Lo siento, no pude procesar tu consulta. Intenta de nuevo.', 'done': False})}\n\n"
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'suggestions': []})}\n\n"
                return

            content = response.content
            suggestions: list[str] = []

            # Try to parse JSON response for suggestions
            try:
                parsed = json.loads(content)
                content = parsed.get("reply", content)
                suggestions = parsed.get("suggestions", [])[:3]
            except (json.JSONDecodeError, TypeError):
                pass

            # Persist (best-effort) — get message_id for feedback
            message_id = _persist_chat(db, request, payload, content)

            # Stream word by word
            words = content.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                yield f"data: {json.dumps({'chunk': chunk, 'done': False})}\n\n"
                await asyncio.sleep(0.03)

            yield f"data: {json.dumps({'chunk': '', 'done': True, 'suggestions': suggestions, 'message_id': message_id})}\n\n"

        except Exception as e:
            logger.error("Error in /chat/stream: %s", e, exc_info=True)
            yield f"data: {json.dumps({'chunk': 'Error procesando mensaje.', 'done': False})}\n\n"
            yield f"data: {json.dumps({'chunk': '', 'done': True, 'suggestions': []})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# --- Chat History Persistence ---


class ConversationOut(BaseModel):
    id: str
    title: str | None
    current_module: str | None
    created_at: datetime
    updated_at: datetime | None
    message_count: int = 0


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(request: Request, db: Session = Depends(get_db), limit: int = 20):
    """Lista las conversaciones del usuario actual."""
    claims = getattr(request.state, "access_claims", None) or {}
    user_id = claims.get("user_id")
    tenant_id = tenant_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="user_required")

    rows = db.execute(
        text(
            "SELECT c.id, c.title, c.current_module, c.created_at, c.updated_at, "
            "count(m.id) AS msg_count "
            "FROM copilot_conversations c "
            "LEFT JOIN copilot_messages m ON m.conversation_id = c.id "
            "WHERE c.tenant_id = :tid AND c.user_id = :uid "
            "GROUP BY c.id ORDER BY c.updated_at DESC NULLS LAST LIMIT :lim"
        ),
        {"tid": str(tenant_id), "uid": str(user_id), "lim": limit},
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "current_module": r[2],
            "created_at": r[3],
            "updated_at": r[4],
            "message_count": int(r[5] or 0),
        }
        for r in rows
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_conversation_messages(
    conversation_id: str, request: Request, db: Session = Depends(get_db)
):
    """Obtiene los mensajes de una conversación."""
    tenant_id = tenant_id_from_request(request)
    claims = getattr(request.state, "access_claims", None) or {}
    user_id = claims.get("user_id")

    # Verify conversation belongs to this user/tenant
    conv = db.execute(
        text(
            "SELECT id FROM copilot_conversations "
            "WHERE id = :cid AND tenant_id = :tid AND user_id = :uid"
        ),
        {"cid": conversation_id, "tid": str(tenant_id), "uid": str(user_id)},
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="conversation_not_found")

    rows = db.execute(
        text(
            "SELECT id, role, content, created_at "
            "FROM copilot_messages WHERE conversation_id = :cid "
            "ORDER BY created_at ASC"
        ),
        {"cid": conversation_id},
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "role": r[1],
            "content": r[2],
            "created_at": r[3],
        }
        for r in rows
    ]


class FeedbackIn(BaseModel):
    message_id: str
    rating: str = Field(description="thumbs_up | thumbs_down")


@router.post("/feedback")
def ai_feedback(payload: FeedbackIn, request: Request, db: Session = Depends(get_db)):
    """Guarda feedback del usuario (👍👎) sobre una respuesta del copilot."""
    if payload.rating not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="invalid_rating")

    tenant_id = tenant_id_from_request(request)

    # Solo permite actualizar mensajes pertenecientes a este tenant (via conversación)
    result = db.execute(
        text(
            "UPDATE copilot_messages m "
            "SET metadata = metadata || :feedback "
            "FROM copilot_conversations c "
            "WHERE m.id = :mid AND m.conversation_id = c.id AND c.tenant_id = :tid"
        ),
        {
            "mid": payload.message_id,
            "tid": str(tenant_id),
            "feedback": json.dumps({"feedback": payload.rating}),
        },
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="message_not_found")

    return {"status": "ok"}


class ClassifyExpenseIn(BaseModel):
    description: str
    amount: float = 0
    vendor: str | None = None


@router.post("/classify-expense")
async def classify_expense(
    payload: ClassifyExpenseIn, request: Request, db: Session = Depends(get_db)
):
    """Clasifica un gasto usando IA."""
    _check_ai_rate_limit(request, AI_CHAT_LIMIT)
    tenant_id = tenant_id_from_request(request)

    # Get existing categories for context
    categories = db.execute(
        text(
            "SELECT DISTINCT category FROM expenses WHERE tenant_id = :tid AND category IS NOT NULL ORDER BY category"
        ),
        {"tid": str(tenant_id)},
    ).fetchall()
    cat_list = [str(r[0]) for r in categories if r[0]]

    prompt = f"""Clasifica este gasto en una categoría. Categorías existentes: {', '.join(cat_list) or 'ninguna aún'}.
Descripción: {payload.description}
Monto: {payload.amount}
{f'Proveedor: {payload.vendor}' if payload.vendor else ''}

Responde SOLO con JSON: {{"category": "nombre_categoria", "confidence": 0.95, "reasoning": "breve explicación"}}"""

    response = await AIService.query(
        task=AITask.CHAT, prompt=prompt, temperature=0.3, max_tokens=150
    )

    if response.is_error:
        return {"category": "otros", "confidence": 0.0, "reasoning": "ai_unavailable"}

    try:
        data = json.loads(response.content)
        return {
            "category": data.get("category", "otros"),
            "confidence": data.get("confidence", 0.5),
            "reasoning": data.get("reasoning", ""),
        }
    except json.JSONDecodeError:
        return {"category": "otros", "confidence": 0.0, "reasoning": response.content}


class PriceSuggestionIn(BaseModel):
    product_id: str
    target_margin: float = Field(default=30.0, description="Target margin percentage")


@router.post("/suggest-price")
async def suggest_price(
    payload: PriceSuggestionIn, request: Request, db: Session = Depends(get_db)
):
    """Sugiere precio basado en costo de receta + margen objetivo."""
    _check_ai_rate_limit(request, AI_SUGGEST_LIMIT)
    tenant_id = tenant_id_from_request(request)

    # Get product info and recipe cost
    product = db.execute(
        text("SELECT id, name, price FROM products WHERE id = :pid AND tenant_id = :tid"),
        {"pid": payload.product_id, "tid": str(tenant_id)},
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="product_not_found")

    recipe_cost = (
        db.execute(
            text(
                "SELECT coalesce(sum(ri.qty * p.cost), 0) AS total_cost "
                "FROM recipe_items ri "
                "JOIN products p ON p.id = ri.ingredient_id "
                "WHERE ri.recipe_id IN (SELECT id FROM recipes WHERE product_id = :pid AND tenant_id = :tid)"
            ),
            {"pid": payload.product_id, "tid": str(tenant_id)},
        ).scalar()
        or 0
    )

    current_price = float(product[2] or 0)
    cost = float(recipe_cost)
    margin_pct = payload.target_margin / 100
    suggested = cost / (1 - margin_pct) if margin_pct < 1 else cost * 2

    prompt = f"""Analiza este producto y sugiere un precio óptimo.
Producto: {product[1]}
Costo de receta/insumos: ${cost:.2f}
Precio actual: ${current_price:.2f}
Margen objetivo: {payload.target_margin}%
Precio sugerido por fórmula: ${suggested:.2f}

Responde SOLO con JSON: {{"suggested_price": {suggested:.2f}, "min_price": 0.00, "max_price": 0.00, "reasoning": "explicación"}}"""

    response = await AIService.query(
        task=AITask.CHAT, prompt=prompt, temperature=0.4, max_tokens=200
    )

    result = {
        "product_name": product[1],
        "recipe_cost": round(cost, 2),
        "current_price": current_price,
        "suggested_price": round(suggested, 2),
        "target_margin": payload.target_margin,
    }

    if not response.is_error:
        try:
            ai_data = json.loads(response.content)
            result["ai_suggested_price"] = ai_data.get("suggested_price", suggested)
            result["reasoning"] = ai_data.get("reasoning", "")
            result["min_price"] = ai_data.get("min_price", 0)
            result["max_price"] = ai_data.get("max_price", 0)
        except json.JSONDecodeError:
            result["reasoning"] = response.content

    return result


@router.get("/metrics")
def ai_metrics(request: Request, db: Session = Depends(get_db), days: int = 30):
    """Dashboard de métricas IA: requests/día, costo estimado, error rate."""
    tenant_id = tenant_id_from_request(request)

    # Requests per day
    daily = db.execute(
        text(
            "SELECT created_at::date AS day, count(*) AS requests, "
            "count(*) FILTER (WHERE status = 'error') AS errors, "
            "coalesce(sum(tokens_used), 0) AS total_tokens "
            "FROM ai_request_logs WHERE tenant_id = :tid "
            "AND created_at > CURRENT_DATE - :days * INTERVAL '1 day' "
            "GROUP BY 1 ORDER BY 1 DESC"
        ),
        {"tid": str(tenant_id), "days": days},
    ).fetchall()

    # Model usage breakdown
    models = db.execute(
        text(
            "SELECT model, count(*) AS requests, coalesce(sum(tokens_used), 0) AS tokens "
            "FROM ai_request_logs WHERE tenant_id = :tid "
            "AND created_at > CURRENT_DATE - :days * INTERVAL '1 day' "
            "GROUP BY model ORDER BY requests DESC"
        ),
        {"tid": str(tenant_id), "days": days},
    ).fetchall()

    # Task type breakdown
    tasks = db.execute(
        text(
            "SELECT task, count(*) AS requests "
            "FROM ai_request_logs WHERE tenant_id = :tid "
            "AND created_at > CURRENT_DATE - :days * INTERVAL '1 day' "
            "GROUP BY task ORDER BY requests DESC"
        ),
        {"tid": str(tenant_id), "days": days},
    ).fetchall()

    total_requests = sum(r[1] for r in daily) if daily else 0
    total_errors = sum(r[2] for r in daily) if daily else 0
    total_tokens = sum(r[3] for r in daily) if daily else 0

    # Estimate cost: ~$0.002 per 1K tokens (rough average)
    estimated_cost = total_tokens / 1000 * 0.002

    return {
        "period_days": days,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate": round(total_errors / total_requests * 100, 1) if total_requests else 0,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(estimated_cost, 4),
        "daily": [
            {"day": str(r[0]), "requests": r[1], "errors": r[2], "tokens": r[3]} for r in daily
        ],
        "by_model": [{"model": r[0], "requests": r[1], "tokens": r[2]} for r in models],
        "by_task": [{"task": r[0], "requests": r[1]} for r in tasks],
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina una conversación y sus mensajes."""
    tenant_id = tenant_id_from_request(request)
    claims = getattr(request.state, "access_claims", None) or {}
    user_id = claims.get("user_id")

    conv = db.execute(
        text(
            "SELECT id FROM copilot_conversations "
            "WHERE id = :cid AND tenant_id = :tid AND user_id = :uid"
        ),
        {"cid": conversation_id, "tid": str(tenant_id), "uid": str(user_id)},
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="conversation_not_found")

    db.execute(
        text("DELETE FROM copilot_messages WHERE conversation_id = :cid"), {"cid": conversation_id}
    )
    db.execute(text("DELETE FROM copilot_conversations WHERE id = :cid"), {"cid": conversation_id})
    db.commit()

    return {"status": "deleted"}
