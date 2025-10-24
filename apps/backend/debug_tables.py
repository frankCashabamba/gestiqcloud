"""Debug script to check table registration"""
import importlib
from app.config.database import Base

# Load models
modules = [
    "app.models.auth.useradmis",
    "app.models.empresa.empresa",
    "app.models.empresa.usuarioempresa",
]

for m in modules:
    try:
        importlib.import_module(m)
        print(f"✓ Imported {m}")
    except Exception as e:
        print(f"✗ Failed {m}: {e}")

print("\n📋 Registered tables in Base.metadata:")
for table_name in sorted(Base.metadata.tables.keys()):
    print(f"  - {table_name}")

if "usuarios_usuarioempresa" in Base.metadata.tables:
    print("\n✅ usuarios_usuarioempresa IS registered")
else:
    print("\n❌ usuarios_usuarioempresa NOT registered")
