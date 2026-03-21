# [scripts/devops](../scripts/devops)

Скрипты DevOps-цикла (rebuild, restart, smoke) и инфраструктурные инструменты. Общие принципы описаны в [scripts/README.md](../scripts/README.md).

- **configure_erp_sso.sh** — настраивает Keycloak-провайдеры для Odoo/ERPNext. Требует заполненного `erp/.env` и запущенных контейнеров (`docker compose -f erp/docker-compose.yaml up -d`).

## Keycloak + Kill Bill (IAM биллинг/подписки)

- **/int/id/docker-compose.yaml** с профилем `keycloak` — standalone стек Keycloak + Kill Bill + Kaui + PostgreSQL.
- **setup_keycloak_killbill.sh** — управляющий скрипт (`start|stop|restart|logs|down|status`), принимает `--env` для указания файла переменных, проверяет обязательные секреты и автоматически бутстрапит Realm/тенант после запуска.
- Дополнительные флаги: `--clear-theme-cache` (очищает `kc-gzip-cache` в контейнере Keycloak после `up/restart`) и `--selenium-smoke` (запускает `scripts/devops/run_selenium_smoke.sh` для браузерного smoke).
- **killbill.overrides/killbill.properties.example** — пример overrides для Kill Bill (скопируйте в `killbill.properties` и подставьте секреты).
- **/int/id/scripts/devops/run_selenium_smoke.sh** — опциональный Selenium UI smoke для standalone repo Identity; выполняется только если selenium tests добавлены локально.

### Быстрый старт

```bash
# 1. Подготовьте env-файл (.env.dev) и заполните обязательные переменные:
#    ID_KEYCLOAK_DB_NAME, ID_KEYCLOAK_DB_USER, ID_KEYCLOAK_DB_PASSWORD,
#    ID_KEYCLOAK_ADMIN, ID_KEYCLOAK_ADMIN_PASSWORD,
#    ID_KEYCLOAK_ADMIN_CLIENT_ID, ID_KEYCLOAK_ADMIN_CLIENT_SECRET,
#    ID_KEYCLOAK_LOGIN_THEME (по умолчанию intdata),
#    ID_KEYCLOAK_DISPLAY_NAME (по умолчанию "intData SSO"),
#    ID_KEYCLOAK_DISPLAY_NAME_HTML (по умолчанию "intData SSO"),
#    ID_KILLBILL_DB_NAME, ID_KILLBILL_DB_USER, ID_KILLBILL_DB_PASSWORD,
#    ID_KILLBILL_ADMIN_USER, ID_KILLBILL_ADMIN_PASSWORD,
#    ID_KILLBILL_DEFAULT_API_KEY, ID_KILLBILL_DEFAULT_API_SECRET,
#    ID_KILLBILL_WEBHOOK_SECRET
#    ID_KEYCLOAK_REALM (опционально, по умолчанию intdata)
#    ID_KILLBILL_TENANT_NAME (опционально, по умолчанию "IntData Dev")
#    SSO клиенты модулей (см. id/.env.example):
#      NEXUS_SSO_*/NEXUS_ADMIN_SSO_*/NEXUS_API_SSO_*
#      CRM_SSO_*/CRM_ADMIN_SSO_*/CRM_API_SSO_*
##      BRIDGE_SSO_*/BRIDGE_ADMIN_SSO_*/BRIDGE_API_SSO_*
#      CHAT_SSO_*/CHAT_ADMIN_SSO_*/CHAT_API_SSO_*
#      SUITE_SSO_*/SUITE_ADMIN_SSO_*/SUITE_API_SSO_*
#      ID_ADMIN_SSO_*, ID_API_SSO_*
#      BOT_ADMIN_SSO_*, BOT_API_SSO_*
#    (redirect/web_origins задаются CSV, по умолчанию используются dev-домены и localhost-порты)
#
# 2. (опционально) Скопируйте killbill.overrides/killbill.properties.example в
#    killbill.overrides/killbill.properties и обновите значения.
#
# 3. Запустите стек:
/int/id/scripts/devops/setup_keycloak_killbill.sh start --env /int/id/.env
# при изменении тем Keycloak добавьте --clear-theme-cache, чтобы сбросить кеш статических ресурсов
# для end-to-end smoke можно дополнительно указать --selenium-smoke
# при старте выполняются проверки env и bootstrap Keycloak/Kill Bill (можно отключить, установив ID_BOOTSTRAP_DISABLED=1)

# 4. Проверить состояние:
/int/id/scripts/devops/setup_keycloak_killbill.sh status

# 5. Логи конкретного сервиса:
/int/id/scripts/devops/setup_keycloak_killbill.sh logs keycloak
```

> **Примечание:** `docker compose down` удаляет контейнеры/volume’ы; используйте опцию `down` скрипта только при необходимости.
>
> При bootstrap Keycloak создаётся (или обновляется) realm `intdata`, а также полный набор OIDC-клиентов для модулей платформы (`<module>-web`, `<module>-admin`, `<module>-api`). Конфигурация (client id, redirect-uri, web origins, client secret) считывается из переменных `*_SSO_*`/`*_ADMIN_SSO_*`/`*_API_SSO_*`. Значения по умолчанию ориентированы на домены `*.dev.intdata.pro` и локальные порты; перед запуском продакшн-стека обязательно синхронизируйте их через OpenBao.
>
> Сессия bootstrap также применяет тему `ID_KEYCLOAK_LOGIN_THEME` и отображаемое имя Realm (`ID_KEYCLOAK_DISPLAY_NAME`, `ID_KEYCLOAK_DISPLAY_NAME_HTML`). Для брендовой темы `intdata` убедитесь, что в репозитории обновлены файлы `id/keycloak/themes/intdata`, затем выполните `restart` + `logs` + smoke.

### Selenium UI smoke (standalone)

- Скрипт `scripts/devops/run_selenium_smoke.sh` выполняет headless smoke веб-интерфейсов (маркер `selenium`):
  1. создаёт/переиспользует виртуальное окружение `venv/`;
  2. устанавливает зависимости из `tests/requirements.txt`;
  3. запускает `pytest -m selenium tests/web/test_ui_selenium_smoke.py`, передавая дополнительные аргументы pytest из командной строки.
- Параметры через переменные окружения:
  - `CHROME_BINARY` — путь к Chromium/Chrome (по умолчанию `/usr/bin/chromium`);
  - `SELENIUM_URL_<MODULE>` — переопределённые хосты для smoke;
  - `SELENIUM_WAIT_TIMEOUT` — таймаут ожидания (секунды, дефолт 20).
- Примеры:

  ```bash
  /int/id/scripts/devops/run_selenium_smoke.sh -q
  CHROME_BINARY=/opt/google/chrome/chrome /int/id/scripts/devops/run_selenium_smoke.sh --maxfail=1
  ```

- Скриншоты и другие артефакты сохраняются в `tests/web/screenshots/`; не коммитим чувствительные данные.
- Флаг `setup_keycloak_killbill.sh --selenium-smoke` вызывает этот скрипт автоматически в конце DevOps-цикла.

### Что делает стек

- **Keycloak** на `https://localhost:${ID_KEYCLOAK_HTTP_PORT:-8443}` — единый IdP для /id.
- **Kill Bill** на `http://localhost:${ID_KILLBILL_HTTP_PORT:-8081}` — биллинг/подписки.
- **KAUI** (админ Kill Bill) на `http://localhost:${ID_KAUI_HTTP_PORT:-9091}` — опционально (profile `kaui`).

### DevOps задачи

- Создать секреты в vault/1Password (настоящие пароли не коммитить).
- Подготовить инфраструктурные БД (prod/stage) через команды DBA.
- Настроить systemd unit или orchestrator (k8s) на базе compose-файла.
- Добавить health-check в `scripts/devops/smoke.sh` после интеграции с /id.
- После обновления smoke (`scripts/devops/smoke.sh`) будет проверять Keycloak (`/.well-known/openid-configuration`) и Kill Bill (`/1.0/healthcheck`). Убедитесь, что переменные `ID_KEYCLOAK_HTTP_PORT_LEGACY`, `ID_KEYCLOAK_REALM`, `ID_KILLBILL_HTTP_PORT` заданы при запуске.

## Mailpit (единый SMTP шлюз)

- **/int/id/docker-compose.yaml** с профилем `mailpit` — standalone манифест SMTP/UI сервиса (`mail.intdata.pro`, `smtp.intdata.pro`).
```
docker compose -f /int/id/docker-compose.yaml --profile mailpit ps
```
- **run-mailpit.sh** — zero-wait цикл (`rebuild → restart → logs → log-scan → smoke`), готовит каталоги и проверяет API `/api/v1/info` через `mail.intdata.pro`.
- **meta-intdata-mailpit-dev.service** — systemd-юнит (см. `configs/systemd/`) для автономного рестарта.

### Быстрый старт

```bash
# 1. Создайте директории и секреты:
#    sudo mkdir -p /var/lib/intdata/mailpit /etc/intdata/mailpit/tls /var/log/intdata/mailpit
#    sudo htpasswd -bc /etc/intdata/mailpit/users.htpasswd intdata-smtp '<smtp-password>'
#    sudo htpasswd -bc /etc/intdata/mailpit/ui.htpasswd intdata-ui '<ui-password>'
#    # TLS сертификаты mail.intdata.pro / smtp.intdata.pro поместите в /etc/intdata/mailpit/tls/
#
# 2. Экспортируйте переменные (или заполните .env):
export SMTP_PASSWORD='<smtp-password>'
export MAILPIT_SMTP_USER='intdata-smtp'
export MAILPIT_UI_USER='intdata-ui'
export MAILPIT_DATA_DIR='/var/lib/intdata/mailpit'
export MAILPIT_CONFIG_DIR='/etc/intdata/mailpit'
export MAILPIT_LOG_DIR='/var/log/intdata/mailpit'

# 3. Запустите цикл:
scripts/devops/run-mailpit.sh

# 4. Убедитесь, что mailpit работает:
docker compose -f id/docker-compose.yaml --profile mailpit ps
```

> **Важно:** файлы `users.htpasswd`, `ui.htpasswd`, TLS-ключи и пароли не попадают в git. Управляйте ими через секрет-хранилище Владельца.

### Сертификаты mail.intdata.pro / smtp.intdata.pro
- Фронт: `nginx` (80/443) → `apache2` (8080/8443) → `mailpit`.
- Сертификат Let's Encrypt выпускаем через snap `certbot`:

```bash
sudo certbot certonly \
  --webroot -w /var/www/letsencrypt \
  --cert-name mail.intdata.pro \
  -d mail.intdata.pro -d smtp.intdata.pro \
  --agree-tos --no-eff-email -m prointdata@ya.ru
```

- Симлинки в `/etc/intdata/mailpit/tls/` должны указывать на `/etc/letsencrypt/live/mail.intdata.pro-0001/{fullchain,privkey}.pem` для UI и SMTP (`mail.*`, `smtp.*`).
- После выпуска выполните `systemctl reload nginx apache2` и `scripts/devops/run-mailpit.sh` для обновления контейнера.

### SMTP (Яндекс Почта)
- Проектные сервисы отправляют письма через `smtp.yandex.ru` (порт `465`, SSL), аккаунт `prointdata@yandex.ru`, пароль приложения задаёт владелец.
- Минимальные переменные `.env`: `SMTP_HOST=smtp.yandex.ru`, `SMTP_PORT=465`, `SMTP_USE_SSL=true`, `SMTP_USER=prointdata@yandex.ru`, `SMTP_PASSWORD=<yandex_app_password>`, `EMAIL_FROM=prointdata@yandex.ru`.
- Smoke-проверка отправки:

```bash
python - <<'PY'
import smtplib, ssl
from email.message import EmailMessage
msg = EmailMessage()
msg['Subject'] = 'Yandex SMTP smoke'
msg['From'] = 'prointdata@yandex.ru'
msg['To'] = 'prointdata@yandex.ru'
msg.set_content('Smoke delivery через smtp.yandex.ru')
context = ssl.create_default_context()
with smtplib.SMTP_SSL('smtp.yandex.ru', 465, context=context, timeout=15) as smtp:
    smtp.login('prointdata@yandex.ru', '<yandex_app_password>')
    smtp.send_message(msg)
print('sent')
PY
```

- Mailpit (`https://mail.intdata.pro`) используется только для QA/наблюдения; реальные письма уходят напрямую через Яндекс. Пароль приложения держим в секрет‑хранилище владельца, а в `.env` подставляем при деплое.

### OpenBao (self-host)
- Конфиг объединён в `id/docker-compose.yaml` (profile `openbao`); переменные читаются из корневого `.env` (`OPENBAO_*`). Отдельный `.env.infisical УДАЛЁН` больше не используется.
- UI/API доступен по `https://kms.intdata.pro`. Apache/Nginx проксируют запросы на локальный порт `8200` (см. `configs/apache2/kms.intdata.pro.conf`).
- Запуск/перезапуск:

```bash
OPENBAO_ENV_FILE=.env \
scripts/devops/run-openbao.sh
```

- После старта выполните `python -m id.api.cli sync-openbao --env-file .env`, чтобы выгрузить секреты модулей в OpenBao и обновить секцию `OPENBAO SYNC` в `.env`.
- Проверка доступности:

```bash
curl -Ik https://kms.intdata.pro/v1/sys/health
```

- Root token (`ID_OPENBAO_TOKEN`) хранится только во внешнем секрет-хранилище. При ротации токена сначала обновите `.env`, затем повторно выполните `sync-openbao`.

## Утилиты и вспомогательные скрипты

- **certbot-chat.sh** — выпуск/обновление сертификатов Let's Encrypt для доменов чата (`chat.intdata.pro`, `admin.chat.intdata.pro`, `element.chat.intdata.pro`). Настраивает `snap`/`certbot`, выполняет `certbot --apache` для каждой зоны. Запуск под учеткой DevOps:\
  `scripts/devops/certbot-chat.sh`.

- **check_duplicates.py** — ищет дубликаты файлов по SHA-1. По умолчанию сканирует `/int/nexus/web/static/diagnostics`, игнорируя `.git`, `node_modules`, build-артефакты. Код возврата `0`, если дублей нет, и `1`, если найдены совпадения. Пример:\
  `python3 scripts/devops/check_duplicates.py shared/assets -e build -e cache`.

- **dev-redeploy.sh** — стандартный DevOps-цикл для ветки `dev`: подтягивает `.env`, запускает rebuild/restart сервисов, собирает логи в `logs/devops/<UTC>/`, прогоняет `log-scan.py`, выполняет HTTP-smoke и дополнительно запускает [`smoke.sh`](smoke.sh) (включая OpenBao). Использование:\
  `scripts/devops/dev-redeploy.sh`.

- **generate_nginx_from_apache.py** — миграционная утилита: читает активные Apache vhost’ы и генерирует эквивалентные прокси-конфиги nginx (HTTP+HTTPS) в `configs/nginx/generated/`. Требует root-доступ. Запуск:\
  `sudo python3 scripts/devops/generate_nginx_from_apache.py`.

- **import_archive_to_project.py** — импортирует оффлайн-черновики из `AGENTS/issues.json` (`offline_queue`) в GitHub Project V2: создаёт Draft Issue, переносит статус и основные поля (Status/Role/Module/Type) и очищает запись в зеркале. Нужен `GITHUB_TOKEN` (или `gh auth token`). Пример:\
  `python3 scripts/devops/import_archive_to_project.py --project-number 1`.

- **install_services.sh** — устанавливает/обновляет systemd unit’ы из `configs/systemd/` (копирование в `/etc/systemd/system`, `daemon-reload`, `enable`). Запуск только от root:\
  `sudo scripts/devops/install_services.sh`.

- **local-redeploy.sh** — локальный перезапуск dev-стека без полного DevOps-цикла: обновляет зависимости, кэширует фронт, перезапускает docker-compose сервисы. Применяется во время разработки:\
  `scripts/devops/local-redeploy.sh`.

- **log-scan.py** — ищет критические записи в логах (паттерн `ERROR|FATAL|CRITICAL|Traceback|...`). Используется внутри `dev-redeploy.sh`, но может запускаться отдельно:\
  `python3 scripts/devops/log-scan.py logs/devops/<timestamp>`.

- **project_deadline_guardian.py** — контролирует дедлайны карточек GitHub Project: переводит просроченные элементы в статус `Expired` и уведомляет указанных пользователей (см. workflow `project_deadline_guardian.yml`).

- **rebuild_service.sh** — точечный пересбор docker-compose сервиса: вызовет `docker compose build <service>` + `up -d`. Указываем compose-name из корневого `docker-compose.yml`:\
  `scripts/devops/rebuild_service.sh nexus-web`.

- **rebuild_smart_sidebar.sh** — пересборка фронтенда Nexus из canonical repo `/int/nexus/web`, затем синхронизация артефактов в target web-root. Использование:\
  `scripts/devops/rebuild_smart_sidebar.sh`.

- **run_task_reminder_worker.py** — entrypoint для фонового воркера напоминаний (используется в systemd/cron). Интервал опроса берёт из `TASK_REMINDER_INTERVAL` (секунды). Запуск:\
  `python3 scripts/devops/run_task_reminder_worker.py`.

- **sync_discussions_mirror.py** — выгружает GitHub Discussions по категориям в JSON (например, `AGENTS/announcements.json`, `AGENTS/research.json`). По умолчанию берёт только активные обсуждения; флаг `--include-closed` добавляет закрытые. Примеры:\
  `python3 scripts/devops/sync_discussions_mirror.py --slug announcements --output AGENTS/announcements.json`\
  `python3 scripts/devops/sync_discussions_mirror.py --slug research --output AGENTS/research.json --include-closed`.

- **run-openbao.sh**, **run-mailpit.sh**, **run_selenium_smoke.sh**, **setup_keycloak_killbill.sh**, **smoke.sh** — описаны в разделах выше (OpenBao, Mailpit, Selenium smoke, IAM стек, DevOps smoke).
