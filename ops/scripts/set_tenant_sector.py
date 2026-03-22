#!/usr/bin/env python3
"""
Configura el sector/plantilla de un tenant por su slug o nombre.

Uso:
  python ops/scripts/set_tenant_sector.py --slug demo-empresa --sector panaderia_pro
  python ops/scripts/set_tenant_sector.py --name "demo empresa" --sector panaderia_pro

Sectores válidos: panaderia, panaderia_pro, taller, taller_pro, retail, default
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from app.config.database import SessionLocal
from app.models.tenant import Tenant


def main():
    p = argparse.ArgumentParser(description="Set tenant sector template")
    p.add_argument("--slug", help="Tenant slug (e.g. demo-empresa)")
    p.add_argument("--name", help="Tenant name (e.g. 'demo empresa')")
    p.add_argument("--sector", required=True, help="Sector code (e.g. panaderia_pro)")
    args = p.parse_args()

    if not args.slug and not args.name:
        print("ERROR: Debes especificar --slug o --name")
        sys.exit(1)

    db = SessionLocal()
    try:
        query = db.query(Tenant)
        if args.slug:
            tenant = query.filter(Tenant.slug == args.slug).first()
        else:
            tenant = query.filter(Tenant.name.ilike(f"%{args.name}%")).first()

        if not tenant:
            identifier = args.slug or args.name
            print(f"ERROR: No se encontró tenant con slug/nombre '{identifier}'")
            # List available tenants
            tenants = db.query(Tenant.slug, Tenant.name, Tenant.sector_template_name).limit(10).all()
            print("\nTenants disponibles:")
            for t in tenants:
                print(f"  slug={t.slug!r}  name={t.name!r}  sector={t.sector_template_name!r}")
            sys.exit(1)

        old_sector = tenant.sector_template_name
        tenant.sector_template_name = args.sector
        db.add(tenant)
        db.commit()
        print(f"OK: Tenant '{tenant.name}' (slug={tenant.slug!r})")
        print(f"    sector: {old_sector!r} -> {args.sector!r}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
