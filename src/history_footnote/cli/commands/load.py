"""🆕 v2.10.9 cmd_load — 加载指定 session+slot"""
from __future__ import annotations

import sys

from history_footnote.cli.era_loader import load_era_config
from history_footnote.cli.llm_factory import make_llm


def cmd_load(
    session_id: str,
    slot: str = "auto",
    provider: str = "mock",
    model: str = "",
    api_key: str = "",
    base_url: str = "",
) -> None:
    """加载指定 session 的指定 slot"""
    from history_footnote.storage import DEFAULT_SAVE_ROOT, SaveManager

    save_manager = SaveManager(DEFAULT_SAVE_ROOT)
    session = save_manager.find_session(session_id)

    if session is None:
        print(f"[ERROR] 找不到session: {session_id}")
        sys.exit(1)

    loaded = save_manager.load_state(session, slot)
    if loaded is None:
        print(f"[ERROR] {session_id} 的 {slot} 没有存档")
        sys.exit(1)

    print(f"[INFO] 加载session: {session_id} slot={slot}")
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