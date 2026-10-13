# Pakistan AI — Universal Provider MVP

A Pakistan-focused AI chatbot with live Wikipedia retrieval, official Pakistani source routing, multilingual answers, Pakistani/visitor modes, and a **provider-agnostic AI backend**.

## What changed in v2

The original MVP was tied to BazaarLink. This version uses a universal provider layer. You choose the active AI service only through `.env`; the chat application, Wikipedia retrieval, prompts, frontend, and source routing stay unchanged.

Built-in presets include:

- Gemini (through its OpenAI-compatible endpoint)
- OpenRouter
- Groq
- xAI / Grok
- BazaarLink
- OpenAI
- DeepSeek
- Together
- Mistral
- Anthropic / Claude (native Messages API adapter)
- Ollama / local OpenAI-compatible server
- `custom` for any other OpenAI-compatible API

> No program can literally support every AI API automatically because some vendors use different request/response protocols. This project covers OpenAI-compatible APIs generically, Anthropic natively, and provides a clean adapter file (`app/services/llm.py`) for adding any other protocol later.

---

## 1. Install

Windows PowerShell:

```powershell
cd C:\Users\NCS\Downloads\pakistan-ai

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Then start the server:

```powershell
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

The health endpoint will show the active provider, API style, model, and whether the provider is configured. It never returns your API key.

---

## 2. Generic `.env` format

The most important settings are:

```env
AI_PROVIDER=custom
AI_API_KEY=PASTE_YOUR_KEY_HERE
AI_BASE_URL=https://provider.example/v1
AI_MODEL=provider-model-name
AI_API_STYLE=openai
AI_AUTH_MODE=bearer
```

For a named provider preset, you normally only need:

```env
AI_PROVIDER=gemini
AI_API_KEY=PASTE_YOUR_KEY_HERE
AI_MODEL=your-model-name
```

The preset supplies its default base URL and authentication style.

---

## 3. Provider examples

### Gemini

```env
AI_PROVIDER=gemini
AI_API_KEY=PASTE_YOUR_GEMINI_KEY_HERE
AI_MODEL=YOUR_GEMINI_MODEL_NAME

AI_API_STYLE=auto
AI_BASE_URL=
AI_AUTH_MODE=auto
```

### OpenRouter

```env
AI_PROVIDER=openrouter
AI_API_KEY=PASTE_YOUR_OPENROUTER_KEY_HERE
AI_MODEL=YOUR_OPENROUTER_MODEL_NAME

AI_API_STYLE=auto
AI_BASE_URL=
AI_AUTH_MODE=auto
```

### Groq

```env
AI_PROVIDER=groq
AI_API_KEY=PASTE_YOUR_GROQ_KEY_HERE
AI_MODEL=YOUR_GROQ_MODEL_NAME
```

### xAI / Grok

```env
AI_PROVIDER=xai
AI_API_KEY=PASTE_YOUR_XAI_KEY_HERE
AI_MODEL=YOUR_GROK_MODEL_NAME
```

### BazaarLink

```env
AI_PROVIDER=bazaarlink
AI_API_KEY=PASTE_YOUR_BAZAARLINK_KEY_HERE
AI_MODEL=auto:free
DISABLE_PAID_FALLBACK=true
```

### Anthropic / Claude

Anthropic uses a different native API, so this project automatically switches to the Anthropic adapter:

```env
AI_PROVIDER=anthropic
AI_API_KEY=PASTE_YOUR_ANTHROPIC_KEY_HERE
AI_MODEL=YOUR_CLAUDE_MODEL_NAME

AI_API_STYLE=auto
AI_AUTH_MODE=auto
```

### Ollama (local, no cloud API key)

Start Ollama separately, then:

```env
AI_PROVIDER=ollama
AI_API_KEY=
AI_MODEL=YOUR_LOCAL_MODEL_NAME
AI_AUTH_MODE=auto
```

The preset points to:

```text
http://127.0.0.1:11434/v1
```

### Any other OpenAI-compatible provider

```env
AI_PROVIDER=custom
AI_API_STYLE=openai
AI_API_KEY=PASTE_PROVIDER_KEY_HERE
AI_BASE_URL=https://your-provider.example/v1
AI_MODEL=provider-model-name
AI_AUTH_MODE=bearer
```

You do not need to edit Python code for an OpenAI-compatible provider.

---

## 4. Providers with unusual requirements

The universal configuration also supports custom headers, query parameters, endpoint paths, and request-body fields.

### Extra headers

```env
AI_EXTRA_HEADERS_JSON={"X-Project-ID":"my-project"}
```

### Query parameters

Useful for APIs that require parameters such as an API version:

```env
AI_QUERY_PARAMS_JSON={"api-version":"2026-01-01"}
```

### Custom endpoint path

The default OpenAI-compatible path is `/chat/completions`.

Override it with:

```env
AI_CHAT_PATH=/my/chat/path
```

### Authentication modes

Supported values:

```text
auto
bearer
x-api-key
api-key
none
```

Example:

```env
AI_AUTH_MODE=api-key
```

### Models that use `max_completion_tokens`

```env
AI_MAX_TOKENS=1100
AI_MAX_TOKENS_FIELD=max_completion_tokens
```

To send no token-limit field:

```env
AI_MAX_TOKENS_FIELD=none
```

### Models that reject `temperature`

```env
AI_SEND_TEMPERATURE=false
```

### Additional request-body fields

```env
AI_EXTRA_BODY_JSON={"top_p":"0.9"}
```

These are merged into the outgoing request body.

---

## 5. Full `.env` starter

```env
AI_PROVIDER=gemini
AI_API_KEY=PASTE_YOUR_API_KEY_HERE
AI_MODEL=YOUR_MODEL_NAME

AI_API_STYLE=auto
AI_BASE_URL=
AI_AUTH_MODE=auto
AI_CHAT_PATH=

AI_EXTRA_HEADERS_JSON={}
AI_QUERY_PARAMS_JSON={}
AI_EXTRA_BODY_JSON={}

AI_TIMEOUT_SECONDS=45
AI_TEMPERATURE=0.25
AI_SEND_TEMPERATURE=true
AI_MAX_TOKENS=1100
AI_MAX_TOKENS_FIELD=max_tokens

DISABLE_PAID_FALLBACK=true

MAX_DAILY_LLM_REQUESTS=45
MAX_REQUESTS_PER_MINUTE_PER_IP=8

WIKIPEDIA_RESULTS=3
WIKIPEDIA_CHARS_PER_PAGE=3200

ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

---

## 6. How requests flow

```text
User
  |
  v
FastAPI backend
  |
  +--> Wikipedia retrieval
  |
  +--> Official Pakistan source routing
  |
  v
Universal AI Provider Layer
  |
  +--> OpenAI-compatible adapter
  |      Gemini / OpenRouter / Groq / xAI / BazaarLink /
  |      OpenAI / DeepSeek / Together / Mistral / custom
  |
  +--> Anthropic adapter
  |
  +--> Local OpenAI-compatible service (for example Ollama)
  |
  v
Answer + sources + warnings
```

---

## 7. Security

- Keep `.env` server-side only.
- Never paste API keys into `app/static/app.js` or `index.html`.
- Never commit `.env` to Git.
- If a key has been posted publicly or in a chat, rotate/revoke it and create a new one.
- The frontend talks only to your FastAPI backend; it never receives the provider secret.

---

## 8. Project structure

```text
pakistan-ai/
├── .env.example
├── .gitignore
├── Dockerfile
├── README.md
├── requirements.txt
└── app/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── models.py
    ├── data/
    │   └── official_sources.json
    ├── services/
    │   ├── __init__.py
    │   ├── llm.py
    │   ├── prompt.py
    │   ├── source_router.py
    │   └── wikipedia.py
    └── static/
        ├── app.js
        ├── index.html
        └── styles.css
```

The main provider abstraction is in `app/services/llm.py`. To add a genuinely non-compatible API later, add one adapter there rather than changing your Pakistan AI logic everywhere else.
