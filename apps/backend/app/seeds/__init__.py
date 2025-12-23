"""
Seeds para cargar datos iniciales en la BD.

NOTA: Los sector templates ahora se cargan via migración SQL en lugar de seed.
Ver: ops/migrations/2025-11-29_001_migrate_sector_templates_to_db/
"""

# El seed de sector templates está deprecado
# Los datos se cargan via migración SQL para evitar hardcoding

__all__: list[str] = []
