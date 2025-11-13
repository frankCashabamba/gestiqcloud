"""
ElectricSQL Conflict Resolution for Offline-First Sync

Handles reconciliation of conflicting changes during sync operations.
Implements business logic for resolving data conflicts in multi-tenant environment.
"""

from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


class ConflictResolver:
    """
    Handles conflict resolution for different entity types.

    Strategies:
    - Last Write Wins (LWw): Take the most recent change
    - Merge: Combine changes intelligently
    - Manual: Require user intervention
    - Business Rules: Apply domain-specific logic
    """

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def resolve_stock_conflict(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve stock item conflicts.

        Strategy: Last Write Wins for quantity adjustments.
        If quantities differ, take the one with later updated_at.
        """
        local_time = local.get("updated_at", datetime.min)
        remote_time = remote.get("updated_at", datetime.min)

        if isinstance(local_time, str):
            local_time = datetime.fromisoformat(local_time.replace("Z", "+00:00"))
        if isinstance(remote_time, str):
            remote_time = datetime.fromisoformat(remote_time.replace("Z", "+00:00"))

        # Last Write Wins
        if local_time > remote_time:
            return {
                **remote,
                **local,
                "conflict_resolved": True,
                "resolution": "local_wins",
            }
        else:
            return {
                **local,
                **remote,
                "conflict_resolved": True,
                "resolution": "remote_wins",
            }

    def resolve_receipt_conflict(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve POS receipt conflicts.

        Strategy: Business rule - receipts should not conflict if properly designed.
        If conflict, create separate receipt with conflict note.
        """
        # For receipts, conflicts are rare but possible in offline scenarios
        # Strategy: Create a new receipt for the conflicting one

        local_id = local.get("id", "unknown")
        remote_id = remote.get("id", "unknown")

        conflict_receipt = {
            **remote,
            "id": f"conflict_{remote_id}_{datetime.now().timestamp()}",
            "status": "conflict",
            "notes": f"Conflict resolved: duplicate receipt from offline sync. Original: {local_id}",
            "conflict_resolved": True,
            "resolution": "duplicate_created",
        }

        return conflict_receipt

    def resolve_product_conflict(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve product conflicts.

        Strategy: Merge changes, but price changes require manual review.
        """
        merged = {**remote}  # Start with remote as base

        # If price changed on both sides, flag for manual review
        if local.get("price") != remote.get("price"):
            merged["price"] = max(
                local.get("price", 0), remote.get("price", 0)
            )  # Take higher price as conservative
            merged["conflict_resolved"] = False
            merged["resolution"] = "manual_review_required"
            merged["conflict_details"] = {
                "local_price": local.get("price"),
                "remote_price": remote.get("price"),
                "message": "Price conflict requires manual review",
            }
        else:
            # Safe to merge
            merged.update(local)
            merged["conflict_resolved"] = True
            merged["resolution"] = "merged"

        return merged

    def resolve_conflict(
        self, entity_type: str, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main conflict resolution dispatcher.
        """
        resolvers = {
            "stock_items": self.resolve_stock_conflict,
            "pos_receipts": self.resolve_receipt_conflict,
            "products": self.resolve_product_conflict,
        }

        resolver = resolvers.get(entity_type, self._default_resolution)
        return resolver(local, remote)

    def _default_resolution(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Default: Last Write Wins strategy.
        """
        local_time = local.get("updated_at", datetime.min)
        remote_time = remote.get("updated_at", datetime.min)

        if local_time > remote_time:
            return {
                **remote,
                **local,
                "conflict_resolved": True,
                "resolution": "local_wins",
            }
        else:
            return {
                **local,
                **remote,
                "conflict_resolved": True,
                "resolution": "remote_wins",
            }


async def handle_sync_conflicts(
    conflicts: List[Dict[str, Any]], tenant_id: str, db: Session
) -> List[Dict[str, Any]]:
    """
    Process sync conflicts and return resolved changes.

    Called by ElectricSQL during sync operations.
    """
    resolver = ConflictResolver(db, tenant_id)
    resolved_changes = []

    for conflict in conflicts:
        entity_type = conflict.get("table")
        local_data = conflict.get("local", {})
        remote_data = conflict.get("remote", {})

        resolved = resolver.resolve_conflict(entity_type, local_data, remote_data)
        resolved_changes.append(
            {
                "table": entity_type,
                "id": conflict.get("id"),
                "resolved_data": resolved,
                "conflict_handled": True,
            }
        )

        # Log conflict resolution
        log_conflict_resolution(db, tenant_id, conflict, resolved)

    return resolved_changes


def log_conflict_resolution(
    db: Session,
    tenant_id: str,
    original_conflict: Dict[str, Any],
    resolution: Dict[str, Any],
):
    """
    Log conflict resolution for audit purposes.
    """
    try:
        # Insert into conflict log table (would need to create this table)
        db.execute(
            text("""
            INSERT INTO sync_conflict_log (
                tenant_id, entity_type, entity_id,
                conflict_data, resolution, resolved_at
            ) VALUES (
                :tenant_id, :entity_type, :entity_id,
                :conflict_data, :resolution, NOW()
            )
        """),
            {
                "tenant_id": tenant_id,
                "entity_type": original_conflict.get("table"),
                "entity_id": original_conflict.get("id"),
                "conflict_data": original_conflict,
                "resolution": resolution.get("resolution", "unknown"),
            },
        )
        db.commit()
    except Exception as e:
        # Log error but don't fail sync
        print(f"Failed to log conflict resolution: {e}")


# Migration to create conflict log table
CONFLICT_LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sync_conflict_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    conflict_data JSONB,
    resolution TEXT,
    resolved_at TIMESTAMPTZ DEFAULT NOW(),

    INDEX idx_sync_conflicts_tenant (tenant_id),
    INDEX idx_sync_conflicts_entity (entity_type, entity_id)
);
"""
