from __future__ import annotations

import ast
import math
import re
from typing import Any, Mapping


def _to_number(x: Any) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    # Normalize decimals like "1.234,56" or "1,234.56"
    s_norm = re.sub(r"[^0-9,.-]", "", s)
    # If both comma and dot, assume last one is decimal sep
    if "," in s_norm and "." in s_norm:
        if s_norm.rfind(",") > s_norm.rfind("."):
            s_norm = s_norm.replace(".", "").replace(",", ".")
        else:
            s_norm = s_norm.replace(",", "")
    else:
        s_norm = s_norm.replace(",", ".")
    try:
        return float(s_norm)
    except Exception:
        return None


def _coalesce(*args: Any) -> Any:
    for a in args:
        if a not in (None, ""):
            return a
    return None


def _nullif(a: Any, b: Any) -> Any:
    return None if a == b else a


def _round(a: Any, n: Any = 0) -> float | None:
    aa = _to_number(a)
    if aa is None:
        return None
    try:
        return round(aa, int(n))
    except Exception:
        return round(aa, 0)


ALLOWED_FUNCS = {
    "coalesce": _coalesce,
    "nullif": _nullif,
    "to_number": _to_number,
    "round": _round,
}


class SafeEval(ast.NodeVisitor):
    def __init__(self, ctx: Mapping[str, Any]):
        self.ctx = ctx

    def visit_Expression(self, node: ast.Expression):  # type: ignore
        return self.visit(node.body)

    def visit_Name(self, node: ast.Name):  # type: ignore
        return self.ctx.get(node.id)

    def visit_Constant(self, node: ast.Constant):  # type: ignore
        return node.value

    def visit_UnaryOp(self, node: ast.UnaryOp):  # type: ignore
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            v = _to_number(operand)
            return -v if v is not None else None
        if isinstance(node.op, ast.UAdd):
            return _to_number(operand)
        raise ValueError("Operator not allowed")

    def visit_BinOp(self, node: ast.BinOp):  # type: ignore
        a = _to_number(self.visit(node.left))
        b = _to_number(self.visit(node.right))
        if a is None or b is None:
            return None
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            try:
                return a / b if b != 0 else None
            except ZeroDivisionError:
                return None
        raise ValueError("Operator not allowed")

    def visit_Call(self, node: ast.Call):  # type: ignore
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple functions allowed")
        fname = node.func.id
        fn = ALLOWED_FUNCS.get(fname)
        if not fn:
            raise ValueError(f"Function {fname} not allowed")
        args = [self.visit(a) for a in node.args]
        return fn(*args)

    def generic_visit(self, node):  # type: ignore
        raise ValueError("Expression contains unsupported syntax")


def eval_expr(expr: str, ctx: Mapping[str, Any]) -> Any:
    tree = ast.parse(expr, mode="eval")
    return SafeEval(ctx).visit(tree)


def apply_mapping_pipeline(
    headers: list[str],
    values: list[Any],
    *,
    mapping: dict[str, str] | None,
    transforms: dict[str, Any] | None,
    defaults: dict[str, Any] | None,
) -> dict[str, Any]:
    # Build case-insensitive header index
    idx = {h.lower(): i for i, h in enumerate(headers)}
    base: dict[str, Any] = {}
    if mapping:
        for src, dst in mapping.items():
            if not dst or str(dst).lower() == "ignore":
                continue
            i = idx.get(str(src).lower())
            if i is not None and i < len(values):
                base[dst] = values[i]

    # Evaluate transforms
    if transforms:
        # context includes base and safe numeric helpers
        ctx = dict(base)
        for field, spec in transforms.items():
            try:
                if isinstance(spec, str):
                    val = eval_expr(spec, ctx)
                elif isinstance(spec, dict) and "expr" in spec:
                    val = eval_expr(str(spec.get("expr")), ctx)
                    if spec.get("type") == "number":
                        val = _to_number(val)
                    if spec.get("round") is not None and val is not None:
                        try:
                            val = round(float(val), int(spec.get("round")))
                        except Exception:
                            pass
                else:
                    continue
                if val is not None:
                    base[field] = val
                ctx[field] = base.get(field)
            except Exception:
                # do not fail whole row on a bad transform
                continue

    # Apply defaults
    if defaults:
        for k, v in defaults.items():
            if k not in base or base[k] in (None, ""):
                base[k] = v

    return base

