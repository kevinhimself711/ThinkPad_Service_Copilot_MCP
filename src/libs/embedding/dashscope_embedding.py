"""DashScope/Bailian embedding provider."""

from __future__ import annotations

import os
from typing import Any

from src.libs.embedding.base_embedding import BaseEmbedding


class DashScopeEmbeddingError(RuntimeError):
    """Raised when DashScope embedding calls fail."""


class DashScopeEmbedding(BaseEmbedding):
    """Embedding provider for Alibaba Cloud Model Studio DashScope."""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL = "text-embedding-v4"
    DEFAULT_DIMENSIONS = 1024
    MAX_BATCH_SIZE = 10

    def __init__(
        self,
        settings: Any,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.model = getattr(settings.embedding, "model", None) or self.DEFAULT_MODEL
        self.dimensions = getattr(settings.embedding, "dimensions", None) or self.DEFAULT_DIMENSIONS
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DashScope API key not provided. Set DASHSCOPE_API_KEY.")

        settings_base_url = getattr(settings.embedding, "base_url", None)
        self.base_url = (base_url or settings_base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(kwargs.get("timeout", 60.0))
        self.max_retries = int(kwargs.get("max_retries", 3))
        self.retry_backoff_seconds = float(kwargs.get("retry_backoff_seconds", 1.0))
        self.max_batch_size = self.MAX_BATCH_SIZE

    def embed(
        self,
        texts: list[str],
        trace: Any | None = None,
        **kwargs: Any,
    ) -> list[list[float]]:
        """Generate embeddings using the DashScope OpenAI-compatible endpoint."""

        self.validate_texts(texts)
        dimensions = int(kwargs.get("dimensions", self.dimensions))
        payload: dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "input": texts,
            "dimensions": dimensions,
        }
        response_data = self._post_json("/embeddings", payload)
        try:
            embeddings = [item["embedding"] for item in response_data["data"]]
        except (KeyError, TypeError) as exc:
            raise DashScopeEmbeddingError("Failed to parse DashScope embedding response") from exc

        if len(embeddings) != len(texts):
            raise DashScopeEmbeddingError(
                f"Output length mismatch: expected {len(texts)}, got {len(embeddings)}"
            )
        return embeddings

    def get_dimension(self) -> int:
        """Return the configured embedding dimension."""

        return int(self.dimensions)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import time

        import httpx

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        retry_statuses = {429, 500, 502, 503, 504}
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload, headers=headers)
            except httpx.RequestError as exc:
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (2**attempt))
                    continue
                raise DashScopeEmbeddingError(f"DashScope embedding request failed: {exc}") from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise DashScopeEmbeddingError("DashScope embedding response is not valid JSON") from exc

            if response.status_code in retry_statuses and attempt < self.max_retries:
                time.sleep(self.retry_backoff_seconds * (2**attempt))
                continue

            raise DashScopeEmbeddingError(
                f"DashScope embedding API error (HTTP {response.status_code}): {response.text}"
            )

        raise DashScopeEmbeddingError("DashScope embedding request failed after retries")
