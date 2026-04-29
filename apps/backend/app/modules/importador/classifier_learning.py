"""Self-feeding learning for the pre-classifier.

Called after every document confirmation. Updates:
  - imp_filename_pattern : confirms/fails existing patterns, promotes new learned ones
  - imp_header_doc_type  : records canonical field set → doc_type mappings
  - imp_field_alias      : records new column name → canonical field aliases (global, tenant_id=NULL)

Design principles:
  - No human intervention needed for common patterns
  - Confidence is computed from history (confirmed / total), not stored as fixed value
  - Only promotes patterns that are safe: no UUIDs, no pure numbers, no long values
  - Field aliases only learned for short, clean header names (not data values)
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.importador.runtime_config import (
    load_learning_config,
    load_snapshot_learning_config,
)

logger = logging.getLogger("importador.classifier_learning")


def _classifier_limits() -> dict[str, int]:
    return load_snapshot_learning_config()


# Palabras reservadas SQL/DDL que nunca deben tratarse como nombres de columna
_SQL_BLOCKLIST: frozenset[str] = frozenset(
    {
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "create",
        "alter",
        "truncate",
        "exec",
        "execute",
        "union",
        "where",
        "from",
        "join",
        "grant",
        "revoke",
        "commit",
        "rollback",
        "declare",
        "cast",
        "into",
        "table",
        "index",
        "view",
        "schema",
        "database",
        "trigger",
        "function",
        "procedure",
        "column",
        "constraint",
        "primary",
        "foreign",
        "key",
        "null",
        "not",
        "and",
        "or",
        "like",
        "exists",
        "having",
        "order",
        "group",
    }
)


def _is_safe_column_name(raw: str) -> bool:
    """True si el nombre de columna es seguro para almacenar en BD.

    Rechaza: SQL keywords, patrones de inyección, strings vacíos,
    demasiado largos/cortos, o con caracteres peligrosos.
    """
    if not raw or not isinstance(raw, str):
        return False
    stripped = raw.strip()
    _limits = _classifier_limits()
    if len(stripped) < _limits["min_alias_len"] or len(stripped) > _limits["max_alias_len"]:
        return False
    # Caracteres de inyección SQL
    if any(c in stripped for c in (";", "--", "/*", "*/", "=", "'", '"', "\\")):
        return False
    # Secuencias de dígitos largas (probablemente un valor, no un nombre de columna)
    if re.search(r"\d{5,}", stripped):
        return False
    # Email o URL
    if "@" in stripped or "://" in stripped:
        return False
    normalized = _normalize_alias(stripped)
    # Tras normalizar, cada palabra no puede ser SQL keyword
    words = set(normalized.split())
    if words & _SQL_BLOCKLIST:
        return False
    # Debe tener al menos una letra
    if not re.search(r"[a-z]", normalized):
        return False
    return True


def learn_from_confirmation(
    db: Session,
    *,
    doc_filename: str,
    doc_type_confirmed: str,
    pre_class_layer: str | None,
    pre_class_doc_type: str | None,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
    tenant_id: UUID | None = None,
) -> dict[str, int]:
    """
    Main learning entry point. Call after user confirms a document.

    Returns counts: {"filename_patterns": N, "header_mappings": N, "aliases": N}
    """
    doc_type = str(doc_type_confirmed or "").upper().strip()
    if not doc_type or doc_type == "OTHER":
        return {"filename_patterns": 0, "header_mappings": 0, "aliases": 0}

    stats = {
        "filename_patterns": _learn_filename(
            db,
            filename=doc_filename,
            confirmed_type=doc_type,
            pre_class_layer=pre_class_layer,
            pre_class_type=str(pre_class_doc_type or "").upper(),
        ),
        "header_mappings": _learn_header_mapping(
            db,
            headers_norm=headers_norm,
            field_aliases=field_aliases,
            confirmed_type=doc_type,
        ),
        "aliases": _learn_column_aliases(
            db,
            headers_norm=headers_norm,
            field_aliases=field_aliases,
        ),
    }

    if any(v > 0 for v in stats.values()):
        logger.info(
            "Classifier learning: file=%s type=%s layer=%s → %s",
            doc_filename,
            doc_type,
            pre_class_layer or "none",
            stats,
        )
    return stats


# ── Filename learning ───────────────────────────────────────────────────────────


def _learn_filename(
    db: Session,
    *,
    filename: str,
    confirmed_type: str,
    pre_class_layer: str | None,
    pre_class_type: str,
) -> int:
    from sqlalchemy import text as sa_text

    updated = 0

    # Update existing pattern counters when filename_pattern layer fired
    if pre_class_layer == "filename_pattern":
        stem = _normalize_stem(filename)
        if stem:
            col = "confirmed_count" if pre_class_type == confirmed_type else "failed_count"
            try:
                result = db.execute(
                    sa_text(
                        f"UPDATE imp_filename_pattern "  # noqa: S608
                        f"SET {col} = {col} + 1, updated_at = now() "
                        f"WHERE active = TRUE AND :stem ~ pattern"
                    ),
                    {"stem": stem},
                )
                updated += result.rowcount or 0
            except Exception as exc:
                logger.debug("Could not update filename pattern counter: %s", exc)

    # Try to promote this filename as a new learned pattern
    stem = _normalize_stem(filename)
    if not stem or _is_uuid_like(stem):
        return updated

    # Use the first meaningful word as the pattern anchor
    words = stem.split()
    anchor = words[0] if words else ""
    _limits = _classifier_limits()
    if len(anchor) < _limits["min_stem_len"] or len(anchor) > _limits["max_stem_len"]:
        return updated

    escaped = re.escape(anchor)
    learning_cfg = load_learning_config(db)
    base_confidence = learning_cfg.get("filename_pattern_base_confidence", 0.65)

    # BLOQUEO PRODUCCION: aprendizaje ML es global (no aislado por tenant).
    # Desactivar hasta añadir columna tenant_id a la migración de imp_filename_pattern.
    if os.getenv("ML_LEARNING_ENABLED", "false") == "true":
        try:
            db.execute(
                sa_text(
                    "INSERT INTO imp_filename_pattern "
                    "    (pattern, doc_type, base_confidence, confirmed_count, source) "
                    "VALUES (:pattern, :doc_type, :base_confidence, 1, 'learned') "
                    "ON CONFLICT (pattern, doc_type) DO UPDATE "
                    "    SET confirmed_count = imp_filename_pattern.confirmed_count + 1, "
                    "        updated_at = now()"
                ),
                {"pattern": escaped, "doc_type": confirmed_type, "base_confidence": base_confidence},
            )
            updated += 1
        except Exception as exc:
            logger.debug("Could not upsert learned filename pattern '%s': %s", anchor, exc)

    return updated


# ── Header → doc_type learning ──────────────────────────────────────────────────


def _learn_header_mapping(
    db: Session,
    *,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
    confirmed_type: str,
) -> int:
    if not headers_norm or not field_aliases:
        return 0

    reverse_map = _build_reverse_alias_map(field_aliases)
    matched = {
        reverse_map[h.strip().lower()] for h in headers_norm if h.strip().lower() in reverse_map
    }
    if not matched:
        return 0

    fhash = _canonical_fields_hash(sorted(matched))
    from sqlalchemy import text as sa_text

    # BLOQUEO PRODUCCION: aprendizaje ML es global (no aislado por tenant).
    # Desactivar hasta añadir columna tenant_id a la migración de imp_header_doc_type.
    if os.getenv("ML_LEARNING_ENABLED", "false") != "true":
        return 0

    try:
        db.execute(
            sa_text(
                "INSERT INTO imp_header_doc_type "
                "    (canonical_fields_hash, canonical_fields, doc_type, confirmed_count) "
                "VALUES (:hash, :fields, :doc_type, 1) "
                "ON CONFLICT (canonical_fields_hash) DO UPDATE "
                "    SET confirmed_count = imp_header_doc_type.confirmed_count + 1, "
                "        updated_at = now()"
            ),
            {
                "hash": fhash,
                "fields": sorted(matched),
                "doc_type": confirmed_type,
            },
        )
        return 1
    except Exception as exc:
        logger.debug("Could not upsert header doc type: %s", exc)
        return 0


# ── Column alias learning ───────────────────────────────────────────────────────


def _learn_column_aliases(
    db: Session,
    *,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
) -> int:
    """Record new global aliases for headers that successfully mapped to canonical fields."""
    if not headers_norm or not field_aliases:
        return 0

    reverse_map = _build_reverse_alias_map(field_aliases)
    known_aliases: set[str] = {
        alias.strip().lower() for aliases in field_aliases.values() for alias in aliases
    }

    from sqlalchemy import text as sa_text

    learned = 0
    for raw_header in headers_norm:
        alias_clean = _normalize_alias(raw_header)
        canonical = reverse_map.get(alias_clean)

        if not canonical:
            continue
        if alias_clean in known_aliases:
            # Already known — just bump last_seen_at
            try:
                db.execute(
                    sa_text(
                        "UPDATE imp_field_alias "
                        "SET confirmed_count = confirmed_count + 1, last_seen_at = now() "
                        "WHERE canonical_field = :c AND alias = :a AND tenant_id IS NULL"
                    ),
                    {"c": canonical, "a": alias_clean},
                )
            except Exception:
                pass
            continue

        _limits = _classifier_limits()
        if (
            len(alias_clean) < _limits["min_alias_len"]
            or len(alias_clean) > _limits["max_alias_len"]
        ):
            continue
        # Skip if looks like a data value (long digit sequences, email-like, etc.)
        if re.search(r"\d{4,}", alias_clean) or "@" in alias_clean:
            continue

        try:
            db.execute(
                sa_text(
                    "INSERT INTO imp_field_alias "
                    "    (tenant_id, canonical_field, alias, priority, source, confirmed_count, last_seen_at) "
                    "VALUES (NULL, :canonical, :alias, 1, 'learned', 1, now()) "
                    "ON CONFLICT (canonical_field, alias) WHERE tenant_id IS NULL DO UPDATE "
                    "    SET confirmed_count = imp_field_alias.confirmed_count + 1, "
                    "        last_seen_at = now()"
                ),
                {"canonical": canonical, "alias": alias_clean},
            )
            known_aliases.add(alias_clean)
            learned += 1
        except Exception as exc:
            logger.debug("Could not learn alias '%s' → %s: %s", alias_clean, canonical, exc)

    return learned


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _normalize_stem(filename: str) -> str:
    stem = Path(filename).stem
    nfd = unicodedata.normalize("NFD", stem)
    stem = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    stem = stem.lower()
    stem = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "", stem)
    stem = re.sub(r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", "", stem)
    stem = re.sub(r"\b\d{2}[-_]\d{2}[-_]\d{4}\b", "", stem)
    stem = re.sub(r"\b\d{4,}\b", "", stem)
    stem = re.sub(r"[_\-\.]+", " ", stem)
    return " ".join(stem.split()).strip()


def _normalize_alias(raw: str) -> str:
    nfd = unicodedata.normalize("NFD", str(raw or ""))
    text = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(text.split()).strip()


def _is_uuid_like(stem: str) -> bool:
    clean = re.sub(r"[^a-f0-9]", "", stem.lower().replace(" ", ""))
    return len(clean) >= 20 and len(clean) / max(len(stem.replace(" ", "")), 1) > 0.65


def _canonical_fields_hash(fields: list[str]) -> str:
    payload = ",".join(sorted({str(f).strip().lower() for f in fields if f}))
    return hashlib.sha256(payload.encode()).hexdigest()


def _build_reverse_alias_map(field_aliases: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for canonical, aliases in field_aliases.items():
        for alias in aliases:
            result[alias.strip().lower()] = canonical
    return result


# ── Vendor → snapshot learning ─────────────────────────────────────────────────


def learn_vendor_snapshot(
    db: Session,
    *,
    ruc: str | None,
    vendor_norm: str | None,
    snapshot_id: UUID,
    tenant_id: UUID,
) -> bool:
    """Asocia un proveedor (RUC y/o nombre normalizado) con un snapshot confirmado.

    Actualiza confirmed_count si ya existe. Devuelve True si hubo cambio.
    """
    from sqlalchemy import text as sa_text

    ruc_clean = str(ruc or "").strip() or None
    vendor_clean = str(vendor_norm or "").strip().lower() or None
    if not ruc_clean and not vendor_clean:
        return False

    try:
        if ruc_clean:
            db.execute(
                sa_text(
                    "INSERT INTO imp_vendor_snapshot "
                    "    (tenant_id, ruc, recipe_snapshot_id, confirmed_count, last_seen_at) "
                    "VALUES (:tid, :ruc, :snap_id, 1, now()) "
                    "ON CONFLICT (tenant_id, ruc) WHERE ruc IS NOT NULL DO UPDATE "
                    "    SET recipe_snapshot_id = EXCLUDED.recipe_snapshot_id, "
                    "        confirmed_count = imp_vendor_snapshot.confirmed_count + 1, "
                    "        last_seen_at = now(), active = TRUE"
                ),
                {"tid": str(tenant_id), "ruc": ruc_clean, "snap_id": str(snapshot_id)},
            )
        if vendor_clean:
            db.execute(
                sa_text(
                    "INSERT INTO imp_vendor_snapshot "
                    "    (tenant_id, vendor_norm, recipe_snapshot_id, confirmed_count, last_seen_at) "
                    "VALUES (:tid, :vendor, :snap_id, 1, now()) "
                    "ON CONFLICT (tenant_id, vendor_norm) WHERE vendor_norm IS NOT NULL DO UPDATE "
                    "    SET recipe_snapshot_id = EXCLUDED.recipe_snapshot_id, "
                    "        confirmed_count = imp_vendor_snapshot.confirmed_count + 1, "
                    "        last_seen_at = now(), active = TRUE"
                ),
                {"tid": str(tenant_id), "vendor": vendor_clean, "snap_id": str(snapshot_id)},
            )
        return True
    except Exception as exc:
        logger.debug("Could not learn vendor snapshot: %s", exc)
        return False


# ── Column candidate discovery ──────────────────────────────────────────────────


def _fuzzy_match_slot(
    col_norm: str,
    canonical_fields: dict[str, dict],
    field_aliases: dict[str, list[str]],
) -> tuple[str, str] | None:
    """Intenta mapear una columna desconocida a un slot estándar por similitud de tokens.

    Compara col_norm contra todos los aliases de los campos que tienen line_item_slot.
    Retorna (slot_name, new_canonical_name) si el score >= 0.5, o None.
    """
    col_tokens = set(col_norm.split())
    if not col_tokens:
        return None

    best_slot: str | None = None
    best_score = 0.0

    for name, cfg in canonical_fields.items():
        slot = cfg.get("line_item_slot")
        if not slot:
            continue
        for alias in field_aliases.get(name, []):
            alias_norm = _normalize_alias(alias)
            alias_tokens = set(alias_norm.split())
            if not alias_tokens:
                continue
            overlap = col_tokens & alias_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(col_tokens), len(alias_tokens))
            if score > best_score:
                best_score = score
                best_slot = slot

    if best_score >= 0.5 and best_slot:
        new_canonical = col_norm.replace(" ", "_")[:50]
        return best_slot, new_canonical
    return None


def learn_column_candidates(
    db: Session,
    *,
    col_names: list[str],
    doc_type: str | None,
    tenant_id: UUID | None,
    field_aliases: dict[str, list[str]],
    canonical_fields: dict[str, dict] | None = None,
) -> int:
    """Registra nombres de columnas desconocidos encontrados en documentos procesados.

    - Columnas ya mapeadas a un campo canónico: bumps confirmed_count en imp_field_alias.
    - Columnas desconocidas pero seguras: upsert en imp_column_candidate para revisión.
    - Columnas que no pasan el filtro de seguridad: descartadas silenciosamente.

    Diseñado para ser llamado en tiempo de procesamiento (no solo en confirmación).
    """
    if not col_names:
        return 0

    from sqlalchemy import text as sa_text

    reverse_map = _build_reverse_alias_map(field_aliases)
    saved = 0

    for raw in col_names:
        if not _is_safe_column_name(raw):
            logger.debug("Column candidate rejected (unsafe): %r", raw)
            continue

        alias_clean = _normalize_alias(raw)
        if not alias_clean:
            continue

        canonical = reverse_map.get(alias_clean)

        if canonical:
            # Ya conocida — bump confirmed_count en imp_field_alias
            try:
                db.execute(sa_text("SAVEPOINT sp_bump"))
                db.execute(
                    sa_text(
                        "UPDATE imp_field_alias "
                        "SET confirmed_count = confirmed_count + 1, last_seen_at = now() "
                        "WHERE canonical_field = :c AND alias = :a AND tenant_id IS NULL"
                    ),
                    {"c": canonical, "a": alias_clean},
                )
                db.execute(sa_text("RELEASE SAVEPOINT sp_bump"))
            except Exception as exc:
                try:
                    db.execute(sa_text("ROLLBACK TO SAVEPOINT sp_bump"))
                except Exception:
                    pass
                logger.debug("Could not bump alias count '%s': %s", alias_clean, exc)
        else:
            # Desconocida — intentar fuzzy match contra slots estándar
            slot_match = (
                _fuzzy_match_slot(alias_clean, canonical_fields, field_aliases)
                if canonical_fields
                else None
            )
            if slot_match:
                slot_name, new_canonical = slot_match
                # Auto-crear canonical field con su slot y alias
                try:
                    db.execute(sa_text("SAVEPOINT sp_auto_canonical"))
                    db.execute(
                        sa_text(
                            "INSERT INTO imp_canonical_field "
                            "    (name, field_type, line_item_slot, label, sort_order) "
                            "VALUES (:name, 'text', :slot, :label, 0) "
                            "ON CONFLICT (name) DO NOTHING"
                        ),
                        {
                            "name": new_canonical,
                            "slot": slot_name,
                            "label": raw[:100],
                        },
                    )
                    db.execute(
                        sa_text(
                            "INSERT INTO imp_field_alias "
                            "    (canonical_field, alias, active, priority, source) "
                            "VALUES (:canonical, :alias, TRUE, 5, 'auto_learned') "
                            "ON CONFLICT DO NOTHING"
                        ),
                        {"canonical": new_canonical, "alias": alias_clean},
                    )
                    db.execute(sa_text("RELEASE SAVEPOINT sp_auto_canonical"))
                    saved += 1
                    logger.info(
                        "Auto-created canonical field '%s' → slot '%s' for alias '%s'",
                        new_canonical,
                        slot_name,
                        alias_clean,
                    )
                except Exception as exc:
                    try:
                        db.execute(sa_text("ROLLBACK TO SAVEPOINT sp_auto_canonical"))
                    except Exception:
                        pass
                    logger.debug(
                        "Could not auto-create canonical field '%s': %s", new_canonical, exc
                    )
            else:
                # Sin match de slot — guardar en imp_column_candidate para revisión manual
                try:
                    db.execute(sa_text("SAVEPOINT sp_candidate"))
                    db.execute(
                        sa_text(
                            "INSERT INTO imp_column_candidate "
                            "    (alias, alias_norm, doc_type, tenant_id) "
                            "VALUES (:alias, :alias_norm, :doc_type, :tenant_id) "
                            "ON CONFLICT (alias_norm, tenant_id) WHERE tenant_id IS NULL DO UPDATE "
                            "    SET seen_count = imp_column_candidate.seen_count + 1, "
                            "        last_seen_at = now(), "
                            "        doc_type = COALESCE(EXCLUDED.doc_type, imp_column_candidate.doc_type) "
                            "ON CONFLICT (alias_norm, tenant_id) WHERE tenant_id IS NOT NULL DO UPDATE "
                            "    SET seen_count = imp_column_candidate.seen_count + 1, "
                            "        last_seen_at = now(), "
                            "        doc_type = COALESCE(EXCLUDED.doc_type, imp_column_candidate.doc_type)"
                        ),
                        {
                            "alias": raw[:100],
                            "alias_norm": alias_clean[:100],
                            "doc_type": (doc_type or "")[:50] or None,
                            "tenant_id": str(tenant_id) if tenant_id else None,
                        },
                    )
                    db.execute(sa_text("RELEASE SAVEPOINT sp_candidate"))
                    saved += 1
                except Exception as exc:
                    try:
                        db.execute(sa_text("ROLLBACK TO SAVEPOINT sp_candidate"))
                    except Exception:
                        pass
                    logger.debug("Could not save column candidate '%s': %s", alias_clean, exc)

    if saved > 0:
        try:
            db.commit()
            # Invalidar caché para que el próximo procesamiento use los nuevos campos
            from .field_alias_loader import invalidate_cache

            invalidate_cache()
        except Exception as exc:
            logger.debug("Could not commit column candidates: %s", exc)

    return saved
