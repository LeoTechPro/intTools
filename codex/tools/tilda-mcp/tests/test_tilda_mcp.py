from __future__ import annotations

import os
from pathlib import Path
import stat

import pytest

from launcher import LauncherError, build_environment, load_secret_file
from tilda_mcp.client import TildaClient, TildaConfigError


def _secret_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "tilda.env"
    path.write_text(text, encoding="utf-8")
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


def test_loads_only_allowlisted_values(tmp_path: Path) -> None:
    path = _secret_file(
        tmp_path,
        "TILDA_PUBLIC_KEY=public\nTILDA_SECRET_KEY=secret\nTILDA_PROJECT_ID=3211313\n",
    )
    values = load_secret_file(path)
    assert set(values) == {
        "TILDA_PUBLIC_KEY",
        "TILDA_SECRET_KEY",
        "TILDA_PROJECT_ID",
    }


def test_rejects_unknown_variable(tmp_path: Path) -> None:
    path = _secret_file(
        tmp_path,
        "TILDA_PUBLIC_KEY=public\nTILDA_SECRET_KEY=secret\nOTHER=value\n",
    )
    with pytest.raises(LauncherError, match="Unsupported variable"):
        load_secret_file(path)


def test_rejects_missing_secret(tmp_path: Path) -> None:
    path = _secret_file(tmp_path, "TILDA_PUBLIC_KEY=public\n")
    with pytest.raises(LauncherError, match="TILDA_SECRET_KEY"):
        load_secret_file(path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_rejects_group_readable_file(tmp_path: Path) -> None:
    path = _secret_file(
        tmp_path,
        "TILDA_PUBLIC_KEY=public\nTILDA_SECRET_KEY=secret\n",
    )
    path.chmod(0o640)
    with pytest.raises(LauncherError, match="0600"):
        load_secret_file(path)


def test_build_environment_sets_source_path(tmp_path: Path) -> None:
    path = _secret_file(
        tmp_path,
        "TILDA_PUBLIC_KEY=public\nTILDA_SECRET_KEY=secret\n",
    )
    environment = build_environment(path)
    assert Path(__file__).parents[1].as_posix() in environment["PYTHONPATH"].replace("\\", "/")


def test_client_requires_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TILDA_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("TILDA_SECRET_KEY", raising=False)
    with pytest.raises(TildaConfigError):
        TildaClient.from_env()
