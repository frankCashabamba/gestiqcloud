from app.shared.utils import now_ts, ping_ok


def test_now_ts_and_ping_ok():
    t = now_ts()
    assert isinstance(t, int)
    assert t > 0
    assert ping_ok() == {"ok": True}

