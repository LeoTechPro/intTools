#!/usr/bin/env python3
"""
Watch a single forum topic (Telegram "Topics" in a forum supergroup) and emit new messages.

Default behavior:
  - listens for TDLib updateNewMessage events
  - filters by chat_id + forum_topic_id
  - appends events as JSONL to ~/.local/share/tg/forum_watch.jsonl

Usage:
  python3 tg_watch_forum_topic.py --chat-id <forum_chat_id> --forum-topic-id <id>

Optional:
  --forward-to-chat-id <chat_id>  # forward a short notification elsewhere (avoid loops)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--chat-id", type=int, required=True)
    p.add_argument("--forum-topic-id", type=int, required=True)
    p.add_argument(
        "--out",
        default=os.path.expanduser("~/.local/share/tg/forum_watch.jsonl"),
        help="JSONL output path",
    )
    p.add_argument("--forward-to-chat-id", type=int, help="Send a short notification to another chat_id")
    return p.parse_args()


def _ensure_ready_client() -> Any:
    conf = os.path.expanduser("~/.config/tg/conf.py")
    if not os.path.isfile(conf):
        _die(
            "Нет ~/.config/tg/conf.py. Сначала запусти интерактивный `tg` (в tmux) и пройди авторизацию.",
            code=2,
        )

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
            code=3,
        )

    return client


def _extract_text(msg: Dict[str, Any]) -> str:
    content = msg.get("content") or {}
    ctype = content.get("@type")
    if ctype == "messageText":
        text = ((content.get("text") or {}).get("text") or "")
        return str(text)
    return f"[{ctype or 'unknown'}]"


def _topic_matches(msg: Dict[str, Any], chat_id: int, forum_topic_id: int) -> bool:
    if msg.get("chat_id") != chat_id:
        return False
    topic = msg.get("topic_id")
    if not isinstance(topic, dict):
        return False
    if topic.get("@type") != "messageTopicForum":
        return False
    return topic.get("forum_topic_id") == forum_topic_id


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main() -> None:
    args = _parse_args()
    out_path = Path(args.out)

    client = _ensure_ready_client()

    # Precompute an offline HTTPS link to the topic (handy for notifications).
    topic_link: Optional[str] = None
    try:
        rv = client.call_method(
            "getForumTopicLink",
            params={"chat_id": int(args.chat_id), "forum_topic_id": int(args.forum_topic_id)},
            block=True,
        )
        if not rv.error and isinstance(rv.update, dict):
            topic_link = rv.update.get("link")
    except Exception:
        topic_link = None

    forward_to = args.forward_to_chat_id
    if forward_to is not None and int(forward_to) == int(args.chat_id):
        _die("--forward-to-chat-id совпадает с --chat-id. Это может устроить петлю. Выбери другой чат.", code=10)

    print(
        f"Watching forum topic: chat_id={args.chat_id} forum_topic_id={args.forum_topic_id}"
        + (f" link={topic_link}" if topic_link else "")
    )
    print(f"JSONL out: {out_path}")

    def on_new_message(_client: Any, update: Dict[str, Any]) -> None:
        msg = update.get("message") or {}
        if not isinstance(msg, dict):
            return
        if not _topic_matches(msg, int(args.chat_id), int(args.forum_topic_id)):
            return

        text = _extract_text(msg)
        event = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "chat_id": msg.get("chat_id"),
            "forum_topic_id": (msg.get("topic_id") or {}).get("forum_topic_id"),
            "message_id": msg.get("id"),
            "is_outgoing": msg.get("is_outgoing"),
            "sender_id": msg.get("sender_id"),
            "text": text,
            "topic_link": topic_link,
        }
        _append_jsonl(out_path, event)
        print(f'[{event["ts_utc"]}] msg_id={event["message_id"]} outgoing={event["is_outgoing"]}: {text}')
        sys.stdout.flush()

        if forward_to is not None and not event["is_outgoing"]:
            note = f"Новое в топике {args.forum_topic_id}: {text}"
            if topic_link:
                note += f"\n{topic_link}"
            try:
                client.send_message(int(forward_to), note)
            except Exception:
                pass

    # python-telegram handlers receive (func(update)) but tg's Telegram expects (func(update)).
    # add_update_handler signature: add_update_handler(handler_type, func)
    client.add_update_handler("updateNewMessage", lambda u: on_new_message(client, u))

    # Block forever.
    try:
        client.idle()
    except KeyboardInterrupt:
        pass
    finally:
        # Best-effort close; don't hang.
        try:
            client.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()

