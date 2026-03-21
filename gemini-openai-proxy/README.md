# Gemini ↔ OpenAI Proxy

Этот каталог теперь живёт внутри `/int/tools` как internal-vendor copy, а не как
самостоятельный git-репозиторий. Источник происхождения:
`https://inthub.com/Brioch/gemini-openai-proxy` (MIT License, см. `LICENSE`).

Что это означает на практике:

- upstream reference фиксируется в этом README, а не через `origin` в отдельном checkout;
- в `tools` храним только versioned исходники и документацию;
- `.git`, `node_modules/`, `dist/` и прочий runtime/build слой сюда не переносим;
- все локальные доработки дальше ведём уже как часть `LeoTechPro/intTools`.

Локальный OpenAI-compatible proxy для Gemini с опорой на current
`@google/gemini-cli`/`@google/gemini-cli-core` и существующую OAuth-сессию в
`~/.gemini`.

Целевой режим этого репозитория сейчас один:

- ручной запуск;
- только `127.0.0.1`;
- `AUTH_TYPE=oauth-personal`;
- совместимость с chat-completions клиентами уровня Cline/OpenWebUI/curl;
- поддержка text, stream, vision и tool calling.

## Требования

- Node.js 24+;
- валидная локальная Gemini OAuth-сессия, обычно файл
  `~/.gemini/oauth_creds.json`;
- установленный доступ к Gemini через Google account.

## Установка

```bash
npm install
```

## Поддержанный запуск

```bash
AUTH_TYPE=oauth-personal \
HOST=127.0.0.1 \
PORT=11434 \
MODEL=gemini-3-flash-preview \
MODEL_FALLBACK_CHAIN=gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-lite \
npm start
```

Переменные окружения:

- `HOST` — по умолчанию `127.0.0.1`
- `PORT` — по умолчанию `11434`
- `AUTH_TYPE` — по умолчанию `oauth-personal`
- `MODEL` — primary model, по умолчанию `gemini-3-flash-preview`
- `MODEL_FALLBACK_CHAIN` — CSV-цепочка фолбэка, по умолчанию `gemini-2.5-pro,gemini-2.5-flash,gemini-2.5-flash-lite`

Текущая policy этого прокси:

- primary request model: `gemini-3-flash-preview`
- fallback chain: `gemini-2.5-pro -> gemini-2.5-flash -> gemini-2.5-flash-lite`
- если клиент передаёт `body.model`, прокси сначала пробует именно его, затем идёт по configured chain
- фолбэк срабатывает только на ошибки доступности модели: quota/capacity/429/not found

Проверка на этом хосте показала, что `auto`, `auto-gemini-2.5`, `pro`, `flash`
и `flash-lite` для `AUTH_TYPE=oauth-personal` использовать как model id не стоит.

Прокси на этом этапе не предназначен для внешней сети. Если нужен внешний
доступ, это отдельная задача с bind/reverse-proxy/auth/hardening.

## Endpoints

- `GET /healthz`
- `GET /v1/models`
- `POST /v1/chat/completions`

## Быстрые проверки

Проверка здоровья:

```bash
curl http://127.0.0.1:11434/healthz
```

Простой chat completion:

```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "Hello Gemini"}
    ]
  }'
```

Stream:

```bash
curl -N -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Say hello in one short sentence"}
    ]
  }'
```

Tool calling roundtrip:

```bash
curl -X POST http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash-preview",
    "messages": [
      {"role": "user", "content": "What is the weather in Paris?"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "Get weather by city",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {"type": "string"}
            },
            "required": ["city"]
          }
        }
      }
    ]
  }'
```

Следующий ход после получения `tool_calls`:

```json
{
  "model": "gemini-3-flash-preview",
  "messages": [
    {"role": "user", "content": "What is the weather in Paris?"},
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_123",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"city\":\"Paris\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_123",
      "content": "{\"temperature\":18,\"conditions\":\"Cloudy\"}"
    }
  ]
}
```

## Как работает фолбэк

Для каждого запроса прокси собирает chain:

1. `body.model`, если клиент его передал
2. primary model из `MODEL`
3. модели из `MODEL_FALLBACK_CHAIN`

Дубликаты убираются. При ошибках вида quota/capacity/not found прокси
моментально пробует следующую модель. В успешном ответе поле `model`
содержит фактически использованную модель.
