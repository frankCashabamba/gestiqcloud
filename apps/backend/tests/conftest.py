import os
import sys
from pathlib import Path

# Ensure repository root is available for `apps.*` imports when running this
# tests package directly.
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Propagate ENV defaults used by the main conftest to avoid duplication.
os.environ.setdefault("ENV", "development")
os.environ.setdefault("ENVIRONMENT", "development")
