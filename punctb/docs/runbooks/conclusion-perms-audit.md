# Аудит conclusion perms/functions

Дата: 2026-02-22  
Контур: `backend + web` (локальный runtime PunctB)

## 1. Канонический источник истины
- Хранилище заключений: `app.user_conclusions`.
- Legacy-таблица `app.conclusions`: выведена из актуального runtime-контракта; в активном migration-дереве переходные steps сохраняются до cleanup-миграции `20260222190000_conclusions_contract_cleanup.sql`, где таблица фактически удаляется.
- Публичный рендер заключения: только через `app.fetch_conclusion_public(...)` с фильтром `issued|viewed` и `removed_at IS NULL`.

## 2. Канонические permissions
- `conclusions:read` — чтение заключений по scope `self|hierarchy|all`.
- `conclusions:edit` — управление заключениями по scope `self|hierarchy|all` (create/edit/status/email/soft-delete).
- `conclusions:deleted:view` — видимость удалённых заключений.
- `conclusions:deleted:restore` — восстановление удалённых заключений.

### 2.1. Где проверяются permissions
- `conclusions:read|edit`:
  - DB: `app.current_user_can_access_conclusion_row(..., false)` + RLS policy `conclusions read by scope`.
  - Frontend: `hasAnyConclusionsViewPerms(...)`, `ConclusionGuard`, `Sidebar`.
- `conclusions:edit`:
  - DB: `app.current_user_can_access_conclusion_row(..., true)` + policy `conclusions manage by scope`.
  - RPC/Edge: `conclusion_update_status`, `conclusion_soft_delete`, `conclusion-actions`.
  - Frontend: viewer/list action-buttons.
- `conclusions:deleted:view`:
  - DB: restrictive policy `conclusions deleted visibility`.
  - Frontend: режим показа удалённых в списке.
- `conclusions:deleted:restore`:
  - DB: `conclusion_restore` + `conclusion_status_guard` (restore-переход).
  - Frontend: кнопка `Восстановить` в viewer/list.

## 3. RLS и ACL по `app.user_conclusions`
### 3.1. Политики
- `conclusions read by scope` (SELECT):
  - `USING app.current_user_can_access_conclusion_row(specialist_id, client_id, false)`.
- `conclusions manage by scope` (ALL):
  - `USING/WITH CHECK app.current_user_can_access_conclusion_row(specialist_id, client_id, true)`.
- `conclusions deleted visibility` (RESTRICTIVE SELECT):
  - разрешает удалённые только для `conclusions:deleted:view` или `rls=system`.

### 3.2. ACL-функции
- `app.current_user_can_access_conclusion_row(uuid, uuid, boolean)`:
  - EXECUTE: `authenticated`, `service_role`, `authenticator`.
- `app.conclusion_update_status(...)`, `app.conclusion_soft_delete(...)`, `app.conclusion_restore(...)`:
  - EXECUTE: `authenticated`, `service_role`.

## 4. RPC/DB функции: кто вызывает и зачем
- `app.fetch_conclusion_public(p_conclusion_id uuid)`:
  - вызывают `web` public/client routes (`/conclusions/:id`, `/:slug/conclusion`).
  - отдаёт только не удалённые `issued|viewed` для public/client; workspace получает доступ по scope helper.
- `app.conclusion_update_status(p_conclusion_id uuid, p_status)`:
  - вызывают workspace viewer/list кнопки.
  - ручные переходы: `draft -> issued|archived`, `issued|viewed -> archived`, `archived (removed_at IS NULL) -> issued`.
  - запреты: ручной `superseded`, ручной `viewed`, любое изменение для `removed_at IS NOT NULL`.
- `app.conclusion_soft_delete(p_conclusion_id uuid)`:
  - вызывают workspace кнопки `Удалить`.
  - проставляет `removed_at/removed_by`, `status='archived'`, `deleted_prev_status`.
- `app.conclusion_restore(p_conclusion_id uuid)`:
  - вызывают workspace кнопки `Восстановить`.
  - очищает `removed_at/removed_by`, возвращает `status` из `deleted_prev_status` (fallback `archived`), чистит `deleted_prev_status`.
- `app.conclusion_mark_viewed(p_conclusion_id uuid)`:
  - вызывается client-flow при просмотре опубликованного заключения.

## 5. Edge функции
- `backend/functions/conclusion-actions/index.ts`:
  - контракт: `action=send_email` only.
  - доступ: `conclusions:edit` или `rls=system`.
  - отправка разрешена только для статусов `issued|viewed`.

## 6. Контракт переходов статусов
- Допустимые статусы: `draft`, `issued`, `viewed`, `archived`, `superseded`.
- Автоматические переходы:
  - `issued|viewed -> superseded` для предыдущих документов клиента при публикации нового `issued` (триггер).
  - `issued -> viewed` только клиентским просмотром.
- Ручные переходы (workspace/system):
  - `draft -> issued|archived`.
  - `issued|viewed -> archived`.
  - `archived -> issued`, если `removed_at IS NULL`.
- Заблокированные случаи:
  - ручной `superseded`;
  - status-update для удалённого (`removed_at IS NOT NULL`) вне restore-потока;
  - смена статуса для `superseded`.

## 7. Frontend-контракт (гейты и UI)
- Доступ к conclusion-разделу: только `conclusions:read|conclusions:edit` (не любой `conclusions:*`).
- `/conclusions/:id`:
  - status-select удалён;
  - статусы управляются action-кнопками в toolbar.
- Матрица действий viewer:
  - `draft`: `Опубликовать`, `Удалить`.
  - `issued|viewed`: `Архивировать`, `Удалить`.
  - `archived` без удаления: `Опубликовать`, `Удалить`.
  - `archived` с удалением: `Восстановить` (только `conclusions:deleted:restore`).

## 8. Удалённые/устаревшие сущности
- Источник дублирования переведён в cleanup-контур: `app.conclusions` и его grants/policies/triggers остаются только как переходный migration-step до финального drop в `20260222190000_conclusions_contract_cleanup.sql`.
- Удалён ручной выбор технического статуса `superseded`.
- Статусный select в header viewer заменён action-кнопками.
