"""Servicio de iteraciones de importación.

Gestiona el ciclo de vida de reprocesado iterativo:
- Carga líneas de staging según scope
- Normaliza solo los campos indicados
- Valida con reglas deterministas
- Registra errores por línea
- Calcula métricas de progreso y mejora
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from uuid import UUID

from sqlalchemy import String, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpIteration, ImpLineErrorLog, ImpStagingLine

from ..ai_classifier import analyze_document
from ..analysis_normalizer import _normalize_analysis_output
from ..canonical_document import build_document_projection
from ..document_fields import detect_document_total
from ..runtime_config import load_doc_type_patterns, load_prompt_config
from ..schemas import IterationResultOut, IterationScopeIn, StagingLineSummary

logger = logging.getLogger("importador.iteration_service")

_DOCUMENT_SHEET_SENTINEL = "__document__"


def _insert_staging_line_idempotent(
    db: Session,
    *,
    tenant_id: UUID,
    doc_id: UUID,
    line_number: int,
    sheet_name: str,
    raw_data: dict,
) -> int:
    existing = db.scalar(
        select(ImpStagingLine.id)
        .where(
            ImpStagingLine.documento_id == doc_id,
            ImpStagingLine.line_number == line_number,
            ImpStagingLine.sheet_name == sheet_name,
        )
        .limit(1)
    )
    if existing:
        return 0

    db.add(
        ImpStagingLine(
            tenant_id=tenant_id,
            documento_id=doc_id,
            line_number=line_number,
            sheet_name=sheet_name,
            raw_data=raw_data,
            estado="PENDING",
        )
    )
    db.flush()
    return 1


# ─── Creación inicial de staging lines ───────────────────────────────────


def upsert_staging_lines_from_extraction(
    db: Session,
    doc_id: UUID,
    tenant_id: UUID,
    datos_extraidos: dict,
) -> int:
    """
    Crea o actualiza staging lines a partir de los datos extraídos.
    Idempotente: si la línea ya existe (por UNIQUE constraint) la ignora.
    Retorna el número de filas insertadas.

    - Excel/CSV: una línea por fila en cada hoja (filas_por_hoja).
    - PDF/XML/imagen/TXT: una línea con el documento completo como raw_data.
    """
    if not isinstance(datos_extraidos, dict):
        return 0

    filas_por_hoja: dict[str, list] = datos_extraidos.get("filas_por_hoja") or {}
    inserted = 0

    if filas_por_hoja:
        # Documento tabular (Excel / CSV): una línea por fila por hoja.
        # INSERT ON CONFLICT DO NOTHING — idempotente: el mismo doc se puede
        # reprocesar N veces sin duplicar filas (UNIQUE documento_id, line_number, sheet_name).
        for sheet_name, rows in filas_por_hoja.items():
            if not isinstance(rows, list):
                continue
            for line_number, raw_row in enumerate(rows, start=1):
                if not isinstance(raw_row, dict):
                    continue
                inserted += _insert_staging_line_idempotent(
                    db,
                    tenant_id=tenant_id,
                    doc_id=doc_id,
                    line_number=line_number,
                    sheet_name=sheet_name,
                    raw_data=raw_row,
                )
    else:
        # Documento no tabular (PDF/XML/imagen): una única línea con el cuerpo completo.
        # PostgreSQL permite duplicados cuando una columna UNIQUE es NULL; usamos un
        # sentinel estable para conservar idempotencia real en reintentos del mismo doc.
        inserted = _insert_staging_line_idempotent(
            db,
            tenant_id=tenant_id,
            doc_id=doc_id,
            line_number=1,
            sheet_name=_DOCUMENT_SHEET_SENTINEL,
            raw_data=datos_extraidos,
        )

    return inserted


# ─── CRUD de staging lines ────────────────────────────────────────────────


def count_staging_lines(db: Session, documento_id: UUID) -> StagingLineSummary:
    """Cuenta líneas por estado para un documento."""
    rows = db.execute(
        select(ImpStagingLine.estado, func.count(ImpStagingLine.id))
        .where(ImpStagingLine.documento_id == documento_id)
        .group_by(ImpStagingLine.estado)
    ).all()
    counts = {str(estado): int(n) for estado, n in rows}
    return StagingLineSummary(
        pending=counts.get("PENDING", 0),
        valid=counts.get("VALID", 0),
        imported=counts.get("IMPORTED", 0),
        invalid=counts.get("INVALID", 0),
        review=counts.get("REVIEW", 0),
        skipped=counts.get("SKIPPED", 0),
        reprocess=counts.get("REPROCESS", 0),
    )


def fetch_lines_for_scope(
    db: Session,
    documento_id: UUID,
    scope: IterationScopeIn,
) -> list[ImpStagingLine]:
    """Retorna las líneas que deben procesarse según el scope."""
    q = select(ImpStagingLine).where(ImpStagingLine.documento_id == documento_id)

    if scope.mode == "ALL":
        q = q.where(ImpStagingLine.estado.in_(["PENDING", "INVALID", "REVIEW", "REPROCESS"]))
    else:
        conditions = []
        if scope.filter_estados:
            conditions.append(ImpStagingLine.estado.in_(scope.filter_estados))
        if scope.filter_error_codes:
            conditions.append(ImpStagingLine.error_code.in_(scope.filter_error_codes))
        if scope.filter_lines:
            conditions.append(ImpStagingLine.line_number.in_(scope.filter_lines))
        if scope.filter_sheet:
            conditions.append(ImpStagingLine.sheet_name == scope.filter_sheet)
        if scope.filter_columns:
            column_conditions = []
            for column in scope.filter_columns:
                if not column:
                    continue
                key_token = f'"{column}"'
                column_conditions.append(ImpStagingLine.raw_data.cast(String).contains(key_token))
                column_conditions.append(
                    ImpStagingLine.normalized_data.cast(String).contains(key_token)
                )
            if column_conditions:
                conditions.append(or_(*column_conditions))
        if scope.filter_campos:
            field_conditions = [
                ImpStagingLine.campos_revision.cast(String).contains(field)
                for field in scope.filter_campos
                if field
            ]
            conditions.append(
                or_(
                    ImpStagingLine.campos_revision.is_(None),
                    ImpStagingLine.campos_revision.cast(String) == "null",
                    *field_conditions,
                )
            )
        if conditions:
            q = q.where(and_(*conditions))
        else:
            return []

    return list(db.scalars(q.order_by(ImpStagingLine.line_number)).all())


def count_lines_for_scope(db: Session, documento_id: UUID, scope: IterationScopeIn) -> int:
    """Cuenta cuántas líneas afecta un scope sin cargarlas todas."""
    lines = fetch_lines_for_scope(db, documento_id, scope)
    return len(lines)


def _document_scope_fields(scope: IterationScopeIn) -> list[str]:
    fields: list[str] = []
    for value in list(scope.filter_campos or []) + list(scope.filter_columns or []):
        item = str(value).strip()
        if item and item not in fields:
            fields.append(item)
    return fields


def _is_document_scope_line(line: ImpStagingLine) -> bool:
    return (line.sheet_name or _DOCUMENT_SHEET_SENTINEL) == _DOCUMENT_SHEET_SENTINEL


def _reextract_document_scope_fields(
    db: Session,
    doc: ImpDocumento,
    selected_fields: list[str],
    canonical_fields: dict[str, dict] | None,
) -> dict:
    if not selected_fields or not str(doc.texto_ocr or "").strip():
        return {}

    canonical_meta = canonical_fields or {}
    narrowed_fields = {field: canonical_meta.get(field, {}) for field in selected_fields if field}
    if not narrowed_fields:
        return {}
    requires_full_document_rerun = any(
        str((canonical_meta.get(field) or {}).get("type") or "").strip().lower() == "list"
        for field in selected_fields
    )
    analysis_fields = canonical_meta if requires_full_document_rerun and canonical_meta else narrowed_fields

    analysis = asyncio.run(
        analyze_document(
            str(doc.texto_ocr or ""),
            doc.nombre_archivo,
            doc.tipo_archivo,
            fallback_patterns=load_doc_type_patterns(db),
            canonical_fields=analysis_fields,
            prompt_config=load_prompt_config(db),
        )
    )
    normalized = _normalize_analysis_output(analysis)
    extracted = normalized.get("fields")
    if not isinstance(extracted, dict):
        return {}
    result = {
        field: extracted[field]
        for field in selected_fields
        if field in extracted and extracted[field] not in (None, "", [])
    }
    if requires_full_document_rerun and "line_items" in result:
        derived_total = detect_document_total({"line_items": result["line_items"]})
        if derived_total is not None:
            result["total_amount"] = derived_total
    return result


def _sync_document_scope_line_to_document(
    db: Session,
    doc: ImpDocumento,
    line: ImpStagingLine,
    scope: IterationScopeIn,
    field_aliases: dict[str, list[str]],
    canonical_fields: dict[str, dict] | None,
) -> bool:
    data = dict(doc.datos_extraidos or {})
    normalized = dict(line.normalized_data or {})
    if not normalized:
        return False

    selected_fields = _document_scope_fields(scope)
    fields_to_apply = selected_fields or list(normalized.keys())
    if "line_items" in fields_to_apply and "total_amount" in normalized and "total_amount" not in fields_to_apply:
        fields_to_apply = [*fields_to_apply, "total_amount"]
    changed = False
    for field in fields_to_apply:
        if field in normalized and data.get(field) != normalized[field]:
            data[field] = normalized[field]
            changed = True
    if not changed:
        return False

    _, projection = build_document_projection(
        data,
        doc_type=doc.tipo_documento_detectado,
        source_format=doc.tipo_archivo,
        field_aliases=field_aliases,
        canonical_fields=canonical_fields,
    )
    doc.datos_extraidos = data
    for key, value in projection.items():
        setattr(doc, key, value)
    db.flush()
    return True


def _normalize_for_diff(value):
    if isinstance(value, dict):
        return {
            str(key): _normalize_for_diff(item)
            for key, item in sorted(value.items(), key=lambda entry: str(entry[0]))
        }
    if isinstance(value, list):
        return [_normalize_for_diff(item) for item in value]
    if isinstance(value, str):
        return value.strip()
    return value


def get_last_iteration(db: Session, documento_id: UUID) -> ImpIteration | None:
    return db.scalars(
        select(ImpIteration)
        .where(ImpIteration.documento_id == documento_id)
        .order_by(ImpIteration.iteration_num.desc())
        .limit(1)
    ).first()


def create_iteration(db: Session, data: dict) -> ImpIteration:
    obj = ImpIteration(**data)
    db.add(obj)
    db.flush()
    return obj


def close_iteration(
    db: Session,
    iteration: ImpIteration,
    *,
    lines_attempted: int,
    lines_imported: int,
    lines_errored: int,
    lines_skipped: int,
    improvement: bool,
    remaining: StagingLineSummary,
) -> str:
    """Calcula estado final y cierra la iteración."""
    if remaining.resolvable == 0:
        estado = "DONE"
    elif not improvement:
        estado = "NO_IMPROVEMENT"
    else:
        estado = "PARTIAL"

    iteration.lines_attempted = lines_attempted
    iteration.lines_imported = lines_imported
    iteration.lines_errored = lines_errored
    iteration.lines_skipped = lines_skipped
    iteration.improvement = improvement
    iteration.estado = estado
    iteration.completed_at = datetime.datetime.now(datetime.UTC)
    db.flush()
    return estado


def log_line_error(
    db: Session,
    staging_line: ImpStagingLine,
    iteration: ImpIteration,
    error_code: str,
    error_detail: str,
    field_name: str | None = None,
) -> None:
    log = ImpLineErrorLog(
        staging_line_id=staging_line.id,
        iteration_id=iteration.id,
        error_code=error_code,
        error_detail=error_detail,
        field_name=field_name,
    )
    db.add(log)


def update_staging_line_estado(
    db: Session,
    line: ImpStagingLine,
    estado: str,
    *,
    error_code: str | None = None,
    error_detail: str | None = None,
    normalized_data: dict | None = None,
    target_table: str | None = None,
    target_id: UUID | None = None,
    campos_revision: list[str] | None = None,
) -> None:
    line.estado = estado
    if error_code is not None:
        line.error_code = error_code
        line.error_detail = error_detail
    elif estado == "IMPORTED":
        line.error_code = None
        line.error_detail = None
        line.imported_at = datetime.datetime.now(datetime.UTC)
    if normalized_data is not None:
        line.normalized_data = normalized_data
    if target_table is not None:
        line.target_table = target_table
    if target_id is not None:
        line.target_id = target_id
    if campos_revision is not None:
        line.campos_revision = campos_revision
    db.flush()


# ─── Normalización parcial de campos ─────────────────────────────────────


def normalize_line_fields(
    line: ImpStagingLine,
    campos_revision: list[str] | None,
    field_aliases: dict[str, list[str]],
    canonical_fields: dict[str, dict] | None = None,
) -> dict:
    """
    Normaliza la línea aplicando aliases de campos.
    Si campos_revision está definido, solo renormaliza esos campos
    y preserva el resto del normalized_data existente.
    """
    from ..document_fields import get_data_value, safe_floatish

    raw = line.raw_data or {}

    if campos_revision and line.normalized_data:
        result = dict(line.normalized_data)
    else:
        result = {}

    fields_to_process = campos_revision or list(field_aliases.keys())

    canonical_meta = canonical_fields or {}

    for campo in fields_to_process:
        aliases = field_aliases.get(campo, [campo])
        raw_value = get_data_value(raw, *aliases)
        field_type = str((canonical_meta.get(campo) or {}).get("type") or "").strip().lower()

        if field_type == "numeric":
            parsed = safe_floatish(raw_value)
            if parsed is not None:
                result[campo] = parsed
        elif field_type == "date":
            if raw_value:
                s = str(raw_value).strip()[:10]
                import re

                if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                    result[campo] = s
        elif field_type == "list":
            if isinstance(raw_value, list):
                result[campo] = raw_value
        else:
            if raw_value is not None:
                cleaned = str(raw_value).strip()
                if cleaned:
                    result[campo] = cleaned

    return result


# ─── Validación determinista ──────────────────────────────────────────────


def validate_normalized_line(
    normalized: dict,
    *,
    error_affected_fields: dict[str, list[str]] | None = None,
) -> list[dict]:
    """
    Validación determinista de una línea normalizada.
    Retorna lista de errores [{code, detail, field}] o lista vacía si es válida.
    Nunca usa IA — solo reglas de negocio deterministas.

    error_affected_fields: mapa {error_code: [campos]} cargado desde imp_error_code.
    Si es None, usa los defaults hardcodeados como fallback.
    """
    import re

    # Sin reglas configuradas desde BD no se aplica ninguna validación.
    # La fuente de verdad es imp_error_code.
    if not error_affected_fields:
        return []

    efa = error_affected_fields
    errors = []

    for amount_field in efa.get("MISSING_AMOUNT", ["total_amount"]):
        value = normalized.get(amount_field)
        if value is None:
            errors.append(
                {
                    "code": "MISSING_AMOUNT",
                    "detail": f"El campo {amount_field} es obligatorio y no se encontró.",
                    "field": amount_field,
                }
            )
        elif isinstance(value, (int, float)) and float(value) <= 0:
            errors.append(
                {
                    "code": "MISSING_AMOUNT",
                    "detail": f"El monto {amount_field} debe ser mayor que cero (valor: {value}).",
                    "field": amount_field,
                }
            )

    for date_field in efa.get("INVALID_DATE", ["issue_date"]):
        date_value = normalized.get(date_field)
        if date_value is not None:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_value)):
                errors.append(
                    {
                        "code": "INVALID_DATE",
                        "detail": f"La fecha '{date_value}' en {date_field} no tiene formato YYYY-MM-DD.",
                        "field": date_field,
                    }
                )

    return errors


# ─── Análisis de campos para revisión selectiva ───────────────────────────


def build_field_analysis(
    lines: list[ImpStagingLine],
    error_affected_fields: dict[str, list[str]],
) -> dict:
    """
    Analiza qué campos tienen problemas en las líneas dadas.
    Retorna stats por campo para mostrar en el UI antes de elegir qué reprocesar.
    """
    field_stats: dict[str, dict] = {}

    for line in lines:
        data = line.normalized_data or line.raw_data or {}
        for field_key, field_value in data.items():
            if str(field_key).startswith("_"):
                continue
            if field_key not in field_stats:
                field_stats[field_key] = {
                    "field": field_key,
                    "total_lines": 0,
                    "filled": 0,
                    "empty": 0,
                    "with_error": 0,
                    "sample_values": [],
                    "related_error_codes": [],
                }
            stat = field_stats[field_key]
            stat["total_lines"] += 1

            value_is_empty = (
                field_value is None
                or (isinstance(field_value, str) and not field_value.strip())
                or field_value == 0
            )
            if value_is_empty:
                stat["empty"] += 1
            else:
                stat["filled"] += 1
                sample = str(field_value)[:60]
                if sample not in stat["sample_values"] and len(stat["sample_values"]) < 3:
                    stat["sample_values"].append(sample)

            if line.error_code:
                affected = error_affected_fields.get(line.error_code, [])
                if field_key in affected:
                    stat["with_error"] += 1
                    if line.error_code not in stat["related_error_codes"]:
                        stat["related_error_codes"].append(line.error_code)

    # Calcular fill_rate y suggested_for_reprocess
    result_fields = []
    for stat in field_stats.values():
        total = stat["total_lines"]
        stat["fill_rate"] = round(stat["filled"] / total, 2) if total > 0 else 0.0
        stat["suggested_for_reprocess"] = stat["empty"] > 0 or stat["with_error"] > 0
        result_fields.append(stat)

    result_fields.sort(key=lambda s: (-(s["with_error"] + s["empty"]), s["field"]))

    suggested = [s["field"] for s in result_fields if s["suggested_for_reprocess"]]

    error_summary: dict[str, int] = {}
    for line in lines:
        if line.error_code:
            error_summary[line.error_code] = error_summary.get(line.error_code, 0) + 1

    return {
        "total_lines_analyzed": len(lines),
        "fields": result_fields,
        "suggested_reprocess_fields": suggested,
        "error_summary": error_summary,
    }


def load_error_affected_fields(db: Session) -> dict[str, list[str]]:
    """Carga desde BD el mapa {error_code: [campos afectados]}.

    Fuente de verdad: imp_error_code. Si la BD falla retorna {} y registra el error.
    """
    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text("SELECT code, affected_fields FROM imp_error_code WHERE active = TRUE")
        ).fetchall()
        return {str(row[0]): list(row[1] or []) for row in rows}
    except Exception as exc:
        logger.error("No se pudieron cargar error_affected_fields desde BD: %s", exc)
        return {}


# ─── Punto de entrada principal ───────────────────────────────────────────


def run_iteration(
    db: Session,
    doc: ImpDocumento,
    tenant_id: UUID,
    user_id: str,
    scope: IterationScopeIn,
    field_aliases: dict[str, list[str]],
    canonical_fields: dict[str, dict] | None = None,
) -> IterationResultOut:
    """
    Ejecuta una iteración de importación sobre el subconjunto de líneas definido por scope.
    Solo procesa las líneas que corresponden al scope.
    Solo modifica los campos indicados por scope.filter_campos (o todos si está vacío).
    Preserva todo lo que ya estaba correcto.
    """
    from .. import crud

    prev = get_last_iteration(db, doc.id)
    iteration = create_iteration(
        db,
        {
            "tenant_id": tenant_id,
            "documento_id": doc.id,
            "iteration_num": (prev.iteration_num + 1) if prev else 1,
            "scope": scope.mode,
            "scope_filter": scope.model_dump() if scope.mode == "SELECTIVE" else None,
            "prev_iteration_id": prev.id if prev else None,
            "llm_model": getattr(doc, "llm_model", None),
            "snapshot_id": getattr(doc, "recipe_snapshot_id", None),
            "initiated_by": user_id,
            "estado": "RUNNING",
        },
    )

    lines = fetch_lines_for_scope(db, doc.id, scope)
    campos_revision = scope.filter_campos or None
    document_scope_fields = _document_scope_fields(scope)
    error_affected_fields = load_error_affected_fields(db)

    attempted = 0
    imported = 0
    errored = 0
    skipped = 0
    content_changed = False

    for line in lines:
        attempted += 1
        previous_state = line.estado
        previous_error_code = line.error_code
        previous_normalized = _normalize_for_diff(line.normalized_data)
        try:
            normalized = normalize_line_fields(
                line,
                campos_revision,
                field_aliases,
                canonical_fields=canonical_fields,
            )
            if _is_document_scope_line(line) and document_scope_fields:
                normalized.update(
                    _reextract_document_scope_fields(
                        db,
                        doc,
                        document_scope_fields,
                        canonical_fields,
                    )
                )
            errors = validate_normalized_line(
                normalized, error_affected_fields=error_affected_fields
            )

            if errors:
                first_error = errors[0]
                update_staging_line_estado(
                    db,
                    line,
                    "INVALID",
                    error_code=first_error["code"],
                    error_detail=first_error["detail"],
                    normalized_data=normalized,
                )
                for err in errors:
                    log_line_error(
                        db, line, iteration, err["code"], err["detail"], err.get("field")
                    )
                errored += 1
            else:
                update_staging_line_estado(
                    db,
                    line,
                    "VALID",
                    normalized_data=normalized,
                    error_code=None,
                )
                imported += 1

            if (
                previous_state != line.estado
                or previous_error_code != line.error_code
                or previous_normalized != _normalize_for_diff(line.normalized_data)
            ):
                content_changed = True

        except Exception as exc:
            logger.error("Error processing line %s: %s", line.line_number, exc)
            update_staging_line_estado(
                db,
                line,
                "INVALID",
                error_code="SYSTEM_ERROR",
                error_detail=str(exc),
            )
            log_line_error(db, line, iteration, "SYSTEM_ERROR", str(exc))
            errored += 1
            if (
                previous_state != line.estado
                or previous_error_code != line.error_code
                or previous_normalized != _normalize_for_diff(line.normalized_data)
            ):
                content_changed = True

    document_line = next((line for line in lines if _is_document_scope_line(line)), None)
    if document_line and imported > 0:
        doc_changed = _sync_document_scope_line_to_document(
            db,
            doc,
            document_line,
            scope,
            field_aliases,
            canonical_fields,
        )
        content_changed = content_changed or doc_changed

    improvement = False
    if prev:
        improvement = (
            (imported > prev.lines_imported)
            or (errored < prev.lines_errored)
            or content_changed
        )
    elif imported > 0:
        improvement = True

    remaining = count_staging_lines(db, doc.id)
    estado_final = close_iteration(
        db,
        iteration,
        lines_attempted=attempted,
        lines_imported=imported,
        lines_errored=errored,
        lines_skipped=skipped,
        improvement=improvement,
        remaining=remaining,
    )

    crud.add_log(
        db,
        doc.id,
        "ITERATE",
        user_id,
        {
            "iteration_num": iteration.iteration_num,
            "scope": scope.mode,
            "attempted": attempted,
            "imported": imported,
            "errored": errored,
            "estado": estado_final,
            "improvement": improvement,
        },
    )

    message_parts = [f"Iteración {iteration.iteration_num}: {imported} líneas válidas"]
    if errored:
        message_parts.append(f"{errored} con error")
    if remaining.resolvable:
        message_parts.append(f"{remaining.resolvable} pendientes")
    if not improvement and prev:
        message_parts.append("Sin mejora — se requiere intervención manual")

    return IterationResultOut(
        iteration_id=iteration.id,
        iteration_num=iteration.iteration_num,
        estado=estado_final,
        improvement=improvement,
        lines_attempted=attempted,
        lines_imported=imported,
        lines_errored=errored,
        lines_skipped=skipped,
        remaining=remaining,
        can_retry=(estado_final == "PARTIAL"),
        message=". ".join(message_parts),
    )
