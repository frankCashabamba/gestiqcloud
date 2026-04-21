"""
Compatibility module for crud_base.

This module provides backward compatibility for existing code that imports
from app.core.crud_base. The actual implementation has been moved to
app.core.base_crud and renamed from CRUDBase to BaseCRUD.
"""

# Import the actual implementation and provide backward compatibility alias
from app.core.base_crud import BaseCRUD

# Maintain backward compatibility
CRUDBase = BaseCRUD

# Also export the original name for new code
__all__ = ["CRUDBase", "BaseCRUD"]
