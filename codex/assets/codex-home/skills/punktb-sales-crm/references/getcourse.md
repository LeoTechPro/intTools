# GetCourse и LMS

## API

Использовать MCP `getcourse`:

- health и каталог: `getcourse_health`, `getcourse_groups_list`;
- выгрузки: `getcourse_*_export_start`, затем `*_wait` или `getcourse_export_get`;
- произвольное чтение: только `getcourse_raw_get` под `/pl/api/account/`;
- import/update выполнять только по точному запросу пользователя и с предусмотренным подтверждением.

API не доказывает, что видео или урок был пройден. Для учебных материалов использовать браузер.

## Постоянный браузерный вход

Credential profile называется `punktb-getcourse`; пароль хранится в зашифрованном auth vault `agent-browser`. Не читать и не выводить его.

VDS-профиль:

```bash
npx -y agent-browser --profile /home/agents/.hermes/browser-profiles/punkt-b --session punktb-lms auth login punktb-getcourse
npx -y agent-browser --profile /home/agents/.hermes/browser-profiles/punkt-b --session punktb-lms open https://lms.punkt-b.pro/teach/control
```

ПК-профиль:

```powershell
npx.cmd -y agent-browser --profile D:\int\tools\.runtime\browser-profiles\punkt-b --session punktb-lms auth login punktb-getcourse
npx.cmd -y agent-browser --profile D:\int\tools\.runtime\browser-profiles\punkt-b --session punktb-lms open https://lms.punkt-b.pro/teach/control
```

Если профиль уже авторизован, начинать сразу со второй команды. Для навигации использовать команды `snapshot`, `click`, `get text`, `download`. Не читать cookies/storage и не печатать значения полей входа.

Рабочий домен: `lms.punkt-b.pro`. Старый `lms.punctb.pro` считать legacy-ссылкой и не использовать как источник доступа.
