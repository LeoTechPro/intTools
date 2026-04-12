# failover-failback-checklist

## Failover

1. Зафиксировать incident window и owner команду.
2. Остановить/ограничить primary writes (fencing).
3. Promotе DR instance.
4. Переключить runtime env/DSN на DR endpoint.
5. Переключить DNS/traffic.
6. Проверить health endpoints и smoke.

## Failback

1. Восстановить primary.
2. Re-seed primary из актуального DR snapshot.
3. Синхронно переключить traffic обратно.
4. Повторно включить обычный replication flow.

## Anti split-brain

- запрет двойного writable primary.
- явная фиксация active primary в runbook/incident log.
