#!/usr/bin/env python3
"""
Seed inicial: crea empresa, usuario de empresa y superusuario admin.

Uso:
  python scripts/py/seed_initial.py \
    --empresa "Mi Empresa" --slug "mi-empresa" \
    --tenant-user "usuario" --tenant-email "usuario@empresa.com" --tenant-pass "secreto" \
    --admin-user "admin" --admin-email "admin@gestiqcloud.com" --admin-pass "adminpass"

Requiere que la app pueda importar app.config.database y modelos.
Lee DATABASE_URL de entorno (como el API).
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--empresa", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--tenant-user", required=True)
    parser.add_argument("--tenant-email", required=True)
    parser.add_argument("--tenant-pass", required=True)
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-pass", required=True)
    args = parser.parse_args(argv)

    # Importar app (soporta rutas del monorepo)
    try:
        from app.config.database import session_scope
        from app.models.empresa.empresa import Empresa
        from app.models.empresa.usuarioempresa import UsuarioEmpresa
        from app.models.auth.useradmis import SuperUser
        from app.core.security import hash_password
    except Exception:
        # fallback si se ejecuta desde raíz distinta
        from apps.backend.app.config.database import session_scope  # type: ignore
        from apps.backend.app.models.empresa.empresa import Empresa  # type: ignore
        from apps.backend.app.models.empresa.usuarioempresa import UsuarioEmpresa  # type: ignore
        from apps.backend.app.models.auth.useradmis import SuperUser  # type: ignore
        from apps.backend.app.core.security import hash_password  # type: ignore

    with session_scope() as db:
        # Empresa
        empresa = db.query(Empresa).filter(Empresa.slug == args.slug).first()
        if not empresa:
            empresa = Empresa(nombre=args.empresa, slug=args.slug)
            db.add(empresa)
            db.flush()
            print(f"✔ Empresa creada: {empresa.id} {empresa.nombre}")
        else:
            print(f"↪ Empresa existente: {empresa.id} {empresa.nombre}")

        # Usuario de empresa
        ten = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.email == args.tenant_email).first()
        if not ten:
            ten = UsuarioEmpresa(
                empresa_id=empresa.id,
                nombre_encargado=args.tenant_user,
                apellido_encargado="",
                email=args.tenant_email,
                username=args.tenant_user,
                activo=True,
                es_admin_empresa=True,
                password_hash=hash_password(args.tenant_pass),
                is_verified=True,
            )
            db.add(ten)
            print(f"✔ UsuarioEmpresa creado: {ten.email}")
        else:
            print(f"↪ UsuarioEmpresa existente: {ten.email}")

        # SuperUser (admin global)
        su = db.query(SuperUser).filter(SuperUser.username == args.admin_user).first()
        if not su:
            su = SuperUser(
                username=args.admin_user,
                email=args.admin_email,
                password_hash=hash_password(args.admin_pass),
                is_active=True,
                is_superadmin=True,
                is_staff=True,
                is_verified=True,
            )
            db.add(su)
            print(f"✔ SuperUser creado: {su.username}")
        else:
            print(f"↪ SuperUser existente: {su.username}")

    print("✅ Seed completado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

