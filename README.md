# intTools

`intTools` — репозиторий вспомогательных утилит, скриптов и небольших подсистем `intData.pro`, не являющихся обязательной частью конкретных продуктовых репозиториев. Каждый каталог содержит автономный набор tooling-артефактов и инструкций. Основной принцип — конфигурация исключительно через переменные окружения и `.env` файлы, чтобы не хранить секреты в исходном коде.

Канонический путь этого репозитория — `/git/tools`; старое имя допустимо только в historical references и не должно использоваться в живых runtime-контрактах.

## Структура

- `codex/` — versioned host-tooling для Codex/OpenClaw. Managed assets, bootstrap и policy лежат в репозитории; живой секретный слой вынесен в `/git/.runtime/codex-secrets`, а Codex-generated runtime/state остаётся в `~/.codex`.
- `probe/` — maintenance/audit утилиты для `Probe Monitor`, которые не нужны для boot prod-сервиса.
- `punctb/` — внешний ops/tooling-контур проекта «Пункт Б»: `sync_punctb.py`, process-scripts, hooks, internal runbooks и skills, которые не должны жить в product repo `/git/punctb`.

Общее правило для этого репозитория: versioned исходники и инструкции храним здесь, а runtime outputs, логи, временные файлы и mutable state уезжают во внешние host-path.

Исключение по явному решению владельца: cloud-access контур для `rclone` держит mountpoints и runtime config в `/git/.runtime/cloud-access` и `/git/cloud/*`, а secret runtime Codex/MCP держится в `/git/.runtime/codex-secrets`, чтобы восстановление рабочей машины шло из `/git` без раскладывания кастомных env по `~/.codex`.

## Требования

- Python 3.8 или новее
- Виртуальное окружение Python (`venv`)
- Установленные зависимости из `pip`

Рекомендуется создавать отдельное виртуальное окружение для каждого каталога со скриптами:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
```

## PunctB Sync Script

`sync_punctb.py` синхронизирует данные между исходной и целевой базами данных PostgreSQL. Скрипт поддерживает проверку расхождений, дельтовые загрузки и полный ре-импорт выбранных таблиц.

## PunctB Ops Tooling

`/git/tools/punctb` теперь также хранит versioned process/ops/tooling для PunctB:
- `bin/punctb-ops` — единый launcher для `issue:*`, `release:*`, `teamlead:*` и других process-команд;
- `ops/**` — process-scripts и gate wrappers, которые продукт вызывает через внешний ops-контур;
- `docs/**` и `templates/**` — versioned internal docs, policy и шаблоны для ops/process use-cases;
- `git-hooks/**` — git hooks, которые ставятся в checkout продукта внешней командой;
- `backend-ops/**` — ручные backend utility scripts, не входящие в product-core репозиторий.

Инварианты:
- product repo `/git/punctb` не хранит versioned ops/tooling вроде `deploy`, `backend/scripts`, `.mcp.json`, `codex.skill` и старых внутренних repo-local process paths;
- runtime scratch/log/tmp для PunctB ops и Codex живут вне git, по умолчанию в `~/.codex/tmp/punctb` и соседних host-path;
- команды из product repo вызывают внешний контур через `PUNCTB_OPS_HOME=${PUNCTB_OPS_HOME:-/git/tools/punctb}`.
- для самого репозитория `/git/tools` используем single-branch flow в `main`; dev/main promotion-контракт относится к продуктовым checkout, а не к этому репозиторию.

### Возможности

- Чтение источника только в read-only режиме
- UPSERT по первичному ключу для таблиц с полем `updated_at`
- Дозагрузка новых строк в append-only таблицах с PK `id`
- Режим полного ре-импорта (`--full-refresh`) для сложных таблиц
- Сравнение агрегатов (`count`, `max(id)`, `max(updated_at)`, контрольные суммы PK)

### Настройка окружения

1. Установите зависимости:
   ```bash
   pip install -r punctb/requirements.txt  # либо вручную: psycopg2-binary, python-dotenv, tabulate
   ```
   *(файл `requirements.txt` создайте при необходимости; перечислите нужные пакеты)*

2. Скопируйте шаблон переменных окружения:
   ```bash
   cp punctb/env punctb/.env
   ```

3. Заполните `punctb/.env`. Доступны переменные:
   - `SRC_HOST`, `SRC_PORT`, `SRC_DB`, `SRC_USER`, `SRC_PASSWORD`, `SRC_SSLMODE`
   - `DST_HOST`, `DST_PORT`, `DST_DB`, `DST_USER`, `DST_PASSWORD`, `DST_SSLMODE`, `DST_SSLROOTCERT`

   Файл `.env` добавлен в `.gitignore` и не попадёт в репозиторий. При утечке значений немедленно измените пароли и токены на стороне баз данных.

### Запуск

- Проверка без внесения изменений:
  ```bash
  python punctb/sync_punctb.py --verify-only
  ```

- Дельтовая синхронизация всех таблиц схемы `public`:
  ```bash
  python punctb/sync_punctb.py
  ```

- Дельта только по выбранным таблицам:
  ```bash
  python punctb/sync_punctb.py --tables clients,diagnostics,managers
  ```

- Указание размера батча (по умолчанию 5000):
  ```bash
  python punctb/sync_punctb.py --batch-size 20000
  ```

- Полный ре-импорт таблицы (удаляет данные в целевой БД перед загрузкой):
  ```bash
  python punctb/sync_punctb.py --full-refresh --tables diagnostics
  ```

### Отчёт о выполнении

По завершении скрипт выводит таблицу с основными метриками:

| table   | src_count | dst_count | src_max_id | dst_max_id | src_max_updated | dst_max_updated |
|---------|-----------|-----------|------------|------------|-----------------|-----------------|
| clients | 15234     | 15234     | 20001      | 20001      | 2025-09-28 09:00 | 2025-09-28 09:00 |

Совпадение метрик означает успешную синхронизацию. Рассинхрон указывает на таблицы, требующие повторного запуска.

### Практические рекомендации

- Выполняйте `--verify-only` перед каждой синхронизацией.
- Планируйте дельтовые загрузки в тихие часы.
- Таблицы без явного PK или `updated_at` безопаснее перезаливать через `--full-refresh`.
- Скрипт не изменяет источник, все операции выполняются в целевой базе.

### Частые проблемы

- **Несовпадающая схема** — обновите структуру целевой БД с помощью `pg_dump -s` и `psql`, указав параметры подключения из `.env`.
- **Большие объёмы данных** — увеличьте `--batch-size` и используйте фильтрацию по таблицам.
- **Отсутствует PK** — применяйте режим полного ре-импорта.

### Откат изменений

- Для пересоздания данных повторите загрузку с `--full-refresh`.
- Для чистки конкретных таблиц используйте `TRUNCATE TABLE ... RESTART IDENTITY CASCADE;` на целевой базе (с осторожностью).

### Безопасность

Если конфиденциальные параметры ранее попадали в публичный репозиторий, немедленно:
- Прокрутите новые пароли/ключи в админ-панели БД.
- Обновите значения в `punctb/.env`.
- Убедитесь, что секреты отсутствуют в истории коммитов перед публикацией.

## Вклад

Добавляйте новые каталоги с tooling-утилитами, следуя правилам:
- Документация в общем `README.md` или в отдельном файле внутри каталога.
- Настройки через `.env` с шаблоном `<module>/env`.
- Никаких чувствительных данных, логов и runtime outputs в репозитории.

## Лицензия

Если не указано иное, скрипты распространяются внутри команды «Пункт Б» без публичной лицензии. Уточните условия перед передачей третьим лицам.
