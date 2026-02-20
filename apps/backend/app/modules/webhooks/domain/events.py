"""Event definitions for webhook system."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class WebhookEvent:
    """Event payload structure for all webhooks."""
    event_type: str
    event_id: str
    timestamp: datetime
    tenant_id: UUID
    resource_type: str
    resource_id: UUID
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "event_type": self.event_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "tenant_id": str(self.tenant_id),
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id),
            "data": self.data,
            "metadata": self.metadata or {},
        }
