from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and not key.startswith("#"):
            os.environ.setdefault(key, _strip_quotes(value))


def normalize_webhook_url(value: str) -> str:
    url = value.strip()
    if url and not url.endswith("/"):
        url += "/"
    return url


@dataclass(frozen=True)
class Config:
    webhook_url: str
    transport: str
    port: int
    timeout: float
    root_dir: Path

    @property
    def has_webhook_url(self) -> bool:
        return bool(self.webhook_url)

    @classmethod
    def load(cls) -> "Config":
        root_dir = Path(__file__).resolve().parents[1]
        load_env_file(root_dir / ".env")
        webhook_url = (
            os.getenv("BITRIX_WEBHOOK_URL")
            or os.getenv("BITRIX_WEBHOOK_BASE_URL")
            or ""
        )
        return cls(
            webhook_url=normalize_webhook_url(webhook_url),
            transport=os.getenv("BITRIX_TRANSPORT", "stdio").strip().lower(),
            port=int(os.getenv("BITRIX_PORT", "8012")),
            timeout=float(os.getenv("BITRIX_TIMEOUT", "30")),
            root_dir=root_dir,
        )
