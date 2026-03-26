# Аудит event-системы и legacy-cleanup (2026-02-21)

## 1. Контекст и объём
- Контур: локальный репозиторий `/int/assess`, локальная БД `intdata`, read-only smoke `https://api.punctb.pro`.
- Цель: проверить и зафиксировать реальное состояние event-centric модели (`event_log` + timeline + notifications), устранить runtime-остатки legacy, синхронизировать документацию.
- Вне scope: архивные миграции (`backend/init/migrations/archive/**`) как historical/no-runtime.

## 2. Критические инциденты и статус
| ID | Симптом | Причина | Статус |
| --- | --- | --- | --- |
| EVT-01 | `PROFILE_LOAD_FAILED`, SQL `42P01 relation "app.audit_events" does not exist` при `user_profile_detail` | runtime-функция `app.user_profile_assignments` ссылалась на удалённую таблицу `app.audit_events` | Fixed |
| EVT-02 | риск падения cleanup delivery-лога | `app.purge_notification_deliveries` удаляла из legacy `app.notification_deliveries` | Fixed |

## 3. Внесённые исправления
1. Миграция `backend/init/migrations/20260221023000_event_core_runtime_legacy_fix.sql`:
- `app.user_profile_assignments(p_target uuid)` переведена на `app.event_log`.
- `app.purge_notification_deliveries(p_before timestamptz)` переведена на `app.event_notification_deliveries`.
- Добавлены `REVOKE/GRANT` и регистрация версии в `public.schema_migrations`.
2. Frontend cleanup (dynamic labels/fallback без hardcoded allowlist-блокировок, уже в актуальной `areas/workspace` taxonomy):
- `web/src/areas/workspace/notifications/model/notificationSettings.ts`
- `web/src/areas/workspace/settings/pages/SettingsPage.runtime.tsx`
- `web/src/areas/workspace/notifications/pages/NotificationsPage.tsx`
- `web/src/areas/workspace/timeline/model/timeline.constants.ts`
- `web/src/areas/workspace/timeline/hooks/useTimelineQueries.ts`
- `web/src/areas/workspace/timeline/ui/TimelineCard.tsx`
- `web/src/shared/lib/api.ts` (улучшена классификация ошибок `user_profile_detail` по SQLSTATE/HTTP).
3. Документация/спеки:
- `backend/README.md` синхронизирован с runtime-моделью `event_*`.
- `openspec/changes/notifications-core/context.md` и `openspec/changes/notifications-core/specs/notifications-core/spec.md` очищены от legacy-названий как текущего контракта.
- `openspec/changes/notifications-core/tasks.md` синхронизирован с `event_*` RPC/таблицами.

## 4. Проверка runtime-состояния БД
Выполнено в `intdata`:

```sql
-- Миграция зарегистрирована
select version from public.schema_migrations where version='20260221023000';
-- => 20260221023000

-- Активные функции больше не ссылаются на legacy таблицы
with f as (
  select pg_get_functiondef(p.oid) as d
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='app'
)
select count(*) from f where d ilike '%app.audit_events%';
-- => 0

with f as (
  select pg_get_functiondef(p.oid) as d
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='app'
)
select count(*) from f where d ilike '%app.notification_deliveries%';
-- => 0

-- Smoke профиля
select app.user_profile_detail('leonid', '<system_uuid>');
-- => ok (JSON, без 42P01)

-- Smoke cleanup delivery
select app.purge_notification_deliveries(now() - interval '90 days');
-- => ok (0+)
```

Дополнительная инвентаризация активных runtime-объектов (`pg_proc` + `pg_views` + `pg_matviews` + `pg_trigger` в `schema=app`):

```sql
with proc_hits as (
  select pg_get_functiondef(p.oid) as def
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='app'
),
view_hits as (
  select definition as def
  from pg_views
  where schemaname='app'
),
mview_hits as (
  select definition as def
  from pg_matviews
  where schemaname='app'
),
trig_hits as (
  select pg_get_triggerdef(t.oid) as def
  from pg_trigger t
  join pg_class c on c.oid=t.tgrelid
  join pg_namespace n on n.oid=c.relnamespace
  where n.nspname='app' and not t.tgisinternal
),
all_objs as (
  select * from proc_hits
  union all
  select * from view_hits
  union all
  select * from mview_hits
  union all
  select * from trig_hits
),
markers as (
  select * from (values
    ('app.audit_events'),
    ('app.notification_deliveries'),
    ('app.notification_matrix_list('),
    ('app.notification_matrix_set('),
    ('app.collect_client_timeline('),
    ('app.collect_specialist_timeline('),
    ('impersonation')
  ) as t(marker)
)
select marker, count(a.def) as hits
from markers m
left join all_objs a on strpos(lower(a.def), lower(m.marker)) > 0
group by marker
order by marker;
```

Результат:
- `app.audit_events`: `0`
- `app.notification_deliveries`: `0`
- `app.notification_matrix_list(`: `0`
- `app.notification_matrix_set(`: `0`
- `app.collect_client_timeline(`: `0`
- `app.collect_specialist_timeline(`: `0`
- `impersonation`: `0`

## 5. Read-only API smoke (`api.punctb.pro`)
Проверка `POST /rest/v1/rpc/user_profile_detail` с anon key:
- HTTP: `401`
- payload: `{"code":"42501", ... "message":"permission denied for function user_profile_detail"}`

Вывод:
- 404 по RPC в текущем состоянии read-only smoke не воспроизведён.
- Ошибки из `content.js` (`resetSearchEnhanceTriggerMode`) классифицированы как шум браузерного расширения, не как runtime платформы.

## 6. Аудит legacy-следов (runtime vs historical)
### Runtime (active)
- `app.audit_event_type` и `app.notification_type`: отсутствуют.
- Role-specific timeline RPC `collect_client_timeline` / `collect_specialist_timeline`: отсутствуют.
- Активные таблицы и RPC: `event_log`, `event_types`, `event_channels`, `event_type_channel_rules`, `event_channel_preferences`, `event_notifications`, `event_notification_deliveries`, `event_timeline_collect`, `event_notification_matrix_list/set`.

### Historical (допустимо)
- Архив миграций и исторические release-записи содержат legacy-термины (`audit_events`, `notification_*`) как ретроспективный контекст.
- В `backend/init/migrations/*.sql` есть pre-cutover миграции с legacy-названиями (например создание/ремедиация до `event_*` rename). Это исторические DDL-следы, не текущий runtime-контракт.
- Эти упоминания не влияют на runtime-контракт.

## 7. Текущее состояние (итог)
- Модель event-centric в runtime восстановлена и подтверждена.
- Критический блокер профиля устранён.
- Канонические `event_*` контракты зафиксированы в документации и active OpenSpec `notifications-core`.
- Остаточные legacy-следы классифицированы как historical/no-runtime.
