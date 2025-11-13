#!/usr/bin/env python3
"""Generate test JWT token for kusi panaderia tenant"""

import datetime
import os

import jwt

SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")

payload = {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "tenant_id": "5c7bea07-05ca-457f-b321-722b1628b170",
    "roles": ["owner"],
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30),
    "iat": datetime.datetime.utcnow(),
}

token = jwt.encode(payload, SECRET, algorithm="HS256")
print("\n[OK] Token de prueba generado (valido 30 dias):\n")
print(token)
print("\n[INFO] Usar con:")
print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/products/')
print("\n[INFO] O en localStorage del navegador:")
print(f"localStorage.setItem('auth_token', '{token}')")
print()
