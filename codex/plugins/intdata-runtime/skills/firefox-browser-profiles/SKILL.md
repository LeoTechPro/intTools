---
name: firefox-browser-profiles
description: Firefox MCP profiles. Используйте для dedicated Firefox profile launch/browser-proof workflows через intData Runtime.
---

# Firefox MCP profiles

- Используй эту capability-группу только когда задача совпадает с trigger ниже.
- Каждый raw MCP tool описан отдельной карточкой; не вызывай tools, которых нет в карточках.

## Tool cards

### browser_profile_launch
- Когда: нужно запустить dedicated Firefox MCP profile.
- Required inputs: `confirm_mutation`, `issue_context`, `profile`
- Optional/schema inputs: `cwd`, `timeout_sec`, `args`
- Режим: mutating
- Approval / issue requirements: Для mutating/high-risk вызова требуются owner approval, `confirm_mutation=true` и `issue_context=INT-*`; unattended mutation запрещена.
- Не использовать когда: нет нужного контекста, target/profile не подтверждён, требуется production/destructive действие без явной команды владельца, или задача относится к Cabinet.
- Пример вызова: `{"name":"browser_profile_launch","arguments":{"confirm_mutation": true, "issue_context": "INT-226", "profile": "firefox-default"}}`
- Fallback/blocker: если required args неизвестны, MCP вернул policy/config error, или запрос требует mutation без approval, остановиться и записать blocker вместо shell fallback.
