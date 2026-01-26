#!/usr/bin/env python3
"""
Script para identificar archivos/carpetas que deberían estar en .gitignore
pero están siendo trackeados por git.

NO ejecuta comandos automáticamente, solo imprime los comandos para revisión manual.
"""

import subprocess
import sys
from pathlib import Path

PATTERNS_TO_CHECK = [
    ".mypy_cache/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    "*.pyc",
    ".coverage",
    "htmlcov/",
    "test.db",
]


def get_tracked_files() -> set[str]:
    """Obtiene lista de archivos trackeados por git."""
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.strip().split("\n"))


def find_tracked_ignored_files(tracked_files: set[str]) -> dict[str, list[str]]:
    """Encuentra archivos trackeados que coinciden con patrones de .gitignore."""
    matches: dict[str, list[str]] = {}

    for pattern in PATTERNS_TO_CHECK:
        pattern_matches = []

        if pattern.endswith("/"):
            folder_name = pattern.rstrip("/")
            for f in tracked_files:
                if f"/{folder_name}/" in f"/{f}" or f.startswith(f"{folder_name}/"):
                    pattern_matches.append(f)
        elif pattern.startswith("*."):
            extension = pattern[1:]
            for f in tracked_files:
                if f.endswith(extension):
                    pattern_matches.append(f)
        else:
            for f in tracked_files:
                if f == pattern or f.endswith(f"/{pattern}"):
                    pattern_matches.append(f)

        if pattern_matches:
            matches[pattern] = sorted(set(pattern_matches))

    return matches


def get_git_rm_commands(matches: dict[str, list[str]]) -> list[str]:
    """Genera comandos git rm --cached para cada patrón encontrado."""
    commands = []
    folders_to_remove = set()
    files_to_remove = set()

    for pattern, files in matches.items():
        if pattern.endswith("/"):
            folder_name = pattern.rstrip("/")
            for f in files:
                parts = Path(f).parts
                for i, part in enumerate(parts):
                    if part == folder_name:
                        folder_path = "/".join(parts[: i + 1])
                        folders_to_remove.add(folder_path)
                        break
        else:
            files_to_remove.update(files)

    for folder in sorted(folders_to_remove):
        commands.append(f'git rm -r --cached "{folder}"')

    for file in sorted(files_to_remove):
        if not any(file.startswith(f"{folder}/") for folder in folders_to_remove):
            commands.append(f'git rm --cached "{file}"')

    return commands


def main() -> int:
    print("=" * 60)
    print("ANÁLISIS DE ARCHIVOS TRACKEADOS QUE DEBERÍAN ESTAR IGNORADOS")
    print("=" * 60)
    print()

    try:
        tracked_files = get_tracked_files()
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando git: {e}")
        return 1
    except FileNotFoundError:
        print("Error: git no está instalado o no está en el PATH")
        return 1

    matches = find_tracked_ignored_files(tracked_files)

    if not matches:
        print("[OK] No se encontraron archivos trackeados que deban estar ignorados.")
        return 0

    print("ARCHIVOS ENCONTRADOS:")
    print("-" * 40)
    for pattern, files in matches.items():
        print(f"\nPatrón: {pattern}")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... y {len(files) - 10} más")

    commands = get_git_rm_commands(matches)

    print()
    print("=" * 60)
    print("COMANDOS PARA ELIMINAR DEL TRACKING (NO DEL DISCO)")
    print("=" * 60)
    print()

    for cmd in commands:
        print(cmd)

    print()
    print("=" * 60)
    print("INSTRUCCIONES")
    print("=" * 60)
    print("""
1. Revisa los comandos anteriores para asegurarte de que son correctos.

2. Copia y pega los comandos en tu terminal para ejecutarlos.
   Esto eliminará los archivos del tracking de git, pero NO del disco.

3. Después de ejecutar los comandos, haz un commit:
   git commit -m "chore: remove cached files that should be gitignored"

4. Verifica que .gitignore incluye estos patrones para que no se
   vuelvan a agregar accidentalmente.

NOTA: Si hay errores de "pathspec did not match", significa que
el archivo/carpeta ya no está siendo trackeado.
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
