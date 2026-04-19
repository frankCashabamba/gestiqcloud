from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from .runtime_config import load_destination_registry_config
from .schemas import DestinationCapabilitiesOut, DestinationRegistryItemOut


class DestinationRegistryCapabilities(BaseModel):
    supports_update_stock: bool = False
    supports_line_matching: bool = False
    supports_partial_payment: bool = False
    supports_multi_record_save: bool = False


class DestinationRegistryItem(BaseModel):
    code: str
    label: str
    target: str
    target_tables: tuple[str, ...] = ()
    save_api: str = "save_document"
    enabled: bool = True
    confirmation_required: bool = True
    include_in_candidates: bool = True
    save_order: int = Field(default=100, ge=0)
    compatible_document_types: tuple[str, ...] = ()
    compatible_source_categories: tuple[str, ...] = ()
    capabilities: DestinationRegistryCapabilities = Field(
        default_factory=DestinationRegistryCapabilities
    )

    @field_validator(
        "code",
        "label",
        "target",
        "save_api",
        mode="before",
    )
    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator(
        "target_tables",
        "compatible_document_types",
        "compatible_source_categories",
        mode="before",
    )
    @classmethod
    def _normalize_string_tuple(cls, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)):
            return ()
        items: list[str] = []
        for item in value:
            text = str(item or "").strip()
            if text:
                items.append(text)
        return tuple(items)

    def to_out(self) -> DestinationRegistryItemOut:
        return DestinationRegistryItemOut(
            code=self.code,
            label=self.label,
            target=self.target,
            target_tables=list(self.target_tables),
            save_api=self.save_api,
            enabled=self.enabled,
            confirmation_required=self.confirmation_required,
            include_in_candidates=self.include_in_candidates,
            save_order=self.save_order,
            capabilities=DestinationCapabilitiesOut(
                supports_update_stock=self.capabilities.supports_update_stock,
                supports_line_matching=self.capabilities.supports_line_matching,
                supports_partial_payment=self.capabilities.supports_partial_payment,
                supports_multi_record_save=self.capabilities.supports_multi_record_save,
            ),
        )


def load_destination_registry(db: Any | None = None) -> dict[str, DestinationRegistryItem]:
    payload = load_destination_registry_config(db)
    result: dict[str, DestinationRegistryItem] = {}
    for key, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        item = DestinationRegistryItem.model_validate(raw)
        code = item.code or str(key).strip()
        if not code:
            continue
        result[code] = item
    return result


def list_destination_registry(db: Any | None = None) -> list[DestinationRegistryItemOut]:
    items = sorted(load_destination_registry(db).values(), key=lambda item: item.save_order)
    return [item.to_out() for item in items if item.enabled]


__all__ = [
    "DestinationRegistryItem",
    "DestinationRegistryCapabilities",
    "load_destination_registry",
    "list_destination_registry",
]
