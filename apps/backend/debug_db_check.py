"""Debug test to check DB setup"""
import os
import sys

# Set test env
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["FRONTEND_URL"] = "http://localhost:8081"
os.environ["TENANT_NAMESPACE_UUID"] = "00000000-0000-0000-0000-000000000000"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["REFRESH_SECRET"] = "test-refresh"

from app.config.database import Base, engine
import importlib

# Import models
models = [
    "app.models.auth.useradmis",
    "app.models.empresa.empresa",
    "app.models.empresa.usuarioempresa",
]

print("Loading models...")
for m in models:
    try:
        importlib.import_module(m)
        print(f"  OK {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")

print("\nCreating tables...")
Base.metadata.create_all(bind=engine)

print("\n📋 Tables in metadata:")
for table_name in sorted(Base.metadata.tables.keys()):
    print(f"  - {table_name}")

print("\n✅ Check if usuarios_usuarioempresa exists:")
print(f"  {'usuarios_usuarioempresa' in Base.metadata.tables}")

# Check actual DB
from sqlalchemy import inspect
inspector = inspect(engine)
print("\n🗂️  Tables in SQLite database:")
for table_name in sorted(inspector.get_table_names()):
    print(f"  - {table_name}")
