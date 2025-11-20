# app/security/login_rate_limit.py
import logging
import os
import time
from dataclasses import dataclass

from fastapi import Request

from app.config.settings import settings

_logger = logging.getLogger(__name__)

try:
    # Prefer shared utils when available
    from apps.backend.app.shared.utils import now_ts, utcnow_iso  # type: ignore
except Exception:
    # Minimal fallbacks for test/CI environments without 'apps' alias
    def now_ts() -> int:
        return int(time.time())

    def utcnow_iso() -> str:
        import datetime as _dt

        return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None

# ---------- Config (override via settings) ----------
WINDOW_SECONDS = getattr(settings, "LOGIN_WINDOW_SECONDS", 900)  # 15 min
MAX_ATTEMPTS = int(getattr(settings, "LOGIN_MAX_ATTEMPTS", 10))  # 10 fallos (por defecto)
COOLDOWN_SECONDS = getattr(settings, "LOGIN_COOLDOWN_SECONDS", 900)  # 15 min cool-down
BACKOFF_BASE = getattr(settings, "LOGIN_BACKOFF_BASE", 2)  # 2^n
BACKOFF_STEP = getattr(settings, "LOGIN_BACKOFF_STEP", 2)  # cada 2 fallos
KEY_PREFIX = getattr(settings, "LOGIN_RL_PREFIX", "rl:login")
RL_ENABLED = str(os.getenv("LOGIN_RATE_LIMIT_ENABLED", "1")).lower() not in ("0", "false")


# ---------- Redis client (optional) ----------
def _redis_client():
    # Check if Redis is disabled via env var (for tests)
    if os.getenv("DISABLE_REDIS") == "1":
        return None
    if not getattr(settings, "REDIS_URL", None) or redis is None:
        return None
    try:
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


r = _redis_client()


def _disable_redis(exc: Exception) -> None:
    global r
    _logger.warning("Disabling Redis for login rate limiting: %s", exc)
    if not r:
        return
    try:
        r.close()
    except Exception:
        pass
    r = None


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
    import warnings

    warnings.warn(
        "Deprecated: use apps.backend.app.shared.utils.now_ts",
        DeprecationWarning,
        stacklevel=2,
    )
    return now_ts()


def _calc_backoff(failures: int) -> int:
    # Backoff escalonado: cada BACKOFF_STEP fallos aumenta la potencia
    power = max(0, failures // BACKOFF_STEP)
    return int(BACKOFF_BASE**power)


# ---------- Public API ----------
def check(request: Request, ident: str) -> RLStatus:
    if not RL_ENABLED:
        return RLStatus(True, retry_after=0, remaining=MAX_ATTEMPTS, reason="disabled")
    ip = request.client.host if request.client else "unknown"
    k = _key(ip, ident)

    # Redis path
    if r:
        try:
            pipe = r.pipeline(True)
            pipe.get(k)
            pipe.pttl(k)
            current, ttl = pipe.execute()
        except redis.RedisError as exc:  # pragma: no cover - best effort logging
            _disable_redis(exc)
        else:
            failures = int(current or 0)
            remaining = max(0, MAX_ATTEMPTS - failures)
            if failures >= MAX_ATTEMPTS:
                retry_after = int((ttl or COOLDOWN_SECONDS * 1000) / 1000)
                return RLStatus(
                    False,
                    retry_after=retry_after,
                    remaining=0,
                    reason="max_attempts",
                )
            # Soft backoff
            backoff = _calc_backoff(failures)
            if backoff > 0:
                # Si hay backoff, pedimos al cliente que espere (no bloqueamos estrictamente)
                return RLStatus(True, retry_after=backoff, remaining=remaining, reason="backoff")
            return RLStatus(True, retry_after=0, remaining=remaining, reason="ok")
    # Fallback en memoria por proceso (mejor usar Redis en prod)
    # Nota: este fallback se resetea si el proceso reinicia
    store = getattr(check, "_mem", {})
    now = now_ts()
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
    if not RL_ENABLED:
        return RLStatus(True, retry_after=0, remaining=MAX_ATTEMPTS, reason="disabled")
    ip = request.client.host if request.client else "unknown"
    k = _key(ip, ident)

    if r:
        try:
            # INCR + set TTL si no existe
            pipe = r.pipeline(True)
            pipe.incr(k, 1)
            pipe.expire(k, WINDOW_SECONDS)
            failures, _ = pipe.execute()
            if failures >= MAX_ATTEMPTS:
                r.expire(k, COOLDOWN_SECONDS)
                return RLStatus(
                    False,
                    retry_after=COOLDOWN_SECONDS,
                    remaining=0,
                    reason="max_attempts",
                )
            remaining = max(0, MAX_ATTEMPTS - failures)
            return RLStatus(
                True,
                retry_after=_calc_backoff(failures),
                remaining=remaining,
                reason="fail_inc",
            )
        except redis.RedisError as exc:  # pragma: no cover - best effort logging
            _disable_redis(exc)
    # fallback memoria
    store = getattr(check, "_mem", {})
    now = now_ts()
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
    return RLStatus(
        True,
        retry_after=_calc_backoff(failures),
        remaining=remaining,
        reason="fail_inc",
    )


def reset(request: Request, ident: str) -> None:
    if not RL_ENABLED:
        return
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
