---
name: ssh
description: Runtime SSH routes. Используйте ssh_resolve как единую canonical intData Runtime transport surface.
---

# Runtime SSH routes

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### ssh_resolve
- Когда: нужно read-only понять SSH route для logical host.
- Required inputs: `host`
- Optional/schema inputs: `cwd`, `timeout_sec`, `mode`, `json`, `destination_only`
- Режим: read-only
- Approval / issue requirements: Не требуется для read-only вызова. Если команда превращается в запись, остановиться и получить owner approval.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"ssh_resolve","arguments":{"host": "dev", "json": true}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
