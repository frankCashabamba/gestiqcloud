from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.modules.imports.application.transform_dsl import (
    ALLOWED_FUNCS as _BASE_FUNCS,
    SafeEval as _BaseSafeEval,
    _to_number,
)


def _to_date(value: Any, fmt: str | None = None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if fmt:
        try:
            return datetime.strptime(s, fmt).isoformat()
        except (ValueError, TypeError):
            return None
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, f).isoformat()
        except (ValueError, TypeError):
            continue
    return None


def _regex_extract(value: Any, pattern: str, group: int = 0) -> str | None:
    if value is None:
        return None
    m = re.search(pattern, str(value))
    if m:
        try:
            return m.group(int(group))
        except (IndexError, TypeError):
            return None
    return None


def _lower(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).lower()


def _upper(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).upper()


def _trim(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _concat(*args: Any) -> str:
    return "".join(str(a) if a is not None else "" for a in args)


def _if_empty(value: Any, default: Any) -> Any:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return value


ALLOWED_FUNCS: dict[str, Any] = {
    **_BASE_FUNCS,
    "to_date": _to_date,
    "regex_extract": _regex_extract,
    "lower": _lower,
    "upper": _upper,
    "trim": _trim,
    "concat": _concat,
    "if_empty": _if_empty,
}


class SafeEval(_BaseSafeEval):
    def visit_Call(self, node: ast.Call):  # type: ignore
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple functions allowed")
        fname = node.func.id
        fn = ALLOWED_FUNCS.get(fname)
        if not fn:
            raise ValueError(f"Function {fname} not allowed")
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords if kw.arg}
        return fn(*args, **kwargs)


def eval_dsl_expr(expr: str, ctx: Mapping[str, Any]) -> Any:
    tree = ast.parse(expr, mode="eval")
    return SafeEval(ctx).visit(tree)
