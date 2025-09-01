# Shared module helpers

Pequeños utilitarios para reducir boilerplate en casos de uso y repositorios.

## BaseUseCase
- Ubicación: `app/modules/shared/application/base.py`
- Propósito: almacenar la dependencia `repo` para evitar repetir `__init__`.

Ejemplo:
```py
from app.modules.shared.application.base import BaseUseCase
from .ports import MyRepo

class DoSomething(BaseUseCase[MyRepo]):
    def execute(self, x: int) -> str:
        return self.repo.work(x)
```

## SqlAlchemyRepo
- Ubicación: `app/modules/shared/infrastructure/sqlalchemy_repo.py`
- Propósito: almacenar `self.db: Session` y compartir helpers comunes.

Ejemplo:
```py
from app.modules.shared.infrastructure.sqlalchemy_repo import SqlAlchemyRepo
from sqlalchemy.orm import Session

class SqlFooRepo(SqlAlchemyRepo):
    def get(self, id: int):
        return self.db.get(FooORM, id)
```

## Cómo aplicar el patrón
1) En casos de uso: hereda de `BaseUseCase[<RepoInterface>]` y elimina el `__init__` que solo guarda `repo`.
2) En repositorios SQLAlchemy: hereda de `SqlAlchemyRepo` y elimina el `__init__(self, db: Session)` que solo asigna `self.db = db`.
3) No cambies la firma pública de `execute(...)` o métodos del repo; solo quita constructores duplicados.

## Módulos actualizados como referencia
- empresa: `ListarEmpresas*`, `SqlEmpresaRepo`
- modulos: `ListarModulos*`, `SqlModuloRepo`
- productos: `Crear/ListarProductos`, `SqlAlchemyProductoRepo`
- clients: `Crear/Actualizar/Listar/EliminarCliente`, `SqlAlchemyClienteRepo`

