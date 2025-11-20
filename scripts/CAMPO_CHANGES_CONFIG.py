"""
CONFIGURACIÓN CENTRAL DE CAMBIOS DE CAMPOS

Edita este archivo con TODOS los cambios español → inglés
que quieras aplicar. Luego usa los scripts para aplicarlos
automáticamente.
"""

# CAMBIOS DE CAMPOS (SPANISH -> ENGLISH)
# Asegúrate que sean exactamente iguales a tus cambios en Python
FIELD_MAPPINGS = {
    # Ejemplo de formato:
    # "nombre": "name",
    # "descripcion": "description",
    # "creado_en": "created_at",
    # "actualizado_en": "updated_at",
    # "activo": "active",
}

# REGLAS ESPECIALES
# Usa esto para casos where el cambio depende del contexto
SPECIAL_RULES = {
    # Ejemplo: si "estado" es un enum en algunos lugares
    # "estado": {
    #     "pattern": r"estado\s*=|estado\s*:",
    #     "replacement": "status",
    # }
}

# ARCHIVOS A EXCLUIR (paths con "/" o glob patterns)
EXCLUDE_PATTERNS = [
    ".git/",
    ".venv/",
    "node_modules/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    "*.min.js",
    "*.min.css",
]

# EXTENSIONES DE ARCHIVO A PROCESAR
PROCESS_EXTENSIONS = [
    ".py",  # Python
    ".ts",  # TypeScript
    ".tsx",  # React TypeScript
    ".js",  # JavaScript
    ".jsx",  # React JavaScript
    ".json",  # JSON configs
    ".sql",  # SQL scripts
]
