import datetime as dt
import unicodedata
import time


def utcnow_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def slugify(text: str) -> str:
    text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    text = "".join(c if c.isalnum() else "-" for c in text.lower())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")


def now_ts() -> int:
    """Epoch seconds (UTC)."""
    return int(time.time())

def ping_ok() -> dict:
    return {"ok": True}
