---
name: timeweb-app-platform-deploy
description: "Развёртывание frontend PunctB в Timeweb App Platform и historical reference по старому Timeweb backend-контуру; актуальный prod backend живёт на отдельном VDS."
---

# Timeweb App Platform Deploy

## Goal
Используй этот skill, когда нужно:
- спланировать или выполнить развёртывание frontend PunctB в Timeweb App Platform;
- свериться с ограничениями App Platform для публичного frontend-контура;
- поднять historical context по старому backend-контуру в Timeweb без возврата к нему как к актуальному production target.

## Automation Channels
- `Timeweb MCP` — официальный `timeweb-cloud/mcp-server` остаётся deploy-oriented и experimental. По локальной валидации `2026-03-10` доступны только `create_timeweb_app`, `add_vcs_provider`, `get_vcs_providers`, `get_vcs_provider_repositories`, `get_vcs_provider_by_repository_url`, `get_allowed_presets`, `get_deploy_settings`.
- `Timeweb MCP` подходит для bootstrap/deploy/VCS-linking, но не покрывает runtime diagnostics: в сервере нет инструментов для логов, статуса deploy history, restart/pause и user-facing incident triage.
- Для анализа ошибок и разборов инцидентов используй `Public API` и при необходимости `twc` CLI как дополнительный read-only канал. На этой машине проверены read-only endpoints `GET /api/v1/apps`, `GET /api/v1/apps/{app_id}`, `GET /api/v1/apps/{app_id}/deploys`, `GET /api/v1/apps/{app_id}/logs`.
- `twc` полезен для inventory и app metadata, но не считай его источником app-логов по умолчанию: в актуальном CLI есть `apps list/get/create/delete`, а app-log workflow для App Platform нужно брать через Public API/UI.
- Для `twc` безопаснее использовать `TWC_TOKEN` через env, а не плодить новые конфиг-файлы с токеном, если на машине уже есть канонический secret-store.
- Operational note: при локальной интеграции с жёсткими stdio-MCP клиентами проверь startup output сервера. Валидация `timeweb-mcp-server@0.1.3` на этой машине показала лишнюю stdout-строку `Timeweb MCP server started`, из-за чего строгому клиенту может понадобиться stdout-filter/proxy.

## Read Order
1. Сначала открой `references/punctb-production-on-timeweb.md`.
2. Затем открой `references/timeweb-app-platform.md`.
3. Если пользователь просит проверить `latest`/изменения UI/лимитов/поддерживаемых фич, заново открой официальные страницы Timeweb перед ответом.

## Quick Verdict For This Repo
- `web/` разворачивается напрямую как Frontend App через режим `Other JS framework` на `Node.js 24`.
- Продовый frontend нельзя оставлять без явных `VITE_SUPABASE_URL` и `VITE_SUPABASE_ANON_KEY`: код имеет dev-fallback и при ошибке конфигурации может уехать в `api-dev.punctb.pro`.
- Актуальный prod backend `api.punctb.pro` больше не разворачивается в Timeweb App Platform: он живёт на отдельном VDS `5.42.105.191`.
- Корневой [`docker-compose.yml`](/git/punctb/docker-compose.yml) теперь трактуется как production backend artifact для VDS runtime, а не для Timeweb App Platform.
- Канонический production checkout backend на VDS: `/punctb`, отдельный clone `git@github.com:LeoTechRu/PunctB.git`, только ветка `main`.
- Для будущего вывода старого backend с Timeweb на тот же VDS разрешён отдельный clone `/punkt-b/backend` из `git@github.com:punktbDev/punktb.git`, только ветка `master`; до owner-approved cutover любые действия в живом Timeweb backend запрещены.
- Root `deploy/timeweb` в репозитории больше не является допустимым местом для deploy-артефактов: frontend Timeweb runbook хранится только в `references/*` этого skill.

## Default Recommendation For PunctB
1. Frontend публиковать как отдельный Timeweb `Frontend App`.
2. Backend `api.punctb.pro` держать на отдельном VDS `5.42.105.191`.
3. Dev-контур на `vds.intdata.pro` сохранять отдельно, но на том же tracked `docker-compose.yml` и root `.env`.

## Hard DB Guardrail
- DEV-контур `dev.punctb.pro` на текущей машине `vds.intdata.pro` использует локальный PostgreSQL этой машины; этот skill не вводит для него дополнительных запретов сверх обычных проектных правил разработки.
- БД `77.95.201.51:5432/PunctBPro` и DSN `postgresql://PunctBPro:%2C_jn0joar_%23UG%3A@77.95.201.51:5432/PunctBPro` — prod БД `punctb.pro`.
- Read-only аудит и проверки для `77.95.201.51:5432/PunctBPro` в рамках этого skill допустимы по умолчанию.
- Любые изменения в `77.95.201.51:5432/PunctBPro` допустимы только после явного согласования владельца на конкретную операцию, когда владелец прямо понимает и осознаёт последствия и состояние до/после.
- Без такого согласования в рамках этого skill запрещены любые mutating-операции против `77.95.201.51:5432/PunctBPro`: записи, DDL, миграции, ownership/grant-операции, rename/drop/reset и любые иные правки.
- БД `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB`, а также DSN `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunktB` и `postgresql://PunktB:o4FcD%2Ca!Lg(w%2BS@77.95.201.51:5432/PunctB` — запрещённые к изменениям legacy-контуры старой платформы.
- Для `77.95.201.51:5432/PunktB` и `77.95.201.51:5432/PunctB` в рамках этого skill допустимы только read-only проверки и аудит; любые изменения запрещены при любых обстоятельствах.
- Эти контуры запрещено смешивать и путать между собой в deploy/runbook решениях.

## Deployment Modes
### Mode A: Frontend Only In App Platform
Используй, если нужно быстро вынести `punctb.pro` в App Platform, а API пока остаётся на другом контуре.

### Mode B: Frontend In App Platform + Backend On VDS
Это актуальный target для PunctB:
- frontend -> отдельный Timeweb `Frontend App`;
- backend -> отдельный VDS `5.42.105.191` с production checkout `/punctb` и backend runtime из root `docker-compose.yml`;
- dev -> отдельный VDS contour на том же tracked `docker-compose.yml`, но со своим root `.env`.

## Workflow
1. Проверь целевой контур и домены в `README.md`, `.env.example`, `web/src/shared/lib/supabaseClient.ts`.
2. Для frontend используй точные настройки из `references/punctb-production-on-timeweb.md`.
3. Для backend сначала пройди раздел `Блокеры и обязательные адаптации`.
4. Не смешивай tracked compose и runtime env: root `docker-compose.yml` един для `dev` и `prod`, а различия задаются только через root `.env`.
5. Если задача про инцидент, deploy-failure или runtime error, сначала собери read-only контекст из `Public API`: app metadata, последние deploys, app logs. Только после этого переходи к гипотезам и рекомендациям.
6. После конфигурации доменов и env выполни smoke checklist из project reference.
7. Если задача касается frontend cutover в Timeweb, отдельно проверь:
  - `VITE_SUPABASE_URL` и `VITE_SUPABASE_ANON_KEY`;
  - auth redirects;
  - восстановление доступа;
  - что frontend ходит в `api.punctb.pro`, а не в dev-контур.

## What To Avoid
- Не предлагай Timeweb `Backend / Node.js` как прямой target для текущего backend: это не одиночный Node service, а multi-service self-hosted Supabase stack.
- Не считай, что Docker Compose в App Platform поддерживает текущие volume-монты или персистентный диск.
- Не предлагай возврат production backend в Timeweb App Platform как канон: актуальный production backend уже вынесен на отдельный VDS.
- Не возвращай в корень репозитория `deploy/` или backend deploy kit под Timeweb: для проекта это уже drift относительно текущего deployment canon.
- Не оставляй в production fallback-значения на dev-домены.
- Не смешивай user-facing docs с этим skill: внутренний runbook живёт здесь, а не в `docs/**`.
- Не предполагай, что `Timeweb MCP` умеет читать app logs или deploy history: для диагностики это неверное ожидание и оно приводит к ложным выводам.
- Не предполагай, что `twc apps` покрывает диагностику App Platform полностью: статус/metadata есть, но app-log triage нужно строить через `Public API` или UI.

## References
- `references/timeweb-app-platform.md` — сжатая карта официальной документации Timeweb App Platform.
- `references/punctb-production-on-timeweb.md` — PunctB-specific deployment matrix, exact commands, env и smoke.
