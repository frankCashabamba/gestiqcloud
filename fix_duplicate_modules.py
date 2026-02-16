#!/usr/bin/env python3
"""Deactivate old Spanish module entries to avoid duplicates."""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(str(backend_path))

from app.config.database import SessionLocal
from app.models.core.module import Module

def main():
    db = SessionLocal()
    try:
        # Spanish modules to deactivate (they're duplicates of the English versions)
        modules_to_deactivate = [
            ("Compras", "purchases"),       # Duplicate of purchases
            ("Ventas", "sales"),            # Duplicate of sales  
            ("Facturacion", "billing"),     # Duplicate of billing
        ]
        
        print("[INFO] Deactivating duplicate Spanish module entries...\n")
        
        for spanish_name, english_id in modules_to_deactivate:
            spanish_mod = db.query(Module).filter(Module.name == spanish_name).first()
            english_mod = db.query(Module).filter(Module.url == english_id).first()
            
            if spanish_mod and english_mod:
                print(f"[PAIR] '{spanish_name}' (no URL) <-> '{english_mod.name}' (URL: {english_mod.url})")
                print(f"  - Spanish module ID: {spanish_mod.id}")
                print(f"  - English module ID: {english_mod.id}")
                
                if spanish_mod.active:
                    spanish_mod.active = False
                    print(f"  - Deactivating '{spanish_name}'...")
                else:
                    print(f"  - '{spanish_name}' already inactive")
                print()
        
        db.commit()
        print("[SUCCESS] Deactivation completed\n")
        
        # Verify
        print("[VERIFY] Checking active modules now:\n")
        active_modules = db.query(Module).filter(Module.active == True).order_by(Module.name).all()
        print(f"Total active modules: {len(active_modules)}\n")
        for m in active_modules:
            print(f"  {m.name:30} | URL: {m.url or '-':20}")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
