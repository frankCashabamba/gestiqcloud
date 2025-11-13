# app/utils/time.py
from datetime import UTC, datetime  # Python 3.11+


def utcnow() -> datetime:
    # Devuelve un datetime con zona horaria (timezone-aware) en UTC
    return datetime.now(UTC)
