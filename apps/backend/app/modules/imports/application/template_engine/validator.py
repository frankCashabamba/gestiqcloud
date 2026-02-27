from __future__ import annotations

import ast
import re
from typing import Any

from .schema import TemplateV2, TransformSpec


def validate_template(data: dict[str, Any] | TemplateV2) -> list[str]:
    errors: list[str] = []

    if isinstance(data, dict):
        try:
            tpl = TemplateV2(**data)
        except Exception as exc:
            errors.append(f"Schema validation failed: {exc}")
            return errors
    else:
        tpl = data

    if tpl.template_version != 2:
        errors.append(f"Unsupported template_version: {tpl.template_version}")

    if tpl.match.filename_regex:
        try:
            re.compile(tpl.match.filename_regex)
        except re.error as exc:
            errors.append(f"Invalid filename_regex: {exc}")

    for rule in tpl.extract.sheet_rules:
        try:
            re.compile(rule.sheet_name_regex)
        except re.error as exc:
            errors.append(f"Invalid sheet_name_regex '{rule.sheet_name_regex}': {exc}")

    if not tpl.map:
        errors.append("'map' is empty; at least one field mapping is required")

    for field, spec in tpl.transforms.items():
        expr_str: str | None = None
        if isinstance(spec, str):
            expr_str = spec
        elif isinstance(spec, TransformSpec) and spec.expr:
            expr_str = spec.expr
        if expr_str:
            try:
                ast.parse(expr_str, mode="eval")
            except SyntaxError as exc:
                errors.append(f"Invalid DSL expression for '{field}': {exc}")

    for key in tpl.dedupe_keys:
        if key not in tpl.map and key not in tpl.defaults:
            errors.append(f"dedupe_key '{key}' not found in map or defaults")

    return errors
