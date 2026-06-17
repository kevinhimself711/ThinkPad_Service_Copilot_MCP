"""DashScope (Alibaba Bailian) qwen-vl Vision LLM provider.

DashScope exposes an OpenAI-compatible endpoint, so this provider reuses the
OpenAI vision request/response handling and only overrides credential and
base-URL resolution: the API key comes from the ``DASHSCOPE_API_KEY`` environment
variable (or settings), never from a hard-coded value, and the base URL points at
the DashScope compatible-mode endpoint.
"""

from __future__ import annotations

import os
from typing import Any

from src.libs.llm.openai_vision_llm import OpenAIVisionLLM


class DashScopeVisionLLM(OpenAIVisionLLM):
    """qwen-vl vision provider over the DashScope OpenAI-compatible endpoint."""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "qwen-vl-max"

    def __init__(
        self,
        settings: Any,
        api_key: str | None = None,
        base_url: str | None = None,
        max_image_size: int | None = None,
        **kwargs: Any,
    ) -> None:
        vision_settings = getattr(settings, "vision_llm", None)

        resolved_key = api_key
        if not resolved_key and vision_settings is not None:
            resolved_key = getattr(vision_settings, "api_key", None)
        if not resolved_key:
            resolved_key = os.environ.get("DASHSCOPE_API_KEY")
        if not resolved_key:
            raise ValueError(
                "DashScope API key not provided. Set DASHSCOPE_API_KEY in the "
                "environment, vision_llm.api_key in settings, or pass api_key."
            )

        resolved_base_url = base_url
        if not resolved_base_url and vision_settings is not None:
            resolved_base_url = getattr(vision_settings, "base_url", None)
        if not resolved_base_url:
            resolved_base_url = self.DEFAULT_BASE_URL

        super().__init__(
            settings,
            api_key=resolved_key,
            base_url=resolved_base_url,
            max_image_size=max_image_size,
            **kwargs,
        )

        # OpenAIVisionLLM falls back to settings.llm.model when no vision model is
        # configured; for DashScope vision the correct default is a qwen-vl model,
        # not the text model.
        vision_model = getattr(vision_settings, "model", None) if vision_settings else None
        if not vision_model:
            self.model = self.DEFAULT_MODEL
