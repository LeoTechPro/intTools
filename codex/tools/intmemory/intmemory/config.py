from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re


DEFAULT_SCOPE_ROOTS = ("D:\\int", "/int")


def _split_scope_roots(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return DEFAULT_SCOPE_ROOTS
    parts = [item.strip() for item in re.split(r"[;\n,]+", raw) if item.strip()]
    return tuple(parts or DEFAULT_SCOPE_ROOTS)


@dataclass(slots=True)
class IntMemoryConfig:
    owner_id: int | None
    api_base_url: str
    agent_id: str
    agent_key: str
    api_timeout_sec: float
    codex_home: Path
    state_path: Path
    scope_roots: tuple[str, ...]
    source_name: str = "codex.intmemory.v1"

    @classmethod
    def from_env(cls) -> "IntMemoryConfig":
        codex_home = Path(
            os.environ.get(
                "INTMEMORY_CODEX_HOME",
                str(Path.home() / ".codex"),
            )
        ).expanduser()
        state_path = Path(
            os.environ.get(
                "INTMEMORY_STATE_PATH",
                str(codex_home / "memories" / "intmemory" / "state.json"),
            )
        ).expanduser()
        owner_raw = os.environ.get("INTMEMORY_OWNER_ID", "").strip()
        owner_id = int(owner_raw) if owner_raw else None
        return cls(
            owner_id=owner_id,
            api_base_url=os.environ.get("INTBRAIN_API_BASE_URL", "https://brain.api.intdata.pro/api/core/v1").rstrip("/"),
            agent_id=os.environ.get("INTBRAIN_AGENT_ID", "").strip(),
            agent_key=os.environ.get("INTBRAIN_AGENT_KEY", "").strip(),
            api_timeout_sec=float(os.environ.get("INTBRAIN_API_TIMEOUT_SEC", "15")),
            codex_home=codex_home,
            state_path=state_path,
            scope_roots=_split_scope_roots(os.environ.get("INTMEMORY_SCOPE_ROOTS")),
        )
