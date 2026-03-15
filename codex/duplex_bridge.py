#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, json, asyncio, argparse, itertools, shutil, pathlib, re
from typing import Optional, Dict, Any, List, Tuple

# ---------- конфиг по умолчанию ----------
MAX_FORWARD_CHARS = 1600      # сколько символов максимум пересылаем оппоненту
MAX_BUFFER_BYTES  = 2_000_000 # предельный буфер на всякий случай (2 МБ)
CHUNK_SIZE        = 8192      # читаем stdout по кускам
READ_TIMEOUT      = 8.0       # таймаут ожидания порции вывода

INCLUDE_NAMES = {
    "README.md", "AGENTS.md", "backlog.md", "changelog.md",
    "docker-compose.yml", "docker-compose.yaml",
    "pyproject.toml", "poetry.lock", "requirements.txt",
    "go.mod", "go.sum", "openapi.json", "openapi.yaml",
    ".env.example", ".env.sample",
}

DEFAULT_CODEX_HOME = pathlib.Path(os.getenv("CODEX_HOME", str(pathlib.Path.home() / ".codex")))
DEFAULT_LOG_PATH = DEFAULT_CODEX_HOME / "log" / "debate" / "duplex_bridge.log"

# ---------- утилиты ----------
def load_env_file(path: str) -> Dict[str, str]:
    data = {}
    if not os.path.isfile(path): return data
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data

def which_codex() -> str:
    p = shutil.which("codex")
    if not p: raise RuntimeError("codex не найден в PATH. Добавь в PATH или укажи --codex-bin.")
    return p

def make_env() -> Dict[str, str]:
    env = os.environ.copy()     # наследуем PATH, чтобы не ломать uname/bash
    env.setdefault("LC_ALL", "C.UTF-8")
    env.setdefault("LANG",   "C.UTF-8")
    return env

_id_counter = (f"{i}" for i in itertools.count(1))

def op_user_input(text: str) -> Dict[str, Any]:
    return {"id": next(_id_counter),
            "op": {"type": "user_input", "items": [{"type": "text", "text": text}]}}

def op_user_turn() -> Dict[str, Any]:
    return {"id": next(_id_counter), "op": {"type": "user_turn"}}

async def send_json(proc: asyncio.subprocess.Process, obj: Dict[str, Any]) -> None:
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    proc.stdin.write(line.encode("utf-8"))
    await proc.stdin.drain()

async def spawn_agent(codex_bin: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        codex_bin, "proto",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=make_env(),
    )

def extract_text_from_msg(obj: Dict[str, Any]) -> Optional[str]:
    msg = obj.get("msg")
    if not isinstance(msg, dict): return None
    # популярные варианты структуры исходящих сообщений
    if isinstance(msg.get("content"), str):
        return msg["content"]
    if isinstance(msg.get("text"), str):
        return msg["text"]
    items = msg.get("items")
    if isinstance(items, list):
        parts = []
        for it in items:
            if isinstance(it, dict):
                if it.get("type") in ("text", "tool_result"):
                    t = it.get("text")
                    if isinstance(t, str) and t.strip():
                        parts.append(t)
        if parts: return "\n".join(parts)
    return None

def summarize_soft(s: str, limit: int) -> str:
    s = s.strip()
    if len(s) <= limit: return s
    # грубая «суммаризация»: обрезать по границе предложения/строки, затем «…»
    cut = s[:limit]
    # постараемся не рвать слово
    last_punct = max(cut.rfind("\n"), cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if last_punct > limit // 2:
        cut = cut[:last_punct+1]
    return cut.rstrip() + "\n… (сокращено)"


def list_tree(root: str, depth: int = 2) -> str:
    rootp = pathlib.Path(root)
    lines = [f"TREE {root} (depth={depth})"]
    for p in sorted(rootp.rglob("*")):
        rel = p.relative_to(rootp)
        if len(rel.parts) > depth:
            continue
        try:
            if p.is_dir():
                lines.append(f"[D] {rel}/")
            else:
                size = p.stat().st_size
                lines.append(f"[F] {rel} ({size} B)")
        except Exception:
            continue
    return "\n".join(lines)


def read_if_interesting(root: str, max_bytes: int = 100_000) -> List[Tuple[str, str]]:
    rootp = pathlib.Path(root)
    out: List[Tuple[str, str]] = []
    for p in rootp.rglob("*"):
        if p.is_file() and p.name in INCLUDE_NAMES:
            try:
                data = p.read_text(encoding="utf-8", errors="ignore")
                if len(data) > max_bytes:
                    data = data[:max_bytes] + "\n… (truncated)"
                out.append((str(p), data))
            except Exception:
                continue
    return out


async def seed_brief(A, B, topic: str, roots: List[str]) -> None:
    preface = (
        "Регламент: отвечайте ≤1200 символов; 1 тезис + 1 вопрос; "
        "если нужен файл — напишите 'REQUEST_FILE <path> [MAX=<байт>]', "
        "если нужно древо — 'REQUEST_DIR <path> [DEPTH=N]'. "
        "В конце — общий согласованный список решений в виде таблицы."
    )
    for proc in (A, B):
        await send_json(proc, op_user_turn())
        await send_json(proc, op_user_input(f"Тема: {topic}\n{preface}"))

    for root in roots:
        print(f"[bridge] briefing tree {root} (depth=3)", flush=True)
        tree = list_tree(root, depth=3)
        for proc in (A, B):
            await send_json(proc, op_user_input(f"DIR BRIEF {root}\n{tree}"))

    for root in roots:
        for path, data in read_if_interesting(root):
            print(f"[bridge] briefing file {path}", flush=True)
            header = f"FILE {path}"
            chunk = summarize_soft(data, 8000)
            for proc in (A, B):
                await send_json(proc, op_user_input(f"{header}\n{chunk}"))


REQ_FILE = re.compile(r"^REQUEST_FILE\s+(\S+)(?:\s+MAX=(\d+))?$", re.I)
REQ_DIR  = re.compile(r"^REQUEST_DIR\s+(\S+)(?:\s+DEPTH=(\d+))?$", re.I)


def read_file_chunked(path: str, max_bytes: int = 80_000) -> List[str]:
    try:
        data = pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"ERROR reading {path}: {e}"]
    if len(data) <= max_bytes:
        return [data]
    chunks = []
    for i in range(0, len(data), max_bytes):
        chunks.append(data[i:i + max_bytes])
    return chunks


def dir_listing(path: str, depth: int = 2) -> str:
    try:
        return list_tree(path, depth=depth)
    except Exception as e:
        return f"ERROR listing {path}: {e}"


async def maybe_handle_requests(text: str, target_proc) -> bool:
    handled = False
    for line in text.splitlines():
        stripped = line.strip()
        m_file = REQ_FILE.match(stripped)
        if m_file:
            handled = True
            p, mx = m_file.group(1), m_file.group(2)
            lim = int(mx) if mx else 80_000
            chunks = read_file_chunked(p, max_bytes=lim)
            total = len(chunks)
            for idx, chunk in enumerate(chunks, 1):
                await send_json(target_proc, op_user_turn())
                await send_json(target_proc, op_user_input(f"FILE {p} (chunk {idx}/{total})\n{chunk}"))
        m_dir = REQ_DIR.match(stripped)
        if m_dir:
            handled = True
            p, depth = m_dir.group(1), m_dir.group(2)
            dep = int(depth) if depth else 2
            listing = dir_listing(p, depth=dep)
            await send_json(target_proc, op_user_turn())
            await send_json(target_proc, op_user_input(f"DIR {p}\n{listing}"))
    return handled


ON_TOPIC_KEYS = (
    "intdata",
    "intbridge",
    "/git/intdata",
    "/git/intbridge",
    "docker",
    "postgres",
    "openapi",
    "alembic",
    "compose",
    "broker",
    "queue",
    "retry",
    "idempot",
    "metrics",
    "prometheus",
    "grafana",
    "nginx",
    "gunicorn",
    "uvicorn",
)


def is_fluff(text: str) -> bool:
    t = text.lower()
    bad_starts = (
        "**preparing",
        "**planning",
        "**evaluating",
        "**formulating",
        "i'm figuring out",
        "i am figuring out",
        "mapping out",
        "готовлюсь",
        "планирую",
    )
    return any(t.startswith(s) for s in bad_starts) or len(t) < 40


def off_topic(text: str) -> bool:
    t = text.lower()
    return not any(k in t for k in ON_TOPIC_KEYS)


def force_back_to_topic(tag_from: str) -> str:
    return (
        f"{tag_from}: Стоп. Ты ушёл от темы. Немедленно вернись к анализу /git/intdata и /git/intbridge. "
        "Дай минимум 3 проблемы с привязкой к конкретным файлам/путям и решения. "
        "Если не хватает данных — пришли точные REQUEST_FILE/REQUEST_DIR сейчас."
    )

async def read_reply_chunked(proc: asyncio.subprocess.Process,
                             timeout: float = READ_TIMEOUT,
                             max_bytes: int = MAX_BUFFER_BYTES) -> str:
    """
    Читаем stdout по чанкам, сами выделяем JSON-строки (разделитель '\n').
    Извлекаем «человеческий» текст из встреченных JSON-сообщений.
    Возвращаем склеенный текст (может быть пустым).
    """
    buf = bytearray()
    texts: List[str] = []
    # читаем несколько чанков, пока не увидим «достаточно» текста или таймаут
    while True:
        try:
            chunk = await asyncio.wait_for(proc.stdout.read(CHUNK_SIZE), timeout=timeout)
        except asyncio.TimeoutError:
            break
        if not chunk:  # поток закрыт
            break
        buf += chunk
        if len(buf) > max_bytes:
            # защитимся от бесконечного лога
            break
        # разбираем полные строки
        *lines, remainder = buf.split(b"\n")
        for raw in lines:
            line = raw.decode("utf-8", errors="ignore").strip()
            # пытаемся парсить только JSON
            if line.startswith("{") and line.endswith("}"):
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                text = extract_text_from_msg(obj)
                if text:
                    texts.append(text)
                    # эвристика: хватает 1–2 кусков связного ответа
                    if sum(len(t) for t in texts) > 800:
                        pass
        buf = bytearray(remainder)
        # если уже что-то собрали и пришёл новый chunk — выходим, даём ход оппоненту
        if texts and len(buf) == 0:
            break
    return "\n".join(texts).strip()

async def debate_round(speaker: asyncio.subprocess.Process,
                       listener: asyncio.subprocess.Process,
                       tag_s: str, tag_l: str,
                       logf) -> bool:
    reply = await read_reply_chunked(speaker)
    if not reply:
        return False
    # печать и лог
    print(f"\n[{tag_s}] → [{tag_l}]:\n{reply}\n", flush=True)
    if logf:
        logf.write(f"\n[{tag_s}] → [{tag_l}]:\n{reply}\n"); logf.flush()
    if await maybe_handle_requests(reply, listener):
        return True
    if is_fluff(reply) or off_topic(reply):
        redirect = force_back_to_topic(tag_s)
        print(f"[bridge] redirecting {tag_s} → {tag_l}\n", flush=True)
        await send_json(listener, op_user_turn())
        await send_json(listener, op_user_input(redirect))
        return True
    forward = summarize_soft(reply, MAX_FORWARD_CHARS)
    await send_json(listener, op_user_turn())
    await send_json(listener, op_user_input(forward))
    return True

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Duplex debate bridge for two codex proto agents")
    p.add_argument("--codex-bin", default=None, help="Путь к codex (если не в PATH)")
    p.add_argument("--topic", default=None, help="Тема дебатов")
    p.add_argument("--role-a", default=None, help="Роль/позиция агента A")
    p.add_argument("--role-b", default=None, help="Роль/позиция агента B")
    p.add_argument("--rounds", type=int, default=None, help="Количество раундов (A→B пары)")
    p.add_argument("--env-file", default="debate.env", help="ENV-файл с настройками")
    p.add_argument("--log", default=str(DEFAULT_LOG_PATH), help="Файл лога")
    return p.parse_args()

async def main():
    args = parse_args()
    file_cfg = load_env_file(args.env_file)
    log_path = pathlib.Path(args.log).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    codex_bin = args.codex_bin or which_codex()
    topic   = args.topic   or file_cfg.get("TOPIC")   or "Обсудите выбранную тему и придите к выводу."
    role_a  = args.role_a  or file_cfg.get("ROLE_A")  or "Ты — Агент A (Pro). Кратко, по делу."
    role_b  = args.role_b  or file_cfg.get("ROLE_B")  or "Ты — Агент B (Contra). Кратко, по делу."
    rounds  = args.rounds  or int(file_cfg.get("ROUNDS", "4"))

    # усилим регламент и запрет инструментов
    RULES = (
        "Требования: 1) анализ ТОЛЬКО /git/intdata и /git/intbridge; 2) без 'планирую/готовлюсь'; "
        "3) каждая реплика ≤1200 символов, строго: «Проблема ⇒ Причина (путь/файл) ⇒ Решение ⇒ Риск/Трудозатраты»; "
        "4) если НЕ хватает данных — немедленно шли 'REQUEST_FILE <path>' или 'REQUEST_DIR <path> DEPTH=3'; "
        "5) русский язык; 6) никаких инструментов/команд исполнения; 7) в конце — СОВМЕСТНАЯ таблица и согласованный порядок."
    )

    A = await spawn_agent(codex_bin)
    B = await spawn_agent(codex_bin)

    # стартовые настройки и роли
    await send_json(A, op_user_turn())
    await send_json(A, op_user_input(f"{role_a}\nТема: {topic}\n{RULES}"))
    await send_json(B, op_user_turn())
    await send_json(B, op_user_input(f"{role_b}\nТема: {topic}\n{RULES}"))

    roots = ["/git/intdata", "/git/intbridge"]
    await seed_brief(A, B, topic, roots)

    prime_paths = [
        "/git/intdata/README.md",
        "/git/intdata/api/openapi.json",
        "/git/intdata/docker-compose.yml",
        "/git/intbridge/README.md",
        "/git/intbridge/docker-compose.yml",
    ]
    for p in prime_paths:
        print(f"[bridge] priming {p}", flush=True)
        for proc in (A, B):
            await send_json(proc, op_user_turn())
            await send_json(proc, op_user_input(f"REQUEST_FILE {p} MAX=80000"))

    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n=== NEW DEBATE ===\nTOPIC: {topic}\nROLE_A: {role_a}\nROLE_B: {role_b}\n"); logf.flush()
        for _ in range(rounds):
            if not await debate_round(A, B, "A", "B", logf): break
            if not await debate_round(B, A, "B", "A", logf): break

        final_prompt = (
            "ФИНАЛ: дайте СОВМЕСТНУЮ согласованную таблицу (минимум 8 строк):\n"
            "Проблема | Файл/путь | Причина | Решение | Трудозатраты (S/M/L) | Риск | Приоритет (P1..P3)\n"
            "Затем короткий чек-лист действий на 1-ю неделю. Без болтовни."
        )
        for proc in (A, B):
            await send_json(proc, op_user_turn())
            await send_json(proc, op_user_input(final_prompt))

        await debate_round(A, B, "A-final", "B", logf)
        await debate_round(B, A, "B-final", "A", logf)

    for proc in (A, B):
        try:
            if proc.stdin and not proc.stdin.is_closing():
                proc.stdin.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
