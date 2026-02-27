from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MatchRule(BaseModel):
    filename_regex: str | None = None
    language: list[str] = Field(default_factory=lambda: ["es"])
    priority: int = 50


class MergedCellsConfig(BaseModel):
    fill: bool = False


class SheetRule(BaseModel):
    sheet_name_regex: str
    merged_cells: MergedCellsConfig = Field(default_factory=MergedCellsConfig)


class ExtractRule(BaseModel):
    mode: Literal["excel_grid", "csv", "ocr"] = "excel_grid"
    all_sheets: bool = False
    sheet_rules: list[SheetRule] = Field(default_factory=list)


class HeaderNormalization(BaseModel):
    strip_accents: bool = True
    synonyms: dict[str, dict[str, list[str]]] = Field(default_factory=dict)


class TransformSpec(BaseModel):
    type: str | None = None
    expr: str | None = None
    fallback: Any = None
    round: int | None = None


class OutputConfig(BaseModel):
    doc_type: str = "product"


class TemplateV2(BaseModel):
    template_version: Literal[2] = 2
    match: MatchRule = Field(default_factory=MatchRule)
    extract: ExtractRule = Field(default_factory=ExtractRule)
    header_normalization: HeaderNormalization = Field(default_factory=HeaderNormalization)
    map: dict[str, list[str]] = Field(default_factory=dict)
    transforms: dict[str, TransformSpec | str] = Field(default_factory=dict)
    defaults: dict[str, Any] = Field(default_factory=dict)
    dedupe_keys: list[str] = Field(default_factory=list)
    output: OutputConfig = Field(default_factory=OutputConfig)
