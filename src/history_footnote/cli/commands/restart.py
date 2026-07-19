"""🆕 v2.10.9 cmd_restart — 同身份重开"""
from __future__ import annotations

import sys

from history_footnote.cli.era_loader import load_era_config
from history_footnote.cli.llm_factory import make_llm, print_provider_info


def cmd_restart(
    era_id: str,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """同身份重开（创建新的 session，state 完全重置）"""
    try:
        config = load_era_config(era_id)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except ValueError as e:
        # 🆕 v2.10.9：era.json schema 错误
        print(f"[ERROR] {e}")
        sys.exit(1)

    print(f"[INFO] 同身份重开: {config.get('era_name', era_id)}")
    print_provider_info(provider)

    llm = make_llm(
        config, provider=provider, model=model, api_key=api_key,
        base_url=base_url, purpose="dm",
    )

    from history_footnote.game import GameLoop

    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
    )
    print(f"[INFO] 新session: {game.session.session_id}")
    game.run()