from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.models.importador import ImpRoutingProfile, ImpRoutingRule
from app.models.tenant import Tenant
from app.modules.importador.runtime_config import (
    load_routing_fallback_profiles_config,
    load_routing_fallback_rules_config,
)
from app.services.field_config import resolve_sector_code

logger = logging.getLogger("importador.document_routing_config")

SaveDestination = Literal["recipe", "expense", "supplier_invoice"]
RuleSourceKind = Literal["doc_type", "category"]
RoutingMatchScope = Literal["destination_override", "tenant", "sector", "system", "fallback"]

_CACHE_TTL = 300.0
_profiles_cache: tuple[float, dict[str, RoutingProfileConfig]] | None = None
_rules_cache: dict[str, tuple[float, list[RoutingRuleConfig]]] = {}


class RoutingProfileConfig(BaseModel):
    code: str
    document_type: str
    suggested_destination: SaveDestination | None = None
    required_groups: tuple[tuple[str, ...], ...] = ()
    support_fields: tuple[str, ...] = ()
    explanation_fields: tuple[str, ...] = ()
    blocked: bool = False
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)

    @field_validator("code", "document_type", mode="before")
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("routing profile text value cannot be empty")
        return text

    @field_validator("required_groups", mode="before")
    @classmethod
    def _normalize_groups(cls, value: Any) -> tuple[tuple[str, ...], ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        groups: list[tuple[str, ...]] = []
        for raw_group in value:
            if isinstance(raw_group, (list, tuple)):
                normalized = tuple(str(item).strip() for item in raw_group if str(item).strip())
            else:
                normalized = (str(raw_group).strip(),) if str(raw_group).strip() else ()
            if normalized:
                groups.append(normalized)
        return tuple(groups)

    @field_validator("support_fields", "explanation_fields", mode="before")
    @classmethod
    def _normalize_fields(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        return tuple(str(item).strip() for item in value if str(item).strip())


class RoutingRuleConfig(BaseModel):
    source_kind: RuleSourceKind
    source_key: str
    profile_code: str
    priority: int = 100
    specificity: int = 0

    @field_validator("source_key", "profile_code", mode="before")
    @classmethod
    def _normalize_upper(cls, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("routing rule key cannot be empty")
        return text.upper()

    @field_validator("source_kind", mode="before")
    @classmethod
    def _normalize_kind(cls, value: Any) -> RuleSourceKind:
        text = str(value or "").strip().lower()
        if text not in {"doc_type", "category"}:
            raise ValueError("invalid routing source kind")
        return text  # type: ignore[return-value]


@dataclass(frozen=True)
class RoutingConfigBundle:
    profiles: dict[str, RoutingProfileConfig]
    rules: list[RoutingRuleConfig]
    sector: str


@dataclass(frozen=True)
class RoutingResolution:
    profile: RoutingProfileConfig
    matched_by: str
    matched_scope: RoutingMatchScope
    rule_source_kind: RuleSourceKind | None
    rule_source_key: str | None
    resolved_sector: str


def _fallback_profiles() -> dict[str, RoutingProfileConfig]:
    payload = load_routing_fallback_profiles_config(None)
    return {
        str(code).strip().upper(): RoutingProfileConfig.model_validate(config)
        for code, config in payload.items()
        if isinstance(config, dict)
    }


def _fallback_rules() -> list[RoutingRuleConfig]:
    result: list[RoutingRuleConfig] = []
    for raw in load_routing_fallback_rules_config(None):
        if not isinstance(raw, dict):
            continue
        try:
            result.append(
                RoutingRuleConfig(
                    source_kind=str(raw.get("source_kind") or ""),
                    source_key=str(raw.get("source_key") or ""),
                    profile_code=str(raw.get("profile_code") or ""),
                    priority=int(raw.get("priority") or 100),
                    specificity=0,
                )
            )
        except Exception:
            continue
    return result


def invalidate_document_routing_cache() -> None:
    global _profiles_cache
    _profiles_cache = None
    _rules_cache.clear()


def _cache_valid(ts: float) -> bool:
    return (time.monotonic() - ts) <= _CACHE_TTL


def _normalize_scope_key(tenant_id: UUID | str | None, sector: str | None) -> str:
    tenant_key = str(tenant_id) if tenant_id else "-"
    sector_key = str(sector or "_system").strip().lower()
    return f"{tenant_key}|{sector_key}"


def _tenant_sector_code(
    db: Session, tenant_id: UUID | str | None, *, sector_override: str | None = None
) -> str:
    if str(sector_override or "").strip():
        return resolve_sector_code(db, sector_override)
    if not tenant_id:
        return "default"
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        tenant = db.get(Tenant, str(tenant_id))
    raw_sector = getattr(tenant, "sector_template_name", None) if tenant else None
    return resolve_sector_code(db, raw_sector or "default")


def _load_profiles_from_db(db: Session | None) -> dict[str, RoutingProfileConfig]:
    global _profiles_cache

    if _profiles_cache is not None and _cache_valid(_profiles_cache[0]):
        return dict(_profiles_cache[1])

    profiles = _fallback_profiles()
    if db is not None:
        try:
            rows = (
                db.query(ImpRoutingProfile)
                .filter(ImpRoutingProfile.active == True)  # noqa: E712
                .all()
            )
            for row in rows:
                profile = RoutingProfileConfig.model_validate(
                    {
                        "code": row.code,
                        "document_type": row.document_type,
                        "suggested_destination": row.suggested_destination,
                        "required_groups": row.required_groups or [],
                        "support_fields": row.support_fields or [],
                        "explanation_fields": row.explanation_fields or [],
                        "blocked": bool(row.blocked),
                        "confidence_threshold": row.confidence_threshold,
                    }
                )
                profiles[profile.code.upper()] = profile
        except Exception as exc:
            logger.warning("No se pudieron cargar routing profiles desde BD: %s", exc)

    _profiles_cache = (time.monotonic(), dict(profiles))
    return profiles


def _build_rule(
    *,
    source_kind: RuleSourceKind,
    source_key: str,
    profile_code: str,
    priority: int,
    specificity: int,
) -> RoutingRuleConfig:
    return RoutingRuleConfig(
        source_kind=source_kind,
        source_key=source_key,
        profile_code=profile_code,
        priority=priority,
        specificity=specificity,
    )


def _load_rules_from_db(
    db: Session | None,
    *,
    tenant_id: UUID | str | None,
    sector: str,
) -> list[RoutingRuleConfig]:
    cache_key = _normalize_scope_key(tenant_id, sector)
    cached = _rules_cache.get(cache_key)
    if cached is not None and _cache_valid(cached[0]):
        return list(cached[1])

    rules: list[RoutingRuleConfig] = [
        _build_rule(
            source_kind=rule.source_kind,
            source_key=rule.source_key,
            profile_code=rule.profile_code,
            priority=rule.priority,
            specificity=0,
        )
        for rule in _fallback_rules()
    ]

    if db is not None:
        try:
            db_rows = (
                db.query(ImpRoutingRule).filter(ImpRoutingRule.active == True).all()  # noqa: E712
            )
            for row in db_rows:
                specificity = 0
                row_tenant_id = str(row.tenant_id) if row.tenant_id else None
                wanted_tenant_id = str(tenant_id) if tenant_id else None
                row_sector = str(row.sector or "").strip().lower()

                if row_tenant_id and wanted_tenant_id and row_tenant_id == wanted_tenant_id:
                    specificity = 3
                elif not row_tenant_id and row_sector and row_sector == str(sector).strip().lower():
                    specificity = 2
                elif not row_tenant_id and row_sector == "_system":
                    specificity = 1
                else:
                    continue

                rules.append(
                    _build_rule(
                        source_kind=row.source_kind,
                        source_key=row.source_key,
                        profile_code=row.profile_code,
                        priority=int(row.priority or 100),
                        specificity=specificity,
                    )
                )
        except Exception as exc:
            logger.warning("No se pudieron cargar routing rules desde BD: %s", exc)

    ordered = sorted(rules, key=lambda item: (-item.specificity, item.priority, item.source_key))
    _rules_cache[cache_key] = (time.monotonic(), list(ordered))
    return ordered


def load_document_routing_config(
    db: Session | None,
    *,
    tenant_id: UUID | str | None = None,
    sector_override: str | None = None,
) -> RoutingConfigBundle:
    sector = (
        _tenant_sector_code(db, tenant_id, sector_override=sector_override)
        if db is not None
        else str(sector_override or "default").strip().lower()
    )
    return RoutingConfigBundle(
        profiles=_load_profiles_from_db(db),
        rules=_load_rules_from_db(db, tenant_id=tenant_id, sector=sector),
        sector=sector,
    )


def resolve_routing_profile_match(
    *,
    db: Session | None,
    tenant_id: UUID | str | None,
    sector_override: str | None = None,
    source_doc_type: str | None,
    source_category: str | None,
    destination_override: SaveDestination | None = None,
) -> RoutingResolution:
    config = load_document_routing_config(
        db,
        tenant_id=tenant_id,
        sector_override=sector_override,
    )

    if destination_override is not None:
        profile = config.profiles.get(str(destination_override).strip().upper())
        if profile is not None:
            return RoutingResolution(
                profile=profile,
                matched_by="destination_override",
                matched_scope="destination_override",
                rule_source_kind=None,
                rule_source_key=None,
                resolved_sector=config.sector,
            )

    candidates = [
        ("doc_type", str(source_doc_type or "").strip().upper()),
        ("category", str(source_category or "").strip().upper()),
    ]

    for source_kind, source_key in candidates:
        if not source_key:
            continue
        for rule in config.rules:
            if str(rule.source_kind or "").strip().lower() != source_kind:
                continue
            if str(rule.source_key or "").strip().upper() != source_key:
                continue
            profile = (
                config.profiles.get(rule.profile_code)
                or config.profiles.get(rule.profile_code.lower())
                or config.profiles.get(rule.profile_code.upper())
                    )
            if profile is not None:
                matched_scope: RoutingMatchScope
                if rule.specificity >= 3:
                    matched_scope = "tenant"
                elif rule.specificity == 2:
                    matched_scope = "sector"
                elif rule.specificity == 1:
                    matched_scope = "system"
                else:
                    matched_scope = "fallback"
                return RoutingResolution(
                    profile=profile,
                    matched_by=f"{source_kind}:{source_key.lower()}",
                    matched_scope=matched_scope,
                    rule_source_kind=source_kind,
                    rule_source_key=source_key,
                    resolved_sector=config.sector,
                )

    fallback_profile = config.profiles.get("OTHER") or _fallback_profiles()["OTHER"]
    return RoutingResolution(
        profile=fallback_profile,
        matched_by="fallback:other",
        matched_scope="fallback",
        rule_source_kind=None,
        rule_source_key=None,
        resolved_sector=config.sector,
    )


def resolve_routing_profile(
    *,
    db: Session | None,
    tenant_id: UUID | str | None,
    sector_override: str | None = None,
    source_doc_type: str | None,
    source_category: str | None,
    destination_override: SaveDestination | None = None,
) -> tuple[RoutingProfileConfig, str]:
    resolution = resolve_routing_profile_match(
        db=db,
        tenant_id=tenant_id,
        sector_override=sector_override,
        source_doc_type=source_doc_type,
        source_category=source_category,
        destination_override=destination_override,
    )
    return resolution.profile, resolution.matched_by
