"""Pre-classifier: resolve doc_type BEFORE calling the AI when possible.

Layers (evaluated in order):
  L1 — Snapshot cache   (structured docs only) — skip AI entirely, full result cached
  L2 — Filename pattern (all types)            — pre-set doc_type, AI still extracts fields
  L3 — Header mapping   (structured docs only) — pre-set doc_type from confirmed field sets
  L4 — Vendor/RUC       (all types)            — vendor hint from confirmed OCR text
  L5 — Template match   (all types)            — extract fields via regex/label_search,
                                                  skips AI entirely if confidence >= threshold

Returns PreClassResult or None (caller must invoke AI).

All thresholds are loaded from imp_config (module='pre_classifier').
All patterns are loaded from imp_filename_pattern, imp_header_doc_type, imp_doc_type_template.
Nothing is hardcoded.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

logger = logging.getLogger("importador.pre_classifier")

_CACHE_TTL = 300.0  # fallback hasta que se cargue desde DB
_cache: dict[str, tuple[float, Any]] = {}


def _get_cache_ttl() -> float:
    """TTL del caché, configurable desde imp_config(module='cache_ttls')."""
    try:
        from app.modules.importador.runtime_config import load_cache_ttls

        return float(load_cache_ttls(db=None).get("pre_classifier_ttl_seconds") or _CACHE_TTL)
    except Exception:
        return _CACHE_TTL


# ── Result ─────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class PreClassResult:
    doc_type: str
    confidence: float
    layer: (
        str  # "snapshot_cache" | "filename_pattern" | "header_mapping" | "vendor_ruc" | "template"
    )
    reasoning: str
    skip_ai: bool = False  # True for snapshot_cache (structured) and template (high confidence)
    cached_analysis: dict | None = None  # Populated when skip_ai=True (L1) or template result (L5)
    matched_canonicals: list[str] = dc_field(default_factory=list)
    extracted_fields: dict | None = None  # Populated by L5 with template-extracted fields


# ── Config loading ──────────────────────────────────────────────────────────────


def load_pre_classifier_config(db: Any) -> dict[str, float]:
    """Load thresholds from runtime config / imp_config (module='pre_classifier')."""
    entry = _cache.get("config")
    if entry and (time.monotonic() - entry[0]) < _get_cache_ttl():
        return entry[1]  # type: ignore[return-value]

    try:
        from app.modules.importador.runtime_config import load_pre_classifier_runtime_config

        cfg = load_pre_classifier_runtime_config(db)
        _cache["config"] = (time.monotonic(), cfg)
        return cfg
    except Exception as exc:
        logger.debug("Could not load pre_classifier config from runtime config: %s", exc)
        fallback = {
            "min_header_confirmations": 2.0,
            "filename_min_confidence": 0.70,
            "header_coverage_min_ratio": 0.50,
            "structured_skip_threshold": 0.75,
            "ocr_weird_ratio_max": 0.15,
        }
        _cache["config"] = (time.monotonic(), fallback)
        return fallback


def _load_filename_patterns(db: Any) -> list[dict]:
    """Load active filename patterns from imp_filename_pattern, cached 5 min."""
    entry = _cache.get("filename_patterns")
    if entry and (time.monotonic() - entry[0]) < _get_cache_ttl():
        return entry[1]  # type: ignore[return-value]

    if db is None:
        _cache["filename_patterns"] = (time.monotonic(), [])
        return []

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT pattern, doc_type, base_confidence, confirmed_count, failed_count "
                "FROM imp_filename_pattern "
                "WHERE active = TRUE "
                "ORDER BY base_confidence DESC, confirmed_count DESC"
            )
        ).fetchall()
        patterns = [
            {
                "pattern": str(r[0]),
                "doc_type": str(r[1]).upper(),
                "base_confidence": float(r[2]),
                "confirmed_count": int(r[3]),
                "failed_count": int(r[4]),
            }
            for r in rows
        ]
        _cache["filename_patterns"] = (time.monotonic(), patterns)
        return patterns
    except Exception as exc:
        logger.debug("Could not load filename patterns: %s", exc)
        _cache["filename_patterns"] = (time.monotonic(), [])
        return []


def _load_header_doc_types(db: Any, min_confirmations: int) -> list[dict]:
    """Load confirmed header→doc_type mappings, cached 5 min."""
    entry = _cache.get("header_doc_types")
    if entry and (time.monotonic() - entry[0]) < _get_cache_ttl():
        return entry[1]  # type: ignore[return-value]

    if db is None:
        _cache["header_doc_types"] = (time.monotonic(), [])
        return []

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT canonical_fields_hash, doc_type, confirmed_count, failed_count "
                "FROM imp_header_doc_type "
                "WHERE active = TRUE AND confirmed_count >= :min_c "
                "ORDER BY confirmed_count DESC"
            ),
            {"min_c": min_confirmations},
        ).fetchall()
        mappings = [
            {
                "hash": str(r[0]),
                "doc_type": str(r[1]).upper(),
                "confirmed_count": int(r[2]),
                "failed_count": int(r[3]),
            }
            for r in rows
        ]
        _cache["header_doc_types"] = (time.monotonic(), mappings)
        return mappings
    except Exception as exc:
        logger.debug("Could not load header doc types: %s", exc)
        _cache["header_doc_types"] = (time.monotonic(), [])
        return []


# ── Main entry point ────────────────────────────────────────────────────────────


def classify_before_ai(
    *,
    db: Any,
    filename: str,
    headers_norm: list[str],
    field_aliases: dict[str, list[str]],
    cached_analysis: dict | None,
    config: dict[str, float] | None = None,
    ocr_text: str | None = None,
    tenant_id: Any = None,
    tipo_archivo: str | None = None,
) -> PreClassResult | None:
    """
    Try to classify without calling the AI.
    Returns PreClassResult or None (let AI handle it).

    - L1: Snapshot cache  → skip_ai=True, full cached result returned
    - L2: Filename match  → skip_ai=False, doc_type hint for AI
    - L3: Header mapping  → skip_ai=False, doc_type hint for AI
      (for structured docs, if confidence >= structured_skip_threshold → skip AI classification)
    - L4: Vendor/RUC     → skip_ai=False, snapshot hint via proveedor conocido
    - L5: Template match → skip_ai=True if confidence >= min_confidence_para_skip,
      otherwise skip_ai=False but extracted_fields populated as AI hint
    """
    cfg = config or load_pre_classifier_config(db)
    filename_min_conf = cfg.get("filename_min_confidence", 0.70)
    min_header_conf = int(cfg.get("min_header_confirmations", 2))

    # L1: Snapshot cache (already resolved by auto_recipe before this call)
    if cached_analysis:
        doc_type = str(cached_analysis.get("doc_type") or "").upper().strip()
        confidence = float(cached_analysis.get("confidence") or 0.0)
        if doc_type and confidence > 0:
            return PreClassResult(
                doc_type=doc_type,
                confidence=confidence,
                layer="snapshot_cache",
                reasoning="Exact header fingerprint from previously confirmed document",
                skip_ai=True,
                cached_analysis=cached_analysis,
            )

    # L2: Filename pattern
    patterns = _load_filename_patterns(db)
    stem = _normalize_filename_stem(filename)
    if stem and not _is_uuid_like(stem):
        for pat in patterns:
            try:
                if re.search(pat["pattern"], stem, re.IGNORECASE):
                    conf = _effective_confidence(
                        pat["base_confidence"],
                        pat["confirmed_count"],
                        pat["failed_count"],
                    )
                    if conf >= filename_min_conf:
                        return PreClassResult(
                            doc_type=pat["doc_type"],
                            confidence=conf,
                            layer="filename_pattern",
                            reasoning=(
                                f"Filename '{stem}' matches pattern '{pat['pattern']}' "
                                f"(confirmed={pat['confirmed_count']}, "
                                f"failed={pat['failed_count']})"
                            ),
                            skip_ai=False,
                        )
            except re.error:
                logger.debug("Invalid regex in imp_filename_pattern: %s", pat["pattern"])
                continue

    # L3: Header canonical field coverage
    if headers_norm and field_aliases:
        reverse_map = _build_reverse_alias_map(field_aliases)
        matched = _match_headers_to_canonical(headers_norm, reverse_map)
        if matched and headers_norm:
            coverage = len(matched) / len(headers_norm)
            min_coverage = cfg.get("header_coverage_min_ratio", 0.50)
            if coverage >= min_coverage:
                fhash = _canonical_fields_hash(sorted(matched))
                mappings = _load_header_doc_types(db, min_header_conf)
                for m in mappings:
                    if m["hash"] == fhash:
                        conf = _effective_confidence(0.75, m["confirmed_count"], m["failed_count"])
                        return PreClassResult(
                            doc_type=m["doc_type"],
                            confidence=conf,
                            layer="header_mapping",
                            reasoning=(
                                f"Headers matched canonical fields {sorted(matched)} "
                                f"→ {m['doc_type']} "
                                f"(confirmed={m['confirmed_count']})"
                            ),
                            skip_ai=False,
                            matched_canonicals=sorted(matched),
                        )

    # L4: Vendor/RUC — buscar proveedor conocido en texto OCR
    if ocr_text and tenant_id is not None:
        ruc = _extract_ruc_from_text(ocr_text)
        if ruc:
            vendor_snaps = _load_vendor_snapshots(db, tenant_id)
            for vs in vendor_snaps:
                if vs["ruc"] == ruc and vs["confirmed_count"] >= 2:
                    return PreClassResult(
                        doc_type="OTHER",  # El tipo real lo resuelve la IA con el snapshot
                        confidence=0.0,
                        layer="vendor_ruc",
                        reasoning=f"RUC {ruc} matches vendor snapshot (confirmed={vs['confirmed_count']})",
                        skip_ai=False,
                        cached_analysis={"vendor_snapshot_id": vs["snapshot_id"], "ruc": ruc},
                    )

    # L5: Template match — extracción por regex/label_search sin llamar a AI
    if ocr_text and tenant_id is not None:
        templates = _load_doc_type_templates(db, tenant_id)
        for tmpl in templates:
            if not _template_matches_activation(tmpl, filename, ocr_text, tipo_archivo):
                continue

            extracted_fields, confidence = _run_template_extraction(tmpl, ocr_text)
            min_skip = float(tmpl.get("min_confidence_para_skip") or 0.80)

            if confidence <= 0.0:
                # Campos requeridos faltaron → template no aplica
                continue

            skip = confidence >= min_skip
            layer_name = "template"
            reasoning = (
                f"Template '{tmpl['nombre']}' ({tmpl['doc_type']}) "
                f"extrajo {len([v for v in extracted_fields.values() if v is not None])} campos "
                f"con confianza {confidence:.2f}"
                + (" — skip_ai=True" if skip else " — AI usará como hint")
            )
            logger.debug(reasoning)

            # Actualizar stats de uso (best-effort, no bloquea)
            _increment_template_usage(db, tmpl["id"], exitoso=skip)

            # Cuando skip_ai=True: cached_analysis simula resultado AI completo
            cached = None
            if skip:
                cached = {
                    "doc_type": tmpl["doc_type"],
                    "confidence": confidence,
                    "fields": extracted_fields,
                    "is_table": False,
                    "columns": [],
                    "reasoning": reasoning,
                    "model_used": f"template/{tmpl['id'][:8]}",
                    "raw_response": "",
                    "prompt_sent": "",
                }

            return PreClassResult(
                doc_type=tmpl["doc_type"],
                confidence=confidence,
                layer=layer_name,
                reasoning=reasoning,
                skip_ai=skip,
                cached_analysis=cached,
                extracted_fields=extracted_fields,
            )

    return None


# ── Helpers ─────────────────────────────────────────────────────────────────────


def _effective_confidence(
    base: float,
    confirmed_count: int,
    failed_count: int,
) -> float:
    """Blend seed confidence with learned ratio once enough data accumulates."""
    total = confirmed_count + failed_count
    if total < 3:
        return float(base)
    ratio = confirmed_count / total
    weight = min(1.0, total / 20.0)  # Full weight at 20+ samples
    return round(float(base) * (1.0 - weight) + ratio * weight, 3)


def _normalize_filename_stem(filename: str) -> str:
    """Extract meaningful part of filename, strip dates/UUIDs/numbers."""
    stem = Path(filename).stem
    # Strip accents
    nfd = unicodedata.normalize("NFD", stem)
    stem = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    stem = stem.lower()
    try:
        from app.modules.importador.runtime_config import load_filename_normalization_config

        cfg = load_filename_normalization_config(None)
    except Exception:
        cfg = {
            "uuid_patterns": [r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"],
            "date_patterns": [r"\b\d{4}[-_]\d{2}[-_]\d{2}\b", r"\b\d{2}[-_]\d{2}[-_]\d{4}\b"],
            "long_number_patterns": [r"\b\d{4,}\b"],
            "separator_patterns": [r"[_\-\.]+"],
        }
    for pattern in cfg.get("uuid_patterns") or []:
        stem = re.sub(str(pattern), " ", stem)
    for pattern in cfg.get("date_patterns") or []:
        stem = re.sub(str(pattern), " ", stem)
    for pattern in cfg.get("long_number_patterns") or []:
        stem = re.sub(str(pattern), " ", stem)
    for pattern in cfg.get("separator_patterns") or []:
        stem = re.sub(str(pattern), " ", stem)
    return " ".join(stem.split()).strip()


def _is_uuid_like(stem: str) -> bool:
    """True if stem is mostly hex digits — not a meaningful descriptive name."""
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


def _match_headers_to_canonical(
    headers_norm: list[str],
    reverse_map: dict[str, str],
) -> set[str]:
    matched: set[str] = set()
    for h in headers_norm:
        canonical = reverse_map.get(h.strip().lower())
        if canonical:
            matched.add(canonical)
    return matched


def _extract_ruc_from_text(text: str) -> str | None:
    """Extrae el primer RUC/NIF/CUIT encontrado en el texto OCR.

    Soporta formatos comunes: RUC peruano (11 dígitos), NIF español (9 chars),
    CUIT argentino (XX-XXXXXXXX-X). Devuelve solo dígitos del match.
    """
    if not text:
        return None
    # Patrones comunes de identificación fiscal (prefijados por keywords)
    patterns = [
        r"(?:R\.?U\.?C\.?|RUC|NIF|CIF|CUIT|CUIL|RFC)\s*[:\-#]?\s*([0-9][\d\-]{6,19})",
        r"\b(20\d{9}|10\d{9})\b",  # RUC peruano: empieza por 20 (empresa) o 10 (persona)
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:3000], re.IGNORECASE)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if 8 <= len(digits) <= 15:
                return digits
    return None


def _extract_ruc_from_text(text: str) -> str | None:
    """Extrae el primer identificador fiscal configurado encontrado en el OCR."""
    if not text:
        return None
    try:
        from app.modules.importador.runtime_config import load_tax_id_patterns_config

        cfg = load_tax_id_patterns_config(None)
    except Exception:
        cfg = {
            "match_patterns": [
                r"(?:R\.?U\.?C\.?|RUC|NIF|CIF|CUIT|CUIL|RFC)\s*[:\-#]?\s*([0-9][\d\-]{6,19})",
                r"\b(20\d{9}|10\d{9})\b",
            ],
            "scan_max_chars": 3000,
            "min_digits": 8,
            "max_digits": 15,
        }

    patterns = [
        str(pattern) for pattern in (cfg.get("match_patterns") or []) if str(pattern).strip()
    ]
    scan_max_chars = int(cfg.get("scan_max_chars") or 3000)
    min_digits = int(cfg.get("min_digits") or 8)
    max_digits = int(cfg.get("max_digits") or 15)
    for pattern in patterns:
        match = re.search(pattern, text[:scan_max_chars], re.IGNORECASE)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if min_digits <= len(digits) <= max_digits:
                return digits
    return None


def _load_vendor_snapshots(db: Any, tenant_id: Any) -> list[dict]:
    """Carga snapshots de proveedores activos para el tenant, cacheados 5 min."""
    cache_key = f"vendor_snapshots:{tenant_id}"
    entry = _cache.get(cache_key)
    if entry and (time.monotonic() - entry[0]) < _get_cache_ttl():
        return entry[1]  # type: ignore[return-value]

    if db is None:
        return []
    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT ruc, vendor_norm, recipe_snapshot_id, confirmed_count "
                "FROM imp_vendor_snapshot "
                "WHERE tenant_id = :tid AND active = TRUE "
                "ORDER BY confirmed_count DESC"
            ),
            {"tid": str(tenant_id)},
        ).fetchall()
        result = [
            {
                "ruc": str(r[0]) if r[0] else None,
                "vendor_norm": str(r[1]) if r[1] else None,
                "snapshot_id": str(r[2]),
                "confirmed_count": int(r[3]),
            }
            for r in rows
        ]
        _cache[cache_key] = (time.monotonic(), result)
        return result
    except Exception as exc:
        logger.debug("Could not load vendor snapshots: %s", exc)
        _cache[cache_key] = (time.monotonic(), [])
        return []


def _load_doc_type_templates(db: Any, tenant_id: Any) -> list[dict]:
    """Carga templates de extracción activos para el tenant + globales, cacheados.

    Los templates se ordenan por prioridad DESC: los del tenant sobreescriben
    los globales. Los globales (tenant_id IS NULL) siempre se incluyen.
    """
    cache_key = f"doc_type_templates:{tenant_id}"
    entry = _cache.get(cache_key)
    if entry and (time.monotonic() - entry[0]) < _get_cache_ttl():
        return entry[1]  # type: ignore[return-value]

    if db is None:
        _cache[cache_key] = (time.monotonic(), [])
        return []

    try:
        from sqlalchemy import text as sa_text

        rows = db.execute(
            sa_text(
                "SELECT id, tenant_id, doc_type, nombre, prioridad, "
                "       activacion_json, extraccion_json, "
                "       min_confidence_para_skip, campos_requeridos "
                "FROM imp_doc_type_template "
                "WHERE activo = TRUE "
                "  AND (tenant_id = :tid OR tenant_id IS NULL) "
                "ORDER BY "
                "  CASE WHEN tenant_id = :tid THEN 0 ELSE 1 END, "
                "  prioridad DESC"
            ),
            {"tid": str(tenant_id)},
        ).fetchall()
        templates = [
            {
                "id": str(r[0]),
                "tenant_id": str(r[1]) if r[1] else None,
                "doc_type": str(r[2]).upper(),
                "nombre": str(r[3]),
                "prioridad": int(r[4]),
                "activacion_json": r[5] if isinstance(r[5], dict) else {},
                "extraccion_json": r[6] if isinstance(r[6], dict) else {},
                "min_confidence_para_skip": float(r[7]),
                "campos_requeridos": list(r[8]) if r[8] else [],
            }
            for r in rows
        ]
        _cache[cache_key] = (time.monotonic(), templates)
        return templates
    except Exception as exc:
        logger.debug("Could not load doc_type_templates: %s", exc)
        _cache[cache_key] = (time.monotonic(), [])
        return []


def _template_matches_activation(
    template: dict,
    filename: str,
    ocr_text: str | None,
    tipo_archivo: str | None,
) -> bool:
    """Evalúa si las condiciones de activación del template se cumplen (todas AND)."""
    act = template.get("activacion_json") or {}

    # filename_patterns: alguno debe hacer match (OR entre ellos)
    fn_patterns = act.get("filename_patterns")
    if fn_patterns:
        stem = _normalize_filename_stem(filename)
        if not any(re.search(str(p), stem, re.IGNORECASE) for p in fn_patterns if p):
            return False

    # text_keywords: todas deben estar presentes en el texto OCR (AND)
    text_kws = act.get("text_keywords")
    if text_kws:
        if not ocr_text:
            return False
        text_lower = ocr_text[:5000].lower()
        if not all(str(kw).lower() in text_lower for kw in text_kws if kw):
            return False

    # min_text_length: longitud mínima del texto OCR
    min_len = act.get("min_text_length")
    if min_len is not None:
        if not ocr_text or len(ocr_text) < int(min_len):
            return False

    # tipo_archivo: lista de tipos permitidos (PDF, XLSX, etc.)
    allowed_tipos = act.get("tipo_archivo")
    if allowed_tipos and tipo_archivo:
        if str(tipo_archivo).upper() not in [str(t).upper() for t in allowed_tipos]:
            return False

    return True


def _extract_field_value(
    field_cfg: dict,
    ocr_text: str,
) -> Any | None:
    """Extrae el valor de un campo usando regex y/o label_search desde texto OCR."""
    text = ocr_text or ""

    # 1. Intentar con regex (se prueban en orden, primer match gana)
    for pattern in field_cfg.get("regex") or []:
        try:
            m = re.search(str(pattern), text, re.IGNORECASE | re.MULTILINE)
            if m:
                raw = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
                return _coerce_field_value(raw.strip(), field_cfg.get("tipo", "text"))
        except re.error:
            continue

    # 2. Intentar con label_search: busca "LABEL[:]\s*VALUE" en el texto
    for label in field_cfg.get("label_search") or []:
        pattern = rf"(?i)\b{re.escape(str(label))}\s*[:：]\s*([^\n\r,;]{1,80})"
        try:
            m = re.search(pattern, text[:6000])
            if m:
                raw = m.group(1).strip()
                if raw:
                    return _coerce_field_value(raw, field_cfg.get("tipo", "text"))
        except re.error:
            continue

    return None


def _coerce_field_value(raw: str, tipo: str) -> Any:
    """Convierte el string extraído al tipo de dato correcto."""
    if not raw:
        return None

    if tipo == "decimal":
        cleaned = re.sub(r"[^\d.,]", "", raw)
        # Si hay coma y punto, detectar cuál es decimal
        if "," in cleaned and "." in cleaned:
            # Formato europeo: 1.234,56 → 1234.56
            if cleaned.index(",") > cleaned.index("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Puede ser separador de miles o decimal
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    if tipo == "date":
        # Intentar parsear a YYYY-MM-DD
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
            try:
                return _dt.datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue
        return raw[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", raw) else None

    # text: limpiar espacios extra
    return " ".join(raw.split()) or None


def _run_template_extraction(
    template: dict,
    ocr_text: str,
) -> tuple[dict, float]:
    """Ejecuta la extracción del template y retorna (fields, confidence).

    confidence = proporción de campos requeridos extraídos exitosamente.
    Si algún campo requerido falta → confidence = 0.0.
    """
    ext = template.get("extraccion_json") or {}
    fields_cfg: dict = ext.get("fields") or {}
    campos_requeridos: list[str] = template.get("campos_requeridos") or []

    extracted: dict[str, Any] = {}
    for field_name, field_cfg in fields_cfg.items():
        if not isinstance(field_cfg, dict):
            continue
        value = _extract_field_value(field_cfg, ocr_text)
        if value is not None:
            extracted[field_name] = value

    # Verificar campos requeridos
    missing_required = [f for f in campos_requeridos if not extracted.get(f)]
    if missing_required:
        return extracted, 0.0

    # Confianza = % de campos definidos que se extrajeron
    total_fields = len(fields_cfg)
    if total_fields == 0:
        return extracted, 0.5
    extracted_count = sum(1 for v in extracted.values() if v is not None)
    confidence = round(extracted_count / total_fields, 3)
    return extracted, confidence


def _increment_template_usage(db: Any, template_id: str, exitoso: bool) -> None:
    """Incrementa los contadores de uso del template en BD (best-effort)."""
    if db is None:
        return
    try:
        from sqlalchemy import text as sa_text

        db.execute(
            sa_text(
                "UPDATE imp_doc_type_template "
                "SET total_usos = total_usos + 1, "
                "    total_exitosos = total_exitosos + :ex, "
                "    last_used_at = now() "
                "WHERE id = :tid"
            ),
            {"tid": template_id, "ex": 1 if exitoso else 0},
        )
        db.flush()
    except Exception as exc:
        logger.debug("No se pudo actualizar stats de template %s: %s", template_id, exc)


def invalidate_pre_classifier_cache() -> None:
    """Force reload from DB on next call."""
    _cache.clear()
