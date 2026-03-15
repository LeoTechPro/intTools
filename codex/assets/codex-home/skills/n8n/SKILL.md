---
name: n8n
description: "Операционный skill для инстанса n8n на n8n.punctb.pro: проверка здоровья, логи, restart/update, backup/restore, nginx/TLS и безопасная работа с workflow через UI/API."
---

# n8n

## Overview

Использовать этот skill, когда пользователь просит настроить, диагностировать, обновить или обслужить `n8n` на сервере `punctb.pro`.
Этот skill покрывает инфраструктурные операции и базовый прикладной контур workflow.

## When To Use

- Установка и эксплуатация `n8n` в Docker.
- Проверка доступности `https://n8n.punctb.pro`.
- Диагностика ошибок выполнения workflow.
- Обновление `n8n` и контроль миграций.
- Backup/restore базы и данных `n8n`.
- Настройка/проверка `nginx` и TLS для `n8n`.

## Working Rules

- Не записывать секреты (`.env`, API keys, пароли) в ответы, markdown или git.
- Перед рискованными операциями явно помечать риск и проверять контекст.
- Для destructive-команд (`dropdb`, удаление `data`, overwrite restore) требовать явное подтверждение владельца.
- Для routine-операций (status/logs/restart/health/update без потери данных) действовать сразу.

## Execution Flow

1. Проверить состояние инстанса по quick-check из `references/punctb-instance.md`.
2. Если проблема инфраструктурная: контейнер -> порт -> nginx -> TLS -> Postgres.
3. Если проблема прикладная: логи `n8n`, состояние execution, credentials и webhook URL.
4. Если нужен апдейт: backup -> pull/up -d -> smoke (`/healthz`, UI login page).
5. Зафиксировать краткий итог: что сделано, что проверено, что осталось.

## Workflow Automation Scope

- Можно выполнять операции уровня сервиса (Docker/nginx/Postgres) полностью.
- Для содержимого бизнес-workflow (логика узлов, внешние API, ключи) при отсутствии данных сначала запросить недостающие параметры один раз.
- При наличии API key `n8n` можно работать через REST API, иначе через UI с аккаунтом владельца.

## Reference

- Всегда читать: `references/punctb-instance.md`.
