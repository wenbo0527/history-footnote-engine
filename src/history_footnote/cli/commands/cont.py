"""🆕 v2.10.9 cmd_continue — 继续最近一次"""
from __future__ import annotations

import sys

from history_footnote.cli.era_loader import load_era_config
from history_footnote.cli.llm_factory import make_llm


def cmd_continue(
    era_id: str | None = None,
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """继续最近一次游戏"""
    from history_footnote.storage import DEFAULT_SAVE_ROOT, SaveManager

    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    session = save_manager.find_latest_session(era_id=era_id)

    if session is None:
        if era_id:
            print(f"[ERROR] 找不到{era_id}的存档")
        else:
            print("[ERROR] 没有任何存档可继续")
        sys.exit(1)

    # 加载 auto.json
    loaded = save_manager.load_state(session, "auto")
    if loaded is None:
        print(f"[ERROR] {session.session_id} 没有auto.json")
        sys.exit(1)

    print(f"[INFO] 继续session: {session.session_id}")
    print(f"[INFO] 加载回合{loaded.get('round_number')} {loaded.get('current_date')}")

    era_id = loaded.get("era_id", session.era_id)
    try:
        config = load_era_config(era_id)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    llm = make_llm(
        config, provider=provider, model=model, api_key=api_key,
        base_url=base_url, purpose="dm",
    )

    from history_footnote.game import GameLoop

    game = GameLoop(
        era_id=era_id,
        era_config=config,
        llm_model=llm,
        session=session,
        load_state_data=loaded,
    )
    game.run()