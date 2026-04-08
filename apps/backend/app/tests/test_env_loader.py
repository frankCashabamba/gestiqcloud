from __future__ import annotations

from app.config.env_loader import load_env_file


def test_load_env_file_layers_env_local_and_env(tmp_path):
    local_path = tmp_path / ".env.local"
    root_path = tmp_path / ".env"

    local_path.write_text(
        "LOCAL_ONLY=from-local\n"
        "SHARED=value-from-local\n",
        encoding="utf-8",
    )
    root_path.write_text(
        "ROOT_ONLY=from-root\n"
        "SHARED=value-from-root\n",
        encoding="utf-8",
    )

    loaded = load_env_file(local_path)

    assert loaded["LOCAL_ONLY"] == "from-local"
    assert loaded["ROOT_ONLY"] == "from-root"
    assert loaded["SHARED"] == "value-from-local"
