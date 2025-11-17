#!/usr/bin/env python3
"""
Script para generar archivos TypeScript actualizado basado en modelos Python.
Útil para mantener sincronizados los tipos con los modelos backend.
"""

import re
from pathlib import Path
from typing import Dict

# Mapeo de tipos Python a TypeScript
PYTHON_TO_TS = {
    "str": "string",
    "int": "number",
    "float": "number",
    "bool": "boolean",
    "UUID": "string",
    "dict": "Record<string, any>",
    "list": "any[]",
    "datetime": "string",
    "date": "string",
    "Decimal": "number",
}

# Cambios de nombres de campos (estos deben coincidir con FIELD_MAPPINGS del script anterior)
FIELD_CHANGES = {
    # "nombreCampo": "nameCampo",
}


def extract_model_fields(python_file: Path) -> Dict[str, Dict[str, str]]:
    """
    Extraer campos de un archivo de modelo Python.
    Retorna: {modelo: {campo: tipo}}
    """
    try:
        content = python_file.read_text()
    except Exception:
        return {}

    models = {}
    current_class = None

    # Patrón para encontrar clases
    class_pattern = re.compile(r"class\s+(\w+)\s*\(")
    # Patrón para campos de SQLAlchemy
    field_pattern = re.compile(r"(\w+):\s+Mapped\[([^\]]+)\]")

    for line in content.split("\n"):
        class_match = class_pattern.search(line)
        if class_match:
            current_class = class_match.group(1)
            models[current_class] = {}

        if current_class:
            field_match = field_pattern.search(line)
            if field_match:
                field_name = field_match.group(1)
                field_type = field_match.group(2).strip()
                models[current_class][field_name] = field_type

    return models


def generate_ts_interface(model_name: str, fields: Dict[str, str]) -> str:
    """Generar una interface TypeScript."""
    lines = [f"export interface {model_name} {{"]

    for field_name, field_type in fields.items():
        ts_type = convert_python_type_to_ts(field_type)
        lines.append(f"  {field_name}: {ts_type};")

    lines.append("}")
    return "\n".join(lines)


def convert_python_type_to_ts(py_type: str) -> str:
    """Convertir tipo Python a TypeScript."""
    py_type = py_type.strip()

    # Manejar Union types (Optional)
    if "|" in py_type:
        types = [t.strip() for t in py_type.split("|")]
        ts_types = [convert_python_type_to_ts(t) for t in types]
        if "null" in ts_types:
            ts_types.remove("null")
            return f"({' | '.join(ts_types)}) | null"
        return " | ".join(ts_types)

    # Buscar en mapeo directo
    for py, ts in PYTHON_TO_TS.items():
        if py_type.startswith(py):
            return ts

    # Default
    return "any"


def main():
    """Generar archivos TypeScript."""
    print("\n📋 Generador de tipos TypeScript")
    print("=" * 60)

    backend_models_dir = Path("./apps/backend/app/models")
    frontend_types_dir = Path("./apps/frontend/src/types")

    if not backend_models_dir.exists():
        print(f"❌ No encontrado: {backend_models_dir}")
        return

    # Escanear modelos Python
    py_files = list(backend_models_dir.rglob("*.py"))
    print(f"\n🔍 Archivos de modelo encontrados: {len(py_files)}")

    all_models = {}
    for py_file in py_files:
        models = extract_model_fields(py_file)
        all_models.update(models)

    # Generar tipos TypeScript
    frontend_types_dir.mkdir(parents=True, exist_ok=True)

    for model_name, fields in all_models.items():
        ts_interface = generate_ts_interface(model_name, fields)

        # Guardar archivo
        ts_file = frontend_types_dir / f"{model_name}.ts"
        ts_file.write_text(ts_interface)

        print(f"  ✏️  {model_name} ({len(fields)} campos)")

    print(f"\n{'='*60}")
    print(f"✅ Tipos TypeScript generados en: {frontend_types_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
