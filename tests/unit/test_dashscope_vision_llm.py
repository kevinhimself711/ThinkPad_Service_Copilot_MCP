from __future__ import annotations

import pytest

from src.libs.llm.dashscope_vision_llm import DashScopeVisionLLM
from src.libs.llm.llm_factory import LLMFactory


class _LLMSettings:
    provider = "dashscope"
    model = "qwen3.5-flash"
    temperature = 0.0
    max_tokens = 4096
    api_key = None
    azure_endpoint = None
    api_version = None


class _VisionSettings:
    enabled = True
    provider = "dashscope"
    model = "qwen-vl-max"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key = None
    azure_endpoint = None
    deployment_name = None
    api_version = None
    max_image_size = 2048


class _Settings:
    llm = _LLMSettings()
    vision_llm = _VisionSettings()


def test_dashscope_vision_provider_is_registered():
    assert "dashscope" in LLMFactory.list_vision_providers()


def test_dashscope_vision_reads_key_from_env(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-not-real")
    llm = DashScopeVisionLLM(_Settings())
    assert llm.api_key == "sk-test-not-real"
    assert llm.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert llm.model == "qwen-vl-max"
    assert llm._use_azure_auth is False


def test_dashscope_vision_raises_without_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="DashScope API key"):
        DashScopeVisionLLM(_Settings())


def test_factory_creates_dashscope_vision_from_settings(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-not-real")
    llm = LLMFactory.create_vision_llm(_Settings())
    assert isinstance(llm, DashScopeVisionLLM)
    assert llm.model == "qwen-vl-max"
