from __future__ import annotations

from typing import Any

from .dsl import eval_dsl_expr
from .schema import TemplateV2, TransformSpec


class TemplateInterpreter:
    def __init__(self, template: TemplateV2):
        self.template = template

    def apply_map(self, row: dict[str, Any]) -> dict[str, Any]:
        mapped: dict[str, Any] = {}
        row_lower = {k.lower(): v for k, v in row.items()}
        for target, sources in self.template.map.items():
            for src in [target, *sources]:
                val = row_lower.get(src.lower())
                if val is not None and str(val).strip() != "":
                    mapped[target] = val
                    break
        return mapped

    def apply_transforms(self, row: dict[str, Any]) -> dict[str, Any]:
        ctx = dict(row)
        result = dict(row)
        for field, spec in self.template.transforms.items():
            try:
                if isinstance(spec, str):
                    val = eval_dsl_expr(spec, ctx)
                elif isinstance(spec, TransformSpec):
                    if spec.expr:
                        val = eval_dsl_expr(spec.expr, ctx)
                    else:
                        val = ctx.get(field)
                    if spec.type == "number":
                        from app.modules.imports.application.transform_dsl import _to_number

                        val = _to_number(val)
                    if spec.round is not None and val is not None:
                        try:
                            val = round(float(val), spec.round)
                        except (ValueError, TypeError):
                            pass
                    if val is None and spec.fallback is not None:
                        val = spec.fallback
                else:
                    continue
                if val is not None:
                    result[field] = val
                ctx[field] = result.get(field)
            except Exception:
                continue
        return result

    def apply_defaults(self, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        for key, default_val in self.template.defaults.items():
            if key not in result or result[key] in (None, ""):
                result[key] = default_val
        return result

    def dedupe_key(self, row: dict[str, Any]) -> tuple[Any, ...] | None:
        if not self.template.dedupe_keys:
            return None
        return tuple(row.get(k) for k in self.template.dedupe_keys)

    def process_row(self, row: dict[str, Any]) -> dict[str, Any]:
        mapped = self.apply_map(row)
        transformed = self.apply_transforms(mapped)
        return self.apply_defaults(transformed)

    def process_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[Any, ...]] = set()
        results: list[dict[str, Any]] = []
        for row in rows:
            processed = self.process_row(row)
            key = self.dedupe_key(processed)
            if key is not None:
                if key in seen:
                    continue
                seen.add(key)
            results.append(processed)
        return results
