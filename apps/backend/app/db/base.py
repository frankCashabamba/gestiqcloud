# isort: off
# Import Base before the models to avoid circular imports
from app.config.database import Base  # shared Base for the whole project

# Import the aggregator so every model is registered
import app.models  # noqa: F401

# isort: on

# Load vertical-slice module models for the revision scaffold without side effects
try:
    import app.modules.products.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.suppliers.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.purchases.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.expenses.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.hr.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.finance.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.settings.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.invoicing.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.accounting.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.production.infrastructure.models  # noqa: F401
except Exception:
    pass
try:
    import app.models.core.event_outbox  # noqa: F401
except Exception:
    pass
try:
    import app.models.core.profit_snapshots  # noqa: F401
except Exception:
    pass
try:
    import app.models.core.document_storage  # noqa: F401
except Exception:
    pass
try:
    import app.modules.copilot.models  # noqa: F401
except Exception:
    pass
try:
    import app.modules.branches.models  # noqa: F401
except Exception:
    pass

target_metadata = Base.metadata
