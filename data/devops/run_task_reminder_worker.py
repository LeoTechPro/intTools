"""CLI entrypoint to run TaskReminderWorker from cron/systemd."""

from __future__ import annotations

import asyncio
import logging
import os
from signal import SIGINT, SIGTERM

from nexus.api.env import env
from nexus.api.db.init_app import init_app_once
from nexus.api.services.task_reminder_worker import TaskReminderWorker

logger = logging.getLogger("task_reminder_worker")


async def _main() -> None:
    await init_app_once(env)
    interval = float(os.getenv("TASK_REMINDER_INTERVAL", "60"))
    worker = TaskReminderWorker(poll_interval=interval)
    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()

    for sig in (SIGINT, SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # pragma: no cover - on Windows signals unsupported
            pass

    logger.info("TaskReminderWorker started with poll interval %.1f seconds", interval)
    try:
        await worker.start(stop_event)
    finally:
        logger.info("TaskReminderWorker stopped")


if __name__ == "__main__":
    asyncio.run(_main())
