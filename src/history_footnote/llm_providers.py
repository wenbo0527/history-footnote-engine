"""LLM Provider层——支持多种LLM接入

支持：
- mock: Mock LLM（用于开发/测试）
- openai: OpenAI官方（gpt-4o-mini等）
- anthropic: Anthropic官方（claude-3-5-sonnet等）
- minimax-anthropic: Minimax（Anthropic兼容协议，base_url=api.minimaxi.com/anthropic）
- minimax-openai: Minimax（OpenAI兼容协议，base_url=api.minimaxi.com/v1）
- deepseek: DeepSeek（OpenAI兼容协议，base_url=api.deepseek.com，支持思考模式）
- custom: 自定义OpenAI兼容endpoint

设计：所有provider返回LangChain BaseChatModel实例，DM Agent不知道具体是谁。

配置：通过 .env 文件读取 API Key（绝对不要硬编码 Key 到代码或入库！）
"""
from __future__ import annotations

import os
from typing import Any

# 启动时加载 .env（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未装时跳过


def make_llm(
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    extra_kwargs: dict | None = None,
    era_config: dict | None = None,
) -> Any:
    """构造LLM实例

    Args:
        provider: "mock" / "openai" / "anthropic" / "minimax-anthropic" / "minimax-openai" / "deepseek" / "custom"
        model: 模型名称（为空时用provider默认）
        api_key: API Key（为空时从环境变量读）
        base_url: 自定义endpoint（仅custom/minimax-*/deepseek需要）
        extra_kwargs: 透传给LLM的额外参数
        era_config: era配置（mock模式需要，用于生成叙事）

    Returns:
        LangChain BaseChatModel实例
    """
    extra_kwargs = extra_kwargs or {}

    if provider == "mock":
        from history_footnote.mock_llm import MockDMChatModel
        llm = MockDMChatModel(era_config=era_config or {})
        return llm

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "gpt-4o-mini",
            api_key=api_key or os.environ.get("OPENAI_API_KEY"),
            **extra_kwargs,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "claude-3-5-sonnet-20241022",
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
            **extra_kwargs,
        )

    elif provider == "minimax-anthropic":
        # Minimax的Anthropic兼容协议
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model or "MiniMax-M3",
            api_key=api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
            base_url=base_url or "https://api.minimaxi.com/anthropic",
            **extra_kwargs,
        )

    elif provider == "minimax-openai":
        # Minimax的OpenAI兼容协议
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or "MiniMax-M3",
            api_key=api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or "https://api.minimaxi.com/v1",
            **extra_kwargs,
        )

    elif provider == "deepseek":
        # 🆕 v1.7.12 DeepSeek（OpenAI 兼容协议 + 思考模式）
        # 协议参考：https://api-docs.deepseek.com/
        # 用户给定的官方示例：
        #   client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        #   response = client.chat.completions.create(
        #       model="deepseek-v4-pro", ..., reasoning_effort="high",
        #       extra_body={"thinking": {"type": "enabled"}}
        #   )
        # LangChain 透传：reasoning_effort 通过 model_kwargs 传；extra_body 同样通过 model_kwargs
        from langchain_openai import ChatOpenAI
        # 合并思考模式参数（如果未在 extra_kwargs 中显式指定）
        ds_kwargs = {
            "reasoning_effort": "high",
            "extra_body": {"thinking": {"type": "enabled"}},
        }
        # 允许调用方覆盖（通过 extra_kwargs 传入）
        ds_kwargs.update(extra_kwargs or {})
        return ChatOpenAI(
            model=model or "deepseek-v4-pro",
            api_key=api_key or os.environ.get("DEEPSEEK_API_KEY"),
            base_url=base_url or "https://api.deepseek.com",
            **ds_kwargs,
        )

    elif provider == "custom":
        # 自定义OpenAI兼容endpoint
        from langchain_openai import ChatOpenAI
        if not base_url:
            raise ValueError("custom provider需要指定base_url")
        return ChatOpenAI(
            model=model,
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "no-key-needed"),
            base_url=base_url,
            **extra_kwargs,
        )

    else:
        raise ValueError(f"未知provider: {provider}")


def get_provider_info(provider: str) -> dict:
    """获取provider的元信息（用于显示）"""
    info = {
        "mock": {
            "name": "Mock LLM",
            "description": "本地Mock，不调用真实API",
            "env_vars": [],
            "default_model": "mock-dm",
        },
        "openai": {
            "name": "OpenAI",
            "description": "OpenAI官方API（gpt-4o-mini等）",
            "env_vars": ["OPENAI_API_KEY"],
            "default_model": "gpt-4o-mini",
        },
        "anthropic": {
            "name": "Anthropic",
            "description": "Anthropic官方API（claude-3-5-sonnet等）",
            "env_vars": ["ANTHROPIC_API_KEY"],
            "default_model": "claude-3-5-sonnet-20241022",
        },
        "minimax-anthropic": {
            "name": "Minimax (Anthropic兼容)",
            "description": "Minimax MiniMax-M3模型，Anthropic兼容协议，订阅Key",
            "env_vars": ["MINIMAX_API_KEY", "ANTHROPIC_API_KEY"],
            "default_model": "MiniMax-M3",
            "default_base_url": "https://api.minimaxi.com/anthropic",
            "auth": "Token Plan订阅Key（Minimax后台订阅获取）",
        },
        "minimax-openai": {
            "name": "Minimax (OpenAI兼容)",
            "description": "Minimax MiniMax-M3模型，OpenAI兼容协议",
            "env_vars": ["MINIMAX_API_KEY", "OPENAI_API_KEY"],
            "default_model": "MiniMax-M3",
            "default_base_url": "https://api.minimaxi.com/v1",
        },
        "deepseek": {
            "name": "DeepSeek",
            "description": "DeepSeek 模型（OpenAI 兼容 + 思考模式），base_url=api.deepseek.com",
            "env_vars": ["DEEPSEEK_API_KEY"],
            "default_model": "deepseek-v4-pro",
            "default_base_url": "https://api.deepseek.com",
            "features": ["thinking_mode", "reasoning_effort=high"],
        },
        "custom": {
            "name": "Custom OpenAI-compatible",
            "description": "自定义OpenAI兼容endpoint（需要指定base_url）",
            "env_vars": ["OPENAI_API_KEY"],
            "default_model": "（用户指定）",
        },
    }
    return info.get(provider, {})


def list_providers() -> list[str]:
    """列出所有支持的provider"""
    return ["mock", "openai", "anthropic", "minimax-anthropic", "minimax-openai", "deepseek", "custom"]
