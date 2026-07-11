"""🆕 v2.9.x W43: 多 LLM provider 兼容性测试

注意：ChatOpenAI/ChatAnthropic 在 llm_providers.py 中是函数本地 import，
需要 patch 真实来源（langchain_openai.ChatOpenAI / langchain_anthropic.ChatAnthropic）
"""
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_W43_001_mock_provider_returns_mock_dm():
    """mock provider 返回 MockDMChatModel"""
    from history_footnote.llm_providers import make_llm
    from history_footnote.mock_llm import MockDMChatModel
    llm = make_llm(provider="mock", era_config={"era_id": "test"})
    assert isinstance(llm, MockDMChatModel)
    return True


def test_W43_002_openai_provider_returns_chat_openai():
    """openai provider 返回 ChatOpenAI 实例"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(provider="openai", model="gpt-4o", api_key="sk-test")
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["api_key"] == "sk-test"
        return True


def test_W43_003_anthropic_provider_returns_chat_anthropic():
    """anthropic provider 返回 ChatAnthropic 实例"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(provider="anthropic", model="claude-3-5-sonnet", api_key="sk-test")
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["model"] == "claude-3-5-sonnet"
        assert call_kwargs["api_key"] == "sk-test"
        return True


def test_W43_004_minimax_anthropic_uses_base_url():
    """minimax-anthropic provider 用 base_url 含 minimaxi"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(provider="minimax-anthropic", model="MiniMax-Text-01", api_key="sk-test")
        call_kwargs = mock_cls.call_args.kwargs
        assert "minimaxi" in call_kwargs.get("base_url", "").lower()
        return True


def test_W43_005_minimax_openai_uses_base_url():
    """minimax-openai provider 用 base_url 含 minimaxi"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(provider="minimax-openai", model="MiniMax-Text-01", api_key="sk-test")
        call_kwargs = mock_cls.call_args.kwargs
        assert "minimaxi" in call_kwargs.get("base_url", "").lower()
        return True


def test_W43_006_deepseek_uses_base_url():
    """deepseek provider 用 base_url 含 deepseek"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(provider="deepseek", model="deepseek-chat", api_key="sk-test")
        call_kwargs = mock_cls.call_args.kwargs
        assert "deepseek" in call_kwargs.get("base_url", "").lower()
        return True


def test_W43_007_custom_provider_accepts_base_url():
    """custom provider 接受自定义 base_url（moonshot 等 OpenAI 兼容）"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        custom_url = "https://api.moonshot.cn/v1"
        make_llm(
            provider="custom",
            model="moonshot-v1-8k",
            api_key="sk-test",
            base_url=custom_url,
        )
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["base_url"] == custom_url
        assert call_kwargs["model"] == "moonshot-v1-8k"
        return True


def test_W43_008_unknown_provider_raises():
    """未知 provider 抛 ValueError"""
    from history_footnote.llm_providers import make_llm
    with pytest.raises(ValueError) as exc_info:
        make_llm(provider="unknown-fake-provider", api_key="sk-test")
    assert "provider" in str(exc_info.value).lower() or "unknown" in str(exc_info.value).lower()
    return True


def test_W43_009_api_key_from_env_when_empty():
    """api_key 为空时从环境变量读"""
    from history_footnote.llm_providers import make_llm
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            make_llm(provider="openai", model="gpt-4o-mini")
            call_kwargs = mock_cls.call_args.kwargs
            assert call_kwargs["api_key"] == "sk-env-key"
            return True


def test_W43_010_extra_kwargs_passed_through():
    """extra_kwargs 透传给 LLM"""
    from history_footnote.llm_providers import make_llm
    with patch("langchain_openai.ChatOpenAI") as mock_cls:
        mock_cls.return_value = MagicMock()
        make_llm(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test",
            extra_kwargs={"temperature": 0.7, "max_tokens": 1000},
        )
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.7
        assert call_kwargs.get("max_tokens") == 1000
        return True
