#!/usr/bin/env python3
"""
Утилита миграции: строит прокси-конфиги nginx по активным apache vhost'ам.

Допущения:
- Apache-конфиги находятся в /etc/apache2/sites-available/.
- Пары файлов вида <name>.conf и <name>-le-ssl.conf объединяются в один nginx vhost.
- Для TLS используем те же сертификаты Let's Encrypt, что и в Apache.
- Backend Apache слушает на 127.0.0.1:8080 (HTTP) и 127.0.0.1:8443 (HTTPS); nginx проксирует трафик дальше.

Скрипт генерирует конфиги в каталоге configs/nginx/generated/ внутри репозитория.
"""

from __future__ import annotations

import argparse
import os
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

APACHE_SITES_DIR = Path("/etc/apache2/sites-available")
APACHE_ENABLED_DIR = Path("/etc/apache2/sites-enabled")
OUTPUT_DIR = Path("configs/nginx/generated")


SERVER_NAME_RE = re.compile(r"^\s*ServerName\s+(\S+)", re.IGNORECASE | re.MULTILINE)
SERVER_ALIAS_RE = re.compile(r"^\s*ServerAlias\s+(.+)$", re.IGNORECASE | re.MULTILINE)
SSL_CERT_RE = re.compile(r"^\s*SSLCertificateFile\s+(\S+)", re.IGNORECASE | re.MULTILINE)
SSL_KEY_RE = re.compile(r"^\s*SSLCertificateKeyFile\s+(\S+)", re.IGNORECASE | re.MULTILINE)


@dataclass
class VHost:
    name: str
    server_names: Set[str] = field(default_factory=set)
    has_http: bool = False
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    redirect_target: Optional[str] = None

    @property
    def filename(self) -> str:
        return f"{self.name}.conf"

    def nginx_config(self) -> str:
        if not self.server_names:
            return ""

        server_names = " ".join(sorted(self.server_names))
        proxy_common = [
            "proxy_set_header Host $host;",
            "proxy_set_header X-Real-IP $remote_addr;",
            "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
            "proxy_set_header X-Forwarded-Proto $scheme;",
            "proxy_set_header X-Forwarded-Host $host;",
            "proxy_http_version 1.1;",
            "proxy_buffering off;",
            "proxy_read_timeout 120s;",
            "proxy_connect_timeout 30s;",
        ]

        def join_block(lines: List[str]) -> str:
            return "\n".join(lines)

        blocks: List[str] = []

        if self.redirect_target:
            http_lines = [
                "server {",
                "    listen 80;",
                "    listen [::]:80;",
                f"    server_name {server_names};",
                "",
                f"    return 308 {self.redirect_target};",
                "}",
            ]
            blocks.append(join_block(http_lines))

            https_lines = [
                "server {",
                "    listen 443 ssl http2;",
                "    listen [::]:443 ssl http2;",
                f"    server_name {server_names};",
                "",
            ]
            if self.ssl_cert and self.ssl_key:
                https_lines.extend(
                    [
                        f"    ssl_certificate     {self.ssl_cert};",
                        f"    ssl_certificate_key {self.ssl_key};",
                        "    include /etc/nginx/snippets/ssl-params.conf;",
                        "",
                    ]
                )
            https_lines.append(f"    return 308 {self.redirect_target};")
            https_lines.append("}")
            blocks.append(join_block(https_lines))
            return "\n\n".join(blocks).strip() + "\n"

        if self.has_http:
            http_lines: List[str] = [
                "server {",
                "    listen 80;",
                "    listen [::]:80;",
                f"    server_name {server_names};",
                "",
                f"    access_log /var/log/nginx/{self.name}.access.log main;",
                f"    error_log  /var/log/nginx/{self.name}.error.log warn;",
                "",
                "    location / {",
            ]
            for line in proxy_common:
                http_lines.append(f"        {line}")
            http_lines.append("        proxy_pass http://127.0.0.1:8080;")
            http_lines.append("    }")
            http_lines.append("}")
            blocks.append(join_block(http_lines))

            if self.ssl_cert and self.ssl_key:
                https_lines: List[str] = [
                    "server {",
                    "    listen 443 ssl http2;",
                    "    listen [::]:443 ssl http2;",
                    f"    server_name {server_names};",
                    "",
                    f"    access_log /var/log/nginx/{self.name}.access.log main;",
                    f"    error_log  /var/log/nginx/{self.name}.error.log warn;",
                    "",
                    f"    ssl_certificate     {self.ssl_cert};",
                    f"    ssl_certificate_key {self.ssl_key};",
                    "    ssl_session_cache   shared:SSL:10m;",
                    "    ssl_session_timeout 1d;",
                    "    ssl_protocols       TLSv1.2 TLSv1.3;",
                    "    ssl_prefer_server_ciphers on;",
                    "",
                    "    include /etc/nginx/snippets/ssl-params.conf;",
                    "",
                    "    location / {",
                ]
                for line in proxy_common:
                    https_lines.append(f"        {line}")
                https_lines.extend(
                    [
                        "        proxy_ssl_name $host;",
                        "        proxy_ssl_server_name on;",
                        "        proxy_ssl_verify on;",
                        "        proxy_ssl_trusted_certificate /etc/ssl/certs/ca-certificates.crt;",
                        "        proxy_pass https://127.0.0.1:8443;",
                        "    }",
                        "}",
                    ]
                )
                blocks.append(join_block(https_lines))

        return "\n\n".join(blocks).strip() + "\n"


def collect_vhosts() -> Dict[str, VHost]:
    if not APACHE_SITES_DIR.exists():
        raise FileNotFoundError(f"Каталог {APACHE_SITES_DIR} не найден.")

    enabled_names = {p.name for p in APACHE_ENABLED_DIR.glob("*.conf")} if APACHE_ENABLED_DIR.exists() else set()

    result: Dict[str, VHost] = {}

    for conf_path in sorted(APACHE_SITES_DIR.glob("*.conf")):
        if enabled_names and conf_path.name not in enabled_names:
            continue
        stem = conf_path.stem
        is_ssl_variant = False
        if stem.endswith("-le-ssl"):
            stem = stem[: -len("-le-ssl")]
            is_ssl_variant = True

        vhost = result.setdefault(stem, VHost(name=stem))
        content = conf_path.read_text()

        names = set(SERVER_NAME_RE.findall(content))
        for alias_line in SERVER_ALIAS_RE.findall(content):
            for alias in alias_line.split():
                names.add(alias.strip())

        if names:
            vhost.server_names.update(names)

        redirect_match = re.search(r"Redirect\s+(?:permanent|301)\s+/\s+(\S+)", content, re.IGNORECASE)
        if redirect_match:
            vhost.redirect_target = redirect_match.group(1)

        cert_match = SSL_CERT_RE.search(content)
        key_match = SSL_KEY_RE.search(content)

        if cert_match:
            vhost.ssl_cert = cert_match.group(1)
        if key_match:
            vhost.ssl_key = key_match.group(1)

        if not is_ssl_variant and names:
            vhost.has_http = True

    return result


def generate(output_dir: Path, dry_run: bool = False) -> List[Path]:
    vhosts = collect_vhosts()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        for existing in output_dir.glob("*.conf"):
            existing.unlink()
    written: List[Path] = []

    for name, vhost in sorted(vhosts.items()):
        config = vhost.nginx_config()
        if not config:
            continue
        dest = output_dir / vhost.filename
        if dry_run:
            print(f"--- {dest} ---\n{config}")
        else:
            dest.write_text(config)
        written.append(dest)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Генерация nginx-прокси конфигов из apache vhost'ов.")
    parser.add_argument("--dry-run", action="store_true", help="Вывести конфиги в stdout без записи.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Каталог для сохранения конфигов.")
    args = parser.parse_args()

    written = generate(args.output, dry_run=args.dry_run)
    if args.dry_run:
        print(f"Всего конфигов: {len(written)}")
    else:
        print(f"Сохранено конфигов: {len(written)} в {args.output}")


if __name__ == "__main__":
    main()
