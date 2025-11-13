# Muy importante: importar el agregador para registrar TODOS los modelos
import app.models  # noqa: F401
from app.config.database import Base  # la misma Base en todo el proyecto

# Cargar modelos de módulos vertical-slice para Alembic (sin efectos secundarios)
try:
    import app.modules.productos.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.proveedores.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.ventas.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.compras.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.gastos.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.rrhh.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.finanzas.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.settings.infrastructure.models  # noqa: F401
except Exception:
    pass

target_metadata = Base.metadata
