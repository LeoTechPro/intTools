#!/usr/bin/env python3
import argparse
import re
import shutil
import subprocess
import sys
import time


def resolve_bin(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f"Required executable not found in PATH: {name}")


def send_message(target: str, text: str) -> None:
    openclaw = resolve_bin("openclaw")
    subprocess.run(
        [openclaw, "message", "send", "--target", target, "--message", text],
        check=True,
    )


def ask_gemini(prompt: str) -> str:
    gemini = resolve_bin("gemini")
    res = subprocess.run([gemini, "ask", prompt], check=True, capture_output=True, text=True)
    out = re.sub(r"Loaded cached credentials\.\n?", "", res.stdout).strip()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--role1", required=True)
    parser.add_argument("--role2", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--rounds", type=int, default=1000)
    parser.add_argument("--pause-short", type=float, default=2.0)
    parser.add_argument("--pause-long", type=float, default=15.0)
    args = parser.parse_args()

    history = f"Тема дебатов: {args.topic}\n\n"
    send_message(
        args.target,
        f"🎙 **Дебаты начались!**\nТема: {args.topic}\n🔴 {args.role1}\n🔵 {args.role2}\n\n(Чтобы остановить, скажи Клаусу 'останови дебаты')",
    )

    for _ in range(args.rounds):
        time.sleep(args.pause_short)
        prompt1 = (
            f"Ты играешь роль: {args.role1}. Твоя задача вести дебаты с оппонентом ({args.role2}). "
            f"\nВот история диалога:\n{history}\n\n"
            "Напиши свой следующий аргумент (коротко, 1-2 абзаца). Развивай свою позицию. "
            "Не пиши за оппонента и не делай выводов за него."
        )
        resp1 = ask_gemini(prompt1)
        send_message(args.target, f"🔴 **[{args.role1}]**:\n{resp1}")
        history += f"Участник 1 ({args.role1}): {resp1}\n\n"

        time.sleep(args.pause_long)

        prompt2 = (
            f"Ты играешь роль: {args.role2}. Твоя задача вести дебаты с оппонентом ({args.role1}). "
            f"\nВот история диалога:\n{history}\n\n"
            "Напиши свой следующий аргумент (коротко, 1-2 абзаца). Опровергни аргумент оппонента и защищай свою позицию. "
            "Не пиши за оппонента."
        )
        resp2 = ask_gemini(prompt2)
        send_message(args.target, f"🔵 **[{args.role2}]**:\n{resp2}")
        history += f"Участник 2 ({args.role2}): {resp2}\n\n"

        lines = history.split("\n\n")
        if len(lines) > 8:
            history = f"Тема дебатов: {args.topic}\n\n" + "\n\n".join(lines[-7:])

        time.sleep(args.pause_long)

    send_message(args.target, "🏁 **Дебаты завершены!**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
