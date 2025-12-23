"""Legacy alias for company settings schemas (English source of truth)."""

from app.settings.schemas.company_settings import (  # noqa: F401
    CompanySettingsBase as ConfiguracionEmpresaBase,
)
from app.settings.schemas.company_settings import (  # noqa: F401
    CompanySettingsCreate as ConfiguracionEmpresaCreate,
)
from app.settings.schemas.company_settings import (  # noqa: F401
    CompanySettingsUpdate as ConfiguracionEmpresaUpdate,
)
from app.settings.schemas.company_settings import (  # noqa: F401
    CompanySettingsOut as ConfiguracionEmpresaOut,
)
