#!/usr/bin/env python
"""Debug script to test token generation and validation."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-test-secret-key-1234567890")
os.environ.setdefault(
    "JWT_SECRET_KEY", "jwt-test-secret-key-jwt-test-secret-key-jwt-test-secret-1234"
)
os.environ.setdefault("ENV", "development")

import base64
import json

from app.modules.identity.infrastructure.jwt_service import JwtService

# Create token service
svc = JwtService()

# Test payload
payload = {
    "user_id": "test-user",
    "tenant_id": "test-tenant",
    "sub": "test@example.com",
    "kind": "tenant",
}

# Encode
token = svc.encode(payload, kind="access")
print(f"Token: {token[:50]}...")

# Decode parts to see what's in the token
parts = token.split(".")
if len(parts) == 3:
    # Decode header
    header_b64 = parts[0]
    padding = 4 - (len(header_b64) % 4)
    if padding != 4:
        header_b64 += "=" * padding
    header = json.loads(base64.urlsafe_b64decode(header_b64))
    print(f"Header: {json.dumps(header, indent=2)}")

    # Decode payload
    payload_b64 = parts[1]
    padding = 4 - (len(payload_b64) % 4)
    if padding != 4:
        payload_b64 += "=" * padding
    decoded_payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    print(f"Payload: {json.dumps(decoded_payload, indent=2)}")

# Try to decode
try:
    decoded = svc.decode(token, expected_kind="access")
    print(f"Decoded successfully: {json.dumps(decoded, indent=2)}")
except Exception as e:
    print(f"Decode failed: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
