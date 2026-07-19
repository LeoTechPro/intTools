from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

API_KEY_ENV_NAMES = (
    "GETCOURSE_API_KEY",
    "GETCOURSE_LMS_PUNCTB_PRO_API_KEY",
    "GETCOURSE_LMS_PUNKTB_PRO_API_KEY",
)


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
        if not key or key.startswith("#"):
            continue

        os.environ.setdefault(key, _strip_quotes(value))


def normalize_domain(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("GETCOURSE_ACCOUNT_DOMAIN must be a valid hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("GETCOURSE_ACCOUNT_DOMAIN must not contain credentials, path, query, or fragment")
    return parsed.hostname.lower()


@dataclass(frozen=True)
class Config:
    account_domain: str
    api_key: str | None
    transport: str
    port: int
    timeout: float
    root_dir: Path

    @property
    def api_base_url(self) -> str:
        return f"https://{self.account_domain}"

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    @classmethod
    def load(cls) -> "Config":
        root_dir = Path(__file__).resolve().parents[1]
        load_env_file(root_dir / ".env")

        domain = (
            os.getenv("GETCOURSE_ACCOUNT_DOMAIN")
            or os.getenv("GETCOURSE_DOMAIN")
            or os.getenv("GETCOURSE_BASE_DOMAIN")
            or ""
        )

        api_key = next((os.getenv(name) for name in API_KEY_ENV_NAMES if os.getenv(name)), None)
        transport = os.getenv("GETCOURSE_TRANSPORT", "stdio").strip().lower()

        return cls(
            account_domain=normalize_domain(domain),
            api_key=api_key,
            transport=transport,
            port=int(os.getenv("GETCOURSE_PORT", "8011")),
            timeout=float(os.getenv("GETCOURSE_TIMEOUT", "30")),
            root_dir=root_dir,
        )
