from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.libs.embedding.dashscope_embedding import DashScopeEmbedding
from src.libs.embedding.embedding_factory import EmbeddingFactory
from src.libs.llm import DashScopeLLM, LLMFactory, Message
from src.libs.reranker.dashscope_reranker import DashScopeReranker
from src.libs.reranker.reranker_factory import RerankerFactory


@dataclass
class _EmbeddingSettings:
    provider: str = "dashscope"
    model: str = "text-embedding-v4"
    dimensions: int = 1024
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class _LLMSettings:
    provider: str = "dashscope"
    model: str = "qwen3.5-flash"
    temperature: float = 0.0
    max_tokens: int = 1024
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


@dataclass
class _RerankSettings:
    enabled: bool = True
    provider: str = "dashscope"
    model: str = "qwen3-rerank"
    top_k: int = 2
    base_url: str = "https://dashscope.aliyuncs.com"


@dataclass
class _Settings:
    embedding: _EmbeddingSettings = field(default_factory=_EmbeddingSettings)
    llm: _LLMSettings = field(default_factory=_LLMSettings)
    rerank: _RerankSettings = field(default_factory=_RerankSettings)


def _mock_response(payload: dict[str, Any], status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = "mock response"
    return response


def test_dashscope_embedding_requires_env_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        DashScopeEmbedding(_Settings())


def test_dashscope_embedding_embed_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    embedding = DashScopeEmbedding(_Settings())

    with patch("httpx.Client") as client_class:
        post = client_class.return_value.__enter__.return_value.post
        post.return_value = _mock_response(
            {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            }
        )

        vectors = embedding.embed(["hello", "world"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "text-embedding-v4"
    assert payload["dimensions"] == 1024


def test_dashscope_llm_chat_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    llm = DashScopeLLM(_Settings())

    with patch("httpx.Client") as client_class:
        post = client_class.return_value.__enter__.return_value.post
        post.return_value = _mock_response(
            {
                "model": "qwen3.5-flash",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 3},
            }
        )

        response = llm.chat([Message(role="user", content="hello")])

    assert response.content == "ok"
    assert response.model == "qwen3.5-flash"
    assert post.call_args.kwargs["json"]["model"] == "qwen3.5-flash"


def test_dashscope_reranker_maps_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    reranker = DashScopeReranker(_Settings())

    with patch("httpx.Client") as client_class:
        post = client_class.return_value.__enter__.return_value.post
        post.return_value = _mock_response(
            {
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.92},
                        {"index": 0, "relevance_score": 0.31},
                    ]
                }
            }
        )

        ranked = reranker.rerank(
            "battery",
            [{"id": "a", "text": "keyboard"}, {"id": "b", "text": "battery"}],
        )

    assert [item["id"] for item in ranked] == ["b", "a"]
    assert ranked[0]["rerank_score"] == 0.92
    assert post.call_args.kwargs["json"]["model"] == "qwen3-rerank"


def test_factories_create_dashscope_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")

    embedding = EmbeddingFactory.create(_Settings())
    llm = LLMFactory.create(_Settings())
    reranker = RerankerFactory.create(_Settings())

    assert isinstance(embedding, DashScopeEmbedding)
    assert isinstance(llm, DashScopeLLM)
    assert isinstance(reranker, DashScopeReranker)
