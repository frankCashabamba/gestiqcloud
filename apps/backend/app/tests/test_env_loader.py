from __future__ import annotations

from app.config.env_loader import load_env_file


def test_load_env_file_reads_only_selected_file(tmp_path):
    env_path = tmp_path / ".env"
    sibling_local_path = tmp_path / ".env.local"

    env_path.write_text(
        "ROOT_ONLY=from-root\n" "SHARED=value-from-root\n",
        encoding="utf-8",
    )
    sibling_local_path.write_text(
        "LOCAL_ONLY=from-local\n" "SHARED=value-from-local\n",
        encoding="utf-8",
    )

    loaded = load_env_file(env_path)

    assert loaded["ROOT_ONLY"] == "from-root"
    assert loaded["SHARED"] == "value-from-root"
    assert "LOCAL_ONLY" not in loaded
