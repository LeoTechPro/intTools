#!/usr/bin/env python3
"""
Lightweight article fetcher → Markdown with YAML front‑matter.

Usage:
  python delivery/docops/fetch_url.py "<URL>" AGENTS/issues.json  # пример экспорта в зеркало

Implements fetch_to_markdown(url, out_path) with graceful fallbacks:
- Prefer trafilatura if available
- Fallback to readability-lxml (+ BeautifulSoup) if available
- Fallback to plain BeautifulSoup extraction
- Last resort: strip tags heuristically
"""
from __future__ import annotations

import sys
import re
import json
import html
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    import trafilatura  # type: ignore
except Exception:  # pragma: no cover
    trafilatura = None  # type: ignore

try:
    from readability import Document  # type: ignore
except Exception:  # pragma: no cover
    Document = None  # type: ignore

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None  # type: ignore


@dataclass
class PageMeta:
    title: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    source_url: Optional[str] = None


def _http_get(url: str) -> Tuple[str, str]:
    """Fetch URL returning (final_url, text). Avoids non-std deps when possible."""
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    if requests is not None:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return (str(resp.url), resp.text)
    # Fallback to urllib
    import urllib.request

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:  # nosec B310
        charset = r.headers.get_content_charset() or "utf-8"
        data = r.read()
        return (str(r.geturl()), data.decode(charset, errors="replace"))


def _extract_meta_from_html(html_text: str) -> PageMeta:
    meta = PageMeta()
    if BeautifulSoup is None:
        # Minimal heuristic
        m = re.search(r"<title>(.*?)</title>", html_text, re.I | re.S)
        if m:
            meta.title = html.unescape(m.group(1)).strip()
        return meta
    soup = BeautifulSoup(html_text, "lxml" if "lxml" else "html.parser")
    # Title
    if soup.title and soup.title.string:
        meta.title = soup.title.string.strip()
    # OpenGraph / meta
    def _content(name: str, prop: str) -> Optional[str]:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": prop})
        return tag.get("content") if tag and tag.get("content") else None

    meta.author = _content("author", "article:author") or _content("og:author", "og:author")
    meta.publisher = _content("og:site_name", "og:site_name") or _content("publisher", "article:publisher")
    return meta


def _markdown_from_bs(soup: "BeautifulSoup") -> str:
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    # Prefer main/article
    root = soup.find("article") or soup.find("main") or soup.body or soup

    lines = []
    toc = []

    def text_of(node) -> str:
        # Handle links
        if node.name == "a":
            href = node.get("href")
            label = (node.get_text(" ", strip=True) or href or "").strip()
            if href:
                return f"[{label}]({href})"
            return label
        return node.get_text(" ", strip=True)

    def walk(node):
        name = getattr(node, "name", None)
        if name and name.startswith("h") and len(name) == 2 and name[1].isdigit():
            level = int(name[1])
            title = text_of(node).strip()
            if title:
                anchor = re.sub(r"[^a-zA-Z0-9\- ]+", "", title).strip().lower().replace(" ", "-")
                toc.append((level, title, anchor))
                lines.append(f"{'#'*level} {title}")
                lines.append("")
            return
        if name == "p":
            t = text_of(node)
            if t:
                lines.append(t)
                lines.append("")
            return
        if name in ("ul", "ol"):
            for li in node.find_all("li", recursive=False):
                t = text_of(li)
                if t:
                    prefix = "- " if name == "ul" else "1. "
                    lines.append(prefix + t)
            lines.append("")
            return
        if name == "pre":
            code = node.get_text("\n", strip=False)
            lines.append("```")
            lines.append(code.rstrip("\n"))
            lines.append("```")
            lines.append("")
            return
        if name == "blockquote":
            q = node.get_text("\n", strip=True)
            for l in q.splitlines():
                lines.append("> " + l)
            lines.append("")
            return
        # Recurse shallowly for sections/divs
        for child in getattr(node, "children", []) or []:
            walk(child)

    walk(root)

    # Build TOC if we captured any headings
    md = []
    # Insert TOC only if at least two headings
    if len(toc) >= 2:
        md.append("## Содержание")
        for level, title, anchor in toc:
            indent = "  " * max(0, level - 1)
            md.append(f"{indent}- [{title}](#{anchor})")
        md.append("")
    md.extend(lines)
    return "\n".join(md).rstrip() + "\n"


def _to_markdown(html_text: str) -> str:
    if trafilatura is not None:
        try:  # Prefer structured extraction
            extracted = trafilatura.extract(html_text, include_comments=False, include_tables=False)
            if extracted and extracted.strip():
                # Traf returns plain text; wrap into paragraphs
                paras = [p.strip() for p in extracted.splitlines() if p.strip()]
                return "\n\n".join(paras) + "\n"
        except Exception:
            pass
    if Document is not None and BeautifulSoup is not None:
        try:
            doc = Document(html_text)
            content_html = doc.summary(html_partial=True)
            soup = BeautifulSoup(content_html, "lxml" if "lxml" else "html.parser")
            return _markdown_from_bs(soup)
        except Exception:
            pass
    if BeautifulSoup is not None:
        try:
            soup = BeautifulSoup(html_text, "lxml" if "lxml" else "html.parser")
            return _markdown_from_bs(soup)
        except Exception:
            pass
    # Last resort: strip tags
    text = re.sub(r"<\s*script[\s\S]*?<\s*/\s*script\s*>", "", html_text, flags=re.I)
    text = re.sub(r"<\s*style[\s\S]*?<\s*/\s*style\s*>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html.unescape(text)
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n\n".join(lines) + "\n"


def _wrap_front_matter(meta: PageMeta, body_md: str) -> str:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm = {
        "title": (meta.title or ""),
        "source_url": (meta.source_url or ""),
        "fetched_at": fetched_at,
        "author": (meta.author or ""),
        "publisher": (meta.publisher or ""),
    }
    yfm = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()) + "\n---\n\n"
    title_line = f"# {meta.title}\n\n" if meta.title else ""
    return yfm + title_line + body_md


def fetch_to_markdown(url: str, out_path: str) -> None:
    """Fetch URL and save readable Markdown with YAML front‑matter."""
    try:
        final_url, html_text = _http_get(url)
        meta = _extract_meta_from_html(html_text)
        meta.source_url = final_url
        body_md = _to_markdown(html_text)
        content = _wrap_front_matter(meta, body_md)
    except Exception as e:  # Network or parsing failure
        # Produce a stub so repo is self-sufficient
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        stub = (
            "---\n"
            f"title: {json.dumps('Хабр/НСПК: Второй мозг (заглушка)', ensure_ascii=False)}\n"
            f"source_url: {json.dumps(url, ensure_ascii=False)}\n"
            f"fetched_at: {json.dumps(fetched_at)}\n"
            "author: \n"
            f"publisher: {json.dumps('Habr / NSPK', ensure_ascii=False)}\n"
            "---\n\n"
            "# Второй мозг — заглушка\n\n"
            "> Автоматическая загрузка не удалась. Заполните файл, запустив скрипт повторно.\n\n"
            "## TODO\n\n"
            f"```bash\npython delivery/docops/fetch_url.py {json.dumps(url)} {json.dumps(out_path)}\n```\n"
            f"\n<!-- error: {type(e).__name__}: {str(e)} -->\n"
        )
        content = stub
    # Write UTF‑8
    from pathlib import Path

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(content, encoding="utf-8")


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python delivery/docops/fetch_url.py <URL> <OUT_PATH>")
        return 2
    url, out_path = argv[1], argv[2]
    fetch_to_markdown(url, out_path)
    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv))
