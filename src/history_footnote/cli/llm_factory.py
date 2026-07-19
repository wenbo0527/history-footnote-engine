"""🆕 v2.10.9 LLM 工厂（CLI 共享）

P1-1：从 __main__.py 下沉。多个 cmd_* 都要 make_llm。
"""
from __future__ import annotations

from typing import Any


def make_llm(
    era_config: dict,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    purpose: str = "dm",
) -> Any:
    """构造 LLM

    Args:
        era_config: 时代包配置（Mock 模式需要）
        provider: mock/openai/anthropic/minimax-anthropic/minimax-openai/custom
        model: 模型名（默认用 provider 默认模型）
        api_key: API Key（默认从环境变量）
        base_url: 自定义 endpoint（仅 custom/minimax-*）
        purpose: 🆕 v2.7 默认 dm（温度 0，可重放）；character/lore/...
    """
    from history_footnote.llm.providers import make_llm_for_purpose

    return make_llm_for_purpose(
        purpose=purpose,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        era_config=era_config,
    )


def print_provider_info(provider: str) -> None:
    """打印 LLM provider 详情"""
    from history_footnote.llm.providers import get_provider_info

    info = get_provider_info(provider)
    print(f"[INFO] LLM Provider: {info.get('name', provider)}")
    if info.get("default_model"):
        print(f"[INFO] Model: {info['default_model']} (默认)")