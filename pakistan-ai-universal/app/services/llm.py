from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderPreset:
    style: str
    base_url: str
    auth_mode: str = "bearer"
    chat_path: str = ""
    headers: dict[str, str] = field(default_factory=dict)


# These are conveniences only. You can always set AI_PROVIDER=custom and
# provide your own AI_BASE_URL, AI_MODEL, AI_API_STYLE and AI_AUTH_MODE.
PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "openai": ProviderPreset("openai", "https://api.openai.com/v1"),
    "gemini": ProviderPreset("openai", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "openrouter": ProviderPreset("openai", "https://openrouter.ai/api/v1"),
    "groq": ProviderPreset("openai", "https://api.groq.com/openai/v1"),
    "xai": ProviderPreset("openai", "https://api.x.ai/v1"),
    "grok": ProviderPreset("openai", "https://api.x.ai/v1"),
    "bazaarlink": ProviderPreset("openai", "https://api.bazaarlink.ai/v1"),
    "deepseek": ProviderPreset("openai", "https://api.deepseek.com/v1"),
    "together": ProviderPreset("openai", "https://api.together.xyz/v1"),
    "mistral": ProviderPreset("openai", "https://api.mistral.ai/v1"),
    "ollama": ProviderPreset("openai", "http://127.0.0.1:11434/v1", auth_mode="none"),
    "anthropic": ProviderPreset(
        "anthropic",
        "https://api.anthropic.com/v1",
        auth_mode="x-api-key",
        headers={"anthropic-version": "2023-06-01"},
    ),
    "claude": ProviderPreset(
        "anthropic",
        "https://api.anthropic.com/v1",
        auth_mode="x-api-key",
        headers={"anthropic-version": "2023-06-01"},
    ),
}


@dataclass
class AIProviderConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    style: str
    auth_mode: str
    chat_path: str
    extra_headers: dict[str, str]
    query_params: dict[str, str]
    timeout_seconds: float
    temperature: float
    max_tokens: int
    max_tokens_field: str
    send_temperature: bool
    extra_body: dict[str, str]
    disable_paid_fallback: bool = True

    @property
    def configured(self) -> bool:
        # Local providers such as Ollama can intentionally use no API key.
        key_ok = bool(self.api_key) or self.auth_mode == "none"
        return bool(self.base_url and self.model and key_ok)


def build_provider_config(settings: Any) -> AIProviderConfig:
    provider = settings.effective_provider.lower().strip() or "custom"
    preset = PROVIDER_PRESETS.get(provider)

    style = settings.ai_api_style.lower().strip()
    if style == "auto":
        style = preset.style if preset else "openai"
    if style not in {"openai", "anthropic"}:
        raise LLMError("AI_API_STYLE must be one of: auto, openai, anthropic.")

    base_url = settings.effective_base_url or (preset.base_url if preset else "")
    auth_mode = settings.ai_auth_mode.lower().strip()
    if auth_mode == "auto":
        auth_mode = preset.auth_mode if preset else "bearer"
    if auth_mode not in {"bearer", "x-api-key", "api-key", "none"}:
        raise LLMError("AI_AUTH_MODE must be one of: auto, bearer, x-api-key, api-key, none.")

    default_path = "/messages" if style == "anthropic" else "/chat/completions"
    chat_path = settings.ai_chat_path.strip() or (preset.chat_path if preset and preset.chat_path else default_path)

    headers: dict[str, str] = {}
    if preset:
        headers.update(preset.headers)
    headers.update(settings.extra_headers)

    # Keep the original BazaarLink free-only behavior, but only when that
    # provider is selected. No provider-specific headers leak elsewhere.
    if provider == "bazaarlink" and settings.disable_paid_fallback:
        headers["X-Free-Fallback"] = "false"

    # Backward compatibility: if an old .env only contains BAZAARLINK_*,
    # use its base URL automatically.
    if provider == "bazaarlink" and not settings.ai_base_url.strip():
        base_url = settings.bazaarlink_base_url.strip() or base_url

    return AIProviderConfig(
        provider=provider,
        api_key=settings.effective_api_key,
        base_url=base_url.rstrip("/"),
        model=settings.effective_model,
        style=style,
        auth_mode=auth_mode,
        chat_path=chat_path if chat_path.startswith("/") else f"/{chat_path}",
        extra_headers=headers,
        query_params=settings.query_params,
        timeout_seconds=settings.ai_timeout_seconds,
        temperature=settings.ai_temperature,
        max_tokens=settings.ai_max_tokens,
        max_tokens_field=settings.ai_max_tokens_field.strip().lower(),
        send_temperature=settings.ai_send_temperature,
        extra_body=settings.extra_body,
        disable_paid_fallback=settings.disable_paid_fallback,
    )


class UniversalLLM:
    """Provider-agnostic LLM client.

    Supports:
    - Any OpenAI-compatible Chat Completions API.
    - Anthropic's native Messages API.
    - Local OpenAI-compatible servers such as Ollama.

    Providers with a different protocol can be added as another adapter
    without changing the rest of the Pakistan AI application.
    """

    def __init__(self, config: AIProviderConfig):
        self.config = config
        if not config.configured:
            missing: list[str] = []
            if not config.base_url:
                missing.append("AI_BASE_URL")
            if not config.model:
                missing.append("AI_MODEL")
            if not config.api_key and config.auth_mode != "none":
                missing.append("AI_API_KEY")
            raise LLMError(
                "AI provider is not configured. Missing: " + ", ".join(missing) + "."
            )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.config.extra_headers}
        if self.config.auth_mode == "bearer":
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.auth_mode == "x-api-key":
            headers["x-api-key"] = self.config.api_key
        elif self.config.auth_mode == "api-key":
            headers["api-key"] = self.config.api_key
        return headers

    @staticmethod
    def _history(history: list[dict[str, str]]) -> list[dict[str, str]]:
        return [
            {"role": item["role"], "content": item["content"]}
            for item in history[-8:]
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ]

    def _openai_payload(
        self, system_prompt: str, user_prompt: str, history: list[dict[str, str]]
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(self._history(history))
        messages.append({"role": "user", "content": user_prompt})
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }
        if self.config.send_temperature:
            payload["temperature"] = self.config.temperature
        if self.config.max_tokens_field not in {"", "none"}:
            payload[self.config.max_tokens_field] = self.config.max_tokens
        payload.update(self.config.extra_body)
        return payload

    def _anthropic_payload(
        self, system_prompt: str, user_prompt: str, history: list[dict[str, str]]
    ) -> dict[str, Any]:
        messages = self._history(history)
        messages.append({"role": "user", "content": user_prompt})
        payload: dict[str, Any] = {
            "model": self.config.model,
            "system": system_prompt,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
        }
        if self.config.send_temperature:
            payload["temperature"] = self.config.temperature
        payload.update(self.config.extra_body)
        return payload

    @staticmethod
    def _extract_openai(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("The AI provider returned an unexpected OpenAI-compatible response.") from exc

        if isinstance(content, str):
            return content.strip()

        # Some compatible providers return rich content parts instead of a string.
        if isinstance(content, list):
            pieces: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        pieces.append(text)
            return "\n".join(pieces).strip()

        return ""

    @staticmethod
    def _extract_anthropic(data: dict[str, Any]) -> str:
        content = data.get("content")
        if not isinstance(content, list):
            raise LLMError("The AI provider returned an unexpected Anthropic response.")
        pieces: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                pieces.append(part["text"])
        return "\n".join(pieces).strip()

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return response.text[:400].strip()
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict):
                for key in ("message", "detail", "type"):
                    if error.get(key):
                        return str(error[key])[:400]
            for key in ("message", "detail"):
                if body.get(key):
                    return str(body[key])[:400]
        return ""

    async def answer(self, system_prompt: str, user_prompt: str, history: list[dict[str, str]]) -> str:
        if self.config.style == "anthropic":
            payload = self._anthropic_payload(system_prompt, user_prompt, history)
        else:
            payload = self._openai_payload(system_prompt, user_prompt, history)

        url = f"{self.config.base_url}{self.config.chat_path}"
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    url,
                    headers=self._headers(),
                    params=self.config.query_params or None,
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise LLMError(
                f"Could not reach the configured AI provider ({self.config.provider}). "
                "Check your internet connection, AI_BASE_URL and provider settings."
            ) from exc

        if response.status_code == 429:
            raise LLMError(
                f"The AI provider ({self.config.provider}) is rate-limited or its quota is exhausted."
            )
        if response.is_error:
            detail = self._error_detail(response)
            suffix = f" {detail}" if detail else ""
            raise LLMError(
                f"The AI provider ({self.config.provider}) returned HTTP {response.status_code}.{suffix}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("The AI provider returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise LLMError("The AI provider returned an unexpected response format.")

        content = (
            self._extract_anthropic(data)
            if self.config.style == "anthropic"
            else self._extract_openai(data)
        )
        if not content:
            raise LLMError("The AI provider returned an empty answer.")
        return content
