---
name: telegram
description: "Telegram в Linux через терминал: клиент `tg` (TDLib), авторизация, чтение/отправка сообщений, автоматизация и работа с forum topics (topic_id/forum_topic_id), диагностика TDLib/OpenSSL."
metadata:
  short-description: "Telegram TUI/TDLib workflows"
---

**IMPORTANT - Path Resolution:**
Этот скилл может быть установлен глобально или проектно. Перед командами определи директорию скилла по пути этого `SKILL.md` и используй её как `$SKILL_DIR`.

Обычно:
- Global: `~/.codex/skills/telegram`

# Telegram (tg + TDLib) на Linux

## Правило актуализации (обязательное)

Если в ходе любой задачи по Telegram появляются новые сведения (новые ошибки/фиксы, изменения версий, новые рабочие приёмы, новые скрипты), ОБЯЗАТЕЛЬНО обнови этот скилл: `SKILL.md` и/или `scripts/*` так, чтобы в следующий раз не приходилось исследовать проблему заново.

## Быстрый старт (интерактивный `tg` в tmux)

Цель: стабильная авторизация и работа в терминале без GUI.

1. Старт/проверка окружения:
   - Диагностика: `bash $SKILL_DIR/scripts/tg_doctor.sh`
   - Если `tg` не установлен: `pip3 install --user tg python-telegram mailcap_fix`
2. Запуск `tg` в `tmux` (чтобы не терять сессию):
   - `bash $SKILL_DIR/scripts/tg_start_tmux.sh`
   - Подключиться: `tmux attach -t tg-auth`
   - Отсоединиться: `Ctrl+b`, затем `d`
   - Если бинаря `tg` нет в `$PATH`, это нормально: используем `python3 -m tg` (скрипт запуска умеет fallback).
3. Авторизация:
   - Номер телефона, одноразовый код, 2FA-пароль вводятся ТОЛЬКО внутри `tmux/tg`, не в чат.

## Клавиши `tg` (то, что реально нужно помнить)

- `?` справка по хоткеям (в списке чатов и в режиме сообщений)
- `/` поиск/прыжок в чат
- `l` перейти в сообщения выбранного чата, `h` назад в список чатов
- `a` или `i` написать сообщение
- `r` отметить прочитанным текущий чат (в списке чатов)
- `q` выход

## Каноничные пути `tg` (по умолчанию)

- Конфиг: `~/.config/tg/conf.py`
- Данные/база TDLib: `~/.cache/tg/`
- Логи: `~/.local/share/tg/`

## Автоматизация без curses (через TDLib)

Если нужно отправлять/читать без UI-автоматизации, используй скрипты:

- Отправить сообщение:
  - `python3 $SKILL_DIR/scripts/tg_send.py --to @username --text 'привет'`
  - `python3 $SKILL_DIR/scripts/tg_send.py --chat-id 123456 --text 'привет'`
  - В форум-топик: `python3 $SKILL_DIR/scripts/tg_send.py --chat-id <forum_chat_id> --forum-topic-id <id> --text 'привет в топик'`
- Смотреть конкретный форум-топик и писать новые сообщения в JSONL-ленту:
  - `python3 $SKILL_DIR/scripts/tg_watch_forum_topic.py --chat-id <forum_chat_id> --forum-topic-id <id>`
  - Вывод по умолчанию: `~/.local/share/tg/forum_watch.jsonl`

Важно:
- Скрипты ожидают, что вы уже авторизовались интерактивно хотя бы один раз (иначе TDLib потребует код/пароль).
- Не печатай одноразовые коды/2FA в этот чат. Скрипты должны работать без секретов (сессия хранится в `~/.cache/tg/`).

## Форумы и топики (topics) в Telegram

Факты, на которых строится фильтрация/ответы:
- В TDLib у сообщения есть `topic_id`.
- Для форумов: `topic_id["@type"] == "messageTopicForum"` и `topic_id["forum_topic_id"] == <topic_id>`.
- Отправка в топик делается через `sendMessage` с полем `topic_id` вида `{"@type":"messageTopicForum","forum_topic_id":<id>}`.
- Список топиков: TDLib метод `getForumTopics`.
- История топика: TDLib метод `getForumTopicHistory`.

## Траблшутинг (частые поломки)

1. `ModuleNotFoundError: No module named 'mailcap_fix'`
   - Фикс: `pip3 install --user mailcap_fix`
2. `OSError: libssl.so.1.1: cannot open shared object file`
   - Причина: `python-telegram` может тянуть `libtdjson.so`, собранную под OpenSSL 1.1, которой нет в Debian 13.
   - Рабочий путь: собрать TDLib под OpenSSL 3 и прописать `TDLIB_PATH` в `~/.config/tg/conf.py`.
   - Скрипт для сборки/регистрации (запускать только по прямому запросу пользователя): `bash $SKILL_DIR/scripts/tg_build_tdlib.sh`
3. `fzf: not found` при `c` (contacts) или справке/пейджере
   - Причина: `tg` вызывает `fzf` для выбора контактов; без него команды падают.
   - Варианты:
     - Установить `fzf` (если можно использовать пакетный менеджер).
     - Локальный stub без сетевых установок: `bash $SKILL_DIR/scripts/tg_fzf_stub.sh leotechru`
       - Скрипт ставит `~/.local/bin/fzf` и задаёт фильтр через `~/.cache/tg/fzf_query`.
4. `Can't lock file ".../td.binlog", because it is already in use`
   - Причина: `tg` (TUI) уже запущен и держит базу TDLib.
   - Решение: закрыть `tg` или остановить `tmux`-сессию `tg-auth`, затем повторить TDLib-скрипт.
5. `Unknown class "getChatFolders"` при попытке работать с папками
   - Причина: текущая сборка TDLib не поддерживает API папок.
   - Решение: обновить TDLib до версии с поддержкой chat folders или выполнять работу с папками через официальный клиент Telegram (Desktop/Mobile).

---

# Telegram Bot API через OpenClaw (актуально)

Старый `queue-only` мост удалён и больше не используется.

Для задач через Telegram-ботов использовать текущий контур:
- `@AgentIDClawBot` (`OpenClaw`) как мост задач.
- `@intProbeBot` (`Probe Monitor`) как watcher/алерт-канал.
- Конфигурация runtime: `/git/openclaw/openclaw.json`.
- Сервис: `systemctl --user status openclaw-gateway.service --no-pager`.

Если пользователь просит операции Bot API вручную, не возвращаться к старому мосту; работать через OpenClaw-конфиг и его runtime-политики.

## Политика обновления skill

Если меняется Telegram-контур OpenClaw (ACL, команды панели, watcher-события), обновлять этот блок `SKILL.md` в том же изменении.
