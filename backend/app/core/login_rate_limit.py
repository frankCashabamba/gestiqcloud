# app/security/login_rate_limit.py
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from fastapi import Request
from app.config.settings import settings

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None

# ---------- Config (override via settings) ----------
WINDOW_SECONDS = getattr(settings, "LOGIN_WINDOW_SECONDS", 900)           # 15 min
MAX_ATTEMPTS = int(getattr(settings, "LOGIN_MAX_ATTEMPTS", 10))           # 10 fallos (por defecto)
COOLDOWN_SECONDS = getattr(settings, "LOGIN_COOLDOWN_SECONDS", 900)      # 15 min cool-down
BACKOFF_BASE = getattr(settings, "LOGIN_BACKOFF_BASE", 2)                 # 2^n
BACKOFF_STEP = getattr(settings, "LOGIN_BACKOFF_STEP", 2)                 # cada 2 fallos
KEY_PREFIX = getattr(settings, "LOGIN_RL_PREFIX", "rl:login")

# ---------- Redis client (optional) ----------
def _redis_client():
    if not getattr(settings, "REDIS_URL", None) or redis is None:
        return None
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

r = _redis_client()

@dataclass
class RLStatus:
    allowed: bool
    retry_after: int = 0
    remaining: int = MAX_ATTEMPTS
    reason: str = ""

def _key(ip: str, ident: str) -> str:
    ident = (ident or "").strip().lower()
    return f"{KEY_PREFIX}:{ip}:{ident}"

def _now() -> int:
    return int(time.time())

def _calc_backoff(failures: int) -> int:
    # Backoff escalonado: cada BACKOFF_STEP fallos aumenta la potencia
    power = max(0, failures // BACKOFF_STEP)
    return int(BACKOFF_BASE ** power)

# ---------- Public API ----------
def check(request: Request, ident: str) -> RLStatus:
    ip = request.client.host if request.client else "unknown"
    k = _key(ip, ident)

    # Redis path
    if r:
        pipe = r.pipeline(True)
        pipe.get(k)
        pipe.pttl(k)
        current, ttl = pipe.execute()
        failures = int(current or 0)
        remaining = max(0, MAX_ATTEMPTS - failures)
        if failures >= MAX_ATTEMPTS:
            retry_after = int((ttl or COOLDOWN_SECONDS*1000) / 1000)
            return RLStatus(False, retry_after=retry_after, remaining=0, reason="max_attempts")
        # Soft backoff
        backoff = _calc_backoff(failures)
        if backoff > 0:
            # Si hay backoff, pedimos al cliente que espere (no bloqueamos estrictamente)
            return RLStatus(True, retry_after=backoff, remaining=remaining, reason="backoff")
        return RLStatus(True, retry_after=0, remaining=remaining, reason="ok")
    # Fallback en memoria por proceso (mejor usar Redis en prod)
    # Nota: este fallback se resetea si el proceso reinicia
    store = getattr(check, "_mem", {})
    now = _now()
    window = getattr(check, "_window", WINDOW_SECONDS)
    entry = store.get(k) or {"failures": 0, "reset": now + window}
    if now > entry["reset"]:
        entry = {"failures": 0, "reset": now + window}
    failures = entry["failures"]
    remaining = max(0, MAX_ATTEMPTS - failures)
    if failures >= MAX_ATTEMPTS:
        retry_after = max(1, entry["reset"] - now)
        return RLStatus(False, retry_after=retry_after, remaining=0, reason="max_attempts")
    backoff = _calc_backoff(failures)
    check._mem = {**store, k: entry}
    return RLStatus(True, retry_after=backoff, remaining=remaining, reason="ok")

def incr_fail(request: Request, ident: str) -> RLStatus:
    ip = request.client.host if request.client else "unknown"
    k = _key(ip, ident)

    if r:
        # INCR + set TTL si no existe
        pipe = r.pipeline(True)
        pipe.incr(k, 1)
        pipe.expire(k, WINDOW_SECONDS)
        failures, _ = pipe.execute()
        if failures >= MAX_ATTEMPTS:
            r.expire(k, COOLDOWN_SECONDS)
            return RLStatus(False, retry_after=COOLDOWN_SECONDS, remaining=0, reason="max_attempts")
        remaining = max(0, MAX_ATTEMPTS - failures)
        return RLStatus(True, retry_after=_calc_backoff(failures), remaining=remaining, reason="fail_inc")
    # fallback memoria
    store = getattr(check, "_mem", {})
    now = _now()
    entry = store.get(k)
    if not entry or now > entry["reset"]:
        entry = {"failures": 0, "reset": now + WINDOW_SECONDS}
    entry["failures"] += 1
    failures = entry["failures"]
    check._mem = {**store, k: entry}
    if failures >= MAX_ATTEMPTS:
        entry["reset"] = now + COOLDOWN_SECONDS
        return RLStatus(False, retry_after=COOLDOWN_SECONDS, remaining=0, reason="max_attempts")
    remaining = max(0, MAX_ATTEMPTS - failures)
    return RLStatus(True, retry_after=_calc_backoff(failures), remaining=remaining, reason="fail_inc")

def reset(request: Request, ident: str) -> None:
    ip = request.client.host if request.client else "unknown"
    k = _key(ip, ident)
    if r:
        r.delete(k)
        return
    store = getattr(check, "_mem", {})
    if k in store:
        del store[k]
        check._mem = store

def _login_ident(email: str, realm: str) -> str:
    return f"{realm}:{email.strip().lower()}"

def _forgot_ident(email: str, realm: str) -> str:
    return f"forgot:{realm}:{email.strip().lower()}"
