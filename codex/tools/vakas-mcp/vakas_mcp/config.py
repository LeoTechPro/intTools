from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


EVENT_ENV_PREFIX = {
    "registration": "VAKAS_REGISTRATION_ENDPOINT",
    "report": "VAKAS_REPORT_ENDPOINT",
    "order": "VAKAS_ORDER_ENDPOINT",
}


class ConfigError(ValueError):
    """Raised when runtime configuration violates the safety contract."""


def _positive_float(value: str, *, name: str, default: float, maximum: float) -> float:
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if parsed <= 0 or parsed > maximum:
        raise ConfigError(f"{name} must be greater than 0 and at most {maximum:g}")
    return parsed


def _positive_int(value: str, *, name: str, default: int, maximum: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if parsed <= 0 or parsed > maximum:
        raise ConfigError(f"{name} must be greater than 0 and at most {maximum}")
    return parsed


def _load_endpoint(prefix: str, *, repo_root: Path) -> tuple[str | None, str]:
    inline_value = os.getenv(prefix, "").strip()
    file_value = os.getenv(f"{prefix}_FILE", "").strip()
    if inline_value and file_value:
        raise ConfigError(f"Configure only one of {prefix} and {prefix}_FILE")
    if inline_value:
        return inline_value, "environment"
    if not file_value:
        return None, "unset"

    path = Path(file_value).expanduser().resolve()
    try:
        path.relative_to(repo_root)
    except ValueError:
        pass
    else:
        raise ConfigError(f"{prefix}_FILE must be outside the repository")
    try:
        file_stat = path.stat()
    except OSError as exc:
        raise ConfigError(f"{prefix}_FILE is not readable") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise ConfigError(f"{prefix}_FILE must be a regular file")
    if stat.S_IMODE(file_stat.st_mode) & 0o077:
        raise ConfigError(f"{prefix}_FILE must not be accessible by group or others")
    try:
        endpoint = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigError(f"{prefix}_FILE is not readable") from exc
    if not endpoint:
        raise ConfigError(f"{prefix}_FILE is empty")
    return endpoint, "file"


@dataclass(frozen=True)
class Config:
    endpoints: dict[str, str | None]
    endpoint_sources: dict[str, str]
    timeout_seconds: float
    dedupe_ttl_seconds: int
    transport: str
    port: int

    @classmethod
    def load(cls) -> "Config":
        # This resolves to /int/tools from both the source tree and the VDS runtime target.
        repo_root = Path(__file__).resolve().parents[4]
        endpoints: dict[str, str | None] = {}
        endpoint_sources: dict[str, str] = {}
        for event_type, prefix in EVENT_ENV_PREFIX.items():
            endpoint, source = _load_endpoint(prefix, repo_root=repo_root)
            endpoints[event_type] = endpoint
            endpoint_sources[event_type] = source

        transport = os.getenv("VAKAS_MCP_TRANSPORT", "stdio").strip().lower() or "stdio"
        if transport not in {"stdio", "sse", "streamable-http"}:
            raise ConfigError("VAKAS_MCP_TRANSPORT must be stdio, sse or streamable-http")
        return cls(
            endpoints=endpoints,
            endpoint_sources=endpoint_sources,
            timeout_seconds=_positive_float(
                os.getenv("VAKAS_TIMEOUT_SECONDS", ""),
                name="VAKAS_TIMEOUT_SECONDS",
                default=15.0,
                maximum=60.0,
            ),
            dedupe_ttl_seconds=_positive_int(
                os.getenv("VAKAS_DEDUPE_TTL_SECONDS", ""),
                name="VAKAS_DEDUPE_TTL_SECONDS",
                default=86400,
                maximum=604800,
            ),
            transport=transport,
            port=_positive_int(
                os.getenv("VAKAS_MCP_PORT", ""),
                name="VAKAS_MCP_PORT",
                default=8768,
                maximum=65535,
            ),
        )
