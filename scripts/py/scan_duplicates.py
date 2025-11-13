import ast
import hashlib
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
# Prefer new path; fallback to legacy path if needed
NEW_ROOT = os.path.join(REPO, "apps", "backend", "app")
LEGACY_ROOT = os.path.join(REPO, "backend", "app")
ROOT = NEW_ROOT if os.path.isdir(NEW_ROOT) else LEGACY_ROOT


def normalize_function(fn: ast.FunctionDef) -> str:
    # strip docstring and arg names; focus on body shape. Rebuild with locations.
    new = ast.FunctionDef(
        name="f",
        args=ast.arguments(
            posonlyargs=[],
            args=[],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            vararg=None,
            kwarg=None,
        ),
        body=fn.body,
        decorator_list=[],
        returns=None,
        type_comment=None,
    )
    ast.fix_missing_locations(new)
    src = ast.unparse(new) if hasattr(ast, "unparse") else ast.dump(new)
    return src


def hash_src(src: str) -> str:
    return hashlib.sha1(src.encode()).hexdigest()


def scan():
    by_hash = defaultdict(list)
    for base, _, files in os.walk(ROOT):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(base, f)
            try:
                src = open(p, "r", encoding="utf-8").read()
                tree = ast.parse(src)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    norm = normalize_function(node)
                    h = hash_src(norm)
                    by_hash[h].append((p, node.name))
    print("hash,function_count")
    for h, items in by_hash.items():
        if len(items) > 1:
            print(h, len(items))
            for p, name in items:
                print(" ", p, name)


if __name__ == "__main__":
    scan()
