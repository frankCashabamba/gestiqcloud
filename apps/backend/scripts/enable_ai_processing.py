#!/usr/bin/env python
"""
Activa el procesamiento IA en el importador.
Uso: python scripts/enable_ai_processing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import SessionLocal
from app.models.importador import ImpConfig

KEYS = {
    "processing_runtime": {
        "ai_enabled": "true",
        "pre_extract_image_force_ai": "true",
    }
}

def main():
    db = SessionLocal()
    try:
        for module, keys in KEYS.items():
            for key, value in keys.items():
                row = db.query(ImpConfig).filter_by(module=module, key=key).first()
                if row:
                    row.value_text = value
                    print(f"  UPDATED  {module}.{key} = {value}")
                else:
                    db.add(ImpConfig(module=module, key=key, value_text=value))
                    print(f"  INSERTED {module}.{key} = {value}")
        db.commit()
        print("\nListo. Reinicia el worker para aplicar los cambios.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
