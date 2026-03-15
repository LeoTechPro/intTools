# PunctB -> Timeweb: frontend runbook и historical backend notes

Проверено по коду и документации репозитория `2026-03-08`.

Важное ограничение: root `deploy/timeweb` в этом репозитории больше не используется и не считается местом для актуальных deploy-артефактов. Если для frontend Timeweb нужен operational context, он живёт только в этом reference-файле и в `SKILL.md`.

## 1. Краткий вывод
- `web` публикуется как отдельный Timeweb `Frontend App`.
- `backend` больше не публикуется в Timeweb App Platform: актуальный production backend живёт на отдельном VDS `5.42.105.191`.
- Production checkout backend на VDS: `/punctb` как отдельный clone `git@github.com:LeoTechPro/PunctB.git`, только ветка `main`.
- Для миграции backend старой платформы допускается второй отдельный clone `/punkt-b/backend` из `git@github.com:punktbDev/punktb.git`, только ветка `master`.
- Dev-контур на `vds.intdata.pro` не мигрирует и запускается только через явные `*.dev.yml`.

## DB Guardrail
- DEV-контур `dev.punctb.pro` на текущей машине `vds.intdata.pro` использует локальный PostgreSQL этой машины; для него этот runbook не вводит новых ограничений сверх обычных проектных правил разработки.
- БД `77.95.201.51:5432/PunctBPro` и DSN `postgresql://PunctBPro:%2C_jn0joar_%23UG%3A@77.95.201.51:5432/PunctBPro` считать prod БД `punctb.pro`.
- Read-only аудит и проверки для `77.95.201.51:5432/PunctBPro` допустимы по умолчанию.
- Любые изменения в `77.95.201.51:5432/PunctBPro` допускаются только после явного согласования владельца на конкретную операцию, когда владелец прямо понимает и осознаёт последствия и состояние до/после.
- Без такого согласования запрещены любые записи и structural changes против `77.95.201.51:5432/PunctBPro`: `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, DDL, миграции, rename/drop/reset, смена владельца, `GRANT/REVOKE` и любые иные правки.
- БД `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB`, а также DSN `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunktB` и `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunctB` считать запрещёнными к изменениям legacy-контурами старой платформы.
- Для `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB` допустимы только read-only проверки и аудит; любые mutating-операции запрещены при любых обстоятельствах.

## 2. Что именно есть в проекте сейчас

### Frontend
- Каталог: `web/`
- Стек: `React 19 + Vite 7 + TypeScript`
- Build command: `npm --prefix web run build`
- Output directory: `web/dist`
- Критичные env:
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
  - `VITE_SUPABASE_REALTIME_ENABLED` (опционально, по умолчанию в коде включён)

### Frontend-specific risk
- В [`web/src/shared/lib/supabaseClient.ts`](/git/punctb/web/src/shared/lib/supabaseClient.ts) есть fallback на `https://api-dev.punctb.pro` и dev anon key.
- Следствие: если в проде забыть `VITE_SUPABASE_URL`/`VITE_SUPABASE_ANON_KEY`, frontend может начать работать против dev-контура.
- Для production это считать hard blocker конфигурации.

### Backend
- Каталог: `backend/`
- Тип: self-hosted Supabase stack поверх внешней PostgreSQL.
- Основные сервисы:
  - `postgrest`
  - `auth`
  - `auth-mailer-templates`
  - `realtime`
  - `storage`
  - `kong`
  - `functions`
  - `meta` и `studio` как admin profile
- Публичный вход в API идёт через `kong`.
- Edge Functions проксируются через `/functions/v1/*`.

### Backend-specific risks
- Root [`docker-compose.yml`](/git/punctb/docker-compose.yml) теперь один для `dev` и `prod`; различие между контурами задаётся только root `.env`.
- Для актуального VDS backend file-backed storage допустим и уже каноничен; S3 остаётся только опциональным backend mode, а не обязательным production-требованием.
- Несколько backend-функций используют fallback `SITE_URL=https://dev.punctb.pro`, поэтому `SITE_URL` и `SUPABASE_PUBLIC_URL` в production обязательны.

## 3. Матрица применимости Timeweb App Platform

| Часть PunctB | Режим Timeweb | Статус | Комментарий |
| --- | --- | --- | --- |
| `web/` | `Frontend -> Other JS framework` | `YES` | Прямой target |
| `backend` как single Node app | `Backend` | `NO` | Это не одиночный Node/API процесс |
| root `docker-compose.yml` | VDS backend runtime | `YES` | Канонический production artifact для backend на VDS |
| backend через кастомные образы | `Dockerfile` | `YES` | Но нужны отдельные Dockerfile/image-level изменения |

## 4. Рекомендуемая целевая схема

### Вариант 1. Актуальный production contour
1. Frontend (`punctb.pro`) -> Timeweb App Platform Frontend.
2. Backend (`api.punctb.pro`) -> отдельный prod VDS `5.42.105.191`.
3. PostgreSQL -> нативно на том же VDS, вне Docker Compose.

### Вариант 2. Historical fallback, неканонический
1. Frontend (`punctb.pro`) можно продолжать держать в Timeweb Apps.
2. Старый backend можно заранее подготовить на VDS через `/punkt-b/backend`, но не считать cutover завершённым без отдельного owner decision и без остановки живого Timeweb backend в рамках отдельного окна переключения.

## 5. Frontend: точные настройки в Timeweb

### Что выбирать в wizard
- Тип: `Frontend`
- Framework: `Other JS framework`
- Environment: `Node.js 24`
- Repository branch: `dev` для dev/beta, `main` только после owner-approved prod cutover

### Build settings
- Build command:
```bash
npm --prefix web ci && npm --prefix web run build
```
- Build directory:
```text
web/dist
```

### Обязательные env для frontend app
```env
VITE_SUPABASE_URL=https://api.punctb.pro
VITE_SUPABASE_ANON_KEY=<prod-anon-key>
VITE_SUPABASE_REALTIME_ENABLED=true
VITE_PUNCTB_REQUIRE_EXPLICIT_SUPABASE_CONFIG=true
```

Последняя переменная включает strict gate, который запрещает production frontend молча уходить на dev Supabase defaults.

### Frontend smoke после деплоя
1. Открыть `/`.
2. Открыть `/login`.
3. Проверить прямой вход на client-side route вроде `/<slug>` и `/conclusions`.
4. Убедиться, что frontend ходит в `api.punctb.pro`, а не в `api-dev.punctb.pro`.
5. Проверить авторизацию и восстановление доступа.

### Frontend smoke: terminal snippet
```bash
export PUNCTB_PROD_APP_URL=https://punctb.pro
export PUNCTB_PROD_API_URL=https://api.punctb.pro
export PUNCTB_PROD_ANON_KEY=<prod-anon-key>

curl -fsS "${PUNCTB_PROD_APP_URL%/}/" >/dev/null
curl -fsS "${PUNCTB_PROD_APP_URL%/}/login" >/dev/null
curl -fsS "${PUNCTB_PROD_API_URL%/}/healthz"
curl -fsS \
  -H "apikey: ${PUNCTB_PROD_ANON_KEY}" \
  -H "Authorization: Bearer ${PUNCTB_PROD_ANON_KEY}" \
  "${PUNCTB_PROD_API_URL%/}/functions/v1/main"
```

## 6. Historical backend notes

Эти заметки нужны только как historical context. Отдельные backend Timeweb bundle/config/scripts в корне репозитория больше не храним.

### Блокер 1. Почему старый App Platform path был нестабилен
- Timeweb docs требуют `docker-compose.yml` в корне.
- Это требование раньше использовалось для backend, но теперь [`docker-compose.yml`](/git/punctb/docker-compose.yml) считается production artifact для VDS runtime.
- Актуальный dev-контур использует тот же tracked compose, но со своим root `.env`.

### Блокер 2. `volumes` запрещены в App Platform
- Для Timeweb это нельзя допускать только в hypothetical App Platform backend-path, который больше не является каноном.
- Для актуального backend на VDS volume-монты и file-backed storage допустимы.

### Блокер 3. Storage state сидел в контейнере
- Для исторического production на Timeweb пришлось бы:
  - вынести storage в S3-compatible backend;
  - убрать `storage-data`;
  - не рассчитывать на локальный persistent disk приложения.

### Блокер 4. Публичный health path был неудобен для App Platform
- Timeweb backend/dockerfile healthcheck ожидает path с `200 OK`.
- У актуального backend на VDS публичный `/healthz` уже есть, но этот путь появился как часть VDS runtime canon, а не как отдельный App Platform backend artifact.
- Для smoke сейчас можно использовать:
```bash
curl -sS https://api.punctb.pro/healthz
```
- Для historical App Platform backend-path этого всё равно было недостаточно: нужен был не просто path, а поддерживаемый и сопровождаемый backend artifact, который больше не является каноном проекта.

## 7. Что важно помнить после ухода backend с Timeweb

### Актуальный production backend canon
1. Поддерживать root `docker-compose.yml` как production artifact для backend на VDS `5.42.105.191`.
2. Держать production checkout только в `/punctb` и не смешивать его с dev-клонами.
3. Не возвращать backend в Timeweb App Platform как default target без отдельного owner decision.
4. Сохранять `kong`, auth, postgrest, realtime, storage, functions в одном backend runtime-контуре на VDS.
5. PostgreSQL держать нативно на хосте VDS, не контейнером.

### Что можно оставить внешним
- PostgreSQL
- SMTP
- S3-compatible object storage
- DNS

## 8. Production env matrix для backend

### Базовые env
```env
SUPABASE_PUBLIC_URL=https://api.punctb.pro
SUPABASE_URL=https://api.punctb.pro
SITE_URL=https://punctb.pro
ADDITIONAL_REDIRECT_URLS=https://punctb.pro,https://punctb.pro/recovery,https://punctb.pro/reset-password,https://diag.punctb.pro
```

### DB env
```env
POSTGRES_DB=<existing-db-name>
POSTGRES_USER=<existing-db-user>
POSTGRES_PASSWORD=<existing-db-password>
DB_HOST=<existing-db-host>
DB_PORT=5432
```

### Auth / JWT
```env
JWT_SECRET=<prod-jwt-secret>
ANON_KEY=<prod-anon-jwt>
SERVICE_ROLE_KEY=<prod-service-role-jwt>
SUPABASE_SERVICE_ROLE_KEY=<prod-service-role-jwt>
```

### SMTP / mail
```env
SMTP_HOST=<smtp-host>
SMTP_PORT=587
SMTP_USER=<smtp-user>
SMTP_PASS=<smtp-pass>
SMTP_ADMIN_EMAIL=<auth-from-email>
SMTP_FROM_NAME=<auth-from-name>
NOTIFY_SMTP_HOST=<smtp-host>
NOTIFY_SMTP_PORT=587
NOTIFY_SMTP_USER=<notify-user>
NOTIFY_SMTP_PASS=<notify-pass>
NOTIFY_SMTP_ADMIN_EMAIL=<notify-email>
NOTIFY_SMTP_FROM_NAME=<notify-name>
```

### Secrets для runtime-сервисов
```env
REALTIME_SECRET_KEY_BASE=<secret>
REALTIME_DB_ENC_KEY=<secret>
PG_META_CRYPTO_KEY=<secret>
CHAT_TELEGRAM_BOT_TOKEN=<secret>
CHAT_TELEGRAM_WEBHOOK_SECRET=<secret>
CHAT_LINK_SIGNING_SECRET=<secret>
CRM_FRANCHISEE_WEBHOOK_TOKEN=<secret>
BITRIX_WEBHOOK_BASE_URL=<secret>
```

### Storage
- В production App Platform не использовать `STORAGE_BACKEND=file`.
- Нужен S3-compatible backend и соответствующая конфигурация storage-service.

## 9. Домены

### Рекомендуемое соответствие
- `punctb.pro` -> frontend app
- `api.punctb.pro` -> backend public gateway (`kong`)
- `admin.punctb.pro` -> optional studio/admin app
- `diag.punctb.pro` -> добавить в redirect allow-list, если он остаётся в рабочем сценарии

### Обязательная синхронизация доменов
- frontend env `VITE_SUPABASE_URL` должен смотреть в `api.punctb.pro`
- backend `SITE_URL` должен смотреть в `punctb.pro`
- backend `SUPABASE_PUBLIC_URL` должен смотреть в `api.punctb.pro`
- `ADDITIONAL_REDIRECT_URLS` должен включать все recovery/reset/diag сценарии

## 10. Smoke checklist после продового cutover

### Frontend
1. `punctb.pro` открывается по HTTPS.
2. SPA-маршруты открываются напрямую без белого экрана.
3. Логин и logout работают.
4. После логина запросы идут в `api.punctb.pro`.

### Backend
1. Публичный gateway отвечает на базовый smoke-запрос.
2. `curl -H "apikey: ..."` на `/functions/v1/main` возвращает `ok: true`.
3. Auth magic link / recovery письма приходят с правильными ссылками.
4. Edge Functions, которые используют `SITE_URL`, больше не генерируют `dev.punctb.pro`.
5. Upload/download через storage проходят на новом backend.
6. Realtime-подключение клиента работает.

### RBAC / бизнес-потоки
1. Менеджер входит и видит workspace.
2. Специалист открывает профиль и результаты.
3. Клиентский профиль и публичные страницы открываются.
4. Заключения и диагностические сценарии не ломаются после cutover.

## 11. Rollback-модель
1. Не выключать старый prod API до завершения smoke.
2. Сначала поднять Timeweb apps на технических доменах.
3. Проверить env и функциональность до привязки custom domains.
4. После перевода DNS держать старый контур готовым к быстрому возврату.
5. Если обнаружена ошибка env/domain, rollback делать через возврат DNS/домена и остановку cutover, а не через срочный hotfix на проде без проверки.

## 12. Что я бы считал Definition of Ready для полного переезда
1. Есть Timeweb-compatible backend artifact.
2. Storage вынесен в S3-compatible backend.
3. Добавлен public health endpoint.
4. Все prod env собраны без dev-fallback.
5. Доменная схема `punctb.pro` / `api.punctb.pro` / optional `admin.punctb.pro` протестирована на технических доменах.
6. Пройден полный smoke по login, diagnostics, conclusions, notifications и uploads.
