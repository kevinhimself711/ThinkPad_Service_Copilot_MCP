"""DashScope/Bailian OpenAI-compatible LLM provider."""

from __future__ import annotations

import os
from typing import Any

from src.libs.llm.base_llm import BaseLLM, ChatResponse, Message


class DashScopeLLMError(RuntimeError):
    """Raised when DashScope chat completion calls fail."""


class DashScopeLLM(BaseLLM):
    """Text LLM provider for Alibaba Cloud Model Studio DashScope."""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "qwen3.5-flash"

    def __init__(
        self,
        settings: Any,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.model = getattr(settings.llm, "model", None) or self.DEFAULT_MODEL
        self.default_temperature = float(getattr(settings.llm, "temperature", 0.0))
        self.default_max_tokens = int(getattr(settings.llm, "max_tokens", 2048))
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DashScope API key not provided. Set DASHSCOPE_API_KEY.")

        settings_base_url = getattr(settings.llm, "base_url", None)
        self.base_url = (base_url or settings_base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(kwargs.get("timeout", 60.0))

    def chat(
        self,
        messages: list[Message],
        trace: Any | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a chat completion using the DashScope compatible endpoint."""

        self.validate_messages(messages)
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": kwargs.get("temperature", self.default_temperature),
            "max_tokens": kwargs.get("max_tokens", self.default_max_tokens),
        }
        response_data = self._post_json("/chat/completions", payload)
        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DashScopeLLMError("Failed to parse DashScope chat response") from exc

        return ChatResponse(
            content=str(content),
            model=str(response_data.get("model", payload["model"])),
            usage=response_data.get("usage"),
            raw_response=response_data,
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise DashScopeLLMError(f"DashScope chat request failed: {exc}") from exc

        if response.status_code != 200:
            raise DashScopeLLMError(
                f"DashScope chat API error (HTTP {response.status_code}): {response.text}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise DashScopeLLMError("DashScope chat response is not valid JSON") from exc
