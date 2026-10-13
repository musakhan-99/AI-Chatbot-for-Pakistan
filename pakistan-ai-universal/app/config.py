from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Pakistan AI"
    environment: str = "development"

    # Provider-agnostic AI configuration.
    # Use one active provider at a time. Most providers can use the
    # OpenAI-compatible adapter; Anthropic also has a native adapter.
    ai_provider: str = "custom"
    ai_api_style: str = "auto"  # auto | openai | anthropic
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""
    ai_auth_mode: str = "auto"  # auto | bearer | x-api-key | api-key | none
    ai_chat_path: str = ""
    ai_extra_headers_json: str = "{}"
    ai_query_params_json: str = "{}"
    ai_timeout_seconds: float = 45.0
    ai_temperature: float = 0.25
    ai_max_tokens: int = 1100
    ai_max_tokens_field: str = "max_tokens"  # max_tokens | max_completion_tokens | none
    ai_send_temperature: bool = True
    ai_extra_body_json: str = "{}"

    # BazaarLink-specific optional guard. Ignored by other providers.
    disable_paid_fallback: bool = True

    # Legacy variables from the original MVP. They are kept only so an old
    # .env can still boot; new installations should use AI_* variables above.
    bazaarlink_api_key: str = ""
    bazaarlink_base_url: str = "https://api.bazaarlink.ai/v1"
    bazaarlink_model: str = "auto:free"

    max_daily_llm_requests: int = 45
    max_requests_per_minute_per_ip: int = 8
    wikipedia_results: int = 3
    wikipedia_chars_per_page: int = 3200

    allowed_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def effective_provider(self) -> str:
        # Backward compatibility for the first BazaarLink-only project.
        requested = self.ai_provider.strip().lower()
        new_style_configured = bool(self.ai_api_key.strip() or self.ai_base_url.strip() or self.ai_model.strip())
        if requested and not (requested == "custom" and not new_style_configured and self.bazaarlink_api_key):
            return requested
        if self.bazaarlink_api_key:
            return "bazaarlink"
        return requested or "custom"

    @property
    def effective_api_key(self) -> str:
        return self.ai_api_key.strip() or self.bazaarlink_api_key.strip()

    @property
    def effective_base_url(self) -> str:
        return self.ai_base_url.strip()

    @property
    def effective_model(self) -> str:
        return self.ai_model.strip() or (
            self.bazaarlink_model.strip() if self.effective_provider == "bazaarlink" else ""
        )

    @staticmethod
    def _parse_json_object(raw: str, field_name: str) -> dict[str, str]:
        if not raw.strip():
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{field_name} must contain valid JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{field_name} must be a JSON object.")
        return {str(k): str(v) for k, v in value.items()}

    @property
    def extra_headers(self) -> dict[str, str]:
        return self._parse_json_object(self.ai_extra_headers_json, "AI_EXTRA_HEADERS_JSON")

    @property
    def query_params(self) -> dict[str, str]:
        return self._parse_json_object(self.ai_query_params_json, "AI_QUERY_PARAMS_JSON")

    @property
    def extra_body(self) -> dict[str, str]:
        return self._parse_json_object(self.ai_extra_body_json, "AI_EXTRA_BODY_JSON")


@lru_cache
def get_settings() -> Settings:
    return Settings()
