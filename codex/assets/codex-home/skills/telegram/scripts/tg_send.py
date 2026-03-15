#!/usr/bin/env python3
"""
Send a text message via TDLib using the same config as the `tg` TUI client.

Usage examples:
  python3 tg_send.py --to @leotechru --text "hello"
  python3 tg_send.py --chat-id 123456 --text "hello"
  python3 tg_send.py --chat-id <forum_chat_id> --forum-topic-id <id> --text "hello topic"

Notes:
  - Assumes you have already logged in interactively at least once (session in ~/.cache/tg/).
  - Does NOT ask for OTP/2FA in a non-interactive environment. If auth is needed, it exits with a clear message.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Optional


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    dst = p.add_mutually_exclusive_group(required=True)
    dst.add_argument("--to", help="Username like @user (public) or plain user")
    dst.add_argument("--chat-id", type=int, help="Target chat id")
    p.add_argument("--forum-topic-id", type=int, help="Forum topic id (messageTopicForum)")
    p.add_argument("--text", required=True, help="Text to send")
    return p.parse_args()


def _ensure_config_exists() -> None:
    conf = os.path.expanduser("~/.config/tg/conf.py")
    if not os.path.isfile(conf):
        _die(
            "Нет ~/.config/tg/conf.py. Сначала запусти интерактивный `tg` (лучше в tmux) и пройди авторизацию.",
            code=2,
        )


def _resolve_chat_id(tg: Any, to: str) -> int:
    username = to.strip()
    if username.startswith("@"):
        username = username[1:]
    if not username:
        _die("Пустой --to", code=3)

    # TDLib: searchPublicChat(username) -> chat
    rv = tg.call_method("searchPublicChat", params={"username": username}, block=True)
    if rv.error:
        _die(f"searchPublicChat error: {rv.error}", code=4)
    chat = rv.update or {}
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        _die(f"Не удалось получить chat_id из searchPublicChat ответа: {chat}", code=5)
    return chat_id


def _format_text(tg: Any, text: str) -> Dict[str, Any]:
    # Try to let TDLib parse entities (Markdown-like). Fallback to plain text.
    formatted: Dict[str, Any] = {"@type": "formattedText", "text": text}
    try:
        res = tg.parse_text_entities(text)
        res.wait()
        if not res.error and isinstance(res.update, dict):
            formatted = res.update
    except Exception:
        pass
    return formatted


def _send_to_forum_topic(tg: Any, chat_id: int, forum_topic_id: int, text: str) -> None:
    formatted_text = _format_text(tg, text)
    data: Dict[str, Any] = {
        "@type": "sendMessage",
        "chat_id": chat_id,
        "topic_id": {"@type": "messageTopicForum", "forum_topic_id": forum_topic_id},
        "input_message_content": {"@type": "inputMessageText", "text": formatted_text},
    }
    rv = tg._send_data(data, block=True)  # pylint: disable=protected-access
    if rv.error:
        _die(f"sendMessage error: {rv.error}", code=10)


def _send_to_chat(tg: Any, chat_id: int, text: str) -> None:
    rv = tg.send_message(chat_id, text)
    rv.wait()
    if rv.error:
        _die(f"send_message error: {rv.error}", code=11)


def main() -> None:
    args = _parse_args()
    _ensure_config_exists()

    # Import AFTER config exists, because tg.config may prompt otherwise.
    from telegram.client import AuthorizationState  # type: ignore
    from tg import config  # type: ignore
    from tg.tdlib import Tdlib  # type: ignore

    client = Tdlib(
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        phone=config.PHONE,
        database_encryption_key=config.ENC_KEY,
        files_directory=config.FILES_DIR,
        tdlib_verbosity=config.TDLIB_VERBOSITY,
        library_path=config.TDLIB_PATH,
    )

    state = client.login(blocking=False)
    if state != AuthorizationState.READY:
        _die(
            f"Нужна интерактивная авторизация (state={state}). Запусти `tg` в tmux и введи код/пароль, затем повтори.",
            code=20,
        )

    chat_id: int
    if args.chat_id is not None:
        chat_id = int(args.chat_id)
    else:
        chat_id = _resolve_chat_id(client, args.to)

    if args.forum_topic_id is not None:
        _send_to_forum_topic(client, chat_id, int(args.forum_topic_id), args.text)
    else:
        _send_to_chat(client, chat_id, args.text)

    print("OK")


if __name__ == "__main__":
    main()

