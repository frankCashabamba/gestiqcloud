#!/usr/bin/env python3
"""
replace_empresa_tenant.py (fixed)

Busca y sustituye ocurrencias de:
  - empresa_id   -> tenant_id
  - EMPRESA_ID   -> TENANT_ID
  - empresaId    -> tenantId
  - EmpresaId    -> TenantId

en los archivos de tu proyecto, con *dry-run* por defecto.
Incluye filtros por extensión, exclusión de directorios, backups y resumen.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Reglas de reemplazo (ordenadas). ¡OJO!: usar \b (una sola barra) para límites de palabra.
REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bempresa_id\b"), "tenant_id"),
    (re.compile(r"\bEMPRESA_ID\b"), "TENANT_ID"),
    (re.compile(r"(?<![A-Za-z0-9_])empresaId(?![A-Za-z0-9_])"), "tenantId"),
    (re.compile(r"(?<![A-Za-z0-9_])EmpresaId(?![A-Za-z0-9_])"), "TenantId"),
]


DEFAULT_EXTENSIONS = [
    ".py",
    ".sql",
    ".ini",
    ".cfg",
    ".toml",
    ".env",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".graphql",
    ".sh",
    ".dockerfile",
    ".conf",
]

DEFAULT_EXCLUDES = [
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".idea",
    ".vscode",
    ".DS_Store",
    "scripts",  # evitar auto-editar el script
]


@dataclass
class FileChange:
    path: Path
    matches: int = 0
    per_rule: Dict[str, int] = field(default_factory=dict)
    changed: bool = False


def is_probably_text(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return False
        try:
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            try:
                chunk.decode("latin-1")
                return True
            except UnicodeDecodeError:
                return False
    except Exception:
        return False


def iter_paths(
    root: Path, include_exts: Iterable[str], exclude_dirs: Iterable[str]
) -> Iterable[Path]:
    include_exts = [e.lower() for e in include_exts]
    exclude_set = set(exclude_dirs)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_set]
        for fname in filenames:
            p = Path(dirpath) / fname
            if p.suffix.lower() in include_exts or (
                p.suffix == "" and fname.lower() in {"dockerfile", "makefile"}
            ):
                yield p


def apply_replacements(text: str) -> Tuple[str, int, Dict[str, int]]:
    total = 0
    per_rule: Dict[str, int] = {}
    for pat, repl in REPLACEMENTS:
        new_text, n = pat.subn(repl, text)
        if n:
            per_rule[pat.pattern] = n
            text = new_text
            total += n
    return text, total, per_rule


def process_file(path: Path, write: bool, create_backup: bool) -> FileChange:
    fc = FileChange(path=path)
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw = path.read_text(encoding="latin-1")
        except Exception:
            return fc
    except Exception:
        return fc

    new_text, total, per_rule = apply_replacements(raw)
    fc.matches = total
    fc.per_rule = per_rule
    if total == 0:
        return fc

    fc.changed = True
    if write:
        if create_backup:
            backup = path.with_suffix(path.suffix + ".bak")
            try:
                if not backup.exists():
                    backup.write_text(raw, encoding="utf-8")
            except UnicodeEncodeError:
                backup.write_text(raw, encoding="latin-1")
        try:
            path.write_text(new_text, encoding="utf-8")
        except UnicodeEncodeError:
            path.write_text(new_text, encoding="latin-1")
    return fc


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sustituye empresa_id -> tenant_id (y variantes) en tu proyecto."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Directorio raíz del proyecto (default: .)",
    )
    parser.add_argument(
        "--ext", nargs="*", default=DEFAULT_EXTENSIONS, help="Extensiones a incluir"
    )
    parser.add_argument(
        "--exclude", nargs="*", default=DEFAULT_EXCLUDES, help="Directorios a excluir"
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Escribir cambios (por defecto solo dry-run)",
    )
    parser.add_argument(
        "--no-backup", action="store_true", help="No crear archivos .bak"
    )
    parser.add_argument(
        "--only-list",
        action="store_true",
        help="Solo listar archivos con coincidencias",
    )

    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"[ERR] Root no válido: {root}", file=sys.stderr)
        return 2

    files = list(iter_paths(root, args.ext, args.exclude))
    if not files:
        print("[INFO] No se encontraron archivos con las extensiones dadas.")
        return 0

    total_files = 0
    changed_files = 0
    total_matches = 0
    per_rule_global: Dict[str, int] = {}

    for p in files:
        if not is_probably_text(p):
            continue
        fc = process_file(p, write=args.write, create_backup=not args.no_backup)
        if fc.matches > 0:
            total_files += 1
            changed_files += int(fc.changed)
            total_matches += fc.matches
            for k, v in fc.per_rule.items():
                per_rule_global[k] = per_rule_global.get(k, 0) + v
            if args.only_list:
                print(p.as_posix())
            else:
                print(f"{p.as_posix()}  (+{fc.matches})")

    mode = "WRITE" if args.write else "DRY-RUN"
    print("\n=== RESUMEN ===")
    print(f"Modo: {mode}")
    print(f"Archivos con coincidencias: {total_files}")
    if args.write:
        print(f"Archivos modificados:      {changed_files}")
    print(f"Reemplazos totales:        {total_matches}")
    if not args.only_list:
        print("Por regla:")
        for pat, count in per_rule_global.items():
            print(f"  {pat}  -> {count}")

    if not args.write:
        print(
            "\nNada se ha modificado (dry-run). Ejecuta con --write para aplicar cambios."
        )
    else:
        if not args.no_backup:
            print("\nSe han creado backups .bak de los archivos modificados.")
        print("Revisa el diff y ejecuta tu suite de tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
