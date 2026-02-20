#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

# Allow running from repo root: python scripts/merge_duplicate_products.py
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/backend"))

from app.config.database import SessionLocal  # noqa: E402


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    txt = unicodedata.normalize("NFKD", str(value))
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = txt.lower().strip()
    out = []
    prev_space = False
    for ch in txt:
        if ch.isalnum():
            out.append(ch)
            prev_space = False
        else:
            if not prev_space:
                out.append(" ")
                prev_space = True
    return "".join(out).strip()


def _normalize_tokens(value: str | None) -> list[str]:
    base = _normalize_name(value)
    if not base:
        return []
    tokens: list[str] = []
    for tok in base.split():
        if len(tok) > 3 and tok.endswith("s"):
            tokens.append(tok[:-1])
        else:
            tokens.append(tok)
    return tokens


def _similar_name(a: str | None, b: str | None, threshold: float) -> bool:
    a_tokens = _normalize_tokens(a)
    b_tokens = _normalize_tokens(b)
    if not a_tokens or not b_tokens:
        return False
    a_num = {t for t in a_tokens if any(ch.isdigit() for ch in t)}
    b_num = {t for t in b_tokens if any(ch.isdigit() for ch in t)}
    # If both names carry numeric variants (size/weight/presentation) and differ,
    # treat them as different products.
    if a_num and b_num and a_num != b_num:
        return False
    sa = " ".join(a_tokens)
    sb = " ".join(b_tokens)
    if sa == sb:
        return True
    if sa in sb or sb in sa:
        min_len = min(len(sa), len(sb))
        max_len = max(len(sa), len(sb))
        if min_len >= 4 and (min_len / max_len) >= 0.6:
            return True
    ratio = SequenceMatcher(None, sa, sb).ratio()
    if ratio >= threshold:
        return True
    aset = set(a_tokens)
    bset = set(b_tokens)
    # Avoid overly broad merges when one side is a single generic token
    # (e.g. "agua" vs "agua dasani 600ml").
    if len(aset) == 1 or len(bset) == 1:
        return False
    overlap = len(aset.intersection(bset))
    if overlap == 0:
        return False
    min_side = overlap / max(min(len(aset), len(bset)), 1)
    jaccard = overlap / max(len(aset.union(bset)), 1)
    return min_side >= 0.8 and jaccard >= 0.55


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@dataclass
class ProductRow:
    id: UUID
    name: str
    sku: str | None
    created_at: datetime | None
    ref_count: int = 0


class DSU:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _find_product_fk_tables(db) -> list[tuple[str, bool]]:
    rows = db.execute(
        text(
            """
            SELECT c.table_name
            FROM information_schema.columns c
            WHERE c.table_schema='public'
              AND c.column_name='product_id'
              AND c.table_name <> 'products'
            ORDER BY c.table_name
            """
        )
    ).fetchall()
    tables = [str(r[0]) for r in rows]
    out: list[tuple[str, bool]] = []
    for table in tables:
        has_tenant = (
            db.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name=:tbl
                      AND column_name='tenant_id'
                    LIMIT 1
                    """
                ),
                {"tbl": table},
            ).first()
            is not None
        )
        out.append((table, has_tenant))
    return out


def _count_refs(db, tenant_id: str, product_id: UUID, tables: list[tuple[str, bool]]) -> int:
    total = 0
    for table, has_tenant in tables:
        qtable = _quote_ident(table)
        if has_tenant:
            count = db.execute(
                text(
                    f"SELECT COUNT(*) FROM public.{qtable} "
                    "WHERE tenant_id=:tid AND product_id=:pid"
                ),
                {"tid": tenant_id, "pid": str(product_id)},
            ).scalar() or 0
        else:
            count = db.execute(
                text(f"SELECT COUNT(*) FROM public.{qtable} WHERE product_id=:pid"),
                {"pid": str(product_id)},
            ).scalar() or 0
        total += int(count)
    return total


def _load_products(db, tenant_id: str) -> list[ProductRow]:
    rows = db.execute(
        text(
            """
            SELECT id, name, sku, created_at
            FROM products
            WHERE tenant_id=:tid
            ORDER BY created_at ASC NULLS LAST, name ASC
            """
        ),
        {"tid": tenant_id},
    ).fetchall()
    out: list[ProductRow] = []
    for r in rows:
        out.append(
            ProductRow(
                id=r[0] if isinstance(r[0], UUID) else UUID(str(r[0])),
                name=str(r[1] or ""),
                sku=(str(r[2]).strip() if r[2] else None),
                created_at=r[3],
            )
        )
    return out


def _cluster_products(products: list[ProductRow], threshold: float) -> list[list[ProductRow]]:
    n = len(products)
    dsu = DSU(n)
    for i in range(n):
        for j in range(i + 1, n):
            if _similar_name(products[i].name, products[j].name, threshold):
                dsu.union(i, j)
    groups: dict[int, list[ProductRow]] = {}
    for i, p in enumerate(products):
        root = dsu.find(i)
        groups.setdefault(root, []).append(p)
    return [g for g in groups.values() if len(g) > 1]


def _pick_survivor(group: list[ProductRow]) -> ProductRow:
    # Prefer SKU, then most references, then oldest created_at.
    def score(p: ProductRow):
        has_sku = 1 if (p.sku and p.sku.strip()) else 0
        created = p.created_at or datetime.max
        return (-has_sku, -p.ref_count, created, str(p.id))

    return sorted(group, key=score)[0]


def _apply_merge(
    db,
    tenant_id: str,
    winner_id: UUID,
    loser_id: UUID,
    tables: list[tuple[str, bool]],
) -> dict[str, int]:
    updated_by_table: dict[str, int] = {}
    for table, has_tenant in tables:
        qtable = _quote_ident(table)
        if has_tenant:
            res = db.execute(
                text(
                    f"UPDATE public.{qtable} "
                    "SET product_id=:winner "
                    "WHERE tenant_id=:tid AND product_id=:loser"
                ),
                {
                    "winner": str(winner_id),
                    "loser": str(loser_id),
                    "tid": tenant_id,
                },
            )
        else:
            res = db.execute(
                text(
                    f"UPDATE public.{qtable} "
                    "SET product_id=:winner "
                    "WHERE product_id=:loser"
                ),
                {
                    "winner": str(winner_id),
                    "loser": str(loser_id),
                },
            )
        updated = int(res.rowcount or 0)
        if updated > 0:
            updated_by_table[table] = updated

    db.execute(
        text("DELETE FROM products WHERE tenant_id=:tid AND id=:pid"),
        {"tid": tenant_id, "pid": str(loser_id)},
    )
    return updated_by_table


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge duplicate products by similar name for one tenant."
    )
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.88,
        help="Name similarity threshold (default: 0.88)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, runs in dry-run mode.",
    )
    args = parser.parse_args()

    tenant_id = str(UUID(args.tenant_id))

    with SessionLocal() as db:
        tables = _find_product_fk_tables(db)
        products = _load_products(db, tenant_id)
        if not products:
            print("No products found for tenant.")
            return 0

        for p in products:
            p.ref_count = _count_refs(db, tenant_id, p.id, tables)

        groups = _cluster_products(products, args.threshold)
        if not groups:
            print("No duplicate groups found.")
            return 0

        print(f"Found {len(groups)} duplicate group(s).")
        merge_plan: list[tuple[ProductRow, ProductRow]] = []
        for idx, group in enumerate(groups, start=1):
            winner = _pick_survivor(group)
            losers = [p for p in group if p.id != winner.id]
            print(
                f"\n[{idx}] Winner: {winner.name} ({winner.id}) sku={winner.sku} refs={winner.ref_count}"
            )
            for loser in losers:
                print(
                    f"    - loser: {loser.name} ({loser.id}) sku={loser.sku} refs={loser.ref_count}"
                )
                merge_plan.append((winner, loser))

        if not args.apply:
            print("\nDry-run complete. Re-run with --apply to execute merges.")
            return 0

        print("\nApplying merges...")
        try:
            for winner, loser in merge_plan:
                updated = _apply_merge(db, tenant_id, winner.id, loser.id, tables)
                if updated:
                    details = ", ".join(f"{k}:{v}" for k, v in sorted(updated.items()))
                    print(f"Merged {loser.id} -> {winner.id} [{details}]")
                else:
                    print(f"Merged {loser.id} -> {winner.id} [no references moved]")
            db.commit()
            print("\nMerge complete.")
            return 0
        except Exception as exc:
            db.rollback()
            print(f"ERROR applying merge: {exc}")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
