from app.config.database import Base  # la misma Base en todo el proyecto

# Muy importante: importar el agregador para registrar TODOS los modelos
import app.models  # noqa: F401

target_metadata = Base.metadata