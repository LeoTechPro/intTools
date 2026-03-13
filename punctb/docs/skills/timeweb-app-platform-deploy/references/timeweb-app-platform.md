# Timeweb App Platform: актуальная опорная сводка

Проверено по официальной документации Timeweb `2026-03-08`.
Если пользователь спрашивает про `latest`, лимиты, UI-поля или новые режимы деплоя, нужно заново открыть официальные страницы Timeweb.

## Источники
- https://timeweb.cloud/docs/apps/how-it-works
- https://timeweb.cloud/docs/apps/connecting-repositories
- https://timeweb.cloud/docs/apps/deploying-frontend-apps
- https://timeweb.cloud/docs/apps/deploying-frontend-apps/other
- https://timeweb.cloud/docs/apps/deploying-backend-applications
- https://timeweb.cloud/docs/apps/deploying-backend-applications/express
- https://timeweb.cloud/docs/apps/deploying-with-dockerfile
- https://timeweb.cloud/docs/apps/deploying-with-docker-compose
- https://timeweb.cloud/docs/apps/managing-apps
- https://timeweb.cloud/docs/apps/variables
- https://timeweb.cloud/docs/apps/healthcheck-path
- https://timeweb.cloud/docs/apps/faq
- https://timeweb.cloud/docs/cloud-servers/private-networks
- https://timeweb.cloud/api-docs/
- https://timeweb.cloud/docs/twc-cli
- https://timeweb.cloud/docs/twc-cli/twc-cli-start
- https://timeweb.cloud/docs/account-management/token

## 1. Базовая модель платформы
- App Platform умеет деплоить приложения напрямую из Git-репозитория.
- Для GitHub/GitLab можно включать автодеплой.
- Для деплоя по URL публичного репозитория автодеплой недоступен.
- После создания приложение получает технический домен вида `*.twc1.net`.
- Основные режимы в docs: `Frontend`, `Backend`, `Dockerfile`, `Docker Compose`.

## 2. Репозиторий и точка входа
- Платформа ориентируется на корень репозитория.
- Для frontend важен `package.json` в проекте.
- Для Dockerfile ожидается `Dockerfile` в корне репозитория.
- Для Docker Compose ожидается `docker-compose.yml` в корне репозитория.
- Git LFS в App Platform не поддерживается.

## 3. Frontend Apps
- Подходят для статических frontend-проектов, которые собираются в артефакт и потом отдаются платформой.
- В wizard для `Other JS framework` доступны:
  - команда сборки;
  - системные зависимости;
  - директория сборки.
- Timeweb сам ставит зависимости по менеджеру пакетов проекта, затем выполняет build-команду.
- Типичный pipeline: выбрать framework, указать ветку, указать build command, указать output/build directory.
- Для frontend-apps нет SSH/console режима как у backend/dockerfile apps.

## 4. Backend Apps
- Подходят для приложений, которые сами слушают порт внутри контейнера/процесса.
- При создании задаются CPU/RAM/NVMe, ветка, env, домены, опционально путь healthcheck.
- Для backend-apps есть встроенная консоль приложения.
- В официальных backend examples явно проверяется:
  - приложение слушает `0.0.0.0`, а не только localhost;
  - задан корректный порт;
  - в корне есть нужные project files.

## 5. Dockerfile Apps
- Используются, когда стандартный frontend/backend preset не подходит.
- Dockerfile должен лежать в корне репозитория.
- Контейнер должен объявлять `EXPOSE`.
- В wizard доступны custom domain, env, healthcheck path и выбор private network.
- По FAQ Dockerfile-app поддерживает console/SSH-доступ.

## 6. Docker Compose Apps
- `docker-compose.yml` должен лежать в корне репозитория.
- Каждый сервис должен иметь `image` или `build`.
- Первый сервис в `docker-compose.yml` считается основным: именно на него проксируются запросы с технического и кастомного домена.
- Если другие сервисы тоже проброшены наружу через host-port, к ним можно ходить только с явным `:<port>` в URL.
- Нельзя использовать host-порты `80` и `443`.
- В panel для Docker Compose apps нет настройки healthcheck path.
- По FAQ для Docker Compose apps нет встроенной консоли приложения.

### Запрещённые/неподдерживаемые элементы Docker Compose
- `volumes`
- `network_mode`
- `build.network`
- `build.extra_hosts`

### Практический вывод
- Compose в App Platform подходит только для stateless/multi-service topology без bind mounts и без named volumes.
- Любое состояние нужно выносить наружу: БД, object storage, очереди, конфиги/шаблоны через image или env.

## 7. Переменные окружения
- В docs есть локальные и глобальные переменные.
- Ограничение платформы: максимум `100` env vars на приложение.
- Переменные задаются в настройках приложения и применяются при деплое.

## 8. Домены, логи, история, управление
- После создания можно привязать custom domain в настройках приложения.
- В интерфейсе есть как минимум:
  - dashboard/overview;
  - logs;
  - settings;
  - history.
- Логи разделяются на build/deploy/container runtime.
- Есть операции restart/pause/redeploy через UI.

## 9. Healthcheck
- Отдельный `healthcheck path` поддерживается у backend/dockerfile apps.
- Для Docker Compose apps эта настройка в panel недоступна.
- Если path задан, он должен отдавать публичный `200 OK` без нестандартных предпосылок.

## 10. Private Network и внешние зависимости
- При создании backend/dockerfile app можно выбрать private network.
- По docs private network для cloud servers нельзя сменить после создания сервера.
- У cloud database cluster есть режим работы только внутри private network.
- Практически это означает:
  - если БД уже живёт внутри private network, backend/dockerfile app логично сажать в тот же приватный контур;
  - frontend app обычно работает через публичный HTTPS API.

## 11. Persistence и storage-ограничения
- По FAQ платформа не даёт монтировать сетевые хранилища.
- По FAQ нет отдельного управления диском приложения.
- Поэтому App Platform не стоит использовать как место для production file storage "внутри контейнера".
- Для production state используем внешние managed services: PostgreSQL, S3-compatible object storage и т.п.

## 12. Что важно помнить при проектировании под Timeweb
- `Frontend` хорошо подходит под Vite/SPA/static builds.
- `Backend` хорошо подходит под single-process API service.
- `Dockerfile` нужен для custom runtime и image-level упаковки.
- `Docker Compose` годится только если приложение уже не зависит от `volumes` и может жить без console/healthcheck path в panel.

## 13. Каналы автоматизации и диагностики
- `Timeweb MCP` (`timeweb-cloud/mcp-server`) — официальный experimental MCP для bootstrap/deploy сценариев. Локально проверен `2026-03-10`.
- По локальной валидации через MCP доступны только deploy/VCS/presets/settings операции: `create_timeweb_app`, `add_vcs_provider`, `get_vcs_providers`, `get_vcs_provider_repositories`, `get_vcs_provider_by_repository_url`, `get_allowed_presets`, `get_deploy_settings`.
- В MCP пока нет инструментов для runtime logs, deploy history, restart/pause или incident triage. Для анализа ошибок нужен `Public API` и/или UI.
- На этой машине read-only проверены следующие app endpoints официального Public API `https://api.timeweb.cloud/api/v1`:
  - `GET /apps`
  - `GET /apps/{app_id}`
  - `GET /apps/{app_id}/deploys`
  - `GET /apps/{app_id}/logs`
- `GET /apps/{app_id}/logs` реально возвращает runtime/build output и пригоден для диагностики. Используй его для frontend apps и historical incident review по старым App Platform-контурам.
- `twc` CLI остаётся официальным каналом для inventory и app metadata, но app-log workflow для App Platform в CLI не зафиксирован как основной. Не подменяй им Public API, когда разбираешь инциденты.
- Для безопасной локальной автоматизации токен лучше держать в env, а не дублировать по нескольким config-файлам. `twc` официально поддерживает `TWC_TOKEN`; наличие config-файла при этом необязательно.
- Практический вывод для Codex/агентов:
  - deploy/create/VCS bootstrap -> `Timeweb MCP`
  - app inventory/basic metadata -> `twc` или `GET /apps*`
  - runtime error triage -> `GET /apps/{app_id}/logs` + `GET /apps/{app_id}/deploys`
  - destructive actions -> только после явного подтверждения владельца, даже если API/MCP технически позволяют их вызвать

## PunctB Project Guardrail
- Для проекта PunctB dev-контур `dev.punctb.pro` на текущей машине `vds.intdata.pro` использует локальный PostgreSQL этой машины; этот reference не вводит для него новых ограничений сверх обычных проектных правил разработки.
- Для проекта PunctB БД `77.95.201.51:5432/PunctBPro` и DSN `postgresql://PunctBPro:%2C_jn0joar_%23UG%3A@77.95.201.51:5432/PunctBPro` считаются prod БД `punctb.pro`.
- Read-only аудит и проверки против `77.95.201.51:5432/PunctBPro` допустимы по умолчанию.
- Любые изменения против `77.95.201.51:5432/PunctBPro` допускаются только после явного согласования владельца на конкретную операцию, когда владелец прямо понимает и осознаёт последствия и состояние до/после.
- Без такого согласования запрещены любые mutating-операции против `77.95.201.51:5432/PunctBPro`: записи, DDL, миграции, rename/drop/reset, смена владельца/прав и любые иные правки.
- БД `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB`, а также DSN `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunktB` и `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunctB` считаются запрещёнными к изменениям legacy-контурами старой платформы.
- Для `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB` допустимы только read-only проверки и аудит; любые mutating-операции запрещены при любых обстоятельствах.
