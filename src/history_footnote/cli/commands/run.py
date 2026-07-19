"""🆕 v2.10.9 cmd_run — 新游戏"""
from __future__ import annotations

import sys

from history_footnote.cli.era_loader import load_era_config
from history_footnote.cli.character_wizard import ask_character
from history_footnote.cli.llm_factory import make_llm, print_provider_info


def cmd_run(
    era_id: str,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
    skip_character: bool = False,
    validate_schema: bool = True,
    strict_schema: bool = False,
) -> None:
    """运行新游戏

    Args:
        era_id: 时代包ID
        provider: LLM provider（mock/openai/anthropic/minimax-anthropic/minimax-openai/custom）
        model: 模型名（默认用 provider 默认）
        api_key: API Key
        base_url: 自定义 endpoint
        skip_character: 是否跳过角色创建（用默认身份）
        validate_schema: 是否校验 era.json（🆕 v2.10.9，默认 True）
        strict_schema: 严格校验（🆕 v2.10.9，extra 字段也报错）
    """
    try:
        config = load_era_config(era_id, validate=validate_schema, strict=strict_schema)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        # 🆕 v2.10.9：era.json schema 错误 → 友好提示 + 非零退出
        print(f"[ERROR] {e}")
        print("[HINT] 用 --skip-schema-validate 临时绕过校验（不推荐）")
        sys.exit(1)

    print(f"[INFO] 加载时代包: {config.get('era_name', era_id)}")
    print_provider_info(provider)
    if model:
        print(f"[INFO] Model: {model}")

    # 角色创建（v1.1+）
    selected_identity = ""
    if not skip_character and config.get("world", {}).get("player_identities"):
        selected_identity = ask_character(config)
        identity = config["world"]["player_identities"][selected_identity]
        print(f"\n[INFO] 你选择了: {identity.get('label', selected_identity)}")
        gender_cn = "男" if identity.get("gender") == "male" else "女"
        print(f"  性别: {gender_cn} | 角色: {identity.get('role', '')}")

    llm = make_llm(
        config, provider=provider, model=model, api_key=api_key,
        base_url=base_url, purpose="character",
    )

    from history_footnote.game import GameLoop

    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        selected_identity=selected_identity,
    )
    print(f"[INFO] 新建session: {game.session.session_id}")
    game.run()