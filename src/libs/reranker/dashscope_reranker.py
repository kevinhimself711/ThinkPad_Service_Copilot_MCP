"""DashScope/Bailian text reranker provider."""

from __future__ import annotations

import os
from typing import Any

from src.libs.reranker.base_reranker import BaseReranker


class DashScopeRerankerError(RuntimeError):
    """Raised when DashScope rerank calls fail."""


class DashScopeReranker(BaseReranker):
    """Reranker provider for Alibaba Cloud Model Studio DashScope."""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com"
    DEFAULT_MODEL = "qwen3-rerank"

    def __init__(
        self,
        settings: Any,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.settings = settings
        self.model = getattr(settings.rerank, "model", None) or self.DEFAULT_MODEL
        self.top_k = int(getattr(settings.rerank, "top_k", 5) or 5)
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("DashScope API key not provided. Set DASHSCOPE_API_KEY.")

        settings_base_url = getattr(settings.rerank, "base_url", None)
        self.base_url = (base_url or settings_base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(kwargs.get("timeout", 60.0))

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        trace: Any | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Rerank candidate records using DashScope text rerank."""

        self.validate_query(query)
        self.validate_candidates(candidates)
        if len(candidates) == 1:
            return list(candidates)

        documents = [str(candidate.get("text", candidate.get("content", ""))) for candidate in candidates]
        payload = {
            "model": kwargs.get("model", self.model),
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": int(kwargs.get("top_k", self.top_k)),
                "return_documents": False,
            },
        }
        response_data = self._post_json("/api/v1/services/rerank/text-rerank/text-rerank", payload)
        try:
            results = response_data["output"]["results"]
        except (KeyError, TypeError) as exc:
            raise DashScopeRerankerError("Failed to parse DashScope rerank response") from exc

        reranked: list[dict[str, Any]] = []
        used_indexes: set[int] = set()
        for item in results:
            index = int(item["index"])
            score = float(item.get("relevance_score", item.get("score", 0.0)))
            if 0 <= index < len(candidates):
                candidate = dict(candidates[index])
                candidate["rerank_score"] = score
                reranked.append(candidate)
                used_indexes.add(index)

        for index, candidate in enumerate(candidates):
            if index not in used_indexes:
                fallback = dict(candidate)
                fallback["rerank_score"] = float(fallback.get("score", 0.0))
                reranked.append(fallback)

        reranked.sort(key=lambda candidate: candidate.get("rerank_score", 0.0), reverse=True)
        return reranked[: int(kwargs.get("top_k", self.top_k))]

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
            raise DashScopeRerankerError(f"DashScope rerank request failed: {exc}") from exc

        if response.status_code != 200:
            raise DashScopeRerankerError(
                f"DashScope rerank API error (HTTP {response.status_code}): {response.text}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise DashScopeRerankerError("DashScope rerank response is not valid JSON") from exc
